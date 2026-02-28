"""
Search services for web search, combiphar site search, and general GPT responses.
Handles various search strategies and result processing.
"""
import os
import json
import re
import time
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Any, Optional, Set
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin

import requests
from openai import AuthenticationError, RateLimitError, APIError

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BS4_AVAILABLE = False

from app.utils.setting import get_setting_value_by_name
from app.utils.time_provider import get_current_datetime
try:
    from app.services.agent.tools import current_datetime_tool, current_context_tool
except ImportError:
    current_datetime_tool = None
    current_context_tool = None
from app.services.agent.error_handler import ErrorHandler
import app.services.agent.system_prompts as system_prompts

# External dependencies
try:
    from ddgs import DDGS
    from langchain_community.document_loaders import WebBaseLoader, PlaywrightURLLoader
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.tools import Tool
    LANGCHAIN_TOOLS_AVAILABLE = True
    DUCKDUCKGO_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_TOOLS_AVAILABLE = False
    DUCKDUCKGO_AVAILABLE = False
    logging.warning(f"Web search tools not available: {e}. Install ddgs and langchain-community for internet search functionality.")

logger = logging.getLogger('agent.search_service')

class SearchService:
    """
    Handles various search strategies including web search, site-specific search, and LLM-based responses.
    """

    def __init__(self, llm, prompt_service):
        """
        Initialize search service with LLM and prompt service dependencies.
        
        Args:
            llm: Language model instance
            prompt_service: Prompt service for template creation and formatting
        """
        self.llm = llm
        self.prompt_service = prompt_service

        # Generic stopwords for dynamic phrase extraction (language-agnostic core + ID/EN)
        self._stopwords = {
            # Indonesian
            "yang","untuk","dengan","dan","atau","dari","pada","di","ke","sebagai","ini","itu","ada","karena","adalah","tidak","sudah","akan","dalam","agar","bagi","oleh","jika","juga","lebih","kurang","saja","sangat","dapat","bisa","kini","serta","tanpa","namun","tetapi","apa","bagaimana","mengapa","kenapa","berapa","dimana","kapan","apakah","nya","tersebut",
            # English
            "the","a","an","and","or","of","to","in","on","for","as","is","are","was","were","be","been","by","with","at","from","this","that","these","those","it","its","not","can","could","may","might","should","will","would","about","into","than","then","so","such","very","how","what","why","where","when"
        }
        # Tokens/phrases we never want to recycle into enhanced questions
        self._context_blacklist = {
            "tolong","gunakan","kalimat","lain","maksud","paham","detail","detailnya",
            "mohon","harap","harapakan","silakan","please","kindly","explain","clarify",
            "jawab","jawaban","ulang","ulangi","rephrase","restate"
        }

        # Default headers for outbound HTTP calls (used by custom loaders)
        self._http_headers = {
            "User-Agent": os.getenv("USER_AGENT", "combiphar-be/1.0"),
            "Accept": "application/json, text/html;q=0.8"
        }

    @staticmethod
    def _describe_ddgs_error(exc: Any) -> str:
        """Convert noisy DDGS exceptions into terse, user-friendly messages."""
        message = str(exc) if exc else ""
        lowered = message.lower()
        if "remoteprotocolerror" in lowered or "protocol_error" in lowered:
            return "DuckDuckGo menutup koneksi secara tiba-tiba (protocol error)."
        if "timed out" in lowered:
            return "Permintaan ke DuckDuckGo melebihi batas waktu."
        return message or "DuckDuckGo tidak merespons."

    @staticmethod
    def _is_recoverable_ddgs_error(exc: Any) -> bool:
        """Check if the DDGS exception is transient so we can silently ignore it."""
        text = str(exc).lower() if exc else ""
        recoverable_keywords = (
            "remoteprotocolerror",
            "protocol_error",
            "timed out",
            "timeout",
            "ssl",
            "certificate",
            "forbidden",
            "http error",
            "httperror",
            "too many requests",
            "429",
            "no results"
        )
        return any(keyword in text for keyword in recoverable_keywords)

    @staticmethod
    def _is_placeholder_content(value: Any) -> bool:
        """Return True when scraped content is just a placeholder indicating missing data."""
        if not value or not isinstance(value, str):
            return True
        lowered = value.strip().lower()
        if not lowered:
            return True
        placeholder_markers = (
            "content not available",
            "unable to find information",
            "unable to find specific information",
            "no search results found",
            "no search results were found",
            "i was unable to find information",
            "i could not find information",
        )
        return any(marker in lowered for marker in placeholder_markers)

    @staticmethod
    def _build_snippet(text: str, keywords: List[str], limit: int = 320) -> str:
        """Extract a concise snippet containing the given keywords."""
        if not text:
            return ""

        lowered_keys = [kw.lower() for kw in keywords if kw]
        collected: List[str] = []
        total_len = 0

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lowered_line = line.lower()
            if any(key in lowered_line for key in lowered_keys):
                collected.append(line)
                total_len += len(line)
            if total_len >= limit:
                break

        snippet = " ".join(collected).strip()
        if not snippet:
            snippet = text[:limit].strip()
        return snippet

    # -------------------- Combiphar helper utilities --------------------
    @staticmethod
    def _is_combiphar_domain(url: str) -> bool:
        """Return True if the URL targets the main combiphar.com site."""
        try:
            split = urlsplit(url)
        except Exception:
            return False

        host = split.netloc.lower().split(':')[0]
        return host in {"combiphar.com", "www.combiphar.com"}

    @staticmethod
    def _guess_locale_from_path(path: str) -> str:
        """Infer locale code from Combiphar URI path."""
        parts = [segment for segment in path.split('/') if segment]
        if parts:
            first = parts[0].lower()
            if first in {"id", "en"}:
                return first
        return "id"

    @staticmethod
    def _normalize_combiphar_path(path: str) -> Optional[str]:
        """Normalize URL path for Combiphar API queries."""
        if path is None:
            return None
        normalized = path if path.startswith('/') else f"/{path}"
        if normalized == "/":
            return None
        return normalized

    @staticmethod
    def _extract_domains(urls: List[str]) -> List[str]:
        """Extract unique domain patterns (with/without www) from a list of URLs."""
        seen = set()
        domains: List[str] = []
        for raw in urls or []:
            if not isinstance(raw, str):
                continue
            candidate = raw.strip()
            if not candidate:
                continue
            try:
                host = urlsplit(candidate).netloc.lower()
            except Exception:
                continue
            host = host.split(':')[0]
            if not host:
                continue
            options = [host]
            if host.startswith("www."):
                options.append(host[4:])
            for option in options:
                if option and option not in seen:
                    seen.add(option)
                    domains.append(option)
        return domains

    def _combiphar_html_to_text(self, value: str) -> str:
        """Convert HTML snippets to clean text."""
        if not value or not isinstance(value, str):
            return ""

        text = value
        if '<' in value and '>' in value:
            if BS4_AVAILABLE and BeautifulSoup is not None:
                text = BeautifulSoup(value, "html.parser").get_text(separator=" ", strip=True)
            else:
                # Basic tag removal fallback when BeautifulSoup is unavailable
                text = re.sub(r"<[^>]+>", " ", value)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _looks_like_non_text(value: str) -> bool:
        if not value:
            return True
        lowered = value.lower()
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return True
        if re.match(r"^[a-z0-9_\-/.]+$", lowered):
            return True
        if len(value.strip()) <= 2:
            return True
        return False

    @staticmethod
    def _format_combiphar_label(parts: Tuple[str, ...]) -> str:
        cleaned = []
        for part in parts:
            if not part:
                continue
            candidate = str(part).replace('_', ' ').strip()
            if not candidate or candidate.isdigit() or candidate.lower() in {"data", "attributes"}:
                continue
            candidate = re.sub(r"item_(\d+)", lambda m: f"Item {m.group(1)}", candidate, flags=re.IGNORECASE)
            cleaned.append(candidate.title())
        return " > ".join(cleaned)

    def _collect_combiphar_text(self, value: Any, path: Tuple[str, ...], output: List[Tuple[Tuple[str, ...], str]]) -> None:
        """Recursively collect textual fields from Combiphar JSON payloads."""
        skip_keys = {
            "id", "slug", "image", "image_desktop", "image_mobile", "image_footer_desktop",
            "image_footer_mobile", "photo", "cutoff_photo", "thumbnail", "created_at", "updated_at",
            "weight", "link", "url", "page", "per_page", "path", "type", "seo"
        }

        if isinstance(value, dict):
            for key, val in value.items():
                if key is None:
                    continue
                key_lower = str(key).lower()
                if key_lower in skip_keys:
                    continue
                self._collect_combiphar_text(val, path + (str(key),), output)
            return

        if isinstance(value, list):
            for idx, item in enumerate(value, start=1):
                self._collect_combiphar_text(item, path + (f"item_{idx}",), output)
            return

        if isinstance(value, str):
            text = self._combiphar_html_to_text(value)
            if text and not self._looks_like_non_text(text):
                output.append((path, text))

    def _render_combiphar_page(self, page_data: Dict[str, Any]) -> Optional[str]:
        """Convert Combiphar page payload into readable plain text."""
        if not page_data:
            return None

        collected: List[Tuple[Tuple[str, ...], str]] = []
        self._collect_combiphar_text(page_data, tuple(), collected)
        if not collected:
            return None

        seen = set()
        lines: List[str] = []
        for label_parts, text in collected:
            label = self._format_combiphar_label(label_parts)
            key = (label, text)
            if key in seen:
                continue
            seen.add(key)
            if label:
                lines.append(f"{label}: {text}")
            else:
                lines.append(text)

        if not lines:
            return None

        combined = "\n".join(lines)
        return combined[:6000]

    def _fetch_combiphar_content(self, url: str) -> Optional[str]:
        """Fetch Combiphar page content via official backend API."""
        if not self._is_combiphar_domain(url):
            return None

        split = urlsplit(url)
        path = self._normalize_combiphar_path(split.path)
        if not path:
            return None

        locale = self._guess_locale_from_path(path)
        base_api = "https://www.combiphar.com/back/api/v1/"

        try:
            router_resp = requests.get(
                base_api + "webrouter",
                params={"uri": path},
                headers=self._http_headers,
                timeout=10
            )
            router_resp.raise_for_status()
            router_data = router_resp.json()
        except (requests.RequestException, ValueError) as exc:
            logging.warning(f"Combiphar router fetch failed for {url}: {exc}")
            return None

        data_block = router_data.get("data") if isinstance(router_data, dict) else None
        page_info = (
            data_block.get("pages", {}).get("data")
            if isinstance(data_block, dict) else None
        )

        if not isinstance(page_info, dict):
            return None

        page_code = page_info.get("page_code")
        if not page_code:
            return None

        try:
            page_resp = requests.get(
                base_api + "pages/find",
                params={"locale": locale, "pageCode": page_code},
                headers=self._http_headers,
                timeout=10
            )
            page_resp.raise_for_status()
            page_payload = page_resp.json()
        except (requests.RequestException, ValueError) as exc:
            logging.warning(f"Combiphar page fetch failed for {url}: {exc}")
            return None

        page_data = (
            (page_payload.get("data") or {})
            .get("pages", {})
            .get("data")
            if isinstance(page_payload, dict) else None
        )

        if not isinstance(page_data, dict):
            return None

        return self._render_combiphar_page(page_data)

    def _search_combiphar_pages_via_api(
        self,
        websites: List[str],
        query: str,
        max_items: int = 5
    ) -> List[Dict[str, Any]]:
        """Fallback search using Combiphar public API when DDGS returns nothing."""
        sanitized_query = re.sub(r"site:[^\s]+", " ", (query or ""))
        query_tokens = [
            token for token in self._tokenize(sanitized_query)
            if len(token) >= 3 and token not in self._stopwords and token not in {"combiphar", "www", "com", "id", "en"}
        ]

        if not query_tokens:
            logging.info("Combiphar API fallback skipped due to empty query tokens")
            return []

        results: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        main_domains = {"www.combiphar.com", "combiphar.com"}

        try:
            pages_resp = requests.get(
                "https://www.combiphar.com/back/api/v1/pages",
                headers=self._http_headers,
                timeout=10
            )
            pages_resp.raise_for_status()
            pages_payload = pages_resp.json()
            pages_data = (
                (pages_payload.get("data") or {}).get("pages") or {}
            ).get("data") if isinstance(pages_payload, dict) else None
        except (requests.RequestException, ValueError) as exc:
            logging.warning(f"Combiphar API fallback failed to list pages: {exc}")
            pages_data = None

        for base_url in websites or []:
            if len(results) >= max_items:
                break
            if not isinstance(base_url, str) or not base_url.strip():
                continue
            try:
                parsed = urlsplit(base_url)
            except Exception:
                continue

            host = parsed.netloc.lower()
            locale = self._guess_locale_from_path(parsed.path)
            base_prefix = f"{parsed.scheme or 'https'}://{parsed.netloc}"
            locale_path = f"/{locale}" if locale else ""
            base_combined = f"{base_prefix}{locale_path}".rstrip('/') + '/'

            if host in main_domains and isinstance(pages_data, list):
                for page in pages_data:
                    if len(results) >= max_items:
                        break
                    translations = page.get('translated_locales') or {}
                    translation = translations.get(locale) if isinstance(translations, dict) else None
                    if not translation:
                        continue
                    slug = translation.get('slug')
                    title = translation.get('title') or page.get('title') or 'Combiphar Page'
                    if not slug:
                        continue

                    page_url = urljoin(base_combined, slug)
                    if page_url in seen_urls:
                        continue

                    content = self._fetch_combiphar_content(page_url)
                    if not content:
                        continue

                    content_tokens = set(self._tokenize(content))
                    if not content_tokens:
                        continue

                    hits = [token for token in query_tokens if token in content_tokens]
                    if not hits:
                        continue

                    snippet = self._build_snippet(content, hits)
                    seen_urls.add(page_url)
                    results.append({
                        'title': title,
                        'href': page_url,
                        'body': snippet,
                        'score': 0.85 + min(0.1, 0.03 * len(hits))
                    })
            else:
                candidate_urls = self._discover_site_pages(base_combined, query_tokens, limit=max_items * 3)
                for candidate in candidate_urls:
                    if len(results) >= max_items:
                        break
                    if candidate in seen_urls:
                        continue
                    content = self._fetch_generic_site_content(candidate)
                    if not content:
                        continue
                    content_tokens = set(self._tokenize(content))
                    if not content_tokens:
                        continue
                    hits = [token for token in query_tokens if token in content_tokens]
                    if not hits:
                        continue
                    snippet = self._build_snippet(content, hits)
                    title = candidate
                    seen_urls.add(candidate)
                    results.append({
                        'title': title,
                        'href': candidate,
                        'body': snippet,
                        'score': 0.78 + min(0.1, 0.02 * len(hits))
                    })

        if results:
            logging.info(f"Combiphar API fallback produced {len(results)} results for query '{query}'")
        else:
            logging.info(f"Combiphar API fallback found no matches for query '{query}'")

        return results[:max_items]

    # -------------------- Dynamic context helpers --------------------
    def _discover_site_pages(self, base_url: str, query_tokens: List[str], limit: int = 10) -> List[str]:
        """Discover candidate pages from a site via sitemap or heuristics."""
        seen: Set[str] = set()
        candidates: List[str] = []

        sitemap_suffixes = [
            "sitemap.xml",
            "sitemap_index.xml",
            "sitemap-index.xml"
        ]

        base_root = base_url.rstrip('/') + '/'

        for suffix in sitemap_suffixes:
            if len(candidates) >= limit:
                break
            sitemap_url = urljoin(base_root, suffix)
            try:
                resp = requests.get(
                    sitemap_url,
                    headers=self._http_headers,
                    timeout=10
                )
                if resp.status_code >= 400 or len(resp.text) < 10:
                    continue
                tree = ET.fromstring(resp.text)
                for loc in tree.iterfind('.//{*}loc'):
                    url = (loc.text or '').strip()
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    candidates.append(url)
                    if len(candidates) >= limit:
                        break
            except (requests.RequestException, ET.ParseError):
                continue

        if not candidates:
            candidates.append(base_root.rstrip('/'))

        def _priority(target: str) -> Tuple[int, str]:
            lowered = target.lower()
            has_token = any(tok in lowered for tok in query_tokens)
            return (0 if has_token else 1, target)

        candidates.sort(key=_priority)

        return candidates[:limit]

    def _fetch_generic_site_content(self, url: str) -> Optional[str]:
        """Fetch and sanitize HTML content from arbitrary Combiphar-affiliated sites."""
        try:
            resp = requests.get(
                url,
                headers=self._http_headers,
                timeout=10
            )
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as exc:
            logging.debug(f"Generic site fetch failed for {url}: {exc}")
            return None

        text = self._combiphar_html_to_text(html)
        return text if text else None

    def _tokenize(self, text: str) -> List[str]:
        import re
        if not isinstance(text, str):
            text = str(text)
        return re.findall(r"[a-z0-9]+", text.lower())

    def _extract_keyphrases(self, text: str, top_k: int = 8) -> List[str]:
        """RAKE-like keyphrase extraction; no domain rules.
        Splits by stopwords, scores phrases by word degree/frequency.
        """
        import re
        if not text:
            return []
        tokens = self._tokenize(text)
        if not tokens:
            return []
        # Build phrases: sequences of non-stopword tokens
        phrases: List[List[str]] = []
        current: List[str] = []
        for t in tokens:
            if len(t) < 3 or t in self._stopwords:
                if current:
                    phrases.append(current)
                    current = []
            else:
                current.append(t)
        if current:
            phrases.append(current)

        if not phrases:
            return []

        # Word frequency and degree
        freq: Dict[str, int] = {}
        deg: Dict[str, int] = {}
        for p in phrases:
            L = len(p)
            for w in p:
                freq[w] = freq.get(w, 0) + 1
                deg[w] = deg.get(w, 0) + (L - 1)

        # Word score: (deg + freq) / freq
        wscore: Dict[str, float] = {w: (deg.get(w, 0) + freq.get(w, 0)) / max(1, freq.get(w, 0)) for w in freq}

        # Phrase score: sum word scores; prefer 1-3 grams for search compatibility
        pscore: List[Tuple[str, float]] = []
        for p in phrases:
            if len(p) == 0:
                continue
            p2 = p[:3]
            s = sum(wscore.get(w, 0.0) for w in p2)
            phrase_text = " ".join(p2)
            pscore.append((phrase_text, s))

        pscore.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        result: List[str] = []
        for phrase, _ in pscore:
            if phrase not in seen:
                seen.add(phrase)
                result.append(phrase)
            if len(result) >= top_k:
                break
        return result

    def _build_contextual_query(self, question: str, chat_history: Optional[List[Tuple[str, str]]], use_last_n: int = 3, max_phrases: int = 5) -> str:
        """Build a self-contained query by adding dynamic keyphrases from recent conversation."""
        if not chat_history:
            return question
        recent = chat_history[-use_last_n:]
        context_texts = []
        for q, _ in recent:
            if isinstance(q, str):
                context_texts.append(q)
        context_blob = " \n".join(context_texts)
        keyphrases = self._extract_keyphrases(context_blob, top_k=max_phrases * 2)
        # Filter phrases already present in the question
        q_tokens = set(t for t in self._tokenize(question) if t not in self._stopwords)
        filtered: List[str] = []
        for p in keyphrases:
            ptoks = [t for t in self._tokenize(p) if t not in self._stopwords]
            if not ptoks:
                continue
            if any(t in self._context_blacklist for t in ptoks):
                continue
            if any(t not in q_tokens for t in ptoks):
                filtered.append(p)
            if len(filtered) >= max_phrases:
                break
        if not filtered:
            return question
        context_snippet = "; ".join(filtered)
        # enhanced = f"{question} (konteks: {context_snippet})"
        enhanced = f"{question}"
        logging.info(f"🔗 Context phrases used: {filtered}")
        return enhanced

    def enhance_query_for_recency(self, question: str) -> str:
        """
        Enhance search query intelligently with current year context.
        Explicitly provides current year to overcome LLM knowledge cutoff limitations.
        """
        question_lower = question.lower().strip()
        current_year = get_current_datetime().year

        # Advanced categorization patterns
        categories = {
            'historical': {
                'patterns': [
                    r'\b(sejarah|history|dahulu|masa lalu|awalnya|originally)\b',
                    r'\b(founded|didirikan|establish|created|invented|discover)\b',
                    r'\b(lahir|born|meninggal|died|death|wafat)\b',
                    r'\b(perang|war|konflik|revolusi|kemerdekaan|independence)\b',
                    r'\b(asal usul|origin|background|latar belakang)\b',
                    r'\b(kapan.*dibuat|when.*created|when.*founded|when.*invented)\b',
                    r'\b(abad|century|era|periode|period)\b',
                    r'\b(masa.*|zaman.*)\b',
                    r'\b(19\d{2}|20[0-1]\d)\b',  # Specific years
                ],
                'weight': 1.0
            },
            'current_events': {
                'patterns': [
                    r'\b(berita|news|terbaru|latest|breaking)\b',
                    r'\b(hari ini|today|kemarin|yesterday|minggu ini|this week)\b',
                    r'\b(bulan ini|this month|tahun ini|this year)\b',
                    r'\b(sekarang|now|saat ini|currently|present)\b',
                    r'\b(update|terkini|recent|baru)\b',
                    r'\b(happening|sedang terjadi|berlangsung)\b',
                    r'\b(trend|trending|viral|popular|populer)\b',
                ],
                'weight': 1.0
            },
            'technology': {
                'patterns': [
                    r'\b(teknologi|technology|software|hardware|AI|artificial intelligence)\b',
                    r'\b(programming|coding|development|framework|library)\b',
                    r'\b(python|javascript|react|vue|angular|node|docker)\b',
                    r'\b(update|version|release|launch|fitur baru|new feature)\b',
                    r'\b(trend|popular|populer|viral)\b',
                ],
                'weight': 0.8
            },
            'business_finance': {
                'patterns': [
                    r'\b(saham|stock|crypto|cryptocurrency|bitcoin|investment)\b',
                    r'\b(ekonomi|economy|bisnis|business|market|pasar)\b',
                    r'\b(harga|price|nilai|value|kurs|exchange rate)\b',
                    r'\b(startup|company|perusahaan|IPO|merger)\b',
                ],
                'weight': 0.9
            },
            'health_science': {
                'patterns': [
                    r'\b(kesehatan|health|medical|medis|obat|medicine)\b',
                    r'\b(penelitian|research|study|riset|jurnal)\b',
                    r'\b(covid|virus|vaksin|vaccine|pandemi|pandemic)\b',
                    r'\b(gizi|nutrisi|diet|fitness|olahraga)\b',
                ],
                'weight': 0.7
            },
            'global_trends': {
                'patterns': [
                    r'\b(trend|trending|viral|popular|populer)\b',
                    r'\b(dunia|world|global|international|internasional)\b',
                    r'\b(climate|iklim|environment|lingkungan)\b',
                    r'\b(politik|politics|election|pemilu|government)\b',
                ],
                'weight': 0.8
            }
        }

        # Calculate category scores
        category_scores = {}
        for category, data in categories.items():
            score = 0
            for pattern in data['patterns']:
                matches = len(re.findall(pattern, question_lower, re.IGNORECASE))
                score += matches * data['weight']
            category_scores[category] = score

        # Find dominant category
        dominant_category = None
        max_score = 0
        if any(v > 0 for v in category_scores.values()):
            dominant_category = max(category_scores.items(), key=lambda kv: kv[1])[0]
            max_score = category_scores[dominant_category]

        # Enhanced query strategies based on analysis with explicit year context
        if dominant_category == 'historical' and max_score > 0:
            # For historical queries, keep original question unchanged
            logging.info(f"🏛️ Historical query detected, keeping original: {question}")
            return question

        elif dominant_category == 'current_events' and max_score > 0:
            # Current events need explicit year context
            if not any(str(year) in question for year in range(2020, current_year + 1)):
                enhanced = f"{question} {current_year}"
                logging.info(f"📰 Current events query enhanced with year: {question} → {enhanced}")
                return enhanced
            return question

        elif dominant_category in ['technology', 'business_finance'] and max_score > 0:
            # Technology and business benefit from recent information with explicit year
            if not any(term in question_lower for term in ['latest', 'terbaru', 'recent', 'terkini']):
                enhanced = f"{question} latest {current_year}"
                logging.info(f"💻 Tech/Business query enhanced with year: {question} → {enhanced}")
                return enhanced
            elif not any(str(year) in question for year in range(2020, current_year + 1)):
                enhanced = f"{question} {current_year}"
                logging.info(f"💻 Tech/Business query enhanced with year: {question} → {enhanced}")
                return enhanced
            return question

        elif dominant_category == 'health_science' and max_score > 0:
            # Health queries benefit from current research with year context
            if not any(term in question_lower for term in ['recent', 'terkini', 'latest', 'current']):
                enhanced = f"{question} current research {current_year}"
                logging.info(f"🔬 Health/Science query enhanced with year: {question} → {enhanced}")
                return enhanced
            elif not any(str(year) in question for year in range(2020, current_year + 1)):
                enhanced = f"{question} {current_year}"
                logging.info(f"🔬 Health/Science query enhanced with year: {question} → {enhanced}")
                return enhanced
            return question

        elif dominant_category == 'global_trends' and max_score > 0:
            # Global trends should be current with explicit year
            if not any(term in question_lower for term in ['current', 'latest', 'terkini', 'sekarang']):
                enhanced = f"{question} current global {current_year}"
                logging.info(f"🌍 Global trends query enhanced with year: {question} → {enhanced}")
                return enhanced
            elif not any(str(year) in question for year in range(2020, current_year + 1)):
                enhanced = f"{question} {current_year}"
                logging.info(f"🌍 Global trends query enhanced with year: {question} → {enhanced}")
                return enhanced
            return question

        # Default enhancement for general queries with explicit year context
        general_enhancement_indicators = [
            'cara', 'how to', 'tutorial', 'guide', 'tips', 'metode', 'method',
            'best', 'terbaik', 'rekomendasi', 'recommendation', 'pilihan', 'choice',
            'apa itu', 'what is', 'pengertian', 'definisi', 'definition',
            'manfaat', 'benefit', 'kegunaan', 'fungsi', 'function',
            'trend', 'trending', 'popular', 'populer', 'saat ini', 'sekarang'
        ]

        # Check if already has time-related terms or years
        time_terms = [
            'saat ini', 'sekarang', 'current', 'now', 'today', 'hari ini',
            'terbaru', 'latest', 'recent', 'terkini', 'baru', 'new'
        ]

        has_year = any(str(year) in question for year in range(2020, current_year + 1))
        has_enhancement_potential = any(indicator in question_lower for indicator in general_enhancement_indicators)
        already_has_time_context = any(term in question_lower for term in time_terms)

        # Special handling for trend/current queries - always add current year
        if any(term in question_lower for term in ['trend', 'trending', 'saat ini', 'sekarang', 'current']) and not has_year:
            enhanced = f"{question} {current_year}"
            logging.info(f"🔥 Trend query enhanced with current year: {question} → {enhanced}")
            return enhanced

        if has_enhancement_potential and not already_has_time_context and not has_year:
            # Add minimal enhancement for general informational queries with year
            enhanced = f"{question} current {current_year}"
            logging.info(f"📚 General query enhanced with year: {question} → {enhanced}")
            return enhanced

        # Return original question if no enhancement is needed
        logging.info(f"✨ Query returned unchanged: {question}")
        return question

    def enhance_query_for_dorking(self, question: str) -> str:
        """
        Enhance search query with Google dorking operators for better search results.
        Used specifically for is_browse mode to perform targeted searches.
        """
        question_lower = question.lower().strip()
        
        # Skip enhancement if already has dorking operators
        existing_operators = ['site:', 'filetype:', 'inurl:', 'intitle:', 'intext:', 'cache:', 'related:']
        if any(op in question_lower for op in existing_operators):
            logging.info(f"🔍 Query already has dorking operators: {question}")
            return question
            
        # Content type enhancement patterns
        enhanced_query = question
        
        # Add file type searches for specific content types
        if any(term in question_lower for term in ['pdf', 'document', 'dokumen', 'paper', 'research']):
            enhanced_query = f"{question} filetype:pdf OR filetype:doc OR filetype:docx"
            logging.info(f"📄 Enhanced with document types: {enhanced_query}")
            
        # Add site restrictions for Indonesian content if language indicators present
        elif any(term in question_lower for term in ['indonesia', 'indonesian', 'bahasa indonesia', 'berita indonesia']):
            enhanced_query = f"{question} site:.id OR site:.co.id"
            logging.info(f"🇮🇩 Enhanced with Indonesian sites: {enhanced_query}")
            
        # Add news site enhancement for current events
        elif any(term in question_lower for term in ['berita', 'news', 'breaking', 'terbaru', 'hari ini']):
            enhanced_query = f"{question} (site:detik.com OR site:kompas.com OR site:tempo.co OR site:cnn.com OR site:bbc.com)"
            logging.info(f"📰 Enhanced with news sites: {enhanced_query}")
            
        # Add technical site enhancement for programming/tech queries
        elif any(term in question_lower for term in ['programming', 'coding', 'python', 'javascript', 'tutorial', 'github']):
            enhanced_query = f"{question} (site:stackoverflow.com OR site:github.com OR site:medium.com OR site:dev.to)"
            logging.info(f"💻 Enhanced with tech sites: {enhanced_query}")
            
        # Add academic enhancement for research queries
        elif any(term in question_lower for term in ['research', 'study', 'analysis', 'penelitian', 'akademik', 'ilmiah']):
            enhanced_query = f"{question} (site:scholar.google.com OR site:researchgate.net OR filetype:pdf)"
            logging.info(f"🎓 Enhanced with academic sources: {enhanced_query}")
            
        # Add recent content enhancement for time-sensitive queries
        elif any(term in question_lower for term in ['latest', 'recent', 'terkini', 'terbaru', '2024', '2025']):
            # Add quotes for exact phrase matching on time-sensitive terms
            enhanced_query = f'"{question}" OR {question} 2024 OR 2025'
            logging.info(f"⏰ Enhanced with recency operators: {enhanced_query}")
            
        # Add title search for specific topics
        elif any(term in question_lower for term in ['apa itu', 'what is', 'definisi', 'pengertian', 'meaning']):
            # Extract the main topic for intitle search
            topic_words = [word for word in question.split() if word.lower() not in ['apa', 'itu', 'what', 'is', 'definisi', 'pengertian', 'meaning', 'of']]
            if topic_words:
                main_topic = ' '.join(topic_words)
                enhanced_query = f'{question} OR intitle:"{main_topic}"'
                logging.info(f"📝 Enhanced with title search: {enhanced_query}")
        
        return enhanced_query

    def enhance_question_with_context(self, question: str, chat_history: Optional[List[Tuple[str, str]]] = None) -> str:
        """
        Enhance current question with context from previous conversation only if they are related.
        """
        try:
            if not chat_history or len(chat_history) == 0:
                logging.info("📝 No chat history available, using original question")
                return question

            # Get the most recent exchange for context analysis
            last_qa = chat_history[-1] if chat_history else None
            if not last_qa:
                return question

            last_question, last_answer = last_qa

            # Use LLM to determine if current question is related to previous conversation
            if self.llm:
                try:
                    # Truncate last answer for analysis
                    last_answer_preview = last_answer[:300] + "..." if len(last_answer) > 300 else last_answer

                    relation_prompt = self.prompt_service.create_robust_prompt_template(
                        system_template=system_prompts.RELATION_ANALYSIS_PROMPT,
                        user_template="PERTANYAAN BARU: {question}",
                        last_question=last_question,
                        last_answer_preview=last_answer_preview
                    )

                    # Format the messages safely before sending to LLM
                    formatted_messages = self.prompt_service.safe_format_messages(
                        relation_prompt,
                        last_question=last_question,
                        last_answer_preview=last_answer_preview,
                        question=question
                    )
                    try:
                        result = self.llm.invoke(formatted_messages)
                        relation_result = str(result.content).strip().upper() if hasattr(result, "content") else str(result).strip().upper()
                    except (AuthenticationError, RateLimitError, APIError) as e:
                        logging.error(f"❌ OpenAI API error in question enhancement: {e}")
                        # Return original question if LLM fails
                        return question

                    logging.info(f"🤖 LLM relation analysis result: {relation_result}")

                    if "RELATED" in relation_result:
                        logging.info("🔗 Questions are related, enhancing with dynamic keyphrases")
                        enhanced_question = self._build_contextual_query(question, chat_history)
                        logging.info(f"✅ Question enhanced: '{question}' → '{enhanced_question}'")
                        return enhanced_question

                    else:
                        logging.info("🆕 Questions are not related, using original question")
                        return question

                except Exception as e:
                    logging.error(f"Error in LLM-based question analysis: {e}")

            # Fallback: dynamic heuristic without LLM
            logging.info("🔄 Using fallback dynamic enhancement (no LLM)")

            # Heuristic: if question has <= 2 content tokens (ex stopwords), treat as follow-up
            content_tokens = [t for t in self._tokenize(question) if t not in self._stopwords]
            if len(content_tokens) <= 2:
                enhanced_question = self._build_contextual_query(question, chat_history)
                logging.info(f"🔄 Fallback dynamic enhancement: '{question}' → '{enhanced_question}'")
                return enhanced_question

            logging.info(f"✨ Question stands alone: {question}")
            return question

        except Exception as e:
            logging.error(f"Error in enhance_question_with_context: {e}")
            return question

    def clean_url(self, url: str) -> str:
        """
        Clean URL from unwanted characters and formatting issues.
        """
        if not url:
            return ""

        # Convert to string and strip whitespace
        original_url = str(url).strip()

        # Remove trailing punctuation and unwanted closing characters
        cleaned_url = re.sub(r'[)\]\}\.,:;]+$', '', original_url)

        # Remove enclosing parentheses if present
        if cleaned_url.startswith('(') and cleaned_url.endswith(')'):
            cleaned_url = cleaned_url[1:-1]

        # Final strip for whitespace
        cleaned_url = cleaned_url.strip()

        # Normalize common tracking parameters to improve deduplication
        try:
            split = urlsplit(cleaned_url)
            if split.scheme in ("http", "https") and split.netloc:
                # Ensure main combiphar.com routes to www.combiphar.com
                netloc_lower = split.netloc.lower()
                host = netloc_lower.split(':')[0]
                port_suffix = split.netloc[len(host):]  # keep :port if present
                new_netloc = split.netloc
                if host == "combiphar.com":
                    new_netloc = "www.combiphar.com" + port_suffix

                tracking_params = {
                    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                    "gclid", "fbclid", "mc_cid", "mc_eid", "ref", "ref_src"
                }
                query_pairs = parse_qsl(split.query, keep_blank_values=True)
                filtered_pairs = [(k, v) for (k, v) in query_pairs if k.lower() not in tracking_params]
                new_query = urlencode(filtered_pairs, doseq=True)
                cleaned_url = urlunsplit((split.scheme, new_netloc, split.path, new_query, ""))
        except Exception:
            # If normalization fails, just return the cleaned string
            pass

        # Log if significant cleaning was done
        if original_url != cleaned_url and original_url:
            logging.info(f"🧹 URL cleaned: '{original_url}' → '{cleaned_url}'")

        return cleaned_url

    def search_web(
        self,
        question: str,
        chat_id: str,
        user_id: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        original_question: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search the web for answers using Agent executor tools.
        Returns a response with answer and source documents containing website links and titles.
        """
        try:
            logging.info(f"🌐 Starting web search for: {question}")

            # Process question with chat history context to create better search prompt
            logging.info(f"📝 Analyzing question with chat history context...")
            enhanced_question = self.enhance_question_with_context(question, chat_history or [])

            if enhanced_question != question:
                logging.info(f"🔄 Question enhanced with context:")
                logging.info(f"   Original: {question}")
                logging.info(f"   Enhanced: {enhanced_question}")
            else:
                logging.info(f"✨ Question used as-is: {question}")

            # Enhance search query for current information
            enhanced_query = self.enhance_query_for_recency(enhanced_question)
            if enhanced_query != enhanced_question:
                logging.info(f"⏰ Query enhanced for recency: {enhanced_query}")
            else:
                logging.info(f"✨ Query kept unchanged for recency: {enhanced_query}")
            
            # Apply Google dorking enhancements for better search targeting
            dorking_enhanced_query = self.enhance_query_for_dorking(enhanced_query)
            if dorking_enhanced_query != enhanced_query:
                logging.info(f"🔍 Query enhanced with dorking: {dorking_enhanced_query}")
            else:
                logging.info(f"✨ Query kept unchanged for dorking: {dorking_enhanced_query}")
            
            final_query = dorking_enhanced_query

            search_results = []
            failure_response = {
                "answer": ErrorHandler.get_message("offline_internet", "Sistem pencarian tidak tersedia"),
                "source_documents": [],
                "confidence": 0.1
            }

            # Try Tool Calling Agent with DuckDuckGo tools
            if LANGCHAIN_TOOLS_AVAILABLE:
                try:
                    logging.info("🔄 Using agent executor method")
                    search_results = self._search_with_agent_executor(final_query, enhanced_question)
                    if search_results:
                        logging.info(f"✅ Agent executor returned {len(search_results)} results")
                except Exception as e2:
                    logging.warning(f"Agent executor search failed: {e2}")

            if not search_results:
                logging.warning("❌ No search results obtained")
                return {
                    "answer": ErrorHandler.get_message("no_information", "Tidak ditemukan informasi yang relevan"),
                    "source_documents": [],
                    "confidence": 0.0
                }

            # Process results with LLM, passing chat history for context
            processed_result = self._process_search_results_with_llm(
                search_results,
                enhanced_question,
                chat_history,
                original_question or question
            )
            if not processed_result:
                logging.info("Web search returned no usable sources; using no_information fallback")
                return {
                    "answer": ErrorHandler.get_message("no_information", "Tidak ditemukan informasi yang relevan"),
                    "source_documents": [],
                    "confidence": 0.0
                }

            # Extract answer and references from processed result
            processed_answer = processed_result.get("answer", "")
            references = processed_result.get("references", [])

            # For internet search, return answer with references and populate source_documents
            logging.info(f"✅ Internet search completed with {len(search_results)} sources and {len(references)} references")

            # Map search results to source documents format
            source_documents = [
                {
                    "content": res.get("content", "")[:500],
                    "metadata": {
                        "source": res.get("url", ""),
                        "title": res.get("title", "")
                    }
                }
                for res in search_results[:5]
            ]

            return {
                "answer": processed_answer,
                "source_documents": source_documents,
                "confidence": 0.9 if len(search_results) > 2 else 0.8 if len(search_results) > 0 else 0.7
            }

        except Exception as e:
            logging.error(f"❌ Error in web search: {e}")
            return {
                "answer": ErrorHandler.get_message("offline_internet", "Sistem pencarian tidak tersedia"),
                "source_documents": [],
                "confidence": 0.0
            }

    def _search_with_agent_executor(self, enhanced_query: str, original_question: str) -> List[Dict[str, Any]]:
        """
        Search using LangChain create_tool_calling_agent with DDGS (DuckDuckGo Search).
        """
        search_results = []

        try:
            # Create DDGS search tool
            def ddgs_search_func(query: str) -> str:
                """Search DuckDuckGo using DDGS library."""
                try:
                    with DDGS(verify=False) as ddgs:
                        results = list(ddgs.text(query, backend="auto", max_results=5))
                        if not results:
                            return "No search results found."

                        formatted_results = []
                        for i, result in enumerate(results, 1):
                            title = result.get('title', 'No Title')
                            url = result.get('href', '')
                            snippet = result.get('body', '')
                            formatted_results.append(f"{i}. {title}\nURL: {url}\nSnippet: {snippet}\n")

                        return "\n".join(formatted_results)
                except Exception as e:
                    return f"Search error: {str(e)}"

            ddgs_tool = Tool(
                name="duckduckgo_search",
                description="Search DuckDuckGo for web results. Returns titles, URLs, and snippets of relevant web pages.",
                func=ddgs_search_func
            )

            # Create web content loader tool
            def load_web_content(url: str) -> str:
                """Load content from a web URL."""
                try:
                    # Normalize URL (add www for combiphar.com and clean tracking params)
                    normalized_url = self.clean_url(url)

                    combiphar_content = self._fetch_combiphar_content(normalized_url)
                    if combiphar_content:
                        return f"Content from {normalized_url}:\n{combiphar_content}"

                    loader = WebBaseLoader([normalized_url])
                    loader.requests_kwargs = {'verify':False}
                    docs = loader.load()
                    if docs and docs[0].page_content:
                        content = docs[0].page_content[:2000]  # Limit content
                        return f"Content from {normalized_url}:\n{content}"
                    return f"Failed to load content from {normalized_url}"
                except Exception as e:
                    return f"Error loading URL {url}: {str(e)}"

            # Create custom tools for the agent
            web_loader_tool = Tool(
                name="web_content_loader",
                description="Load content from a specific web URL. Use this after getting URLs from search results to get detailed content.",
                func=load_web_content
            )

            # Define tools for the agent
            tools = [ddgs_tool, web_loader_tool]
            if current_datetime_tool is not None:
                tools.append(current_datetime_tool)
            if current_context_tool is not None:
                tools.append(current_context_tool)

            # Create system prompt for the tool calling agent
            system_prompt = self.prompt_service.create_robust_prompt_template(
                system_template=system_prompts.WEB_SEARCH_TOOL_AGENT_PROMPT,
                user_template="{input}",
                query=enhanced_query,
                original_question=original_question
            )

            # Create the tool calling agent
            if not self.llm:
                return []
            agent = create_tool_calling_agent(self.llm, tools, system_prompt)

            # Create agent executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=5,
                handle_parsing_errors=True
            )

            # Execute the agent
            logging.info("🤖 Executing tool calling agent for general web search...")

            # Prepare input for the agent
            agent_input = {
                "input": f"Search for information about: {enhanced_query}"
            }

            # Run the agent
            response = agent_executor.invoke(agent_input)

            if response and response.get('output'):
                # Parse the agent's response and extract search results
                agent_output = response['output']

                # First, try to extract URLs and detailed sources from intermediate steps
                urls_found = set()
                if 'intermediate_steps' in response:
                    for step in response['intermediate_steps']:
                        if len(step) >= 2:
                            action, observation = step[0], step[1]

                            # Extract URLs from DuckDuckGo search results
                            if hasattr(action, 'tool') and action.tool == 'duckduckgo_search':
                                # Parse DuckDuckGo search results from observation
                                url_pattern = r'https?://[^\s\],]+'
                                urls_in_observation = re.findall(url_pattern, str(observation))

                                # Extract title and URL pairs from DuckDuckGo results
                                lines = str(observation).split('\n')
                                for line in lines:
                                    if 'http' in line:
                                        # Try to extract title and URL from DuckDuckGo result line
                                        url_match = re.search(url_pattern, line)
                                        if url_match:
                                            url = url_match.group()
                                            urls_found.add(url)

                                            # Extract title (text before the URL)
                                            title_part = line[:url_match.start()].strip()
                                            title = title_part if title_part else url

                                            search_results.append({
                                                'title': title,
                                                'url': url,
                                                'content': line.strip(),
                                                'score': 0.9
                                            })

                            # Extract content from web_content_loader
                            elif hasattr(action, 'tool') and action.tool == 'web_content_loader':
                                url = action.tool_input if isinstance(action.tool_input, str) else str(action.tool_input)
                                if url.startswith('http') and url not in urls_found:
                                    urls_found.add(url)
                                    search_results.append({
                                        'title': f'Detailed Content: {url}',
                                        'url': url,
                                        'content': observation[:1500] if observation else 'Content not available',
                                        'score': 0.95  # Higher score for detailed content
                                    })

                # If no specific URLs were found, create a comprehensive result with extracted URLs
                if not search_results:
                    # Try to extract URLs directly from the agent output
                    url_pattern = r'https?://[^\s\],]+'
                    urls_in_output = re.findall(url_pattern, agent_output)

                    if urls_in_output:
                        # Create individual results for each URL found
                        for url in urls_in_output[:5]:  # Limit to 5 URLs
                            search_results.append({
                                'title': url,
                                'url': url,
                                'content': agent_output,
                                'score': 0.8
                            })
                    else:
                        # Fallback: create a single comprehensive result
                        search_results.append({
                            'title': f"Comprehensive Search Results for: {original_question}",
                            'url': 'https://duckduckgo.com/search',
                            'content': agent_output,
                            'score': 0.7  # Lower score since no specific URLs
                        })

                # Deduplicate results by cleaned URL, keep item with best score/content length
                if search_results:
                    dedup: Dict[str, Dict[str, Any]] = {}
                    for item in search_results:
                        raw_url = item.get('url', '')
                        cleaned = self.clean_url(raw_url)
                        # Build a stable key: prefer URL; fallback to title snippet
                        fallback_key = (item.get('title') or '')[:100].strip()
                        key = cleaned if cleaned else fallback_key
                        cur = dedup.get(key)
                        score = float(item.get('score', 0.0) or 0.0)
                        content_len = len((item.get('content') or '').strip())
                        quality = (score, content_len)
                        if not cur:
                            dedup[key] = item
                            dedup[key]['_quality'] = quality
                        else:
                            cur_quality = cur.get('_quality', (0.0, 0))
                            if quality > cur_quality:
                                item['_quality'] = quality
                                dedup[key] = item
                    # Rebuild list preserving relative order by first appearance
                    seen = set()
                    unique_results: List[Dict[str, Any]] = []
                    for item in search_results:
                        cleaned = self.clean_url(item.get('url', ''))
                        fallback_key = (item.get('title') or '')[:100].strip()
                        key = cleaned if cleaned else fallback_key
                        if key in seen:
                            continue
                        seen.add(key)
                        unique_results.append(dedup.get(key, item))
                    search_results = unique_results

                logging.info(f"✅ Tool calling agent returned {len(search_results)} unique results with {len(urls_found)} URLs parsed")

        except Exception as e:
            logging.error(f"Tool calling agent search failed: {e}")
            # Fallback to simple DDGS search
            try:
                logging.info("🔍 Falling back to simple DDGS search...")
                if DUCKDUCKGO_AVAILABLE:
                    with DDGS(verify=True) as ddgs:
                        results = list(ddgs.text(enhanced_query, backend="auto", max_results=5))

                        for result in results:
                            search_results.append({
                                'title': result.get('title', 'No Title'),
                                'url': result.get('href', ''),
                                'content': result.get('body', ''),
                                'score': 0.7
                            })

            except Exception as fallback_error:
                message = self._describe_ddgs_error(fallback_error)
                if self._is_recoverable_ddgs_error(fallback_error):
                    logging.warning(f"Fallback DDGS search encountered network issue: {message}")
                else:
                    logging.error(f"Fallback DDGS search also failed: {message}")

            # Final fallback: try to extract any URLs mentioned in the enhanced query response
            if not search_results:
                try:
                    logging.info("🔍 Attempting final search with DDGS...")
                    if DUCKDUCKGO_AVAILABLE:
                        with DDGS(verify=True) as ddgs:
                            results = list(ddgs.text(original_question, backend="auto", max_results=3))

                            for i, result in enumerate(results, 1):
                                search_results.append({
                                    'title': result.get('title', f"Search Result {i}"),
                                    'url': result.get('href', ''),
                                    'content': result.get('body', ''),
                                    'score': 0.6 + (0.1 * (4 - i))  # Decreasing score
                                })

                except Exception as final_error:
                    message = self._describe_ddgs_error(final_error)
                    if self._is_recoverable_ddgs_error(final_error):
                        logging.warning(f"Final fallback DDGS search encountered network issue: {message}")
                    else:
                        logging.error(f"Final fallback DDGS search failed: {message}")
                    
                    # No results fallback
                    search_results.append({
                        'title': f"No results found for: {original_question}",
                        'url': 'https://duckduckgo.com/search',
                        'content': f"No search results were found for the query: {original_question}",
                        'score': 0.1
                    })

        return search_results

    def _process_search_results_with_llm(
        self,
        search_results: List[Dict[str, Any]],
        enhanced_question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        original_question: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process internet search results using LLM to generate a comprehensive answer with document-style formatting and proper references.
        """
        try:
            if not self.llm:
                logging.error("🧠 LLM not initialized")
                return None

            if not search_results:
                return None

            # Use original question if provided, otherwise use enhanced question
            user_question = original_question if original_question else enhanced_question
            logger.info("Using default instructions for web search answer (no language detection)")

            # Deduplicate results by URL first, prefer higher score and longer content
            by_url: Dict[str, Dict[str, Any]] = {}
            order: List[str] = []
            for result in search_results:
                cleaned_url = self.clean_url(result.get('url', ''))
                url_key = cleaned_url if cleaned_url else (result.get('title') or '')[:100].strip()
                score = float(result.get('score', 0.0) or 0.0)
                content_len = len((result.get('content') or '').strip())
                quality = (score, content_len)
                if url_key not in by_url:
                    by_url[url_key] = {**result, '_quality': quality}
                    order.append(url_key)
                else:
                    if quality > by_url[url_key].get('_quality', (0.0, 0)):
                        by_url[url_key] = {**result, '_quality': quality}

            unique_results = [by_url[k] for k in order]

            # Filter relevant results
            def _tokens(s: str) -> List[str]:
                return re.findall(r"[a-z0-9]+", (s or '').lower())

            q_tokens = set(_tokens(user_question))
            # Anchor: buang stopwords dasar
            basic_stop = {
                'dan','atau','yang','untuk','dengan','pada','di','ke','dari','itu','ini','adalah','ialah','sebagai',
                'the','a','an','and','or','for','to','of','in','on','at','by','is','are','was','were','be','been',
                'apa','siapa','kapan','dimana','bagaimana','mengapa','kenapa','what','who','when','where','why','how'
            }
            anchors = {t for t in q_tokens if (len(t) >= 4 or any(c.isdigit() for c in t)) and t not in basic_stop}

            def _is_relevant_result(item: Dict[str, Any]) -> bool:
                url = self.clean_url(item.get('url',''))
                title = item.get('title','')
                content = item.get('content','')
                text = ' '.join([url, title, content])
                tset = set(_tokens(text))

                if not anchors:
                    return True
                
                overlap = len(anchors & tset)
                return overlap >= 1

            relevant_results = [it for it in unique_results if _is_relevant_result(it)]
            if not relevant_results:
                logging.info("No sufficiently relevant web results for the question; skipping web-based answer")
                return None

            # Prepare context from deduplicated results
            context_parts = []
            valid_sources = 0
            max_context_sources = 4
            anchor_list = list(anchors) if anchors else list(q_tokens)

            for i, result in enumerate(relevant_results, 1):
                title = result.get('title', 'No Title')
                url = self.clean_url(result.get('url', ''))
                content = result.get('content', '')
                score = result.get('score', 0.0)

                # Skip results with generic/invalid URLs unless they have substantial content
                if url in ['https://duckduckgo.com/search', ''] and len(content.strip()) < 50:
                    continue

                # Validate content quality
                if len(content.strip()) < 30:
                    continue

                if self._is_placeholder_content(content):
                    logging.info("Skipping placeholder web result lacking real content")
                    continue

                snippet = self._build_snippet(content, anchor_list, limit=600)
                if not snippet:
                    snippet = content[:600].strip()
                if len(snippet) < 40:
                    continue

                valid_sources += 1

                # Clean and truncate title if too long
                clean_title = title.replace('"', '').replace("'", "").strip()
                if len(clean_title) > 80:
                    clean_title = clean_title[:77] + "..."

                # Format context for LLM dengan URL yang bisa digunakan secara natural
                if url and url.startswith('http') and url != 'https://duckduckgo.com/search':
                    source_info = f"Website: {clean_title} (URL: {url})"
                else:
                    source_info = f"Website: {clean_title}"

                context_parts.append(f"Sumber {valid_sources}: {source_info}\nRingkasan Konten: {snippet}\n")

                if valid_sources >= max_context_sources:
                    break

            if valid_sources == 0:
                logging.warning("No valid sources found for LLM processing")
                return None

            combined_context = "\n".join(context_parts)

            # Build context from chat history if available (bounded for performance)
            chat_history_context = ""
            if chat_history and len(chat_history) > 0:
                try:
                    turns = int(os.getenv("WEB_HISTORY_TURNS", "4"))
                except Exception:
                    turns = 4
                try:
                    max_chars = int(os.getenv("WEB_HISTORY_MAX_CHARS", "900"))
                except Exception:
                    max_chars = 900
                turns = max(1, min(turns, 10))
                max_chars = max(200, min(max_chars, 4000))

                recent_context = chat_history[-turns:]
                history_parts = []
                total_chars = 0
                for q, a in recent_context:
                    q_norm = re.sub(r"\s+", " ", str(q).lower()).strip()
                    q_norm = re.sub(r"[^\w\s]", " ", q_norm)
                    q_norm = re.sub(r"\s+", " ", q_norm).strip()
                    if (
                        len(q_norm) <= 2
                        or q_norm in {"benar", "ya", "iya", "ok", "oke", "y", "a", "b", "c"}
                    ):
                        continue

                    # Truncate long answers to keep context manageable
                    truncated_answer = a[:200] + "..." if len(a) > 200 else a
                    chunk = f"Q: {q}\nA: {truncated_answer}"
                    if total_chars + len(chunk) > max_chars:
                        break
                    history_parts.append(chunk)
                    total_chars += len(chunk)

                if history_parts:
                    chat_history_context = "\n\nRIWAYAT PERCAKAPAN SEBELUMNYA:\n" + "\n\n".join(history_parts)
                    logging.info(f"Added chat history context from {len(recent_context)} previous exchanges for web search")
                else:
                    logging.info("No usable chat history entries for context")
            else:
                logging.info("No chat history available for web search context")

            # Create enhanced prompt with explicit current year context and chat history
            current_year = time.localtime().tm_year
            current_month = time.localtime().tm_mon
            current_day = time.localtime().tm_mday

            system_template = system_prompts.WEB_SUMMARY_PROMPT

            # system_template = """Anda adalah asisten riset yang menulis jawaban faktual dan ringkas.

            #     Informasi waktu:
            #     - Tahun: {current_year}
            #     - Bulan: {current_month}
            #     - Hari: {current_day}

            #     Petunjuk jawaban:
            #     - Jawab langsung pertanyaan dalam 2-3 paragraf.
            #     - Gunakan **bold** untuk istilah penting dan bullet jika membantu.
            #     - Jangan memasukkan URL; referensi akan ditambahkan terpisah.
            #     - Pertahankan konsistensi dengan riwayat percakapan jika ada.

            #     Ringkasan sumber ({valid_sources}):
            #     {combined_context}
            #     {chat_history_context}
            # """

            user_prompt_template = (
                    "PERTANYAAN USER: {user_question}\n"
                    "PERTANYAAN PENCARIAN: {enhanced_question}\n\n"
                    "Berikan jawaban yang KOMPREHENSIF dan DETAIL berdasarkan sumber-sumber di atas:"
                )

            prompt_template = self.prompt_service.create_robust_prompt_template(
                system_template=system_template,
                user_template=user_prompt_template,
                current_year=current_year,
                current_month=current_month,
                current_day=current_day,
                valid_sources=valid_sources,
                combined_context=combined_context,
                chat_history_context=chat_history_context
            )

            logging.info(f"📝 Processing {valid_sources} valid sources with LLM for comprehensive answer...")
            # Format the messages safely before sending to LLM
            formatted_messages = self.prompt_service.safe_format_messages(
                prompt_template,
                combined_context=combined_context,
                user_question=user_question,
                enhanced_question=enhanced_question,
                valid_sources=valid_sources,
                chat_history_context=chat_history_context,
                current_year=current_year,
                current_month=current_month,
                current_day=current_day
            )
            try:
                result = self.llm.invoke(formatted_messages)
            except (AuthenticationError, RateLimitError, APIError) as e:
                logging.error(f"❌ OpenAI API error in web search: {e}")
                return {
                    "answer": ErrorHandler.get_message("token_empty", "Terjadi kesalahan dengan API OpenAI"),
                    "source_documents": [],
                    "confidence": 0
                }

            # Get answer text
            if hasattr(result, "content"):
                answer_text = str(result.content)
            else:
                answer_text = str(result)

            # Additional check: ensure answer is not a generic LLM response when no information found
            if self.is_not_relevant_answer(answer_text, user_question):
                logging.info("LLM web answer lacked specific information; skipping to fallback step")
                return None
                
            # Check if LLM gave a generic "no information" type response
            if self._is_generic_no_info_response(answer_text):
                logging.info("LLM returned generic 'no information' response; skipping to fallback step") 
                return None

            # Format references similar to document references
            formatted_references = []
            reference_counter = 1
            max_references = 3

            seen_ref_urls = set()
            for result_item in relevant_results:
                title = result_item.get('title', 'No Title')
                url = self.clean_url(result_item.get('url', ''))
                content = result_item.get('content', '')

                # Skip results with generic/invalid URLs unless they have substantial content
                if url in ['https://duckduckgo.com/search', ''] and len(content.strip()) < 50:
                    continue

                # Validate content quality
                if len(content.strip()) < 30:
                    continue

                # Clean and truncate title if too long
                clean_title = title.replace('"', '').replace("'", "").strip()
                if len(clean_title) > 150:
                    clean_title = clean_title[:147] + "..."

                # Format reference entry similar to agent executor output
                if url and url.startswith('http') and url != 'https://duckduckgo.com/search' and url not in seen_ref_urls:
                    reference_entry = f"{reference_counter}. {url}\n"
                    seen_ref_urls.add(url)
                else:
                    reference_entry = None

                if reference_entry is not None:
                    formatted_references.append(reference_entry)
                    reference_counter += 1

                # Limit to maximum 5 references for readability
                if reference_counter > max_references:
                    break

            # Add references section to the answer
            if formatted_references:
                references_section = "\n\n---\n\n**Referensi Sumber:**\n\n" + "\n".join([ref for ref in formatted_references if isinstance(ref, str) and ref.strip()])
                final_answer = answer_text + references_section
            else:
                final_answer = answer_text

            logging.info(f"✅ Successfully processed internet search results with {len(formatted_references)} references")

            return {
                "answer": final_answer,
                "references": formatted_references
            }

        except Exception as e:
            logging.error(f"❌ Error processing search results with LLM: {e}")
            return None

    def is_not_relevant_answer(self, answer: str, question: str) -> bool:
        """
        Check if an answer is not relevant to the question.
        Returns True if the answer is generic, unclear, or doesn't address the question.
        This check is designed to be conservative, preferring to let an answer pass
        if there's any doubt.
        """
        try:
            if not answer or not isinstance(answer, str):
                return True

            answer_lower = answer.lower().strip()
            question_lower = question.lower().strip()

            if not answer_lower:
                return True

            # 1. Check for explicit non-answers or apologies. This is a strong signal.
            generic_responses = [
                # Indonesian
                "saya tidak tahu", "tidak dapat menjawab", "tidak memiliki informasi",
                "tidak cukup informasi", "tidak ada dalam konteks", "tidak tersedia dalam konteks",
                "maaf, saya tidak bisa", "tidak ada informasi yang relevan", "informasi tidak tersedia",
                "tidak ada hasil yang ditemukan", "tidak dapat menemukan informasi spesifik",
                "tidak menemukan informasi spesifik", "saya tidak dapat menemukan informasi spesifik",
                "maaf, saya tidak menemukan informasi spesifik", "sebagai model bahasa",
                "saya tidak memiliki akses ke", "berdasarkan pengetahuan saya",

                # English
                "i don't know", "i cannot answer", "i don't have information",
                "not enough information", "not in the context", "no relevant information",
                "no information available", "i was unable to find", "i could not find",
                "unable to find", "as a language model", "i do not have access to",
                "based on my knowledge"
            ]
            for generic in generic_responses:
                if generic in answer_lower:
                    # Add a check for false positives, e.g., "Saya tidak tahu apa-apa tentang itu, NAMUN..."
                    # If the answer is long, it might have redeemed itself after the generic phrase.
                    if len(answer_lower) > len(generic) + 50:
                        continue # It's a long answer, maybe it's not generic.
                    return True

            # 1.b Company-policy style deflection answers (tidak memberikan informasi spesifik)
            policy_deflection_patterns = [
                "informasi terkait visi dan misi combiphar dapat ditemukan",
                "informasi terkait visi dan misi combiphar",
                "dapat ditemukan dalam dokumen resmi perusahaan atau melalui komunikasi resmi",
                "hubungi langsung bagian corporate communication & community development combiphar",
                "hubungi langsung bagian corporate communication & community development",
                "melalui saluran komunikasi resmi yang tersedia",
            ]
            for pattern in policy_deflection_patterns:
                if pattern in answer_lower:
                    return True

            # 2. Define a function to get meaningful tokens (keywords)
            def get_keywords(s: str) -> set:
                import re
                # Get tokens of 3+ chars, excluding stopwords
                stopwords = getattr(self, "_stopwords", set())
                tokens = re.findall(r"[a-z0-9]+", s.lower())
                return {t for t in tokens if len(t) >= 3 and t not in stopwords}

            q_keywords = get_keywords(question)
            a_keywords = get_keywords(answer)

            # If the question has no keywords, we can't do a keyword-based check.
            if not q_keywords:
                return False

            # 3. Check for keyword overlap.
            overlap_count = len(q_keywords & a_keywords)

            # If there's any overlap, it's probably relevant.
            if overlap_count > 0:
                return False

            # 4. If there is ZERO overlap, we need more checks. It might be using synonyms.
            # An answer with zero overlap is suspicious if it's also very short.
            if len(answer.split()) < 10: # Fewer than 10 words
                logging.warning(f"Answer marked as not relevant due to zero keyword overlap and short length. Q: '{question}' A: '{answer}'")
                return True

            # 5. Check for number correspondence. If the question has numbers, the answer should probably have some.
            # This helps with questions like "what are the 3 main points?"
            question_has_numbers = any(char.isdigit() for char in question)
            answer_has_numbers = any(char.isdigit() for char in answer)

            if question_has_numbers and not answer_has_numbers:
                # If the answer is also short, it's very suspicious.
                if len(answer.split()) < 20:
                    logging.warning(f"Answer marked as not relevant. Question had numbers but the short answer did not. Q: '{question}' A: '{answer}'")
                    return True

            # If we've reached this point, it means the answer has no direct keyword overlap
            # but it's not short enough to be dismissed outright. We will be conservative
            # and assume it's relevant (e.g., it used synonyms).
            logging.info(f"Answer has zero keyword overlap, but passed other checks. Assuming relevant. Q: '{question}' A: '{answer}'")
            return False

        except Exception as e:
            logging.error(f"Error checking answer relevance: {e}")
            return False # Fail safe, assume it's relevant.

    def _is_generic_no_info_response(self, answer: str) -> bool:
        """
        Check if the LLM response is a generic "no information available" type response.
        Returns True if the answer is generic and should be filtered out.
        """
        if not answer or not isinstance(answer, str):
            return True
            
        answer_lower = answer.lower().strip()
        
        # Patterns that indicate LLM couldn't find relevant information
        generic_patterns = [
            "saya tidak memiliki informasi",
            "tidak ada informasi yang tersedia",
            "berdasarkan sumber yang diberikan",
            "berdasarkan konteks yang diberikan", 
            "informasi yang diberikan tidak",
            "tidak dapat menjawab berdasarkan",
            "sumber yang tersedia tidak",
            "tidak ada detail spesifik",
            "informasi tidak cukup spesifik",
            "based on the provided sources",
            "based on the given context",
            "the provided information doesn't",
            "i cannot provide specific",
            "the sources don't contain",
            "no specific information",
            "insufficient information"
        ]
        
        # If answer contains these patterns and is relatively short, it's likely generic
        for pattern in generic_patterns:
            if pattern in answer_lower and len(answer.strip()) < 200:
                return True
                
        return False

    def search_combiphar_site(
        self,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        llm=None,
        original_question: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search the web for answers using Agent executor tools.
        Returns a response with answer and source documents containing website links and titles.
        """
        try:
            logging.info(f"🌐 Starting web search for: {question}")

            # Process question with chat history context to create better search prompt
            logging.info(f"📝 Analyzing question with chat history context...")
            enhanced_question = self.enhance_question_with_context(question, chat_history or [])

            if enhanced_question != question:
                logging.info(f"🔄 Question enhanced with context:")
                logging.info(f"   Original: {question}")
                logging.info(f"   Enhanced: {enhanced_question}")
            else:
                logging.info(f"✨ Question used as-is: {question}")

            # Enhance search query for current information
            enhanced_query = self.enhance_query_for_recency(enhanced_question)
            if enhanced_query != enhanced_question:
                logging.info(f"⏰ Query enhanced for recency: {enhanced_query}")
            else:
                logging.info(f"✨ Query kept unchanged for search: {enhanced_query}")

            search_results = []

            # Try Tool Calling Agent with DuckDuckGo tools
            if LANGCHAIN_TOOLS_AVAILABLE:
                try:
                    logging.info("🔄 Using agent executor method")
                    search_results = self._search_combiphar_site_with_agent_executor(enhanced_query, enhanced_question)
                    if search_results:
                        logging.info(f"✅ Agent executor returned {len(search_results)} results")
                except Exception as e2:
                    logging.warning(f"Agent executor search failed: {e2}")

            if not search_results:
                logging.warning("❌ No search results obtained from combiphar site")
                return {
                    "answer": ErrorHandler.get_message("offline_website", "Website Combiphar tidak dapat diakses"),
                    "source_documents": [],
                    "confidence": 0.0
                }

            # Process results with LLM, passing chat history for context
            processed_result = self._process_search_results_with_llm(
                search_results,
                enhanced_question,
                chat_history,
                original_question or question
            )
            if not processed_result:
                logging.info("Combiphar site search returned no usable sources; using no_information fallback")
                return {
                    "answer": ErrorHandler.get_message("no_information", "Tidak ditemukan informasi yang relevan"),
                    "source_documents": [],
                    "confidence": 0.0
                }

            # Extract answer and references from processed result
            processed_answer = processed_result.get("answer", "")
            references = processed_result.get("references", [])

            # For internet search, return answer with references and populate source_documents
            logging.info(f"✅ Internet search completed with {len(search_results)} sources and {len(references)} references")

            # Map search results to source documents format
            source_documents = [
                {
                    "content": res.get("content", "")[:500],
                    "metadata": {
                        "source": res.get("url", ""),
                        "title": res.get("title", "")
                    }
                }
                for res in search_results[:5]
            ]

            return {
                "answer": processed_answer,
                "source_documents": source_documents,
                "confidence": 0.9 if len(search_results) > 2 else 0.8 if len(search_results) > 0 else 0.7
            }

        except Exception as e:
            logging.error(f"❌ Error in combiphar site search: {e}")
            return {
                "answer": ErrorHandler.get_message("offline_website", "Website Combiphar tidak dapat diakses"),
                "source_documents": [],
                "confidence": 0.0
            }

    def _search_combiphar_site_with_agent_executor(self, enhanced_query: str, original_question: str) -> List[Dict[str, Any]]:
        """
        Search using LangChain create_tool_calling_agent with DDGS (DuckDuckGo Search).
        """
        combiphar_websites: List[str] = ["https://www.combiphar.com/id"]
        try:
            setting = get_setting_value_by_name("combiphar_websites")
            if isinstance(setting, (list, tuple)):
                combiphar_websites = [str(s).strip() for s in setting if isinstance(s, str) and str(s).strip()]
        except Exception:
            pass

        if not combiphar_websites:
            combiphar_websites = ["https://www.combiphar.com/id"]

        allowed_hosts = self._extract_domains(combiphar_websites)

        search_results: List[Dict[str, Any]] = []

        try:
            def _host_allowed(url: str) -> bool:
                if not allowed_hosts:
                    return True
                try:
                    host = urlsplit(url).netloc.lower()
                except Exception:
                    return False
                host = host.split(':')[0]
                if not host:
                    return False
                for allowed in allowed_hosts:
                    if host == allowed or host.endswith(f".{allowed}"):
                        return True
                return False

            def _collect_ddgs_results(query: str, max_items: int = 5) -> Tuple[List[Dict[str, Any]], Optional[str]]:
                q = (query or "").strip()
                if not q:
                    return [], None

                query_lower = q.lower()
                queries = [q]
                if "site:" not in query_lower and allowed_hosts:
                    queries = [f"{q} site:{host}" for host in allowed_hosts]

                aggregated: List[Dict[str, Any]] = []
                seen_urls: Set[str] = set()
                ddgs_error: Optional[str] = None

                try:
                    with DDGS(verify=False) as ddgs:
                        for search_query in queries:
                            try:
                                for result in ddgs.text(search_query, backend="auto", max_results=max_items):
                                    url = result.get('href', '')
                                    if not url:
                                        continue
                                    if not _host_allowed(url):
                                        continue
                                    cleaned_url = self.clean_url(url)
                                    if cleaned_url in seen_urls:
                                        continue
                                    seen_urls.add(cleaned_url)
                                    aggregated.append(result)
                                    if len(aggregated) >= max_items:
                                        break
                            except Exception as inner_exc:
                                message = self._describe_ddgs_error(inner_exc)
                                if self._is_recoverable_ddgs_error(inner_exc):
                                    logging.warning(f"DDGS query hit transient issue for {search_query}: {message}")
                                    continue
                                logging.error(f"DDGS query failed for {search_query}: {message}")
                                ddgs_error = message
                            if len(aggregated) >= max_items:
                                break
                except Exception as exc:
                    message = self._describe_ddgs_error(exc)
                    if self._is_recoverable_ddgs_error(exc):
                        logging.warning(f"DDGS search encountered recoverable issue: {message}")
                    else:
                        logging.error(f"DDGS search failed: {message}")
                    ddgs_error = message

                if not aggregated:
                    api_results = self._search_combiphar_pages_via_api(combiphar_websites, q, max_items=max_items)
                    aggregated.extend(api_results)

                if aggregated:
                    return aggregated, None

                return [], ddgs_error

            # Create DDGS search tool
            def ddgs_search_func(query: str) -> str:
                """Search DuckDuckGo using DDGS library."""
                try:
                    results, error = _collect_ddgs_results(query, max_items=5)
                    if error and not results:
                        return f"Search error: {error}"
                    if not results:
                        return "No search results found."

                    formatted_results = []
                    for i, result in enumerate(results, 1):
                        title = result.get('title', 'No Title')
                        url = result.get('href', '')
                        snippet = result.get('body', '')
                        formatted_results.append(f"{i}. {title}\nURL: {url}\nSnippet: {snippet}\n")

                    return "\n".join(formatted_results)
                except Exception as e:
                    return f"Search error: {str(e)}"

            ddgs_tool = Tool(
                name="duckduckgo_search",
                description="Search DuckDuckGo for web results. Returns titles, URLs, and snippets of relevant web pages.",
                func=ddgs_search_func
            )

            # Create web content loader tool
            def scrape_web_content(url: str) -> str:
                """Load content from a web URL."""
                try:
                    # Normalize URL (add www for combiphar.com and clean tracking params)
                    normalized_url = self.clean_url(url)

                    combiphar_content = self._fetch_combiphar_content(normalized_url)
                    if combiphar_content:
                        return f"Content from {normalized_url}:\n{combiphar_content}"

                    # Using PlaywrightURLLoader
                    loader = PlaywrightURLLoader(
                        urls=[normalized_url],
                        remove_selectors=["header", "nav", "footer"]
                    )
                    docs = loader.load()

                    if docs and docs[0].page_content:
                        content = docs[0].page_content[:2000]  # Limit content
                        if len(content) > 50:  # minimal panjang konten
                            return f"Content from {normalized_url}:\n{content}"

                    return ""
                except Exception as e:
                    return ""

            # Create custom tools for the agent
            web_scrape_tool = Tool(
                name="web_content_scrape",
                description="Load content from a specific web URL. Use this after getting URLs from search results to get detailed content.",
                func=scrape_web_content
            )

            # Define tools for the agent
            tools = [ddgs_tool, web_scrape_tool]
            if current_datetime_tool is not None:
                tools.append(current_datetime_tool)
            if current_context_tool is not None:
                tools.append(current_context_tool)

            # Create system prompt for the tool calling agent
            system_prompt = self.prompt_service.create_robust_prompt_template(
                system_template=system_prompts.CORPORATE_RESEARCH_TOOL_AGENT_PROMPT,
                user_template="{input}",
                query=enhanced_query,
                original_question=original_question,
                combiphar_websites=", ".join(combiphar_websites)
            )

            # Create the tool calling agent
            if not self.llm:
                return []
            agent = create_tool_calling_agent(self.llm, tools, system_prompt)

            # Create agent executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=5,
                handle_parsing_errors=True
            )

            # Execute the agent
            logging.info("🤖 Executing tool calling agent for web search...")

            # Prepare input for the agent
            agent_input = {
                "input": f"Search for information about: {enhanced_query}"
            }

            # Run the agent
            response = agent_executor.invoke(agent_input)

            if response and response.get('output'):
                # Parse the agent's response and extract search results
                agent_output = response['output']

                # First, try to extract URLs and detailed sources from intermediate steps
                urls_found = set()
                if 'intermediate_steps' in response:
                    for step in response['intermediate_steps']:
                        if len(step) >= 2:
                            action, observation = step[0], step[1]

                            # Extract URLs from DuckDuckGo search results
                            if hasattr(action, 'tool') and action.tool == 'duckduckgo_search':
                                # Parse DuckDuckGo search results from observation
                                url_pattern = r'https?://[^\s\],]+'
                                urls_in_observation = re.findall(url_pattern, str(observation))

                                # Extract title and URL pairs from DuckDuckGo results
                                lines = str(observation).split('\n')
                                for line in lines:
                                    if 'http' in line:
                                        # Try to extract title and URL from DuckDuckGo result line
                                        url_match = re.search(url_pattern, line)
                                        if url_match:
                                            url = url_match.group()
                                            urls_found.add(url)

                                            # Extract title (text before the URL)
                                            title_part = line[:url_match.start()].strip()
                                            title = title_part if title_part else url

                                            search_results.append({
                                                'title': title,
                                                'url': url,
                                                'content': line.strip(),
                                                'score': 0.9
                                            })

                            # Extract content from web_content_loader
                            elif hasattr(action, 'tool') and action.tool == 'web_content_loader':
                                url = action.tool_input if isinstance(action.tool_input, str) else str(action.tool_input)
                                if url.startswith('http') and url not in urls_found:
                                    urls_found.add(url)
                                    search_results.append({
                                        'title': f'Detailed Content: {url}',
                                        'url': url,
                                        'content': observation[:1500] if observation else 'Content not available',
                                        'score': 0.95  # Higher score for detailed content
                                    })

                # If no specific URLs were found, create a comprehensive result with extracted URLs
                if not search_results:
                    # Try to extract URLs directly from the agent output
                    url_pattern = r'https?://[^\s\],]+'
                    urls_in_output = re.findall(url_pattern, agent_output)

                    if urls_in_output:
                        # Create individual results for each URL found
                        for url in urls_in_output[:5]:  # Limit to 5 URLs
                            search_results.append({
                                'title': url,
                                'url': url,
                                'content': agent_output,
                                'score': 0.8
                            })
                    else:
                        # Fallback: create a single comprehensive result
                        search_results.append({
                            'title': f"Comprehensive Search Results for: {original_question}",
                            'url': 'https://duckduckgo.com/search',
                            'content': agent_output,
                            'score': 0.7  # Lower score since no specific URLs
                        })

                # Deduplicate results by cleaned URL, keep item with best score/content length
                if search_results:
                    dedup: Dict[str, Dict[str, Any]] = {}
                    for item in search_results:
                        raw_url = item.get('url', '')
                        cleaned = self.clean_url(raw_url)
                        # Build a stable key: prefer URL; fallback to title snippet
                        fallback_key = (item.get('title') or '')[:100].strip()
                        key = cleaned if cleaned else fallback_key
                        cur = dedup.get(key)
                        score = float(item.get('score', 0.0) or 0.0)
                        content_len = len((item.get('content') or '').strip())
                        quality = (score, content_len)
                        if not cur:
                            dedup[key] = item
                            dedup[key]['_quality'] = quality
                        else:
                            cur_quality = cur.get('_quality', (0.0, 0))
                            if quality > cur_quality:
                                item['_quality'] = quality
                                dedup[key] = item
                    # Rebuild list preserving relative order by first appearance
                    seen = set()
                    unique_results: List[Dict[str, Any]] = []
                    for item in search_results:
                        cleaned = self.clean_url(item.get('url', ''))
                        fallback_key = (item.get('title') or '')[:100].strip()
                        key = cleaned if cleaned else fallback_key
                        if key in seen:
                            continue
                        seen.add(key)
                        unique_results.append(dedup.get(key, item))
                    search_results = unique_results

                logging.info(f"✅ Tool calling agent returned {len(search_results)} unique results with {len(urls_found)} URLs parsed")

        except Exception as e:
            logging.error(f"Tool calling agent search failed: {e}")
            # Fallback to simple DDGS search
            try:
                logging.info("🔍 Falling back to simple DDGS search...")
                with DDGS(verify=True) as ddgs:
                    results = list(ddgs.text(enhanced_query, backend="auto", max_results=5))

                    if results:
                        for result in results:
                            search_results.append({
                                'title': result.get('title', 'No Title'),
                                'url': result.get('href', ''),
                                'content': result.get('body', ''),
                                'score': 0.7
                            })

            except Exception as fallback_error:
                message = self._describe_ddgs_error(fallback_error)
                if self._is_recoverable_ddgs_error(fallback_error):
                    logging.warning(f"Fallback DDGS search encountered network issue: {message}")
                else:
                    logging.error(f"Fallback DDGS search also failed: {message}")

            # Final fallback: try to extract any URLs mentioned in the enhanced query response
            if not search_results:
                try:
                    logging.info("🔍 Attempting final search with DDGS...")
                    with DDGS(verify=False) as ddgs:
                        results = list(ddgs.text(original_question, backend="auto", max_results=3))  # Use original question

                        if results:
                            for i, result in enumerate(results, 1):
                                search_results.append({
                                    'title': result.get('title', f"Search Result {i}"),
                                    'url': result.get('href', ''),
                                    'content': result.get('body', ''),
                                    'score': 0.6 + (0.1 * (4-i))  # Decreasing score
                                })
                        else:
                            # No results found at all
                            search_results.append({
                                'title': f"No results found for: {original_question}",
                                'url': 'https://duckduckgo.com/search',
                                'content': f"No search results were found for the query: {original_question}",
                                'score': 0.1
                            })

                except Exception as final_error:
                    message = self._describe_ddgs_error(final_error)
                    if self._is_recoverable_ddgs_error(final_error):
                        logging.warning(f"Final fallback DDGS search encountered network issue: {message}")
                    else:
                        logging.error(f"Final fallback DDGS search failed: {message}")

        return search_results
    def search_general_gpt(self, question: str, chat_history: Optional[List[Tuple[str, str]]] = None) -> Dict[str, Any]:
        """
        Search for answers using general GPT with better context for complex questions.
        """
        try:
            if not self.llm:
                return {
                    "answer": "Maaf, sistem sedang offline.",
                    "source_documents": [],
                    "confidence": 0.0
                }

            # Build context from chat history if available
            context_from_history = ""
            if chat_history and len(chat_history) > 0:
                recent_context = chat_history[-3:]  # Last 3 exchanges for context
                context_parts = []
                for q, a in recent_context:
                    context_parts.append(f"Q: {q}\nA: {a[:200]}...")  # Truncate long answers
                context_from_history = "\n\nKonteks percakapan sebelumnya:\n" + "\n\n".join(context_parts)

            # Enhanced prompt template with better context
            current_year = time.localtime().tm_year
            current_month = time.localtime().tm_mon
            current_day = time.localtime().tm_mday

            prompt_template = self.prompt_service.create_robust_prompt_template(
                system_template=system_prompts.GENERAL_GPT_PROMPT,
                user_template="{question}{context_from_history}",
                current_year=current_year,
                current_month=current_month,
                current_day=current_day
            )

            formatted_messages = self.prompt_service.safe_format_messages(
                prompt_template,
                question=question,
                context_from_history=context_from_history,
                current_year=current_year,
                current_month=current_month,
                current_day=current_day
            )
            try:
                result = self.llm.invoke(formatted_messages)
                answer_text = str(result.content) if hasattr(result, "content") else str(result)
            except (AuthenticationError, RateLimitError, APIError) as e:
                logging.error(f"❌ OpenAI API error in combiphar site search: {e}")
                return {
                    "answer": ErrorHandler.get_message("token_empty", "Terjadi kesalahan dengan API OpenAI"),
                    "source_documents": [],
                    "confidence": 0
                }

            # Validate answer quality
            if len(answer_text.strip()) < 50:
                # If answer is too short, try with more explicit instructions
                fallback_prompt = self.prompt_service.create_robust_prompt_template(
                    system_template=system_prompts.GENERAL_GPT_FALLBACK_PROMPT,
                    user_template="{question}{context_from_history}",
                    current_year=current_year,
                    current_month=current_month,
                    current_day=current_day
                )

                fallback_messages = self.prompt_service.safe_format_messages(
                    fallback_prompt,
                    question=question,
                    context_from_history=context_from_history,
                    current_year=current_year,
                    current_month=current_month,
                    current_day=current_day
                )
                try:
                    result = self.llm.invoke(fallback_messages)
                    answer_text = str(result.content) if hasattr(result, "content") else str(result)
                except (AuthenticationError, RateLimitError, APIError) as e:
                    logging.error(f"❌ OpenAI API error in combiphar site search fallback: {e}")
                    return {
                        "answer": ErrorHandler.get_message("token_empty", "Terjadi kesalahan dengan API OpenAI"),
                        "source_documents": [],
                        "confidence": 0
                    }

            return {
                "answer": answer_text,
                "source_documents": [],
                "confidence": 0.6 if len(answer_text) > 200 else 0.4  # Higher confidence for detailed answers
            }

        except Exception as e:
            logging.error(f"Error in general GPT search: {e}")
            return {
                "answer": f"Maaf, terjadi kesalahan saat memproses pertanyaan Anda. Silakan coba lagi atau reformulasi pertanyaan dengan lebih spesifik.",
                "source_documents": [],
                "confidence": 0.0
            }
