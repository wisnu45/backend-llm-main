import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from openai import APIError, AuthenticationError, RateLimitError
except Exception:  # noqa: BLE001
    # Allow importing this module in minimal environments (e.g., unit tests)
    # where the optional `openai` dependency is not installed.
    class APIError(Exception):
        pass

    class AuthenticationError(Exception):
        pass

    class RateLimitError(Exception):
        pass

try:
    from app.services.agent.prompt_service import PromptService
except Exception:  # noqa: BLE001
    PromptService = None  # type: ignore[assignment]

logger = logging.getLogger("agent.intent_predictor")


class IntentPredictor:
    """
    Intent predictor for LLM-first question digestion and company-insight confirmation.
    """

    def __init__(
        self,
        company_name: Optional[str] = None,
        llm: Optional[Any] = None,
        prompt_service: Optional[PromptService] = None,
    ):
        self.company_name = (company_name or os.getenv("COMPANY_NAME", "Combiphar")).strip()
        try:
            self.low_score_threshold = float(
                os.getenv("INTENT_CONFIRM_SCORE_THRESHOLD", "0.12")
            )
        except Exception:
            self.low_score_threshold = 0.12

        try:
            self.clarification_score_threshold = float(
                os.getenv("CLARIFICATION_SCORE_THRESHOLD", str(self.low_score_threshold))
            )
        except Exception:
            self.clarification_score_threshold = self.low_score_threshold

        self.llm = llm
        if prompt_service is not None:
            self.prompt_service = prompt_service
        elif PromptService is not None:
            self.prompt_service = PromptService()
        else:
            self.prompt_service = None
        self._intent_prompt = None
        self._clarification_prompt = None
        self._clarification_merge_prompt = None
        self._confirmation_decision_prompt = None
        self._allowed_intents = {"small_talk", "ambiguous", "question"}
        self._allowed_subtypes = {"greeting", "thanks", "bye", "affirmation", "none"}
        self._init_intent_prompt()
        self._init_clarification_prompts()
        self._init_confirmation_decision_prompt()
        self._hr_keywords = {
            "cuti",
            "lembur",
            "gaji",
            "thr",
            "tunjangan",
            "absen",
            "absensi",
            "izin",
            "ijin",
            "wfh",
            "work from home",
            "pensiun",
            "mutasi",
            "promosi",
            "kp",
            "kontrak",
            "phk",
            "offboarding",
            "onboarding",
        }

        # Phrases we inject in clarification prompts so we can detect and avoid repeating them
        self._confirmation_markers = (
            "jawab \"benar\"",
            "jawab 'benar'",
            "balas \"benar\"",
            "balas 'benar'",
            "konfirmasi maksud",
            "klarifikasi maksud",
        )
        # Tokens that count as a "yes/confirm" reply when the bot asked for confirmation.
        # Keep these short, high-signal, and language-agnostic.
        self._affirmative_tokens = {
            # Indonesian
            "benar",
            "bener",
            "betul",
            "iya",
            "ya",
            "setuju",
            "sip",
            "siap",
            "baik",
            "noted",
            "lanjut",
            "lanjutkan",
            # Common chat variants
            "ok",
            "oke",
            "okey",
            "okelah",
            "y",
            "yep",
            "yup",
            # English
            "yes",
            "sure",
            "agree",
            "correct",
            "confirmed",
        }
        self._negative_tokens = {
            # Indonesian
            "tidak",
            "ga",
            "gak",
            "nggak",
            "enggak",
            "bukan",
            "jangan",
            "batal",
            "salah",
            "beda",
            "keliru",
            # English
            "no",
            "nope",
            "cancel",
            "cancelled",
            "wrong",
        }
        self._clarification_markers = (
            "konfirmasi konteks pertanyaan",
        )

    def _normalize_short_reply(self, text: Optional[str]) -> str:
        if not text:
            return ""
        normalized = re.sub(r"\s+", " ", str(text).strip().lower())
        # Remove most punctuation, keep alnum+space to stabilize tokens.
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _init_confirmation_decision_prompt(self) -> None:
        """Initialize prompt template for LLM-based confirmation classification."""
        if not self.prompt_service:
            self._confirmation_decision_prompt = None
            return

        system_template = (
            "Anda adalah classifier biner untuk balasan user terhadap pertanyaan konfirmasi. "
            "Konteks: bot baru saja menanyakan pertanyaan ya/tidak untuk mengonfirmasi maksud user. "
            "Tugas: tentukan apakah balasan user berarti SETUJU/KONFIRMASI (true) atau TIDAK/BUKAN/menolak/meralat (false). "
            "Jika balasan ambigu, tidak menjawab konfirmasi, atau menanyakan balik, pilih false. "
            "Keluaran WAJIB hanya satu token lowercase: true atau false.\n\n"
            "Contoh (balasan user -> keluaran):\n"
            "- 'benar' -> true\n"
            "- 'ya' -> true\n"
            "- 'iya' -> true\n"
            "- 'ok' -> true\n"
            "- 'oke' -> true\n"
            "- 'setuju' -> true\n"
            "- 'tidak' -> false\n"
            "- 'bukan' -> false\n"
            "- 'nggak' -> false\n"
            "- 'ga' -> false\n"
            "- 'gak' -> false\n"
            "- 'batal' -> false\n"
            "- 'jelasin lagi' -> false\n"
            "- 'maksudnya apa?' -> false\n"
        )

        try:
            self._confirmation_decision_prompt = self.prompt_service.create_robust_prompt_template(
                system_template=system_template,
                user_template=(
                    "PROMPT_KONFIRMASI_BOT: {confirmation_prompt}\n"
                    "BALASAN_USER: {user_reply}\n"
                    "KELUARAN (true/false saja):"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Confirmation decision prompt init failed: %s", exc)
            self._confirmation_decision_prompt = None

    def _parse_llm_bool(self, text: str) -> Optional[bool]:
        if not text:
            return None
        raw = str(text).strip().lower()

        # Handle JSON-y outputs e.g. {"confirm": true}
        if "true" in raw or "false" in raw:
            match = re.search(r"\b(true|false)\b", raw)
            if match:
                return match.group(1) == "true"
        return None

    def _fast_confirmation_heuristic(self, user_reply: Optional[str]) -> Optional[bool]:
        if not user_reply:
            return None
        text = self._normalize_short_reply(user_reply)
        if not text:
            return None
        text = re.sub(r"(.)\1{2,}", r"\1\1", text)
        tokens = set(text.split())
        if "okay" in tokens:
            tokens.add("ok")
        aff = any(t in self._affirmative_tokens for t in tokens)
        neg = any(t in self._negative_tokens for t in tokens)
        if neg and not aff:
            return False
        if aff and not neg:
            return True
        if aff and neg:
            return False
        return None

    def _llm_decide_confirmation(self, user_reply: Optional[str]) -> Optional[bool]:
        """Ask the LLM to return strict true/false for a confirmation reply."""
        if not user_reply:
            return False
        if not self.llm or not self.prompt_service or not self._confirmation_decision_prompt:
            return None

        try:
            formatted_messages = self.prompt_service.safe_format_messages(
                self._confirmation_decision_prompt,
                user_reply=str(user_reply),
            )
            result = self.llm.invoke(formatted_messages)
            response_text = str(result.content) if hasattr(result, "content") else str(result)
            return self._parse_llm_bool(response_text)
        except (AuthenticationError, RateLimitError, APIError) as exc:
            logger.warning("Confirmation decision LLM error: %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Confirmation decision failed: %s", exc)
            return None

    def is_user_confirmation_reply(
        self,
        user_reply: Optional[str],
        confirmation_prompt: Optional[str] = None,
    ) -> bool:
        if not user_reply:
            return False
        fast = self._fast_confirmation_heuristic(user_reply)
        if fast is not None:
            return bool(fast)
        if not self.llm or not self.prompt_service or not self._confirmation_decision_prompt:
            return False
        try:
            formatted_messages = self.prompt_service.safe_format_messages(
                self._confirmation_decision_prompt,
                user_reply=str(user_reply),
                confirmation_prompt=str(confirmation_prompt or ""),
            )
            result = self.llm.invoke(formatted_messages)
            response_text = str(result.content) if hasattr(result, "content") else str(result)
            parsed = self._parse_llm_bool(response_text)
            return bool(parsed) if parsed is not None else False
        except (AuthenticationError, RateLimitError, APIError) as exc:
            logger.warning("Confirmation decision LLM error: %s", exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Confirmation decision failed: %s", exc)
            return False

    def _init_intent_prompt(self) -> None:
        """Initialize the prompt template for intent digestion."""
        if not self.prompt_service:
            self._intent_prompt = None
            return
        try:
            import app.services.agent.system_prompts as system_prompts
            self._intent_prompt = self.prompt_service.create_robust_prompt_template(
                system_template=system_prompts.INTENT_DIGEST_PROMPT,
                user_template="PERTANYAAN: {question}\nRIWAYAT:\n{chat_history}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Intent digest prompt init failed: %s", exc)
            self._intent_prompt = None

    def _init_clarification_prompts(self) -> None:
        """Initialize prompt templates for clarification flow."""
        if not self.prompt_service:
            self._clarification_prompt = None
            self._clarification_merge_prompt = None
            return
        try:
            import app.services.agent.system_prompts as system_prompts
            self._clarification_prompt = self.prompt_service.create_robust_prompt_template(
                system_template=system_prompts.INTENT_CLARIFICATION_PROMPT,
                user_template="PERTANYAAN: {question}\nRIWAYAT:\n{chat_history}\nALASAN: {reason}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Intent clarification prompt init failed: %s", exc)
            self._clarification_prompt = None

        try:
            import app.services.agent.system_prompts as system_prompts
            self._clarification_merge_prompt = self.prompt_service.create_robust_prompt_template(
                system_template=system_prompts.INTENT_CLARIFICATION_MERGE_PROMPT,
                user_template=(
                    "PERTANYAAN_AWAL: {base_question}\n"
                    "JAWABAN_USER: {user_response}\n"
                    "OPSI: {options}"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Intent clarification merge prompt init failed: %s", exc)
            self._clarification_merge_prompt = None

    def _normalize_for_digest(self, question: str) -> str:
        """Normalize question for intent digestion without losing punctuation."""
        return re.sub(r"\s+", " ", str(question or "").strip())

    def _build_history_context(
        self, chat_history: Optional[List[Tuple[str, str]]], limit: int = 3
    ) -> str:
        """Summarize recent chat history for intent digestion."""
        if not chat_history:
            return ""
        history_parts: List[str] = []
        try:
            turns = int(os.getenv("INTENT_HISTORY_TURNS", "5"))
        except Exception:
            turns = 5
        try:
            max_chars = int(os.getenv("INTENT_HISTORY_MAX_CHARS", "1100"))
        except Exception:
            max_chars = 1100
        try:
            max_answer_chars = int(os.getenv("INTENT_HISTORY_MAX_ANSWER_CHARS", "220"))
        except Exception:
            max_answer_chars = 220

        turns = max(1, min(turns, 12))
        max_chars = max(200, min(max_chars, 6000))
        max_answer_chars = max(80, min(max_answer_chars, 1200))

        recent = chat_history[-turns:]
        total_chars = 0
        for idx, (q, a) in enumerate(recent, start=1):
            q_s = str(q).strip()
            a_s = str(a).strip()

            q_norm = re.sub(r"\s+", " ", q_s.lower()).strip()
            q_norm = re.sub(r"[^\w\s]", " ", q_norm)
            q_norm = re.sub(r"\s+", " ", q_norm).strip()
            if (
                len(q_norm) <= 2
                or q_norm in {"benar", "ya", "iya", "ok", "oke", "y", "a", "b", "c"}
            ):
                continue

            if len(a_s) > max_answer_chars:
                a_s = a_s[:max_answer_chars] + "..."
            chunk = f"Q{idx}: {q_s}\nA{idx}: {a_s}"
            if total_chars + len(chunk) > max_chars:
                break
            history_parts.append(chunk)
            total_chars += len(chunk)
        return "\n\n".join(history_parts)

    def _parse_intent_payload(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON payload from LLM intent response."""
        if not response_text:
            return None
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return None
        return None

    def digest_question(
        self,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze user intent and normalize question using LLM when available.

        Returns:
            dict with keys: intent, subtype, normalized_question, confidence, source
        """
        normalized_input = self._normalize_for_digest(question)
        if not normalized_input:
            return {
                "intent": "ambiguous",
                "subtype": "none",
                "normalized_question": normalized_input,
                "confidence": 0.0,
                "source": "empty",
            }

        if not self.llm or not self._intent_prompt:
            return {
                "intent": "question",
                "subtype": "none",
                "normalized_question": normalized_input,
                "confidence": 0.0,
                "source": "fallback",
            }

        history_text = self._build_history_context(chat_history)
        try:
            formatted_messages = self.prompt_service.safe_format_messages(
                self._intent_prompt,
                question=normalized_input,
                chat_history=history_text,
            )
            result = self.llm.invoke(formatted_messages)
            response_text = str(result.content) if hasattr(result, "content") else str(result)
        except (AuthenticationError, RateLimitError, APIError) as exc:
            logger.warning("Intent digest LLM error: %s", exc)
            return {
                "intent": "question",
                "subtype": "none",
                "normalized_question": normalized_input,
                "confidence": 0.0,
                "source": "fallback",
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Intent digest failed: %s", exc)
            return {
                "intent": "question",
                "subtype": "none",
                "normalized_question": normalized_input,
                "confidence": 0.0,
                "source": "fallback",
            }

        payload = self._parse_intent_payload(response_text)
        if not payload:
            logger.warning("Intent digest JSON parse failed: %s", response_text)
            return {
                "intent": "question",
                "subtype": "none",
                "normalized_question": normalized_input,
                "confidence": 0.0,
                "source": "fallback",
            }

        intent = str(payload.get("intent", "")).strip().lower()
        if intent not in self._allowed_intents:
            intent = "question"

        subtype = str(payload.get("subtype", "")).strip().lower()
        if subtype not in self._allowed_subtypes:
            subtype = "none"

        normalized_question = payload.get("normalized_question")
        if not normalized_question or not isinstance(normalized_question, str):
            normalized_question = normalized_input
        else:
            normalized_question = self._normalize_for_digest(normalized_question)
            if not normalized_question:
                normalized_question = normalized_input

        confidence_raw = payload.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(confidence, 1.0))

        return {
            "intent": intent,
            "subtype": subtype,
            "normalized_question": normalized_question,
            "confidence": confidence,
            "source": "llm",
        }

    def is_clarification_prompt(self, answer_text: Optional[str]) -> bool:
        """Check whether a bot answer is a clarification prompt we sent."""
        if not answer_text:
            return False
        ans = str(answer_text).lower()
        return any(marker in ans for marker in self._clarification_markers)

    def _already_requested_clarification(
        self, chat_history: Optional[List[Tuple[str, str]]]
    ) -> bool:
        """Avoid spamming the same clarification twice in a row."""
        if not chat_history:
            return False
        try:
            return self.is_clarification_prompt(chat_history[-1][1])
        except Exception:
            return False

    def count_recent_clarifications(
        self, chat_history: Optional[List[Tuple[str, str]]], window: int = 4
    ) -> int:
        """Count how many clarification prompts were sent recently."""
        if not chat_history:
            return 0
        try:
            recent = chat_history[-window:]
            return sum(1 for _, ans in recent if self.is_clarification_prompt(ans))
        except Exception:
            return 0

    def _should_clarify_low_signal(
        self, doc_count: Optional[int], top_score: Optional[float]
    ) -> bool:
        """Decide whether to request clarification after low-signal retrieval."""
        if doc_count is None:
            return False
        if doc_count == 0:
            return True
        if top_score is None:
            return True
        try:
            return float(top_score) < float(self.clarification_score_threshold)
        except Exception:
            return True

    def _clean_option(self, value: str) -> str:
        """Normalize option text for clarification prompts."""
        cleaned = re.sub(r"\s+", " ", str(value or "").strip())
        return cleaned.rstrip(" .,:;")

    def _extract_options_from_prompt(self, answer_text: Optional[str]) -> List[str]:
        """Extract lettered options from a clarification prompt message."""
        if not answer_text:
            return []
        options: List[str] = []
        for line in str(answer_text).splitlines():
            match = re.match(r"^[A-Da-d][\)\.]\s*(.+)$", line.strip())
            if match:
                value = self._clean_option(match.group(1))
                if value:
                    options.append(value)
        return options

    def _resolve_option_selection(self, response: str, options: List[str]) -> str:
        """Map user response to an option text when possible."""
        if not response:
            return response
        response_clean = re.sub(r"\s+", " ", str(response).strip())
        response_lower = response_clean.lower().strip(" .,:;!?")
        if not options:
            return response_clean

        tokens = re.findall(r"[a-d]|\d+", response_lower)
        for token in tokens:
            if token in {"a", "b", "c", "d"}:
                idx = ord(token) - ord("a")
                if 0 <= idx < len(options):
                    return options[idx]
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(options):
                    return options[idx]

        for opt in options:
            if response_lower == opt.lower():
                return opt

        return response_clean

    def build_intent_clarification(
        self,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        reason: str = "ambiguous",
    ) -> Optional[Dict[str, Any]]:
        """
        Build a clarification prompt to gather missing context.
        Returns dict with message/confidence if available.
        """
        if not question or not isinstance(question, str):
            return None
        if not self.llm or not self._clarification_prompt:
            return None

        cleaned_question = self._clean_question(question)
        history_text = self._build_history_context(chat_history)

        try:
            formatted_messages = self.prompt_service.safe_format_messages(
                self._clarification_prompt,
                question=cleaned_question,
                chat_history=history_text,
                reason=reason,
            )
            result = self.llm.invoke(formatted_messages)
            response_text = str(result.content) if hasattr(result, "content") else str(result)
        except (AuthenticationError, RateLimitError, APIError) as exc:
            logger.warning("Intent clarification LLM error: %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Intent clarification failed: %s", exc)
            return None

        payload = self._parse_intent_payload(response_text)
        if not payload:
            logger.warning("Intent clarification JSON parse failed: %s", response_text)
            return None

        clarification_question = payload.get("clarification_question")
        if not clarification_question or not isinstance(clarification_question, str):
            return None
        clarification_question = self._clean_question(clarification_question)

        options_raw = payload.get("options", [])
        options: List[str] = []
        if isinstance(options_raw, list):
            for opt in options_raw:
                cleaned = self._clean_option(opt)
                if cleaned and cleaned.lower() not in {o.lower() for o in options}:
                    options.append(cleaned)
        elif isinstance(options_raw, str):
            for line in options_raw.splitlines():
                cleaned = self._clean_option(line)
                if cleaned:
                    options.append(cleaned)

        if len(options) > 4:
            options = options[:4]

        message_lines = [
            f"Konfirmasi konteks pertanyaan \"{cleaned_question}\":",
            clarification_question,
        ]
        if options:
            message_lines.append("Pilih salah satu:")
            for idx, opt in enumerate(options):
                label = chr(ord("A") + idx)
                message_lines.append(f"{label}) {opt}")
        message_lines.append(
            "Jika belum sesuai, jelaskan singkat agar saya bisa mencari jawaban yang tepat."
        )

        confidence_raw = payload.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(confidence, 1.0))

        return {
            "message": "\n".join(message_lines),
            "confidence": confidence,
            "reason": f"intent_clarification_{reason}",
        }

    def maybe_build_intent_clarification(
        self,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        reason: str = "ambiguous",
        doc_count: Optional[int] = None,
        top_score: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Decide whether to ask for clarification based on reason and retrieval signal."""
        if not question or not isinstance(question, str):
            return None
        if self._already_requested_clarification(chat_history):
            return None
        if self.count_recent_clarifications(chat_history) >= 2:
            return None
        if reason == "low_signal" and not self._should_clarify_low_signal(doc_count, top_score):
            return None
        return self.build_intent_clarification(question, chat_history=chat_history, reason=reason)

    def merge_clarification_response(
        self,
        base_question: str,
        user_response: str,
        clarification_prompt: Optional[str] = None,
    ) -> Optional[str]:
        """
        Merge clarification response into a clearer question.
        """
        if not base_question or not user_response:
            return None

        base_clean = self._clean_question(base_question)
        options = self._extract_options_from_prompt(clarification_prompt)
        resolved_response = self._resolve_option_selection(user_response, options)

        if not self.llm or not self._clarification_merge_prompt:
            if resolved_response:
                return f"{base_clean} ({resolved_response})"
            return base_clean

        options_text = "; ".join(options) if options else "-"
        try:
            formatted_messages = self.prompt_service.safe_format_messages(
                self._clarification_merge_prompt,
                base_question=base_clean,
                user_response=resolved_response,
                options=options_text,
            )
            result = self.llm.invoke(formatted_messages)
            response_text = str(result.content) if hasattr(result, "content") else str(result)
        except (AuthenticationError, RateLimitError, APIError) as exc:
            logger.warning("Clarification merge LLM error: %s", exc)
            return f"{base_clean} ({resolved_response})" if resolved_response else base_clean
        except Exception as exc:  # noqa: BLE001
            logger.warning("Clarification merge failed: %s", exc)
            return f"{base_clean} ({resolved_response})" if resolved_response else base_clean

        payload = self._parse_intent_payload(response_text)
        if not payload:
            return f"{base_clean} ({resolved_response})" if resolved_response else base_clean

        clarified = payload.get("clarified_question")
        if not clarified or not isinstance(clarified, str):
            return f"{base_clean} ({resolved_response})" if resolved_response else base_clean

        clarified_clean = self._clean_question(clarified)
        return clarified_clean or base_clean

    def is_enabled(self, user_data: Optional[dict] = None) -> bool:
        """Check feature flag for company insight."""
        try:
            # Lazy import to avoid requiring DB deps (psycopg2) during pure-unit tests.
            from app.utils.permission import check_feature_access
            return bool(check_feature_access("company_insight", user_data=user_data))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Intent predictor flag lookup failed: %s", exc)
            return False

    def is_user_affirmation(self, text: Optional[str]) -> bool:
        """Detect if user replied with a confirmation like 'Benar/Yes'."""
        # LLM-only: keep legacy name but do not use heuristic fallback.
        return self.is_user_confirmation_reply(user_reply=text)

    def is_confirmation_prompt(self, answer_text: Optional[str]) -> bool:
        """Check whether a bot answer is a confirmation prompt we previously sent."""
        if not answer_text:
            return False
        ans = str(answer_text).lower()
        if any(marker in ans for marker in self._confirmation_markers):
            return True

        # Robust fallback: handle different quote styles / translated variants.
        normalized = re.sub(r"[^\w\s]", " ", ans)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return bool(
            re.search(
                r"\b(jawab|balas)\b.*\b(benar|betul|correct|yes)\b",
                normalized,
                re.IGNORECASE,
            )
        )

    def _already_requested_confirmation(
        self, chat_history: Optional[List[Tuple[str, str]]]
    ) -> bool:
        """Avoid spamming the same confirmation twice in a row."""
        if not chat_history:
            return False

        try:
            return self.is_confirmation_prompt(chat_history[-1][1])
        except Exception:
            return False

    def count_recent_confirmations(
        self, chat_history: Optional[List[Tuple[str, str]]], window: int = 4
    ) -> int:
        """Count how many confirmation prompts were sent recently."""
        if not chat_history:
            return 0
        try:
            recent = chat_history[-window:]
            return sum(1 for _, ans in recent if self.is_confirmation_prompt(ans))
        except Exception:
            return 0

    def _should_clarify(self, doc_count: int, top_score: Optional[float]) -> bool:
        """Decide whether we should trigger clarification."""
        if doc_count == 0:
            return True

        try:
            if top_score is None:
                return True
            return float(top_score) < float(self.low_score_threshold)
        except Exception:
            return True

    def _clean_question(self, question: str) -> str:
        """Normalize question for display inside clarification prompt."""
        cleaned = re.sub(r"\s+", " ", str(question or "").strip())
        return cleaned.rstrip(" ?!.,")

    def is_short_hr_question(self, question: Optional[str]) -> bool:
        if not question:
            return False
        text = str(question or "").strip().lower()
        if not text:
            return False
        normalized = re.sub(r"[^\w\s]", " ", text)
        tokens = [t for t in normalized.split() if t]
        if not tokens:
            return False
        if len(tokens) > 7:
            return False
        joined = " ".join(tokens)
        for kw in self._hr_keywords:
            if " " in kw:
                if kw in joined:
                    return True
        for t in tokens:
            if t in self._hr_keywords:
                return True
        return False

    def extract_question_from_confirmation(self, answer_text: Optional[str]) -> Optional[str]:
        """Extract proposed question from our confirmation message."""
        if not answer_text:
            return None
        try:
            text = str(answer_text)
            match = re.search(r"pertanyaan \"([^\"]+)\"", text)
            if match:
                return match.group(1).strip()
            # Follow-up confirmations often quote the refined question.
            match = re.search(r"maksud Anda \"([^\"]+)\"\?\s*Jika iya", text, re.IGNORECASE)
            if match:
                return self._clean_question(match.group(1))
            match = re.search(r"maksud (.+?)\?\s*Jika iya", text, re.IGNORECASE)
            if match:
                return self._clean_question(match.group(1))
        except Exception:
            return None
        return None

    def refine_question_for_company(self, question: str) -> str:
        """Make the question more explicit for company insight searches."""
        base = self._clean_question(question)
        base_lower = base.lower()
        if self.company_name and self.company_name.lower() not in base_lower:
            return f"{base} di {self.company_name}"
        if "perusahaan" not in base_lower:
            return f"{base} di perusahaan"
        return base

    def _build_message(self, question: str) -> str:
        """Compose a short clarification message."""
        target = (
            f"{question} di perusahaan {self.company_name}"
            if self.company_name
            else f"{question} terkait informasi perusahaan"
        )

        return (
            f"Saya perlu memastikan konteks pertanyaan \"{question}\"."
            f" Apakah yang Anda maksud {target}? Jika iya, balas \"Benar\" (atau \"Ya\" / \"OK\")."
            " Jika berbeda, jelaskan singkat (misalnya unit, lokasi, atau sistem) supaya saya bisa mencari jawaban yang tepat."
        )

    def build_followup_confirmation(
        self,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Ask a refined confirmation after a failed/low-signal search."""
        if not question:
            return None

        # Prevent infinite loops: max two confirmations in recent history
        if self.count_recent_confirmations(chat_history) >= 2:
            return None

        refined_question = self.refine_question_for_company(question)
        message = (
            "Saya belum menemukan jawaban pasti untuk pertanyaan tersebut."
            f" Apakah maksud Anda \"{refined_question}\"? Jika iya, balas \"Benar\" (atau \"Ya\" / \"OK\")."
            " Jika berbeda, mohon perjelas singkat agar saya bisa mencari ulang."
        )

        return {
            "message": message,
            "confidence": 0.0,
            "reason": "company_insight_followup",
        }

    def maybe_build_company_confirmation(
        self,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        doc_count: int = 0,
        top_score: Optional[float] = None,
        user_data: Optional[dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build a confirmation prompt when company insight retrieval lacks signal.

        Returns:
            dict with message/confidence if a clarification should be sent, otherwise None.
        """
        if not question or not isinstance(question, str):
            return None

        if not self.is_enabled(user_data=user_data):
            return None

        if self._already_requested_confirmation(chat_history):
            return None

        if not self._should_clarify(doc_count=doc_count, top_score=top_score):
            return None

        cleaned_question = self._clean_question(question)
        message = self._build_message(cleaned_question)

        logger.info(
            "Intent predictor triggered confirmation (docs=%s, top_score=%s)",
            doc_count,
            top_score,
        )

        return {
            "message": message,
            "confidence": 0.0,
            "reason": "company_insight_low_signal",
        }


__all__ = ["IntentPredictor"]
