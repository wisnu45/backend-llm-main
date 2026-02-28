"""
Vector Store Service

This module handles all vector store operations including document retrieval,
validation, caching, and PGVector interactions.
"""

import os
import logging
import hashlib
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Any, Optional, Sequence, Set
import re

from langchain_core.documents import Document

# Vector store - use PGVector
from app.utils.pgvectorstore import PGVectorStore, get_vectorstore
from app.utils.database import safe_db_query
from app.utils.document import validate_document_exist_db

logger = logging.getLogger('agent')

class VectorStoreService:
    """
    Service for managing vector store operations and document retrieval.
    """

    def __init__(self):
        """Initialize the vector store service."""
        self.vectorstore = None
        self.retriever = None
        self.embeddings = None
        self._document_metadata_cache = {}
        self._question_doc_relevance_cache = {}
        self._search_cache = {}
        
        # Initialize vector store and components
        self._init_vector_store()
        self._preload_document_metadata()

    # -------------------- Internal helpers for hybrid retrieval (dynamic) --------------------
    _STOPWORDS: Set[str] = {
        # Bahasa Indonesia (umum)
        "yang","untuk","dengan","dan","atau","dari","pada","di","ke","sebagai","ini","itu","ada","karena","adalah","tidak","sudah","akan","dalam","agar","bagi","oleh","atau","jika","juga","lebih","kurang","saja","sangat","dapat","bisa","kini","serta","tanpa","atau","namun","tetapi",
        # English (umum)
        "the","a","an","and","or","of","to","in","on","for","as","is","are","was","were","be","been","by","with","at","from","this","that","these","those","it","its","not","can","could","may","might","should","will","would","about","into","than","then","so","such","very"
    }
    _FOLLOWUP_HINTS: Set[str] = {
        "ini","itu","tersebut","lanjut","lanjutnya","lanjutkan","detailnya","jelaskan","lebih",
        "lebih lanjut","bagaimana","apa lagi","lanjutan","lanjutannya","more","details","those","that"
    }

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        if not isinstance(text, str):
            text = str(text)
        return re.findall(r"[a-z0-9]+", text.lower())

    def _extract_prf_terms(self, docs_and_scores: List[Tuple[Document, float]], question: str, max_docs: int = 12, max_terms: int = 6) -> List[str]:
        """Pseudo-relevance feedback: extract candidate expansion terms from the top documents dynamically.
        No domain-specific rules; purely statistical on retrieved texts.
        """
        if not docs_and_scores:
            return []
        q_tokens = set(self._tokenize(question))
        df: Dict[str, int] = {}
        tf: Dict[str, int] = {}
        used_docs = 0
        for doc, _ in docs_and_scores[:max_docs]:
            text = getattr(doc, "page_content", getattr(doc, "content", ""))
            tokens = self._tokenize(text)
            if not tokens:
                continue
            used_docs += 1
            seen: Set[str] = set()
            for t in tokens:
                if len(t) < 3 or t in self._STOPWORDS:
                    continue
                tf[t] = tf.get(t, 0) + 1
                if t not in seen:
                    df[t] = df.get(t, 0) + 1
                    seen.add(t)

        if used_docs == 0:
            return []

        # Score terms: prefer terms occurring in many docs and fairly frequent
        # but exclude tokens already in the question
        scored: List[Tuple[str, float]] = []
        for t, d in df.items():
            if t in q_tokens:
                continue
            freq = tf.get(t, 0)
            score = (d / used_docs) * (1 + (freq / max(1, sum(tf.values()) / used_docs)))
            # Slightly prefer tokens containing digits or uppercase patterns (encoded as lower here)
            if any(ch.isdigit() for ch in t):
                score *= 1.15
            scored.append((t, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in scored[:max_terms]]

    def _doc_key(self, doc: Document) -> str:
        """Generate a unique key for a document based on its metadata."""
        meta = getattr(doc, "metadata", {}) or {}
        # Use stored_filename as primary key (UUID-based filename from refactoring)
        stored_filename = meta.get("stored_filename")
        if stored_filename:
            return str(stored_filename)

        # Fallback to document_source for backward compatibility
        document_source = meta.get("document_source") or meta.get("source")
        if document_source:
            return str(document_source)

        # Final fallback to content hash
        return str(hash(getattr(doc, "page_content", "")))

    @staticmethod
    def _normalize_for_overlap(text: str) -> str:
        if not isinstance(text, str):
            text = str(text or "")
        text = text.lower()
        # Collapse whitespace and strip punctuation-like noise at the edges
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _filter_question_echoes(
        self,
        docs_and_scores: List[Tuple[Document, float]],
        question: str,
        ratio_threshold: float = 0.92
    ) -> List[Tuple[Document, float]]:
        """Remove chunks that merely restate the question without additional content."""
        if not docs_and_scores or not question:
            return docs_and_scores

        normalized_question = self._normalize_for_overlap(question)
        if not normalized_question or len(normalized_question) < 8:
            return docs_and_scores

        question_tokens = [t for t in self._tokenize(question) if len(t) >= 3]
        question_token_set = {t for t in question_tokens if t not in self._STOPWORDS}

        filtered: List[Tuple[Document, float]] = []
        for doc, score in docs_and_scores:
            content = getattr(doc, "page_content", getattr(doc, "content", "")) or ""
            normalized_content = self._normalize_for_overlap(content)
            if not normalized_content:
                continue

            # Skip purely question-type segments if metadata marks them explicitly
            metadata = getattr(doc, "metadata", {}) or {}
            segment_type = str(metadata.get("segment_type", "")).lower()
            if segment_type in {"question", "pertanyaan", "prompt"}:
                logging.debug(f"🔎 Dropping doc {self._doc_key(doc)} tagged as segment_type={segment_type}")
                continue

            doc_tokens = [t for t in self._tokenize(content) if len(t) >= 3]
            doc_token_set = {t for t in doc_tokens if t not in self._STOPWORDS}

            # Compare limited snippets to avoid quadratic cost on large chunks
            snippet = normalized_content[:1024]
            ratio = SequenceMatcher(None, snippet, normalized_question[:1024]).ratio()

            coverage = 0.0
            if question_token_set:
                coverage = len(doc_token_set & question_token_set) / len(question_token_set)

            doc_is_echo = False
            if ratio >= ratio_threshold and len(normalized_content) <= len(normalized_question) + 60:
                doc_is_echo = True
            elif coverage >= 0.9 and len(doc_token_set) <= len(question_token_set) + 3:
                doc_is_echo = True
            elif coverage >= 0.85 and len(normalized_content) <= len(normalized_question) * 1.2:
                doc_is_echo = True

            if doc_is_echo:
                logging.debug(
                    "🔎 Dropping doc %s because it mirrors the question (ratio=%.2f, coverage=%.2f)",
                    self._doc_key(doc),
                    ratio,
                    coverage,
                )
                continue

            filtered.append((doc, score))

        return filtered

    def _bm25_scores(self, docs_and_scores: List[Tuple[Document, float]], query_tokens: List[str]) -> Dict[str, float]:
        """Compute simple BM25-like lexical scores for each document against the given query tokens.
        Uses only the candidate set (dynamic, no global corpus dependence).
        """
        if not docs_and_scores or not query_tokens:
            return {}

        # Prepare document tokens and statistics
        doc_tokens_list: List[List[str]] = []
        doc_keys: List[str] = []
        df: Dict[str, int] = {}
        total_len = 0
        for doc, _ in docs_and_scores:
            text = getattr(doc, "page_content", getattr(doc, "content", ""))[:5000]
            tokens = [t for t in self._tokenize(text) if len(t) >= 3 and t not in self._STOPWORDS]
            doc_tokens_list.append(tokens)
            key = self._doc_key(doc)
            doc_keys.append(key)
            total_len += len(tokens)
            seen: Set[str] = set()
            for t in tokens:
                if t not in seen:
                    df[t] = df.get(t, 0) + 1
                    seen.add(t)

        N = max(1, len(doc_tokens_list))
        avgdl = max(1.0, total_len / N)

        # Precompute IDF
        idf: Dict[str, float] = {}
        for term in set(query_tokens):
            n_q = df.get(term, 0)
            # BM25 IDF with add-one smoothing
            idf[term] = float(max(0.0, ( (N - n_q + 0.5) / (n_q + 0.5) )))

        k1 = 1.5
        b = 0.75
        scores: Dict[str, float] = {}
        for tokens, key in zip(doc_tokens_list, doc_keys):
            # term frequencies for this doc
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            dl = len(tokens)
            s = 0.0
            for term in query_tokens:
                if term not in tf:
                    continue
                freq = tf[term]
                numerator = idf.get(term, 0.0) * (freq * (k1 + 1))
                denom = freq + k1 * (1 - b + b * (dl / avgdl))
                s += numerator / denom
            scores[key] = s

        # Normalize scores to 0..1
        if scores:
            mn = min(scores.values())
            mx = max(scores.values())
            rng = (mx - mn) or 1.0
            for k in list(scores.keys()):
                scores[k] = (scores[k] - mn) / rng

        return scores

    def _rerank_hybrid(self, docs_and_scores: List[Tuple[Document, float]], question: str, k: int) -> List[Tuple[Document, float]]:
        if not docs_and_scores:
            return []

        # Collect raw vector scores with fallbacks from metadata similarity
        raw_vector_scores: Dict[str, float] = {}
        for doc, score in docs_and_scores:
            key = self._doc_key(doc)
            metadata = getattr(doc, "metadata", {}) or {}
            meta_sim = metadata.get("similarity")
            if isinstance(meta_sim, (int, float)):
                raw = float(meta_sim)
            else:
                raw = float(score) if isinstance(score, (int, float)) else 0.0
            raw_vector_scores[key] = raw

        if raw_vector_scores:
            s_max = max(raw_vector_scores.values())
            s_min = min(raw_vector_scores.values())
        else:
            s_min = s_max = 0.0

        denom = s_max - s_min
        if denom <= 1e-9:
            # If all scores identical, treat positives as perfectly relevant
            normalized_vectors = {
                key: (1.0 if score > 0 else 0.0)
                for key, score in raw_vector_scores.items()
            }
        else:
            normalized_vectors = {
                key: max(0.0, min(1.0, (score - s_min) / denom))
                for key, score in raw_vector_scores.items()
            }

        # Dynamic PRF expansion and lexical BM25 scores
        prf_terms = self._extract_prf_terms(docs_and_scores, question)
        q_tokens = [t for t in self._tokenize(question) if len(t) >= 3 and t not in self._STOPWORDS]
        q_all_tokens = q_tokens + [t for t in prf_terms if t not in q_tokens]
        bm25_map = self._bm25_scores(docs_and_scores, q_all_tokens)

        # Weights (can be adjusted via env later if needed)
        try:
            vector_w = float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.6"))
        except Exception:
            vector_w = 0.6
        lexical_w = 1.0 - vector_w

        sim_floor = 0.0
        try:
            sim_floor = float(os.getenv("VECTOR_SIMILARITY_FLOOR", "0.15"))
        except Exception:
            sim_floor = 0.15

        reranked: List[Tuple[Document, float]] = []
        for doc, s in docs_and_scores:
            key = self._doc_key(doc)
            vec = normalized_vectors.get(key, 0.0)
            raw_vec = raw_vector_scores.get(key, 0.0)
            if raw_vec < sim_floor:
                logging.debug(f"🔎 Dropping doc {key} due to low vector similarity {raw_vec:.3f} < {sim_floor}")
                continue
            lex = bm25_map.get(key, 0.0)
            combined = max(0.0, min(1.0, vector_w * vec + lexical_w * lex))
            try:
                setattr(doc, "score", combined)
                metadata = getattr(doc, "metadata", None)
                if isinstance(metadata, dict):
                    metadata["score"] = combined
                    metadata.setdefault("combined_score", combined)
                    if "vector_similarity" not in metadata:
                        metadata["vector_similarity"] = raw_vec
                    metadata.setdefault("similarity", raw_vec)
                    metadata.setdefault("lexical_score", lex)
            except Exception:
                pass
            reranked.append((doc, combined))

        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked[:k]

    def refine_question_with_docs(
        self,
        question: str,
        docs_and_scores: List[Tuple[Document, float]],
        max_hints: int = 3
    ) -> str:
        """Refine follow-up questions using top document cues."""
        if not question or not docs_and_scores:
            return question

        tokens = self._tokenize(question)
        content_tokens = [t for t in tokens if len(t) >= 3 and t not in self._STOPWORDS]
        pronoun_hit = any(hint in tokens for hint in self._FOLLOWUP_HINTS)
        needs_context = pronoun_hit or len(content_tokens) <= 3
        if not needs_context:
            return question

        prf_terms = self._extract_prf_terms(docs_and_scores, question, max_docs=5, max_terms=6)

        doc_labels: List[str] = []
        for doc, _ in docs_and_scores[:3]:
            metadata = getattr(doc, "metadata", {}) or {}
            for key in ("title", "document_name", "original_filename", "subject", "heading"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    doc_labels.append(value.strip())
                    break

        hints: List[str] = []
        seen: Set[str] = set()
        question_lower = question.lower()

        def _append_hint(value: str) -> None:
            value = (value or "").strip()
            if not value:
                return
            lowered = value.lower()
            if lowered in seen:
                return
            if lowered in question_lower:
                return
            seen.add(lowered)
            hints.append(value)

        for label in doc_labels:
            _append_hint(label)
        for term in prf_terms:
            if term and len(term) >= 3 and term.lower() not in tokens:
                _append_hint(term)

        if not hints:
            return question

        context_items: List[str] = []
        for hint in hints[:max_hints]:
            shortened = " ".join(hint.split())
            if len(shortened) > 60:
                shortened = shortened[:57].rstrip() + "..."
            context_items.append(shortened)

        if not context_items:
            return question

        context_text = ", ".join(context_items)
        base_question = question.strip()
        if not base_question:
            return question

        if base_question.endswith("?"):
            stem = base_question[:-1].strip()
            if not stem:
                return question
            refined = f"{stem} terkait {context_text}?"
        else:
            refined = f"{base_question} terkait {context_text}"
        logger.info(f"📝 Question refined with vector hints: '{question}' → '{refined}'")
        return refined

    def _init_vector_store(self) -> None:
        """Initialize the vector store with PGVector."""
        try:
            # Initialize OpenAI embeddings
            from ...utils.embedding import get_openai_embeddings
            self.embeddings = get_openai_embeddings()

            logging.info("🔗 Connecting to PGVector store")

            # Initialize PGVector store
            self.vectorstore = get_vectorstore()
            
            if not self.vectorstore:
                logging.error("❌ Failed to initialize PGVector store")
                self.retriever = None
                return

            # Create retriever
            self.retriever = self.vectorstore.as_retriever(search_kwargs={'k': 7})
            logging.info("✅ PGVector store and retriever initialized successfully")

        except Exception as e:
            logging.error(f"❌ Failed to initialize vector store: {e}")
            logging.warning("🔄 Vector search will be disabled")
            self.vectorstore = None
            self.retriever = None

    def _preload_document_metadata(self) -> None:
        """Preload document metadata from database for faster filtering."""
        try:
            query = """
                SELECT id, original_filename as document_name, source_type as document_source, metadata, created_at, updated_at
                FROM documents
            """
            result = safe_db_query(query)

            # Check if result is properly unpacked
            if isinstance(result, tuple) and len(result) == 2:
                results, columns = result
                if results and isinstance(results, list) and columns:
                    for row in results:
                        # Convert row + column names to dict (type: ignore for dynamic typing from DB)
                        doc = dict(zip(columns, row))  # type: ignore[arg-type]
                        doc_id = doc.get('id')
                        if doc_id:
                            self._document_metadata_cache[doc_id] = doc
                    logging.info(f"Preloaded metadata for {len(self._document_metadata_cache)} documents")
                else:
                    logging.warning("No document metadata found or invalid results format")
            else:
                logging.warning(f"Unexpected result format from database query: {type(result)}")
        except Exception as e:
            logging.error(f"❌ Failed to preload document metadata: {e}")
            logging.error(f"Results type: {type(result) if 'result' in locals() else 'unknown'}")

    def _validate_document_exists(
        self,
        stored_filename: Optional[str] = None,
        document_id: Optional[str] = None,
        storage_path: Optional[str] = None,
    ) -> bool:
        """
        Validate if a document still exists in the database.
        Args:
            stored_filename (str, optional): The stored filename (UUID-based) to validate
            document_id (str, optional): Document UUID from documents.id
            storage_path (str, optional): Storage path of the document on disk
        Returns:
            bool: True if document exists, False otherwise
        """
        return validate_document_exist_db(
            stored_filename=stored_filename,
            document_id=document_id,
            storage_path=storage_path,
        )

    def _filter_valid_documents(self, docs_and_scores: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """
        Filter out documents that have been deleted from the database.
        Args:
            docs_and_scores: List of (Document, score) tuples from vector search
        Returns:
            List[Tuple[Document, float]]: Filtered list with only valid documents
        """
        valid_docs = []
        invalid_count = 0

        for doc, score in docs_and_scores:
            try:
                metadata = getattr(doc, "metadata", {}) or {}

                stored_filename = metadata.get("stored_filename")
                document_id = metadata.get("document_id")
                storage_path = metadata.get("storage_path")

                if not storage_path:
                    storage_path = metadata.get("document_source")

                if not any([stored_filename, document_id, storage_path]):
                    invalid_count += 1
                    continue

                if self._validate_document_exists(
                    stored_filename=stored_filename,
                    document_id=document_id,
                    storage_path=storage_path,
                ):
                    valid_docs.append((doc, score))
                else:
                    invalid_count += 1
                    logging.info(
                        f"Filtered out deleted/invalid document: "
                        f"{stored_filename or document_id or storage_path}"
                    )

            except Exception as e:
                logging.warning(f"Error processing document validation: {e}")
                invalid_count += 1
                continue

        if invalid_count > 0:
            logging.info(f"Filtered out {invalid_count} invalid/deleted documents from vector search results")

        return valid_docs

    @staticmethod
    def _normalize_source_types(source_types: Optional[Sequence[str]]) -> Optional[List[str]]:
        """Sanitize source type inputs for vectorstore filters."""
        if not source_types:
            return None
        normalized: List[str] = []
        seen = set()
        for raw in source_types:
            if raw is None:
                continue
            value = str(raw).strip().lower()
            if not value or value in seen:
                continue
            normalized.append(value)
            seen.add(value)
        return normalized or None

    def retrieve(self, question: str, k: int = 7, user_data: Dict = None, source_types: Optional[Sequence[str]] = None) -> List[Document]:
        """
        Retrieve relevant documents for a question, filtering out deleted documents.

        Args:
            question (str): The question to find documents for
            k (int): Number of documents to retrieve
            user_data (Dict, optional): User information for access control
            source_types (Sequence[str], optional): Specific document source types to search

        Returns:
            List[Document]: List of valid relevant documents
        """
        try:
            if not self.retriever:
                logging.error("🔍 Retriever not initialized")
                return []

            normalized_sources = self._normalize_source_types(source_types)

            cache_key = self._get_cache_key(
                question,
                k,
                user_data=user_data,
                source_types=normalized_sources
            )
            if cache_key in self._search_cache:
                user_id = user_data.get('user_id') if user_data else 'Unknown'
                logging.info(f"🔍 Using cached search results for user {user_id}")
                return self._search_cache[cache_key]

            logging.info(f"🔍 Retrieving top {k} documents for question: {question}")
            if normalized_sources:
                logging.info(f"🔐 Applying source filter: {normalized_sources}")

            if not self.vectorstore:
                return []

            filter_kwargs = {"source_types": normalized_sources} if normalized_sources else None
            base_k = min(k * 5, 80)
            docs_and_scores = self.vectorstore.similarity_search_with_score(
                question,
                k=base_k,
                filter=filter_kwargs,
                user_data=user_data
            )
            if not docs_and_scores:
                try:
                    docs_and_scores = self.vectorstore.hybrid_search(
                        question,
                        k=base_k
                    )
                except Exception:
                    docs_and_scores = []

            try:
                prf_terms = self._extract_prf_terms(docs_and_scores, question, max_docs=12, max_terms=6)
                if prf_terms:
                    logging.debug(f"PRF terms identified for '{question}': {prf_terms}")
            except Exception:
                prf_terms = []

            valid_docs_and_scores = self._filter_valid_documents(docs_and_scores)

            dedup: Dict[str, Tuple[Document, float]] = {}
            for doc, sc in valid_docs_and_scores:
                key = self._doc_key(doc)
                if key not in dedup or sc > dedup[key][1]:
                    dedup[key] = (doc, sc)

            merged = self._filter_question_echoes(list(dedup.values()), question)

            if len(merged) < max(k, 5):
                try:
                    mmr_docs = self.vectorstore.max_marginal_relevance_search(
                        question,
                        k=max(k * 2, 10),
                        fetch_k=max(k * 4, 20),
                        filter=filter_kwargs,
                        user_data=user_data
                    )
                    for d in mmr_docs:
                        key = self._doc_key(d)
                        if key not in dedup:
                            dedup[key] = (d, 0.0)
                    merged = self._filter_question_echoes(list(dedup.values()), question)
                except Exception:
                    pass

            final_docs_and_scores = self._rerank_hybrid(merged, question, k)
            docs = [doc for doc, _ in final_docs_and_scores]

            self._search_cache[cache_key] = docs
            logging.info(f"🔍 Retrieved {len(docs)} valid documents for question: {question}")
            return docs
        except Exception as e:
            logging.error(f"⚠️ Error retrieving documents: {e}")
            return []




    def retrieve_with_score(self, question: str, k: int = 15, user_data: Dict = None, source_types: Optional[Sequence[str]] = None) -> List[Tuple[Document, float]]:
        """
        Retrieve relevant documents with similarity scores, filtering out deleted documents.

        Args:
            question (str): The question to find documents for
            k (int): Number of documents to retrieve
            user_data (Dict, optional): User information for access control
            source_types (Sequence[str], optional): Specific document source types to search

        Returns:
            List[Tuple[Document, float]]: List of valid documents and their scores
        """
        try:
            if not self.vectorstore:
                logging.error("Vector store not initialized")
                return []

            normalized_sources = self._normalize_source_types(source_types)

            cache_key = self._get_cache_key(
                question,
                k,
                user_data=user_data,
                source_types=normalized_sources
            )
            if cache_key in self._search_cache:
                user_id = user_data.get('user_id') if user_data else 'Unknown'
                logging.info(f"Using cached search results for user {user_id}")
                return self._search_cache[cache_key]

            filter_kwargs = {"source_types": normalized_sources} if normalized_sources else None
            search_k = min(k * 5, 80)

            extra_search_kwargs: Dict[str, Any] = {}
            q_text = (question or "").strip()
            if q_text:
                upper_q = q_text.upper()
                looks_like_product_code = False
                if "PRODUCT CODE" in upper_q:
                    looks_like_product_code = True
                elif re.search(r"\b[A-Z]{2,}\d{1,4}\b", upper_q):
                    looks_like_product_code = True
                if looks_like_product_code:
                    try:
                        override = float(os.getenv("PRODUCT_CODE_SIMILARITY_THRESHOLD", "0.05"))
                    except Exception:
                        override = 0.05
                    extra_search_kwargs["similarity_threshold"] = override

            docs_and_scores = self.vectorstore.similarity_search_with_score(
                question,
                k=search_k,
                filter=filter_kwargs,
                user_data=user_data,
                **extra_search_kwargs,
            )
            if not docs_and_scores:
                try:
                    docs_and_scores = self.vectorstore.hybrid_search(
                        question,
                        k=search_k,
                        **extra_search_kwargs,
                    )
                except Exception:
                    docs_and_scores = []

            try:
                prf_terms = self._extract_prf_terms(docs_and_scores, question, max_docs=12, max_terms=6)
                if prf_terms:
                    logging.debug(f"PRF terms identified for '{question}': {prf_terms}")
            except Exception:
                prf_terms = []

            valid_docs_and_scores = self._filter_valid_documents(docs_and_scores)

            dedup: Dict[str, Tuple[Document, float]] = {}
            for doc, sc in valid_docs_and_scores:
                key = self._doc_key(doc)
                if key not in dedup or sc > dedup[key][1]:
                    dedup[key] = (doc, sc)

            merged = self._filter_question_echoes(list(dedup.values()), question)

            if len(merged) < max(k, 5):
                try:
                    mmr_docs = self.vectorstore.max_marginal_relevance_search(
                        question,
                        k=max(k * 2, 10),
                        fetch_k=max(k * 4, 20),
                        filter=filter_kwargs,
                        user_data=user_data
                    )
                    for d in mmr_docs:
                        key = self._doc_key(d)
                        if key not in dedup:
                            dedup[key] = (d, 0.0)
                    merged = self._filter_question_echoes(list(dedup.values()), question)
                except Exception:
                    pass

            final_docs_and_scores = self._rerank_hybrid(merged, question, k)

            logging.info(
                f"Retrieved {len(docs_and_scores)} docs, {len(valid_docs_and_scores)} valid, "
                f"merged {len(merged)}, returning {len(final_docs_and_scores)} after hybrid rerank"
            )

            self._search_cache[cache_key] = final_docs_and_scores

            return final_docs_and_scores
        except Exception as e:
            logging.error(f"Error retrieving documents with scores: {e}")
            return []

    def retrieve_attachments_with_score(
        self,
        question: str,
        chat_id: str,
        user_data: Dict,
        source_types: Optional[Sequence[str]] = None,
        k_per_file: int = 50,
        similarity_threshold: float = 0.2,
    ) -> List[Tuple[Document, float]]:
        """
        Ambil chunks dokumen berdasarkan chat_id pada tabel documents yang berelasi ke documents_vectors
        dan lakukan similarity search terhadap embedding pertanyaan.

        Returns:
            List of (Document, score) tuples; score is set to 1.0 to prioritize attachments.
        """
        try:
            if not self.vectorstore:
                logging.error("Vector store not initialized")
                return []

            if not chat_id:
                return []

            # Siapkan where_clause tambahan dari source_types jika ada
            where_clause = ""
            where_params: List[Any] = []
            if source_types:
                where_clause = " AND d.source_type = ANY(%s::document_source_type[])"
                where_params.append(list(source_types))

            # Dapatkan embedding untuk question
            query_embedding: Optional[List[float]] = None
            try:
                if self.vectorstore and hasattr(self.vectorstore, "embed_query"):
                    query_embedding = self.vectorstore.embed_query(question, user_data=user_data)
            except Exception as e:
                logging.warning(f"Failed to embed query for attachments search: {e}")

            if not query_embedding:
                # Fallback: jika tidak dapat membuat embedding, tetap ambil berdasarkan chat_id tanpa similarity
                query = f"""
                    SELECT 
                        dv.id,
                        dv.document_id,
                        dv.content,
                        dv.metadata,
                        dv.chunk_index,
                        d.original_filename as document_name,
                        d.stored_filename as stored_filename,
                        d.storage_path as document_source,
                        d.metadata as document_metadata
                    FROM documents_vectors dv
                    JOIN documents d ON dv.document_id = d.id
                    WHERE d.chat_id = %s {where_clause}
                    ORDER BY d.stored_filename, dv.chunk_index
                    LIMIT %s
                """.format(where_clause=where_clause)
                params_all: List[Any] = [chat_id, *where_params, max(50, k_per_file * 10)]
                results, columns = safe_db_query(query, tuple(params_all))
            else:
                # Similarity search menggunakan pgvector distance operator <=>
                query = f"""
                    SELECT 
                        dv.id,
                        dv.document_id,
                        dv.content,
                        1 - (dv.embedding <=> %s) as similarity,
                        dv.metadata,
                        dv.chunk_index,
                        d.original_filename as document_name,
                        d.stored_filename as stored_filename,
                        d.storage_path as document_source,
                        d.metadata as document_metadata
                    FROM documents_vectors dv
                    JOIN documents d ON dv.document_id = d.id
                    WHERE d.chat_id = %s AND 1 - (dv.embedding <=> %s) > %s {where_clause}
                    ORDER BY dv.embedding <=> %s
                    LIMIT %s
                """.format(where_clause=where_clause)

                # params: similarity uses the embedding multiple times per the ORDER/WHERE
                limit_val = max(50, k_per_file * 10)
                params_all = [query_embedding, chat_id, query_embedding, similarity_threshold, *where_params, query_embedding, limit_val]
                results, columns = safe_db_query(query, tuple(params_all))
            if not results:
                return []

            docs_with_scores: List[Tuple[Document, float]] = []
            for row in results:
                row_dict = dict(zip(columns, row))
                meta = {
                    "document_id": str(row_dict["document_id"]),
                    "document_source": row_dict["document_source"],
                    "document_name": row_dict["document_name"],
                    "stored_filename": row_dict.get("stored_filename"),
                    "chunk_index": row_dict.get("chunk_index"),
                }
                row_meta = row_dict.get("metadata") or {}
                doc_meta = row_dict.get("document_metadata") or {}
                if isinstance(row_meta, dict):
                    meta.update(row_meta)
                if isinstance(doc_meta, dict):
                    meta.update(doc_meta)

                d = Document(page_content=row_dict["content"], metadata=meta)
                score = row_dict.get("similarity") if "similarity" in row_dict else 1.0
                try:
                    score = float(score) if score is not None else 1.0
                except Exception:
                    score = 1.0
                docs_with_scores.append((d, score))

            return docs_with_scores
        except Exception as e:
            logging.error(f"Error retrieving attachments with score: {e}")
            return []




    def assess_answer_grounding(self, docs: List[Document], answer: str) -> float:
        """
        Heuristic grounding score between 0-1.
        Mengukur seberapa besar jawaban memanfaatkan konten dokumen.
        Strategi: ambil hingga 3 dokumen teratas untuk menghindari denominator terlalu besar,
        tokenisasi sederhana, lalu hitung proporsi overlap token informatif.
        """
        try:
            import re
            
            if not docs or not answer:
                return 0.0
            # Gunakan hanya top-3 dokumen agar skor tidak terdilusi oleh konteks yang kurang relevan
            docs_limited = docs[:3]
            # Gabungkan teks dokumen (dibatasi agar ringan)
            doc_text = " \n".join(getattr(d, 'page_content', getattr(d, 'content', ''))[:2000] for d in docs_limited)
            if not doc_text:
                return 0.0
            # Normalisasi
            def tokenize(s: str) -> List[str]:
                return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_]+", s.lower())
            doc_tokens = tokenize(doc_text)
            ans_tokens = set(tokenize(answer))
            if not doc_tokens:
                return 0.0
            # Ambil token unik informatif:
            # - kata dengan panjang > 4
            # - atau token numerik dengan >=2 digit (untuk nilai seperti 200.000, 3A, 4G)
            def is_informative(tok: str) -> bool:
                if len(tok) > 4:
                    return True
                if tok.isdigit() and len(tok) >= 2:
                    return True
                # tangkap pola campuran seperti "3a", "4g"
                if any(ch.isdigit() for ch in tok) and any(ch.isalpha() for ch in tok):
                    return True
                return False
            informative = {t for t in doc_tokens if is_informative(t)}
            if not informative:
                return 0.0
            overlap = informative & ans_tokens
            # Smoothing denominator: batasi maksimal token pembagi agar tidak terlalu kecil
            denom = max(1, min(len(informative), 500))
            raw_score = len(overlap) / denom
            # Clamp & smoothing
            score = max(0.0, min(1.0, raw_score))
            return score
        except Exception:
            return 0.0

    def is_available(self) -> bool:
        """
        Check if vector store is available and properly initialized.
        Returns:
            bool: True if vector store is available, False otherwise
        """
        return self.vectorstore is not None and self.retriever is not None

    def _get_cache_key(self, query: str, k: int = 7, threshold: float = 0.7, user_data: Optional[Dict] = None, source_types: Optional[Sequence[str]] = None) -> str:
        """
        Generate a cache key for a query and user.
        This key is used to cache search results for faster retrieval.
        Args:
            query (str): The query
            k (int): Number of results
            threshold (float): Similarity threshold
            user_data (Dict, optional): User data containing user_id.
        Returns:
            str: Cache key
        """
        # Normalize query
        normalized_query = query.lower().strip()

        # Extract user_id from user_data if available
        user_id = None
        if user_data:
            user_id = user_data.get('user_id')

        # Create hash
        sources_part = "|".join(sorted(source_types)) if source_types else ""
        key_string = f"{user_id}|{normalized_query}|{k}|{threshold}|{sources_part}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def clear_cache(self) -> None:
        """
        Clear all caches (search results, document metadata, etc.).
        This should be called when documents are added, updated, or deleted.
        """
        try:
            self._document_metadata_cache = {}
            self._question_doc_relevance_cache = {}
            self._search_cache = {}
            logging.info("🧹 All caches cleared successfully")
        except Exception as e:
            logging.error(f"❌ Error clearing caches: {e}")

    def refresh_document_metadata(self) -> None:
        """
        Refresh document metadata cache from database.
        Call this after document changes to ensure validation uses current data.
        """
        try:
            self.clear_cache()
            self._preload_document_metadata()
            logging.info("🔄 Document metadata refreshed successfully")
        except Exception as e:
            logging.error(f"❌ Error refreshing document metadata: {e}")

    def invalidate_document_cache(self, stored_filename: Optional[str] = None) -> None:
        """
        Invalidate cache entries for a specific document or all documents.
        Args:
            stored_filename (str, optional): Specific stored filename to invalidate, or None to invalidate all
        """
        try:
            if stored_filename:
                # Clear search cache (all searches potentially affected)
                self._search_cache = {}
                # Remove specific document from metadata cache if present
                keys_to_remove = []
                for key, doc_meta in self._document_metadata_cache.items():
                    # Check both stored_filename and document_source for backward compatibility
                    if (doc_meta.get('stored_filename') == stored_filename or 
                        doc_meta.get('document_source') == stored_filename):
                        keys_to_remove.append(key)
                for key in keys_to_remove:
                    del self._document_metadata_cache[key]
                logging.info(f"🔄 Cache invalidated for document: {stored_filename}")
            else:
                self.clear_cache()
                logging.info("🔄 All document caches invalidated")
        except Exception as e:
            logging.error(f"❌ Error invalidating document cache: {e}")
