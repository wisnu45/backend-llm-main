# agent.py
import os
import re
import json
import logging
import warnings
import uuid

from flask import request
from typing import List, Dict, Tuple, Any, Optional, Sequence, Set

# External dependencies
from langchain_core.documents import Document
from openai import AuthenticationError, RateLimitError, APIError

# Import environment loader (centralized env loading)
from app.utils.env_loader import env_load
from app.utils.database import safe_db_query
from app.utils.setting import get_openai_api_key
from app.utils.llm_timeout import init_chat_openai
from app.utils.time_provider import get_current_datetime_string
from app.utils.document import process_document_for_vector_storage
from app.utils.language import detect_language
from app.utils.text import to_bool

# Import modular services
from app.services.agent.message_classifier import MessageClassifier
from app.services.agent.search_service import SearchService
from app.services.agent.prompt_service import PromptService
from app.services.agent.chat_service import ChatService
from app.services.agent.vectorstore_service import VectorStoreService
from app.services.agent.error_handler import ErrorHandler
from app.services.agent.conversation_chain import ConversationChainPipeline, ConversationContext, ChainResponse
from app.services.agent.translation_service import translation_service
from app.services.agent.intent_predictor import IntentPredictor
from app.services.agent.question_contextualizer import QuestionContextualizer
from app.services.agent.vision_service import VisionService
from app.services.agent.pandas_service import PandasService
import app.services.agent.system_prompts as system_prompts

# Use logging configuration from server.py
logger = logging.getLogger('agent')

class Chatbot:

    def __init__(self, llm_model: str = "gpt-4o"):
        """
        Initialize the chatbot with vector store and LLM.
        Only retrieves from vectordb; does not process files or URLs.
        llm_model: OpenAI model name (default: gpt-4o)
        """
        # Ensure llm_model parameter is a string
        if not isinstance(llm_model, str):
            logging.error(f"❌ Invalid llm_model parameter: {llm_model} (type: {type(llm_model)})")
            llm_model = "gpt-4o"  # Reset to default
            logging.warning(f"⚠️ Reset llm_model parameter to default: {llm_model}")

        self._llm_model = llm_model  # Use private attribute

        # Initialize LLM first
        self._init_llm()

        # Initialize modular services (order matters for dependencies)
        self.message_classifier = MessageClassifier()
        self.prompt_service = PromptService()
        self.chat_service = ChatService()
        self.vectorstore_service = VectorStoreService()
        self.vision_service = VisionService()
        self.pandas_service = PandasService()

        # Initialize search service with required dependencies
        self.search_service = SearchService(llm=self.llm, prompt_service=self.prompt_service)
        
        # Initialize optimized conversation chain pipeline
        self.conversation_chain = ConversationChainPipeline(llm_model=self._llm_model)
        
        # Initialize question contextualizer for understanding contextual questions
        self.question_contextualizer = QuestionContextualizer()
        # Initialize intent predictor for LLM-first digestion and company insight confirmation flow
        self.intent_predictor = IntentPredictor(llm=self.llm, prompt_service=self.prompt_service)

        # Grounding acceptance threshold (configurable via env)
        try:
            self.grounded_min_score: float = float(os.getenv("GROUNDED_MIN_SCORE", "0.10"))
        except Exception:
            self.grounded_min_score = 0.10

        # Minimum doc score to keep a document from vector search (post-rerank)
        try:
            self.vector_doc_min_score: float = float(os.getenv("VECTOR_DOC_MIN_SCORE", "0.10"))
        except Exception:
            self.vector_doc_min_score = 0.10

        # Reference limits
        try:
            self.default_reference_max: int = int(os.getenv("DEFAULT_REFERENCE_MAX", "3"))
        except Exception:
            self.default_reference_max = 3
        try:
            self.company_min_references: int = int(os.getenv("COMPANY_REFERENCE_MIN", "7"))
        except Exception:
            self.company_min_references = 7
        try:
            self.company_max_references: int = int(os.getenv("COMPANY_REFERENCE_MAX", "10"))
        except Exception:
            self.company_max_references = 10
        if self.company_max_references < self.company_min_references:
            self.company_max_references = max(self.company_min_references, 10)

    @property
    def llm_model(self) -> str:
        """Get the LLM model name."""
        return self._llm_model

    @llm_model.setter
    def llm_model(self, value: str) -> None:
        """Set the LLM model name with validation."""
        if not isinstance(value, str):
            logging.error(f"❌ Attempted to set llm_model to non-string: {value} (type: {type(value)})")
            raise TypeError(f"llm_model must be a string, got {type(value)}")
        self._llm_model = value

    def _build_chat_history_context(self, chat_history: Optional[List[Tuple[str, str]]], limit: int = 3) -> str:
        """Summarize recent chat history for prompt context.

        Uses small, bounded context to balance relevance and performance.
        Config:
        - CHAT_HISTORY_CONTEXT_TURNS (default: 4)
        - CHAT_HISTORY_CONTEXT_MAX_CHARS (default: 1400)
        - CHAT_HISTORY_CONTEXT_MAX_ANSWER_CHARS (default: 260)
        """
        if not chat_history:
            return ""
        try:
            try:
                turns = int(os.getenv("CHAT_HISTORY_CONTEXT_TURNS", "4"))
            except Exception:
                turns = 4
            try:
                max_chars = int(os.getenv("CHAT_HISTORY_CONTEXT_MAX_CHARS", "1400"))
            except Exception:
                max_chars = 1400
            try:
                max_answer_chars = int(os.getenv("CHAT_HISTORY_CONTEXT_MAX_ANSWER_CHARS", "260"))
            except Exception:
                max_answer_chars = 260

            turns = max(1, min(turns, 12))
            max_chars = max(200, min(max_chars, 6000))
            max_answer_chars = max(80, min(max_answer_chars, 1200))

            recent = chat_history[-turns:]
            history_parts = []
            total_chars = 0
            for q, a in recent:
                q_s = str(q).strip()
                a_s = str(a).strip()

                # Skip very short/low-signal user replies (confirmation tokens, option letters)
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

                chunk = f"Pengguna: {q_s}\nAsisten: {a_s}"
                if total_chars + len(chunk) > max_chars:
                    break
                history_parts.append(chunk)
                total_chars += len(chunk)
            return "\n\n".join(history_parts)
        except Exception as e:
            logging.warning(f"Gagal membangun ringkasan riwayat percakapan: {e}")
            return ""

    def _init_llm(self) -> None:
        """Initialize the language model with error handling."""
        try:
            # Ensure llm_model is a string - safeguard against corruption
            if not isinstance(self.llm_model, str):
                logging.error(f"❌ llm_model is not a string: {self.llm_model} (type: {type(self.llm_model)})")
                # Reset to default if corrupted
                self.llm_model = "gpt-4o"
                logging.warning(f"⚠️ Reset llm_model to default: {self.llm_model}")

            api_key = get_openai_api_key()
            if not api_key:
                raise ValueError("OpenAI API key is not configured. Please set it via settings or environment variable.")

            llm_kwargs = {
                "temperature": 0.05,
                "model": self.llm_model,
                "top_p": 0.90,
                "frequency_penalty": 0.3,
                "presence_penalty": 0.2,
                "api_key": api_key,
            }
            self.llm = init_chat_openai(llm_kwargs, max_tokens=2048)
            logging.info(f"LLM initialized successfully with model: {self.llm_model}")
        except (AuthenticationError, RateLimitError) as e:
            logging.error(f"❌ OpenAI API error during LLM initialization: {e}")
            self.llm = None
        except Exception as e:
            logging.error(f"❌ Failed to initialize LLM: {e}")
            logging.error(f"LLM model parameter at error: {self.llm_model} (type: {type(self.llm_model)})")
            self.llm = None

    def retrieve(self, question: str, k: int = 7, user_data: Optional[dict] = None, source_types: Optional[Sequence[str]] = None) -> List[Document]:
        """
        Retrieve relevant documents for a question, filtering out deleted documents.
        Args:
            question (str): The question to find documents for
            k (int): Number of documents to retrieve
            source_types (Sequence[str], optional): Specific document sources to scope the search
        Returns:
            List[Document]: List of valid relevant documents
        """
        return self.vectorstore_service.retrieve(question, k, user_data=user_data, source_types=source_types)

    def retrieve_with_score(self, question: str, k: int = 15, user_data: Optional[dict] = None, source_types: Optional[Sequence[str]] = None) -> List[Tuple[Document, float]]:
        """
        Retrieve relevant documents with similarity scores, filtering out deleted documents.
        Args:
            question (str): The question to find documents for
            k (int): Number of documents to retrieve
            source_types (Sequence[str], optional): Specific document sources to scope the search
        Returns:
            List[Tuple[Document, float]]: List of valid documents and their scores
        """
        return self.vectorstore_service.retrieve_with_score(question, k, user_data=user_data, source_types=source_types)

    def _resolve_doc_key(self, doc: Document) -> str:
        """Resolve a stable identifier for deduplicating retrieved documents."""
        try:
            return self.vectorstore_service._doc_key(doc)
        except Exception:
            metadata = getattr(doc, "metadata", {}) or {}
            for key in ("id", "document_id", "stored_filename", "document_source", "source"):
                value = metadata.get(key)
                if value:
                    return str(value)
            return str(hash(getattr(doc, "page_content", "")))

    def _prioritize_company_documents(self, docs_with_scores: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """Prioritize portal documents ahead of other sources for Company Insight mode."""
        if not docs_with_scores:
            return docs_with_scores

        portal_docs: List[Tuple[Document, float]] = []
        website_docs: List[Tuple[Document, float]] = []
        other_docs: List[Tuple[Document, float]] = []

        for doc, score in docs_with_scores:
            metadata = getattr(doc, "metadata", {}) or {}
            source_type = str(metadata.get("source_type", "") or metadata.get("sourceType", "")).lower()
            if source_type == "portal":
                portal_docs.append((doc, score))
            elif source_type == "website":
                website_docs.append((doc, score))
            else:
                other_docs.append((doc, score))

        logging.info(
            "Company source prioritization - portal: %s, website: %s, other: %s",
            len(portal_docs),
            len(website_docs),
            len(other_docs),
        )

        ordered = portal_docs + website_docs + other_docs
        seen: Set[str] = set()
        prioritized: List[Tuple[Document, float]] = []
        for doc, score in ordered:
            key = self._resolve_doc_key(doc)
            if key in seen:
                continue
            seen.add(key)
            prioritized.append((doc, score))
        return prioritized

    def _select_company_docs_for_context(
        self,
        docs_with_scores: List[Tuple[Document, float]],
        threshold: float
    ) -> List[Document]:
        """Select documents for RAG context ensuring portal dominance and sufficient quantity."""
        if not docs_with_scores:
            return []

        max_refs = max(self.company_max_references, self.company_min_references)
        min_refs = min(self.company_min_references, max_refs)

        selected: List[Document] = []
        seen: Set[str] = set()

        for doc, score in docs_with_scores:
            key = self._resolve_doc_key(doc)
            if key in seen:
                continue
            if score >= threshold:
                selected.append(doc)
                seen.add(key)
            if len(selected) >= max_refs:
                break

        if len(selected) < min_refs:
            for doc, _ in docs_with_scores:
                if len(selected) >= min_refs:
                    break
                key = self._resolve_doc_key(doc)
                if key in seen:
                    continue
                selected.append(doc)
                seen.add(key)

        if not selected:
            fallback_docs = [doc for doc, _ in docs_with_scores[:max_refs]]
            logging.debug("Company doc selection fallback triggered with %s docs", len(fallback_docs))
            return fallback_docs

        logging.info(
            "Company doc selection produced %s documents (min target: %s, max target: %s)",
            len(selected),
            min_refs,
            max_refs,
        )
        return selected

    def _is_doc_relevant_to_question(self, doc: Document, question: str) -> bool:
        if not question:
            return True
        metadata = getattr(doc, "metadata", {}) or {}
        title = str(
            metadata.get("title")
            or metadata.get("document_title")
            or metadata.get("name")
            or ""
        )
        url = str(metadata.get("url") or metadata.get("source") or "")
        try:
            content = getattr(doc, "page_content", getattr(doc, "content", "")) or ""
        except Exception:
            content = ""
        haystack = f"{title} {url} {content[:400]}".lower()
        raw_question = question or ""
        tokens = re.split(r"[^a-z0-9]+", raw_question.lower())
        try:
            stopwords_source = getattr(self.search_service, "_stopwords", None)
            if isinstance(stopwords_source, set):
                stopwords = {w.lower() for w in stopwords_source}
            else:
                stopwords = set()
        except Exception:
            stopwords = set()
        base_stopwords = {
            "dan",
            "atau",
            "yang",
            "untuk",
            "dalam",
            "pada",
            "dari",
            "ke",
            "di",
            "itu",
            "ini",
            "adalah",
            "apa",
            "apakah",
            "ada",
            "bagaimana",
            "kapan",
            "dimana",
            "dengan",
            "saat",
            "kami",
            "kita",
            "saya",
            "anda",
            "bisa",
            "dapat",
            "harus",
            "boleh",
        }
        stopwords.update(base_stopwords)
        keywords: List[str] = []
        seen_kw = set()
        for t in tokens:
            if len(t) < 3:
                continue
            if t in stopwords:
                continue
            if t in seen_kw:
                continue
            seen_kw.add(t)
            keywords.append(t)
        if not keywords:
            return True
        abbrs = re.findall(r"\b[A-Z]{2,}\b", raw_question)
        abbr_keywords = [a.lower() for a in abbrs]
        subject_object_candidates: List[str] = []
        for ak in abbr_keywords:
            if ak not in subject_object_candidates:
                subject_object_candidates.append(ak)
        sorted_keywords = sorted(
            keywords,
            key=lambda x: (-len(x), keywords.index(x)),
        )
        for kw in sorted_keywords[:4]:
            if kw not in subject_object_candidates:
                subject_object_candidates.append(kw)
        if not subject_object_candidates:
            return True
        return any(k in haystack for k in subject_object_candidates)

    def _is_error_fallback_message(self, answer: str) -> bool:
        """
        Check if the answer is a fallback error message from ErrorHandler.
        Returns True if the answer matches any of the known error messages.
        """
        if not answer or not isinstance(answer, str):
            return False
            
        try:
            answer_lower = answer.lower().strip()
            if (
                (answer_lower.startswith("mohon maaf") or answer_lower.startswith("maaf,") or answer_lower.startswith("maaf "))
                and len(answer_lower) < 200
            ):
                return True

            error_messages = ErrorHandler.get_all_message()

            # Check if answer matches any error message (case insensitive)
            for error_msg in error_messages.values():
                if error_msg and error_msg.lower().strip() == answer_lower:
                    return True
                    
            # Also check against class defaults in case database is not available
            default_messages = [
                ErrorHandler.offline,
                ErrorHandler.process, 
                ErrorHandler.token_empty,
                ErrorHandler.ambiguous,
                ErrorHandler.insufficient_info,
                ErrorHandler.offline_website,
                ErrorHandler.offline_internet,
                ErrorHandler.no_information
            ]
            
            for default_msg in default_messages:
                if default_msg and default_msg.lower().strip() == answer_lower:
                    return True
                    
            return False
        except Exception as e:
            logging.warning(f"Error checking if message is fallback: {e}")
            return False

    def _ensure_user_role_data(self, user_data: Optional[dict]) -> Dict[str, Any]:
        """Enrich user data with role information by joining the roles table when missing."""
        if not isinstance(user_data, dict):
            return {}

        if user_data.get("role_name") and user_data.get("role_id"):
            return user_data

        user_id = user_data.get("user_id")
        if not user_id:
            return user_data

        try:
            query = (
                "SELECT r.id, r.name "
                "FROM users u "
                "LEFT JOIN roles r ON u.roles_id = r.id "
                "WHERE u.id = %s"
            )
            result, _ = safe_db_query(query, (user_id,))
            if result:
                user_data = dict(user_data)  # Create copy
                user_data["role_id"] = result[0][0]
                user_data["role_name"] = result[0][1]
                logging.info(f"Enriched user data with role_id={result[0][0]}, role_name={result[0][1]}")
            return user_data
        except Exception as e:
            logging.warning(f"Failed to enrich user data with role: {e}")
            return user_data

    def _process_attachments(self, attachments: Optional[List[str]], chat_id: str, user_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Process and save attachments to database and vector store."""
        documents_save = []
        result_attachment = []
        
        if not attachments:
            return result_attachment, documents_save

        for attachment in attachments:
            mimetype = attachment.get("mimetype")
            ext = attachment.get("ext")
            size = attachment.get("size")
            path = attachment.get("path")
            filename = attachment.get("filename")
            
            if not filename or not path:
                logging.warning(f"Attachment invalid: {attachment}")
                continue

            doc_id = str(uuid.uuid4())
            base_url = request.host_url.rstrip('/').replace('http://', 'https://')
            document_url = f"{base_url}/storage/{doc_id}"
            
            result_attachment.append({
                'mimetype': mimetype,
                'ext': ext,
                'url': document_url
            })

            documents_save.append({
                'document_id': doc_id,
                'file_type': ext,
                'upload_method': "chat",
                'file_size': size,
                'source_type': "user",
                'original_filename': filename,
                'mime_type': mimetype,
                'storage_path': path,
                'uploaded_by': user_id,
                'chat_id': chat_id,
            })

        return result_attachment, documents_save

    def _save_attachments_to_db(self, documents_save: List[Dict[str, Any]], chat_id: str) -> None:
        """Save attachment metadata to database."""
        if not documents_save:
            return

        db_records = []
        for doc_meta in documents_save:
            db_records.append((
                doc_meta['document_id'],
                chat_id,
                "user",
                doc_meta['original_filename'],
                doc_meta['original_filename'],
                doc_meta['storage_path'],
                doc_meta['mime_type'],
                doc_meta['file_size'],
                doc_meta['uploaded_by']
            ))

        try:
            query = """
            INSERT INTO documents (id, chat_id, source_type, original_filename, stored_filename, storage_path, mime_type, size_bytes, uploaded_by)
            VALUES %s
            """
            safe_db_query(query, db_records, many=True)
            logging.info(f"✅ Saved {len(db_records)} attachments to database")
        except Exception as e:
            logging.warning(f"❌ Failed to save attachments to database: {e}")

    def _save_attachments_to_vector(self, documents_save: List[Dict[str, Any]]) -> None:
        """Save attachments to vector store."""
        for metadata in documents_save:
            filepath = metadata.get("storage_path")
            original_filename = metadata.get("original_filename")
            document_id = metadata.get("document_id")
            storage_path = metadata.get("storage_path")

            success = process_document_for_vector_storage(
                file_path=filepath,
                document_name=original_filename,
                document_source=original_filename,
                metadata=metadata,
                document_id=document_id,
                storage_path=storage_path
            )

            if success:
                logging.info(f"✅ Document {original_filename} added to vector storage")
            else:
                logging.warning(f"⚠️ Failed to add {original_filename} to vector storage")

    def _get_documents_for_question(self, question: str, chat_id: str, user_data: Optional[dict], options: Dict[str, Any]) -> List[Document]:
        """Get relevant documents based on question and context."""
        # Check for chat attachments first
        try:
            query = "SELECT id FROM documents WHERE chat_id = %s"
            chat_attachments, _ = safe_db_query(query, (chat_id,))
            has_attachments = bool(chat_attachments)
        except Exception as e:
            logging.warning(f"❌ Failed to check chat attachments: {e}")
            has_attachments = False

        # Skip vector database for browse mode (Google dorking) and general mode (direct LLM)
        if (options.get("is_browse", False) or options.get("is_general", False)) and not has_attachments:
            logging.info(f"🚫 Skipping vector database retrieval for mode: browse={options.get('is_browse', False)}, general={options.get('is_general', False)}")
            return []

        # If has attachments, retrieve from them
        if has_attachments:
            try:
                docs_with_scores = self.vectorstore_service.retrieve_attachments_with_score(
                    question,
                    chat_id,
                    user_data=user_data or {},
                    source_types=["user"],
                    k_per_file=20,
                    similarity_threshold=self.vector_doc_min_score
                )
                filtered_docs = [doc for doc, score in docs_with_scores if score >= self.vector_doc_min_score]
                if filtered_docs:
                    logging.info(f"📎 Found {len(filtered_docs)} relevant attachment documents")
                    return filtered_docs
            except Exception as e:
                logging.warning(f"Failed to retrieve attachment documents: {e}")

        # For company mode, retrieve company documents
        if options.get("is_company", False):
            source_types = ["portal", "website", "admin"]
            try:
                docs_with_scores = self.retrieve_with_score(
                    question,
                    k=20,
                    user_data=user_data,
                    source_types=source_types
                )
                filtered_docs = [doc for doc, score in docs_with_scores if score >= self.vector_doc_min_score]
                if filtered_docs:
                    logging.info(f"🏢 Found {len(filtered_docs)} relevant company documents")
                    return filtered_docs[:self.company_max_references]  # Limit for company mode
            except Exception as e:
                logging.warning(f"Failed to retrieve company documents: {e}")

        # General document retrieval
        try:
            docs = self.retrieve(question, k=7, user_data=user_data)
            if docs:
                logging.info(f"📄 Found {len(docs)} relevant general documents")
                return docs
        except Exception as e:
            logging.warning(f"Failed to retrieve general documents: {e}")

        return []

    def generate(
        self,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        chat_id: Optional[str] = None,
        filtered_docs: Optional[list] = None,
        is_company: bool = False,
        original_question: Optional[str] = None,
        user_data: Optional[dict] = None,
        source_types: Optional[Sequence[str]] = None,
        language: str = "id"
    ) -> Dict[str, Any]:
        """
        Generate a response using retrieval and LLM.
        Also updates chat history for the session if chat_id is provided.
        is_company: If True, use formal company policy response style
        language: Detected language code for response (default: 'id')
        """
        try:
            if not self.llm:
                logging.error("🧠 LLM not initialized")
                return {"answer": ErrorHandler.get_message("offline", "Tidak Diketahui"), "source_documents": []}
            if chat_history is None:
                chat_history = []
            # Gunakan filtered_docs jika tersedia, jika tidak fallback ke retrieve
            docs = filtered_docs if filtered_docs is not None else self.retrieve(question, user_data=user_data, source_types=source_types)
            if not docs:
                logging.warning("🔍 No relevant documents found for question.")
                return {
                    "answer": ErrorHandler.get_message("insufficient_info"),
                    "source_documents": []
                }
            # Convert docs to proper Document objects if needed
            formatted_docs = []
            for doc in docs:
                if isinstance(doc, Document):
                    formatted_docs.append(doc)
                else:
                    # Handle case where doc might be a tuple or other format
                    content = getattr(doc, "page_content", getattr(doc, "content", str(doc)))
                    metadata = getattr(doc, "metadata", {})
                    formatted_docs.append(Document(page_content=content, metadata=metadata))

            # Debug: Log the context being sent to conversation chain
            logger.debug(f"📝 Number of docs for conversation chain: {len(formatted_docs)}")

            # Create conversation context for the chain
            conversation_context = ConversationContext(
                chat_id=chat_id or "",
                user_id=user_data.get("user_id", "") if user_data else "",
                current_question=original_question if original_question else question,
                chat_history=chat_history,
                language=language,
                options={"is_company": is_company},
                filtered_docs=formatted_docs,
                original_question=original_question
            )

            logger.debug(f"🤖 Processing via conversation chain - Question: {question}")
            logger.debug(f"🤖 Company mode: {is_company}, Language: {language}")

            # Process through conversation chain
            try:
                chain_response = self.conversation_chain.process_conversation(conversation_context)
                answer_text = chain_response.answer
            except (AuthenticationError, RateLimitError) as e:
                logging.error(f"❌ OpenAI API error in conversation chain: {e}")
                return {
                    "answer": ErrorHandler.get_message("token_empty", "Terjadi kesalahan dengan API OpenAI"),
                    "source_documents": []
                }
            except APIError as e:
                logging.error(f"❌ OpenAI API error in conversation chain: {e}")
                return {
                    "answer": ErrorHandler.get_message("token_empty", "Terjadi kesalahan dengan API OpenAI"),
                    "source_documents": []
                }

            # Check if answer contains common "tidak tahu" phrases and refine if needed
            tidak_tahu_phrases = [
                "saya tidak tahu", "tidak dapat menjawab", "tidak memiliki informasi", 
                "tidak cukup informasi", "tidak ada dalam konteks", "tidak tersedia dalam konteks"
            ]

            needs_refinement = False
            lower_answer = answer_text.lower()
            for phrase in tidak_tahu_phrases:
                if phrase in lower_answer and len(docs) > 1:
                    needs_refinement = True
                    break

            if needs_refinement:
                # Use expanded docs for refinement via conversation chain
                expanded_docs = formatted_docs[:7] if len(formatted_docs) > 1 else formatted_docs
                
                # Create refined conversation context with expanded docs
                refined_context = ConversationContext(
                    chat_id=chat_id or "",
                    user_id=user_data.get("user_id", "") if user_data else "",
                    current_question=f"Mohon perjelas jawaban dengan informasi lengkap dari dokumen: {original_question if original_question else question}",
                    chat_history=chat_history,
                    language=language,
                    options={"is_company": is_company, "is_refinement": True},
                    filtered_docs=expanded_docs,
                    original_question=original_question
                )

                logging.info("🔄 Refining answer with expanded context via conversation chain...")
                try:
                    refined_response = self.conversation_chain.process_conversation(refined_context)
                    answer_text = refined_response.answer
                except (AuthenticationError, RateLimitError, APIError) as e:
                    logging.error(f"❌ OpenAI API error during refinement: {e}")
                    # Keep the original answer if refinement fails due to API error
                    pass

            # --- Grounding assessment: pastikan jawaban benar-benar memakai konten dokumen ---
            try:
                grounding_score = self.vectorstore_service.assess_answer_grounding(docs, answer_text)
                logger.debug(f"🔎 Grounding score: {grounding_score:.3f}")
            except Exception as ge:
                grounding_score = 0.0
                logger.warning(f"Grounding assessment failed: {ge}")

            # Update chat history for the session (hindari duplikasi)
            if chat_id:
                try:
                    self.chat_service.update_chat_history(chat_id, question, answer_text)
                except Exception as e:
                    logging.warning(f"Gagal memperbarui chat history in-memory: {e}")
            logging.info("🧠 LLM response generated.")

            # Create source documents response dengan score
            source_docs = []
            # Ambang referensi agar hanya muncul bila benar-benar ter-grounding
            # Dapat diubah lewat env `GROUNDED_MIN_SCORE` (default 0.10)
            GROUNDED_MIN_SCORE = getattr(self, "grounded_min_score", 0.10)
            hallucination_indicators = [
                "menurut pengetahuan umum", "secara umum", "tidak ada di dokumen", "tidak terdapat dalam dokumen",
                "sepengetahuan saya", "knowledge cutoff", "model AI", "sebagai AI", "sebagai sebuah AI"
            ]
            is_hallucination_style = any(ind.lower() in answer_text.lower() for ind in hallucination_indicators)

            # Deteksi jawaban sapaan / sangat generik (tidak perlu referensi)
            greeting_patterns = [
                r"^selamat (pagi|siang|sore|malam)",
                r"^hai", r"^halo", r"^hello", r"^hi ", r"^hi$",
                r"^apa kabar", r"saya adalah asisten", r"saya adalah asisten virtual"
            ]
            is_greeting_answer = False
            lower_ans = answer_text.lower().strip()
            if len(lower_ans) < 220:  # jawaban pendek cenderung bukan ringkasan dokumen
                for gp in greeting_patterns:
                    if re.search(gp, lower_ans):
                        is_greeting_answer = True
                        break

            if grounding_score >= GROUNDED_MIN_SCORE and not is_hallucination_style and not is_greeting_answer:
                desired_max = self.company_max_references if is_company else self.default_reference_max
                desired_max = max(1, desired_max)
                desired_min = self.company_min_references if is_company else min(desired_max, len(docs))
                desired_min = min(desired_min, len(docs))
                included: List[Dict[str, Any]] = []
                seen_doc_keys: Set[str] = set()

                for doc in docs:
                    key = self._resolve_doc_key(doc)
                    if key in seen_doc_keys:
                        continue
                    original_doc = doc
                    combined_score = None
                    if hasattr(doc, 'score') and isinstance(getattr(doc, 'score'), (int, float)):
                        try:
                            combined_score = float(getattr(doc, 'score'))
                        except Exception:
                            combined_score = None
                    elif isinstance(doc, tuple) and len(doc) == 2:
                        try:
                            combined_score = float(doc[1])
                        except Exception:
                            combined_score = None
                        original_doc = doc[0]

                    metadata = getattr(original_doc, "metadata", {}) or {}
                    if combined_score is None:
                        meta_combined = metadata.get("combined_score") or metadata.get("score")
                        if isinstance(meta_combined, (int, float)):
                            combined_score = float(meta_combined)

                    vector_sim = metadata.get("vector_similarity") or metadata.get("similarity")
                    lexical_score = metadata.get("lexical_score")

                    score_payload = {}
                    if isinstance(combined_score, (int, float)):
                        score_payload["combined"] = round(float(combined_score), 3)
                    if isinstance(vector_sim, (int, float)):
                        score_payload["vector"] = round(float(vector_sim), 3)
                    if isinstance(lexical_score, (int, float)):
                        score_payload["lexical"] = round(float(lexical_score), 3)

                    included.append({
                        "content": getattr(original_doc, "page_content", getattr(original_doc, "content", "")),
                        "metadata": metadata,
                        "score": score_payload if score_payload else None
                    })
                    seen_doc_keys.add(key)

                    if len(included) >= desired_max:
                        break

                if is_company and len(included) < desired_min:
                    logging.debug(
                        "Including %s company references below min target %s due to limited documents",
                        len(included),
                        desired_min,
                    )
                source_docs.extend(included)
            else:
                logger.info(
                    f"🚫 Source documents suppressed (grounding_score={grounding_score:.3f} < threshold={GROUNDED_MIN_SCORE}, hallucination_style={is_hallucination_style}, greeting={is_greeting_answer})"
                )

            return {
                "answer": answer_text,
                "source_documents": source_docs,
                "grounding_score": round(grounding_score, 3)
            }
        except Exception as e:
            logging.error(f"⚠️ Error generating response: {e}")
            return {
                "answer": ErrorHandler.get_message("error"),
                "source_documents": []
            }

    def generate_direct_answer(
        self,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        chat_id: Optional[str] = None,
        language: str = "id"
    ) -> Dict[str, Any]:
        """Produce an LLM-only answer without document retrieval via conversation chain."""
        if not self.llm:
            logging.error("🧠 LLM not initialized for direct answer")
            return {
                "answer": ErrorHandler.get_message("offline", "Tidak Diketahui"),
                "source_documents": [],
                "attachment": [],
                "confidence": 0
            }

        # Create conversation context for direct answer (no documents)
        conversation_context = ConversationContext(
            chat_id=chat_id or "",
            user_id="",  # No user data available in direct answer
            current_question=question,
            chat_history=chat_history or [],
            language=language,
            options={"is_general": True, "is_direct": True},
            filtered_docs=None,  # No documents for direct answer
            original_question=question
        )

        logger.debug(f"🤖 Processing direct answer via conversation chain - Question: {question}")
        logger.debug(f"🤖 Language: {language}")

        try:
            chain_response = self.conversation_chain.process_conversation(conversation_context)
            answer_text = chain_response.answer
        except (AuthenticationError, RateLimitError, APIError) as e:
            logging.error(f"❌ OpenAI API error in direct answer conversation chain: {e}")
            return {
                "answer": ErrorHandler.get_message("token_empty", "Terjadi kesalahan dengan API OpenAI"),
                "source_documents": [],
                "attachment": [],
                "confidence": 0
            }

        if chat_id:
            try:
                self.chat_service.update_chat_history(chat_id, question, answer_text)
            except Exception as e:
                logging.warning(f"Gagal memperbarui riwayat setelah direct answer: {e}")

        response = {
            "answer": answer_text,
            "source_documents": [],
            "attachment": [],
            "confidence": 0.6
        }

        return response

    def ask(self, question: str, chat_id: str, chat_detail_id: str, user_id: str, user_data: Optional[dict] = None, is_browse: bool = False, is_company: bool = False, is_general: bool = False, attachments: Optional[List[str]] = None, original_language: str = 'id', original_question: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user question and return a response.
        
        Mode behaviors:
        1. is_company (Company Insight Mode):
           - Searches ONLY from company data sources:
             a) Vector DB (portal/website documents)
             b) Combiphar websites (from settings table: combiphar_websites)
           - If no answer found from company sources, returns "no_information" message
           - Does NOT fallback to general LLM or web search
           - Scope: Terbatas pada dokumen dan website perusahaan
        
        2. is_general (General LLM Mode):
           - Direct to ChatGPT-4o WITHOUT retrieval from vector DB
           - Scope: Luas, tidak terikat pada dokumen perusahaan
           - Uses LLM's general knowledge only
        
        3. is_browse (Web Search Mode):
           - Searches from internet using Google dorking (ddgs tool)
           - Does NOT use vector DB (except for attachments if present)
           - Scope: Luas, tidak terikat pada dokumen perusahaan
        
        Special case - Attachments:
        - If chat has attachments, will search from attachment documents first
        - This applies to ALL modes (company/general/browse)
        - If attachment provides good answer, returns immediately
        
        Args:
            question: User's question
            chat_id: Chat session ID
            chat_detail_id: Chat detail record ID
            user_id: User ID
            user_data: User metadata (role, permissions, etc.)
            is_browse: Enable web search mode
            is_company: Enable company insight mode (company data only)
            is_general: Enable general LLM mode (no retrieval)
            attachments: List of uploaded files for this chat
            original_language: Detected language from user's question
            original_question: Original question before any translation
        
        Returns:
            Dict with keys: answer, source_documents, attachment, confidence
        """
        # Generate new chat_id if not provided or empty (first chat)
        if not chat_id or chat_id.strip() == "":
            chat_id = str(uuid.uuid4())
            logger.info(f"🆕 Generated new chat_id for first conversation: {chat_id}")
        
        # Convert string parameters to boolean safely
        is_browse = to_bool(is_browse) if isinstance(is_browse, str) else bool(is_browse)
        is_company = to_bool(is_company) if isinstance(is_company, str) else bool(is_company)
        is_general = to_bool(is_general) if isinstance(is_general, str) else bool(is_general)
        
        # Mode handling: allow multiple toggles and process sequentially (company -> general -> browse)
        active_modes = sum([is_browse, is_company, is_general])
        if active_modes > 1:
            logger.info(
                "🧭 Multiple modes requested; will evaluate in order company -> general -> browse "
                f"(is_browse={is_browse}, is_company={is_company}, is_general={is_general})"
            )
        
        options = {
            "is_browse": is_browse,
            "is_company": is_company,
            "is_general": is_general
        }

        excel_mimes = {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/vnd.oasis.opendocument.spreadsheet",
        }

        company_insight_enabled = False
        if is_company:
            try:
                company_insight_enabled = self.intent_predictor.is_enabled(user_data=user_data)
            except Exception as e:
                logging.warning(f"Gagal mengecek toggle company_insight: {e}")

        # user_data = self._ensure_user_role_data(user_data or {})

        source_types: Optional[Sequence[str]] = ["portal", "website", "admin"] if is_company else None
        
        # Use provided original language (already detected in chat.py)
        logger.info(f"🌍 Using original language: {original_language}")
        
        # Prefer language from API (translation_service) to keep conversation stable.
        detected_language = (original_language or '').lower().strip() or detect_language(question)
        logger.info(f"🌍 Using provided language: {detected_language}")

        # Persist stable original language per chat to avoid language flip-flopping on short replies.
        try:
            if isinstance(options, dict):
                lang_to_store = (original_language or detected_language or 'id').lower().strip()
                if lang_to_store in {'id', 'en'}:
                    options["original_language"] = lang_to_store
        except Exception:
            pass
        
        # Detect if this is a time-sensitive question and log realtime context
        self._log_realtime_context(question)
        
        # Load chat history using the conversation chain pipeline for better context management
        try:
            try:
                history_load_limit = int(os.getenv("CHAT_HISTORY_LOAD_LIMIT", "10"))
            except Exception:
                history_load_limit = 10
            history_load_limit = max(3, min(history_load_limit, 30))

            chat_history = self.conversation_chain.load_conversation_history(chat_id, limit=history_load_limit)
            logger.info(f"📜 Loaded {len(chat_history)} previous conversations from conversation chain")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load conversation history from chain, falling back to chat_service: {e}")
            # Fallback to chat_service if conversation_chain fails
            try:
                self.chat_service.ensure_chat_history_loaded(chat_id)
                chat_history = self.chat_service.get_chat_history(chat_id)
            except Exception:
                chat_history = []

        original_question = question if not original_question else original_question
        processing_question = question

        # Track confirmation flow state for company insight
        user_confirmed_company_intent = False
        user_provided_clarification = False
        generation_question = original_question

        # Keep `detected_language` stable; do not re-detect mid-flow.

        # If user replies after our confirmation prompt, reuse the agreed question.
        # Do not depend on feature flag here because we already sent the prompt in the previous turn.
        if chat_history:
            try:
                last_answer = chat_history[-1][1] if chat_history else ""
                if self.intent_predictor.is_confirmation_prompt(last_answer):
                    is_confirm = self.intent_predictor.is_user_confirmation_reply(
                        user_reply=original_question,
                        confirmation_prompt=last_answer,
                    )
                    logger.info("Confirmation reply classified as: %s", is_confirm)

                    if is_confirm:
                        agreed_question = self.intent_predictor.extract_question_from_confirmation(last_answer)
                        if agreed_question:
                            processing_question = agreed_question
                            user_confirmed_company_intent = True
                            is_company = True
                            company_insight_enabled = True
                            options["is_company"] = True
                            generation_question = agreed_question
                            logger.info(
                                "User confirmed company intent; using agreed question for search: %s",
                                agreed_question,
                            )
                    else:
                        # In confirmation-mode, treat non-confirm replies as denial/clarification.
                        proposed = self.intent_predictor.extract_question_from_confirmation(last_answer) or ""
                        if proposed:
                            msg = (
                                f"Baik, berarti bukan itu. Apakah Anda bisa jelaskan maksud pertanyaan \"{proposed}\" secara singkat "
                                "(misalnya unit, lokasi, atau sistem) supaya saya bisa mencari jawaban yang tepat?"
                            )
                        else:
                            msg = (
                                "Baik. Kalau maksudnya berbeda, jelaskan singkat (misalnya unit, lokasi, atau sistem) "
                                "supaya saya bisa mencari jawaban yang tepat."
                            )

                        translated_msg = translation_service.translate_response_to_user_language(
                            msg, original_language
                        )
                        try:
                            self.chat_service.update_chat_history(chat_id, original_question, translated_msg)
                            self.chat_service.save_chat_history(
                                chat_id,
                                chat_detail_id,
                                original_question,
                                translated_msg,
                                [],
                                user_id,
                                options=options,
                                attachments=attachments,
                            )
                        except Exception as e:
                            logging.warning(f"Gagal menyimpan klarifikasi konfirmasi ke riwayat: {e}")
                        return {
                            "answer": translated_msg,
                            "source_documents": [],
                            "attachment": [],
                            "confidence": 0.0,
                        }
            except Exception as e:
                logger.warning(f"Gagal memproses konfirmasi intent: {e}")

        # If user replies after clarification prompt, merge context before routing/search
        if not user_confirmed_company_intent and chat_history:
            try:
                last_question = chat_history[-1][0] if chat_history else ""
                last_answer = chat_history[-1][1] if chat_history else ""
                if self.intent_predictor.is_clarification_prompt(last_answer):
                    clarified_question = self.intent_predictor.merge_clarification_response(
                        base_question=last_question,
                        user_response=processing_question,
                        clarification_prompt=last_answer,
                    )
                    if clarified_question:
                        processing_question = clarified_question
                        generation_question = clarified_question
                        user_provided_clarification = True
                        logger.info(
                            "User clarification resolved; using clarified question for search: %s",
                            clarified_question,
                        )
            except Exception as e:
                logger.warning(f"Gagal memproses klarifikasi intent: {e}")

        # --- Initialize Chat Session
        self.chat_service.save_chat(
            chat_id=chat_id,
            question=question,
            answer=None,
            user_id=user_id,
            options=options
        )

        # --- Intent digestion: LLM-first understanding before routing ---
        intent_snapshot = None
        if not user_confirmed_company_intent and not user_provided_clarification:
            try:
                intent_snapshot = self.intent_predictor.digest_question(
                    question=processing_question,
                    chat_history=chat_history,
                )
                if intent_snapshot and intent_snapshot.get("normalized_question"):
                    normalized_question = intent_snapshot["normalized_question"]
                    if normalized_question and normalized_question != processing_question:
                        logger.info(
                            "Intent digest normalized question: '%s' -> '%s'",
                            processing_question,
                            normalized_question,
                        )
                    processing_question = normalized_question or processing_question
            except Exception as e:
                logger.warning(f"Intent digest failed: {e}")
                intent_snapshot = None

        # --- LLM-first router: small talk & ambiguous handling ---
        if not user_confirmed_company_intent and not user_provided_clarification:
            if intent_snapshot:
                intent_type = intent_snapshot.get("intent")
                if intent_type == "small_talk":
                    route_subtype = intent_snapshot.get("subtype")
                    answer = self.message_classifier.small_talk_reply(route_subtype)
                    # Translate answer to user's language
                    translated_answer = translation_service.translate_response_to_user_language(
                        answer, original_language
                    )
                    try:
                        self.chat_service.update_chat_history(chat_id, original_question, translated_answer)
                        self.chat_service.save_chat_history(
                            chat_id,
                            chat_detail_id,
                            original_question,
                            translated_answer,
                            [],
                            user_id,
                            options=options,
                            attachments=attachments,
                        )
                    except Exception as e:
                        logging.warning(f"Gagal menyimpan small talk ke riwayat: {e}")
                    return {
                        "answer": translated_answer,
                        "source_documents": [],
                        "attachment": [],
                        "confidence": 1 if route_subtype == "greeting" else 0.9
                    }

                if intent_type == "ambiguous":
                    clarification = self.intent_predictor.maybe_build_intent_clarification(
                        question=processing_question,
                        chat_history=chat_history,
                        reason="ambiguous",
                    )
                    if clarification:
                        answer = clarification["message"]
                        translated_answer = translation_service.translate_response_to_user_language(
                            answer, original_language
                        )
                        try:
                            self.chat_service.update_chat_history(chat_id, original_question, translated_answer)
                            self.chat_service.save_chat_history(
                                chat_id,
                                chat_detail_id,
                                original_question,
                                translated_answer,
                                [],
                                user_id,
                                options=options,
                                attachments=attachments,
                            )
                        except Exception as e:
                            logging.warning(f"Gagal menyimpan klarifikasi ke riwayat: {e}")
                        return {
                            "answer": translated_answer,
                            "source_documents": [],
                            "attachment": [],
                            "confidence": clarification.get("confidence", 0.0),
                        }

                    # Fallback ke pesan ambigu sederhana
                    clarify = ErrorHandler.get_message("ambiguous", "Tidak Diketahui")
                    translated_clarify = translation_service.translate_response_to_user_language(
                        clarify, original_language
                    )
                    try:
                        self.chat_service.update_chat_history(chat_id, original_question, translated_clarify)
                        self.chat_service.save_chat_history(
                            chat_id,
                            chat_detail_id,
                            original_question,
                            translated_clarify,
                            [],
                            user_id,
                            options=options,
                            attachments=attachments,
                        )
                    except Exception as e:
                        logging.warning(f"Gagal menyimpan klarifikasi ke riwayat: {e}")
                    return {
                        "answer": translated_clarify,
                        "source_documents": [],
                        "attachment": [],
                        "confidence": 0
                    }

            if not intent_snapshot or intent_snapshot.get("source") != "llm":
                route_type, route_subtype = self.message_classifier.fast_classify(processing_question)
                if route_type == "small_talk":
                    answer = self.message_classifier.small_talk_reply(route_subtype)
                    # Translate answer to user's language
                    translated_answer = translation_service.translate_response_to_user_language(
                        answer, original_language
                    )
                    try:
                        self.chat_service.update_chat_history(chat_id, original_question, translated_answer)
                        self.chat_service.save_chat_history(
                            chat_id,
                            chat_detail_id,
                            original_question,
                            translated_answer,
                            [],
                            user_id,
                            options=options,
                            attachments=attachments,
                        )
                    except Exception as e:
                        logging.warning(f"Gagal menyimpan small talk ke riwayat: {e}")
                    return {
                        "answer": translated_answer,
                        "source_documents": [],
                        "attachment": [],
                        "confidence": 1 if route_subtype == "greeting" else 0.9
                    }

                if route_type == "ambiguous":
                    clarification = self.intent_predictor.maybe_build_intent_clarification(
                        question=processing_question,
                        chat_history=chat_history,
                        reason="ambiguous",
                    )
                    if clarification:
                        answer = clarification["message"]
                        translated_answer = translation_service.translate_response_to_user_language(
                            answer, original_language
                        )
                        try:
                            self.chat_service.update_chat_history(chat_id, original_question, translated_answer)
                            self.chat_service.save_chat_history(
                                chat_id,
                                chat_detail_id,
                                original_question,
                                translated_answer,
                                [],
                                user_id,
                                options=options,
                                attachments=attachments,
                            )
                        except Exception as e:
                            logging.warning(f"Gagal menyimpan klarifikasi ke riwayat: {e}")
                        return {
                            "answer": translated_answer,
                            "source_documents": [],
                            "attachment": [],
                            "confidence": clarification.get("confidence", 0.0),
                        }

                    clarify = ErrorHandler.get_message("ambiguous", "Tidak Diketahui")
                    translated_clarify = translation_service.translate_response_to_user_language(
                        clarify, original_language
                    )
                    try:
                        self.chat_service.update_chat_history(chat_id, original_question, translated_clarify)
                        self.chat_service.save_chat_history(
                            chat_id,
                            chat_detail_id,
                            original_question,
                            translated_clarify,
                            [],
                            user_id,
                            options=options,
                            attachments=attachments,
                        )
                    except Exception as e:
                        logging.warning(f"Gagal menyimpan klarifikasi ke riwayat: {e}")
                    return {
                        "answer": translated_clarify,
                        "source_documents": [],
                        "attachment": [],
                        "confidence": 0
                    }

            # --- Short/long answer handling: simple arithmetic gets concise answer unless explanation requested ---
            try:
                expr = self.message_classifier.extract_arithmetic_expression(processing_question)
            except Exception:
                expr = None
            if expr:
                try:
                    result = self.message_classifier.safe_eval_expression(expr)
                except Exception:
                    result = None
                if result is not None:
                    wants_expl = self.message_classifier.wants_explanation(processing_question)
                    if not wants_expl:
                        brief = self.message_classifier.format_number_brief(result)
                        # Translate answer to user's language
                        translated_brief = translation_service.translate_response_to_user_language(brief, original_language)
                        try:
                            self.chat_service.update_chat_history(chat_id, original_question, translated_brief)
                            self.chat_service.save_chat_history(chat_id, chat_detail_id,  original_question, translated_brief, [], user_id, options=options, attachments=attachments)
                        except Exception as e:
                            logging.warning(f"Gagal menyimpan jawaban ringkas ke riwayat: {e}")
                        return {
                            "answer": translated_brief,
                            "source_documents": [],
                            "attachment": [],
                            "confidence": 1.0
                        }
                    else:
                        detailed = self.message_classifier.explain_arithmetic(expr, result)
                        # Translate answer to user's language
                        translated_detailed = translation_service.translate_response_to_user_language(detailed, original_language)
                        try:
                            self.chat_service.update_chat_history(chat_id, original_question, translated_detailed)
                            self.chat_service.save_chat_history(chat_id, chat_detail_id,  original_question, translated_detailed, [], user_id, options=options, attachments=attachments)
                        except Exception as e:
                            logging.warning(f"Gagal menyimpan penjelasan perhitungan ke riwayat: {e}")
                        return {
                            "answer": translated_detailed,
                            "source_documents": [],
                            "attachment": [],
                            "confidence": 1.0
                        }

        # --- Question Contextualization: Understand contextual questions before search ---
        logger.info("🧠 Analyzing question context and enhancing for better retrieval...")
        
        # Skip contextualization for certain modes that don't need it
        skip_contextualization = (
            is_browse or  # Web search doesn't need document context
            (is_general and not is_company) or  # Pure general mode
            user_confirmed_company_intent or  # Keep agreed question intact
            user_provided_clarification  # Keep clarified question intact
        )
        
        enhanced_question = processing_question  # Default to original
        context_info = None
        
        if not skip_contextualization and chat_history:
            try:
                # Filter low-signal turns (e.g., 'benar', 'ok', option letters) to reduce confusion.
                filtered_history: List[Tuple[str, str]] = []
                for q, a in chat_history:
                    q_norm = re.sub(r"\s+", " ", str(q).lower()).strip()
                    q_norm = re.sub(r"[^\w\s]", " ", q_norm)
                    q_norm = re.sub(r"\s+", " ", q_norm).strip()
                    if (
                        len(q_norm) <= 2
                        or q_norm in {"benar", "ya", "iya", "ok", "oke", "y", "a", "b", "c"}
                    ):
                        continue
                    filtered_history.append((q, a))

                # Contextualize question based on chat history
                context_info = self.question_contextualizer.contextualize_question(
                    question=processing_question,
                    chat_history=filtered_history or chat_history,
                    use_llm=True  # Use LLM for better accuracy
                )
                
                # Use enhanced question for search if contextualization was successful
                if context_info.get("needs_context") and context_info.get("confidence", 0) > 0.4:
                    enhanced_question = context_info["enhanced_question"]
                    logger.info(f"📝 Question enhanced for search: '{processing_question}' -> '{enhanced_question}'")
                    logger.info(f"🎯 Detected topic: {context_info.get('detected_topic')}, Confidence: {context_info.get('confidence', 0):.2f}")
                else:
                    logger.info("📝 Question is already clear or no context needed")
                    
            except Exception as e:
                logger.warning(f"⚠️ Question contextualization failed, using original: {e}")
                enhanced_question = processing_question
        else:
            logger.info("📝 Skipping question contextualization (mode or no history)")

        # if attachment manage the attachment first
        documents_save = []
        documents_vector = []
        result_attachment = []
        vision_context_docs: List[Document] = []
        if attachments:
            for attachment in attachments:
                mimetype = attachment.get("mimetype")
                ext = attachment.get("ext")
                size = attachment.get("size")
                path = attachment.get("path")
                filename = attachment.get("filename")
                if not filename or not path:
                    logging.warning(f"Attachment invalid: {attachment}")
                    continue

                doc_id = str(uuid.uuid4())
                                                
                base_url = request.host_url.rstrip('/').replace('http://', 'https://')
                document_url = f"{base_url}/storage/{doc_id}"
                result_attachment.append({
                    'mimetype': mimetype,
                    'ext': ext,
                    'url': document_url
                })

                documents_save.append((
                    doc_id,
                    chat_id,
                    "user",
                    filename,
                    filename,
                    path,
                    mimetype,
                    size,
                    user_id
                ))

                documents_vector.append({
                    'document_id': doc_id,
                    'file_type': ext,
                    'upload_method': "chat",
                    'file_size': size,
                    'source_type': "user",
                    'original_filename': filename,
                    'mime_type': mimetype,
                    'storage_path': path,
                    'uploaded_by': user_id,
                    'chat_id': chat_id,
                })

                if (
                    self.vision_service
                    and getattr(self.vision_service, "enabled", False)
                    and str(mimetype or "").startswith("image/")
                ):
                    try:
                        description = self.vision_service.describe_image(path, question=original_question)
                        if description:
                            metadata = {
                                "document_id": doc_id,
                                "document_name": filename,
                                "document_source": filename,
                                "title": filename,
                                "source_type": "vision_attachment",
                                "storage_path": path,
                                "source": path,
                                "mime_type": mimetype,
                                "vision_model": self.vision_service.model,
                            }
                            vision_context_docs.append(
                                Document(page_content=description, metadata=metadata)
                            )
                            logging.info(
                                f"📷 Vision summary generated for attachment {filename} ({len(description)} chars)"
                            )
                    except Exception as vision_err:
                        logging.warning(f"Vision summary failed for {filename}: {vision_err}")
                
            logging.info(f"Processing save attachments {len(documents_save)} to documents, session {chat_id}")
            if(documents_save) :
                # save to document
                try:
                    query = """
                    INSERT INTO documents (id, chat_id, source_type, original_filename, stored_filename, storage_path, mime_type, size_bytes, uploaded_by)
                    VALUES %s
                    """
                    safe_db_query(query, documents_save, many=True)
                except Exception as e:
                    logging.warning(f"❌ Gagal menyimpan list documents chat untuk sesi {chat_id}")

                for metadata in documents_vector:
                    if metadata.get("ext") in {"xls", "xlsx", "ods"} or metadata.get("mime_type") in excel_mimes:
                        logging.info(f"Skipping vector storage for Excel-like file: {metadata.get('original_filename')}")
                        continue
                    filepath = metadata.get("storage_path")
                    original_filename = metadata.get("original_filename")
                    document_id = metadata.get("document_id")
                    storage_path = metadata.get("storage_path")

                    success = process_document_for_vector_storage(
                        file_path=filepath,
                        document_name=original_filename,
                        document_source=original_filename,
                        metadata=metadata,
                        document_id=document_id,
                        storage_path=storage_path
                    )

                    if success:
                        logging.info(f"✅ Document {original_filename} added to vector storage")
                        # No cache invalidation for now; keep flow simple
                    else:
                        logging.warning(f"⚠️ Failed to add {original_filename} to vector storage")

        try:
            query = """
                SELECT id, original_filename, storage_path, mime_type
                FROM documents
                WHERE chat_id = %s
            """
            chat_attachments, _ = safe_db_query(query, (chat_id,))
            if not chat_attachments:
                chat_attachments = []
        except Exception as e:
            logging.warning(f"❌ Gagal mengambil dokumen chat untuk sesi {chat_id}: {e}")
            chat_attachments = []

        # Mode flags and explicit mode detection
        explicit_mode = any([is_browse, is_company, is_general])
        # If is_company is True, modify the system prompt for formal company policy responses
        if is_company:
            logging.info("🏢 Company policy mode activated - using formal response style")

        # If is_browse is True *and* no other source flags are enabled, do web-only flow
        if is_browse and not (is_company or is_general) and not chat_attachments:
            logging.info("🌐 Web search mode activated - bypassing internal document search")
            try:
                # Use enhanced question for better web search results
                web_result = self.search_service.search_web(
                    enhanced_question if enhanced_question != processing_question else processing_question,
                    chat_id,
                    user_id,
                    chat_history,
                    original_question=generation_question
                )
                if web_result and web_result.get("answer"):
                    web_result["answer"] = translation_service.translate_response_to_user_language(
                        web_result["answer"], original_language
                    )
                    # Update chat history for the session
                    self.chat_service.update_chat_history(chat_id, original_question, web_result["answer"])

                    # Save chat history for internet search (no source_documents)
                    try:
                        self.chat_service.save_chat_history(chat_id, chat_detail_id,  original_question, web_result["answer"], [], user_id, options=options, attachments=attachments)
                    except Exception as e:
                        logging.error(f"Error saving chat history: {e}")
                    return web_result
                else:
                    # Fallback if internet search fails
                    fallback_answer = ErrorHandler.get_message("offline_internet", "Tidak Diketahui")
                    fallback_answer = translation_service.translate_response_to_user_language(
                        fallback_answer, original_language
                    )
                    try:
                        # Still update chat history with fallback answer
                        self.chat_service.update_chat_history(chat_id, original_question, fallback_answer)
                        self.chat_service.save_chat_history(chat_id, chat_detail_id,  original_question, fallback_answer, [], user_id)
                    except Exception as e:
                        logging.error(f"Error saving chat history: {e}")
                    return {
                        "answer": fallback_answer,
                        "source_documents": [],
                        "attachment": result_attachment,
                        "confidence": 0
                    }
            except Exception as e:
                logging.error(f"Error in internet search: {e}")
                fallback_answer = ErrorHandler.get_message("offline_internet", "Tidak Diketahui")
                fallback_answer = translation_service.translate_response_to_user_language(
                    fallback_answer, original_language
                )
                try:
                    # Still update chat history with fallback answer
                    self.chat_service.update_chat_history(chat_id, original_question, fallback_answer)
                    self.chat_service.save_chat_history(chat_id, chat_detail_id,  original_question, fallback_answer, [], user_id, options=options, attachments=attachments)
                except Exception as e:
                    logging.error(f"Error saving chat history: {e}")
                return {
                    "answer": fallback_answer,
                    "source_documents": [],
                    "attachment": result_attachment,
                    "confidence": 0
                }

        # Direct general mode when explicitly requested
        if is_general and not is_company and not is_browse  and not chat_attachments:
            logging.info("🧠 Direct LLM mode activated via is_general flag")
            direct_response = self.generate_direct_answer(
                generation_question,
                chat_history=chat_history,
                chat_id=chat_id,
                language=detected_language
            )
            if isinstance(direct_response, dict) and direct_response.get("answer") is not None:
                direct_response["answer"] = translation_service.translate_response_to_user_language(
                    direct_response["answer"], original_language
                )
            try:
                self.chat_service.save_chat_history(chat_id, chat_detail_id,  original_question, direct_response["answer"], [], user_id, options=options, attachments=attachments)
            except Exception as e:
                logging.error(f"❌ Error saving chat history: {e}")
            return direct_response

        # Check if vector store is available
        if not self.vectorstore_service.is_available():
            logging.warning("⚠️ Vector store not available, falling back to web search")
            web_result = self.search_service.search_web(
                enhanced_question if enhanced_question != processing_question else processing_question,
                chat_id,
                user_id,
                chat_history,
                original_question=generation_question
            )
            if web_result and web_result.get("answer"):
                web_result["answer"] = translation_service.translate_response_to_user_language(
                    web_result["answer"], original_language
                )
                # Update chat history for the session
                self.chat_service.update_chat_history(chat_id, original_question, web_result["answer"])

                # Save chat history for internet search (no source_documents)
                try:
                    self.chat_service.save_chat_history(chat_id, chat_detail_id,  original_question, web_result["answer"], [], user_id, options=options, attachments=attachments)
                except Exception as e:
                    logging.error(f"Error saving chat history: {e}")
                return web_result
            else:
                # Return basic response if web search also fails
                fallback_answer = ErrorHandler.get_message("offline_internet", "Tidak Diketahui")
                fallback_answer = translation_service.translate_response_to_user_language(
                    fallback_answer, original_language
                )
                return {
                    "answer": fallback_answer,
                    "source_documents": [],
                    "attachment": result_attachment,
                    "confidence": 0
                }

        answer = ""
        source_documents = []
        confidence = 0
        filtered_docs = []
        answer_found = False
        last_doc_count = None
        last_top_score = None
        
        # Check if answer is relevant using search service
        def is_not_relevant(ans: str) -> bool:
            return self.search_service.is_not_relevant_answer(ans, enhanced_question)

        try:
            # Sequential lookup order based on mode:
            # - is_company: 0) attachment → 1) vectordb (portal/website only) → 2) combiphar_websites → STOP
            # - is_general: direct LLM only (no vectordb, no web)
            # - is_browse: web search only (no vectordb)
            # 
            # Order: 
            # 0) vectordb (attachment) - applies to all modes if attachments exist
            # 1) vectordb (is_company only: portal/website docs)
            # 2) combiphar site (is_company only)
            # 3) general LLM (is_general only)
            # 4) internet/web (is_browse only)

            # Use the previously enhanced question from contextualization step
            # enhanced_question is already set above with better contextualization
            logging.info(f"Using contextualized question for search: {enhanced_question}")

            # Lower threshold for document relevance to prioritize document-based answers
            threshold = getattr(self, "vector_doc_min_score", 0.10)

            # Step 0: Attachment-only vector documents (if any attachments present)
            # Note: Attachments are processed for ALL modes (company/general/browse)
            if (chat_attachments) : 
                logger.info("Step 0: Searching from attachment documents only...")
                docs_with_scores = []

                # Prefer attachment-only retrieval when chat attachments exist; otherwise fallback
                try:
                    docs_with_scores = self.vectorstore_service.retrieve_attachments_with_score(
                        enhanced_question,
                        chat_id,
                        user_data=user_data or {},
                        source_types=["user"],
                        k_per_file=50,
                        similarity_threshold=threshold
                    )
                    logging.info(f"📎 Using only attachment docs with content: {len(docs_with_scores)} found")
                except Exception as e:
                    logging.warning(f"Failed fetching attachment chunks; fallback to similarity: {e}")

                if docs_with_scores is not None:
                    last_doc_count = len(docs_with_scores)
                    try:
                        last_top_score = max(
                            float(score)
                            for _, score in docs_with_scores
                            if isinstance(score, (int, float))
                        )
                    except Exception:
                        last_top_score = None

                refined_with_docs = self.vectorstore_service.refine_question_with_docs(enhanced_question, docs_with_scores)
                if refined_with_docs != enhanced_question:
                    logging.info(f"Question refined with vector context: {refined_with_docs}")
                    enhanced_question = refined_with_docs

                filtered_docs = [doc for doc, score in docs_with_scores if score >= threshold]
                
                for attachment in chat_attachments:
                    doc_id, filename, path, mimetype = attachment
                    ext = filename.split(".")[-1]

                    is_excel = str(mimetype or "").lower() in excel_mimes or str(ext or "").lower() in {"xlsx", "xls", "ods"}
                    if (
                        self.pandas_service
                        and getattr(self.pandas_service, "enabled", False)
                        and is_excel
                    ):
                        try:
                            pandas_answer = self.pandas_service.answer_from_path_if_relevant(
                                path,
                                filename,
                                generation_question,
                            )
                            if pandas_answer:
                                metadata = {
                                    "document_id": doc_id,
                                    "document_name": filename,
                                    "document_source": filename,
                                    "title": filename,
                                    "source_type": "pandas_attachment",
                                    "storage_path": path,
                                    "source": path,
                                    "mime_type": mimetype,
                                    "pandas_model": self.pandas_service.model,
                                }
                                vision_context_docs.append(
                                    Document(page_content=str(pandas_answer), metadata=metadata)
                                )
                                logging.info(
                                    f"📊 Pandas agent answer added for attachment {filename} ({len(str(pandas_answer))} chars)"
                                )
                        except Exception as pandas_err:
                            logging.warning(f"Pandas summary/answer failed for {filename}: {pandas_err}")

                if vision_context_docs:
                    filtered_docs = filtered_docs or []
                    filtered_docs.extend(vision_context_docs)
                    logging.info(
                        f"🔍 Augmented attachment context with {len(vision_context_docs)} vision summaries"
                    )

                if not filtered_docs and docs_with_scores:
                    # Fallback: gunakan beberapa dokumen teratas agar tetap mencoba retrieval sebelum web search
                    filtered_docs = [doc for doc, _ in docs_with_scores[:3]]

                if not filtered_docs and vision_context_docs:
                    filtered_docs = list(vision_context_docs)

                logger.info(
                    f"Filtered docs above threshold {threshold}: {len(filtered_docs)} docs"
                )

                if filtered_docs:
                    confidence = max([score for doc, score in docs_with_scores if doc in filtered_docs], default=0)
                    if confidence == 0 and vision_context_docs:
                        confidence = 0.75  # heuristik untuk ringkasan vision
                    response = self.generate(
                        enhanced_question,
                        chat_history,
                        chat_id=chat_id,
                        filtered_docs=filtered_docs,
                        is_company=is_company,  # keep style if company mode requested, otherwise default
                        original_question=generation_question,
                        user_data=user_data,
                        source_types=source_types,
                        language=detected_language
                    )
                    answer = response.get("answer", "")
                    grounding_score = response.get("grounding_score", 0.0)
                    source_docs_generated = response.get("source_documents", [])
                    if not isinstance(answer, str):
                        answer = str(answer)
                    logger.info(f"Generated answer from attachments (first 200 chars): {answer[:200]}...")
                    answer_valid = not is_not_relevant(answer.strip())
                    if answer_valid:
                        logger.info("✅ Accepted answer from attachment documents (auto-approved)")
                        answer_found = True
                        if source_docs_generated:
                            source_documents = source_docs_generated
                        elif vision_context_docs:
                            source_documents = [
                                {"content": doc.page_content, "metadata": doc.metadata}
                                for doc in vision_context_docs
                            ]
                        else:
                            source_documents = []
                    else:
                        logger.info("❌ Attachment-only answer dianggap belum relevan; lanjut ke langkah berikut")
                
            # Start logic flow searching answer, IF attachment still not got relevant answer
            # Step 1: Document vectors (ONLY for is_company mode)
            if is_company and not answer_found:
                logger.info("Step 1: Searching from vector documents (company mode: portal/website only)...")
                retrieval_k = max(20, self.company_max_references * 2)

                docs_with_scores = self.retrieve_with_score(
                    enhanced_question,
                    k=retrieval_k,
                    user_data=user_data,
                    source_types=source_types
                )
                logger.info(f"Search Retrieve with score with user_id {user_id}")
                logger.info(f"Retrieved {len(docs_with_scores)} docs with scores")

                try:
                    top_company_score = max(
                        float(score)
                        for _, score in docs_with_scores
                        if isinstance(score, (int, float))
                    )
                except Exception:
                    top_company_score = None

                last_doc_count = len(docs_with_scores)
                last_top_score = top_company_score

                docs_with_scores = self._prioritize_company_documents(docs_with_scores)

                refined_with_docs = self.vectorstore_service.refine_question_with_docs(enhanced_question, docs_with_scores)
                if refined_with_docs != enhanced_question:
                    logging.info(f"Question refined with vector context: {refined_with_docs}")
                    enhanced_question = refined_with_docs

                filtered_docs = self._select_company_docs_for_context(docs_with_scores, threshold)

                logger.info(
                    f"Filtered docs above threshold {threshold}: {len(filtered_docs)} docs"
                )

                need_company_confirmation = False
                confirm_doc_count = len(docs_with_scores)
                confirm_top_score = top_company_score
                if company_insight_enabled and not user_confirmed_company_intent and not is_general and not is_browse:
                    if not filtered_docs:
                        need_company_confirmation = True
                    elif self.intent_predictor.is_short_hr_question(original_question or enhanced_question):
                        need_company_confirmation = True
                        confirm_doc_count = 0
                        confirm_top_score = None
                if need_company_confirmation:
                    intent_confirmation = self.intent_predictor.maybe_build_company_confirmation(
                        question=original_question or enhanced_question,
                        chat_history=chat_history,
                        doc_count=confirm_doc_count,
                        top_score=confirm_top_score,
                        user_data=user_data,
                    )
                    if intent_confirmation:
                        answer = intent_confirmation["message"]
                        confidence = intent_confirmation.get("confidence", 0.0)
                        source_documents = []
                        answer_found = True
                        logger.info("🤝 Company insight intent confirmation sent before fallback")

                if filtered_docs:
                    portal_refs = sum(
                        1 for doc in filtered_docs
                        if str((getattr(doc, "metadata", {}) or {}).get("source_type", "")).lower() == "portal"
                    )
                    website_refs = sum(
                        1 for doc in filtered_docs
                        if str((getattr(doc, "metadata", {}) or {}).get("source_type", "")).lower() == "website"
                    )
                    logging.info(
                        "Company references breakdown -> portal: %s, website: %s, total: %s",
                        portal_refs,
                        website_refs,
                        len(filtered_docs),
                    )

                    raw_question = generation_question or enhanced_question or original_question or question
                    question_text = str(raw_question or "").strip()
                    product_code_match = None
                    person_name_query = None
                    if question_text:
                        product_code_pattern = re.compile(
                            r"product\s+name\s+dari\s+product\s+code\s*=?\s*([A-Za-z0-9\-]+)",
                            re.IGNORECASE,
                        )
                        m = product_code_pattern.search(question_text)
                        if not m:
                            alt_pattern = re.compile(
                                r"product\s+code\s*=?\s*([A-Za-z0-9\-]+)",
                                re.IGNORECASE,
                            )
                            m = alt_pattern.search(question_text)
                        if not m:
                            generic_pattern = re.compile(
                                r"\b([A-Za-z]{2,}\d{1,4})\b"
                            )
                            m = generic_pattern.search(question_text)
                        if m:
                            product_code_match = m.group(1).upper()

                        person_match = re.search(
                            r"\bsiapa\s+(.+?)(\?|$)",
                            question_text,
                            re.IGNORECASE,
                        )
                        if person_match:
                            candidate = person_match.group(1).strip()
                            candidate = candidate.strip("?.! ").strip()
                            if candidate:
                                person_name_query = candidate

                    if product_code_match:
                        logger.info(f"🔎 Detected product code query for {product_code_match}, attempting direct lookup from documents")
                        found_name = None
                        matched_docs: List[Document] = []
                        code_upper = product_code_match.upper()

                        def _extract_product_name_from_line(line: str, code: str) -> Optional[str]:
                            stripped = line.strip()
                            if not stripped:
                                return None
                            if stripped.startswith("[") and '"key"' in stripped:
                                try:
                                    data = json.loads(stripped)
                                except Exception:
                                    data = None
                                if isinstance(data, list):
                                    for item in data:
                                        key = str(item.get("key", "")).strip().lower()
                                        if key in {"product name", "productname", "nama produk"}:
                                            value = str(item.get("value", "")).strip()
                                            if value:
                                                return value
                            upper = stripped.upper()
                            idx = upper.find(code)
                            if idx == -1:
                                return None
                            segment = stripped[idx + len(code):].strip(" :-\t/")
                            if segment:
                                return segment
                            return stripped

                        candidate_docs: List[Document] = list(filtered_docs)
                        if not candidate_docs:
                            candidate_docs = [doc for doc, _ in docs_with_scores]
                        for doc in candidate_docs:
                            try:
                                content = getattr(doc, "page_content", getattr(doc, "content", "")) or ""
                            except Exception:
                                content = ""
                            if not isinstance(content, str) or not content:
                                continue
                            lines = content.splitlines()
                            for line in lines:
                                if code_upper in line.upper():
                                    extracted = _extract_product_name_from_line(line, code_upper)
                                    if extracted:
                                        found_name = extracted
                                        matched_docs.append(doc)
                                        break
                            if found_name:
                                break

                        db_source_metadata = None
                        db_source_content = None

                        if not found_name:
                            try:
                                pattern = f"%{product_code_match}%"
                                query = """
                                    SELECT content, metadata
                                    FROM documents_vectors
                                    WHERE content ILIKE %s OR metadata::text ILIKE %s
                                    LIMIT 50
                                """
                                rows, _ = safe_db_query(query, (pattern, pattern))
                            except Exception:
                                rows = []
                            for row in rows or []:
                                if not row or not row[0]:
                                    continue
                                try:
                                    text_blob = str(row[0])
                                except Exception:
                                    continue
                                for line in text_blob.splitlines():
                                    if code_upper not in line.upper():
                                        continue
                                    extracted = _extract_product_name_from_line(line, code_upper)
                                    if extracted:
                                        found_name = extracted
                                        db_source_content = line
                                        try:
                                            db_source_metadata = row[1] if len(row) > 1 else None
                                        except Exception:
                                            db_source_metadata = None
                                        break
                                if found_name:
                                    break

                        if found_name:
                            logger.info(f"✅ Found product name '{found_name}' for code {product_code_match} from documents")
                            answer = f"Product Name untuk Product Code {product_code_match} adalah {found_name}."
                            answer_found = True
                            confidence = 1.0

                            if matched_docs:
                                selected_docs = matched_docs
                                max_refs = self.company_max_references if is_company else self.default_reference_max
                                limited_docs = list(selected_docs)[:max_refs]
                                source_documents = [
                                    {
                                        "content": getattr(doc, "page_content", getattr(doc, "content", "")),
                                        "metadata": getattr(doc, "metadata", {}) or {},
                                    }
                                    for doc in limited_docs
                                ]
                                filtered_docs = list(matched_docs)
                            elif db_source_content is not None:
                                meta = db_source_metadata or {}
                                source_documents = [
                                    {
                                        "content": db_source_content,
                                        "metadata": meta,
                                    }
                                ]
                                try:
                                    db_doc = Document(page_content=db_source_content, metadata=meta)
                                    filtered_docs = [db_doc]
                                except Exception:
                                    pass
                            else:
                                selected_docs = candidate_docs
                                max_refs = self.company_max_references if is_company else self.default_reference_max
                                limited_docs = list(selected_docs)[:max_refs]
                                source_documents = [
                                    {
                                        "content": getattr(doc, "page_content", getattr(doc, "content", "")),
                                        "metadata": getattr(doc, "metadata", {}) or {},
                                    }
                                    for doc in limited_docs
                                ]

                            logger.info("Using direct product-code lookup answer instead of LLM generation")
                        else:
                            logger.info(f"ℹ️ No explicit line match found for product code {product_code_match}; falling back to LLM generation")

                    if person_name_query and not answer_found:
                        logger.info(f"🔎 Detected person lookup query for '{person_name_query}', attempting direct lookup from documents")
                        person_info = None
                        person_docs: List[Document] = []
                        name_upper = person_name_query.upper()

                        try:
                            pattern = f"%{person_name_query}%"
                            query = """
                                SELECT content, metadata
                                FROM documents_vectors
                                WHERE content ILIKE %s OR metadata::text ILIKE %s
                                LIMIT 50
                            """
                            rows, _ = safe_db_query(query, (pattern, pattern))
                        except Exception:
                            rows = []

                        for row in rows or []:
                            if not row or not row[0]:
                                continue
                            try:
                                text_blob = str(row[0])
                            except Exception:
                                continue
                            for line in text_blob.splitlines():
                                if name_upper not in line.upper():
                                    continue
                                snippet = line.strip()
                                if not snippet:
                                    continue
                                person_info = snippet
                                meta = row[1] if len(row) > 1 else {}
                                try:
                                    doc = Document(page_content=snippet, metadata=meta or {})
                                    person_docs.append(doc)
                                except Exception:
                                    pass
                                break
                            if person_info:
                                break

                        if person_info:
                            logger.info(f"✅ Found person info for '{person_name_query}' from documents")
                            answer = f"Berdasarkan dokumen perusahaan, berikut informasi tentang {person_name_query}: {person_info}"
                            answer_found = True
                            confidence = 1.0
                            filtered_docs = person_docs
                            source_documents = [
                                {
                                    "content": doc.page_content,
                                    "metadata": doc.metadata or {},
                                }
                                for doc in person_docs
                            ] or [
                                {
                                    "content": person_info,
                                    "metadata": {},
                                }
                            ]

                    if not answer_found:
                        confidence = max([score for doc, score in docs_with_scores if doc in filtered_docs], default=0)
                        response = self.generate(
                            enhanced_question,
                            chat_history,
                            chat_id=chat_id,
                            filtered_docs=filtered_docs,
                            is_company=is_company,
                            original_question=generation_question,
                            user_data=user_data,
                            source_types=source_types,
                            language=detected_language
                        )
                        answer = response.get("answer", "")
                        grounding_score = response.get("grounding_score", 0.0)
                        source_docs_generated = response.get("source_documents", [])
                        if not isinstance(answer, str):
                            answer = str(answer)
                        logger.info(f"Generated answer from vector docs (first 200 chars): {answer[:200]}...")
                        logger.debug(f"Grounding score from generate(): {grounding_score}")
                        threshold = getattr(self, "grounded_min_score", 0.10)
                        if not is_not_relevant(answer.strip()) and (source_docs_generated or grounding_score >= threshold):
                            logger.info("✅ Accepted answer dari vector documents (grounded)")
                            answer_found = True
                            if source_docs_generated:
                                source_documents = source_docs_generated
                            else:
                                max_refs = self.company_max_references if is_company else self.default_reference_max
                                question_for_filter = generation_question or enhanced_question or question
                                context_docs = list(filtered_docs) if filtered_docs else []
                                if context_docs:
                                    relevant_docs: List[Document] = []
                                    for doc in context_docs:
                                        if self._is_doc_relevant_to_question(doc, question_for_filter):
                                            relevant_docs.append(doc)
                                    if not relevant_docs:
                                        relevant_docs = context_docs
                                    limited_docs = relevant_docs[:max_refs]
                                    source_documents = [
                                        {
                                            "content": getattr(doc, "page_content", getattr(doc, "content", "")),
                                            "metadata": getattr(doc, "metadata", {}) or {},
                                        }
                                        for doc in limited_docs
                                    ]
                                    logging.info(
                                        "Selected %s context documents as reference sources (from %s candidates)",
                                        len(limited_docs),
                                        len(context_docs),
                                    )
                                else:
                                    source_documents = []
                                    logging.info("No context documents available for references; not showing sources")
                        else:
                            logger.info(f"❌ Vector document answer dianggap tidak cukup grounded (score={grounding_score:.3f} < threshold={threshold}); lanjut ke langkah berikut")
            
            # Step 1.A: Search Pandas DataFrame agent (ONLY for is_company mode) 
            if is_company and not answer_found:
                try:
                    pandas_results = self.pandas_service.answer_with_pandas_agent(enhanced_question)
                except Exception as e:
                    pandas_results = []
                    logging.warning(f"Pandas service failed: {e}")
                
                logger.info("Result from pandas agent: %s", pandas_results)

                filtered_docs = [doc for doc, score in pandas_results if isinstance(doc, Document)]
                if filtered_docs:
                    confidence = max([float(score) for _, score in pandas_results if isinstance(score, (int, float))], default=0.0)
                    response = self.generate(
                        enhanced_question,
                        chat_history,
                        chat_id=chat_id,
                        filtered_docs=filtered_docs,
                        is_company=is_company,
                        original_question=generation_question,
                        user_data=user_data,
                        source_types=source_types,
                        language=detected_language
                    )
                    answer = response.get("answer", "")
                    grounding_score = response.get("grounding_score", 0.0)
                    source_docs_generated = response.get("source_documents", [])
                    if not isinstance(answer, str):
                        answer = str(answer)
                    logger.info(f"Generated answer from pandas docs (first 200 chars): {answer[:200]}...")
                    logger.debug(f"Grounding score from generate(): {grounding_score}")
                    threshold = getattr(self, "grounded_min_score", 0.10)
                    if not is_not_relevant(answer.strip()) and (source_docs_generated or grounding_score >= threshold):
                        logger.info("✅ Accepted answer from pandas dataframe agent (grounded)")
                        answer_found = True
                        source_documents = source_docs_generated
                    else:
                        logger.info(f"❌ Pandas agent answer dianggap tidak cukup grounded (score={grounding_score:.3f} < threshold={threshold}); lanjut ke langkah berikut")

            # Step 1.B: Combiphar official websites search (ONLY for is_company mode)
            if is_company and not answer_found:
                try:
                    site_result = self.search_service.search_combiphar_site(
                        enhanced_question,
                        chat_history=chat_history,
                        llm=self.llm,
                        original_question=generation_question
                    )
                except Exception as e:
                    site_result = None
                    logging.warning(f"Combiphar site search failed: {e}")

                if site_result and site_result.get("answer"):
                    site_answer = site_result.get("answer", "")
                    if not is_not_relevant(site_answer):
                        answer = site_answer
                        source_documents = site_result.get("source_documents", []) or []
                        confidence = site_result.get("confidence", 0.0)
                        answer_found = True
                        logger.info("✅ Accepted answer from Combiphar official websites (company mode)")
                    else:
                        logging.info("❌ Combiphar site answer dianggap tidak relevan; lanjut ke langkah berikut")

            if is_company and not answer_found:
                if company_insight_enabled and user_confirmed_company_intent:
                    followup = self.intent_predictor.build_followup_confirmation(
                        processing_question,
                        chat_history=chat_history,
                    )
                    if followup:
                        answer = followup["message"]
                        source_documents = []
                        confidence = followup.get("confidence", 0.0)
                        answer_found = True
                        logger.info("🤝 Follow-up company clarification sent after low/empty results")

                if not answer_found:
                    if is_general or is_browse:
                        logger.info("Company mode returned no answer; continuing to general/browse modes per user request")
                    else:
                        logger.info("⛔ is_company mode: No answer found from company vector sources. Delegating to clarification/fallback handler.")

            # Step 2: General LLM (direct chatgpt) - only if is_general is True
            if is_general and not answer_found:
                logger.info("Step 2: Using general LLM (direct) for answer...")
                try:
                    direct_resp = self.generate_direct_answer(
                        generation_question,
                        chat_history=chat_history,
                        chat_id=chat_id,
                        language=detected_language
                    )
                    direct_ans = direct_resp.get("answer", "")
                    if direct_ans and not is_not_relevant(direct_ans):
                        logger.info("✅ Accepted answer from general LLM (direct)")
                        answer = direct_ans
                        source_documents = direct_resp.get("source_documents", []) or []
                        confidence = direct_resp.get("confidence", 0.6)
                        answer_found = True
                    else:
                        logger.info("❌ General LLM returned no relevant answer")
                except Exception as e:
                    logging.error(f"Error in general LLM direct answer: {e}")

            # Step 3: Internet/web search (browse) - only if is_browse is True
            if is_browse and not answer_found:
                logger.info("Step 3: Searching web (internet)...")
                try:
                    web_result = self.search_service.search_web(
                        enhanced_question,
                        chat_id,
                        user_id,
                        chat_history,
                        original_question=generation_question
                    )
                    # Check if result is valid and not a fallback error message
                    if (web_result and 
                        web_result.get("answer") and 
                        web_result.get("confidence", 0) > 0 and
                        not is_not_relevant(web_result["answer"]) and
                        not self._is_error_fallback_message(web_result["answer"])):
                        logger.info("✅ Found answer from web search")
                        answer = web_result["answer"]
                        source_documents = web_result.get("source_documents", []) or []
                        confidence = web_result.get("confidence", 0.0)
                        answer_found = True
                    else:
                        logger.info("❌ No relevant answer from web search or got fallback message")
                except Exception as e:
                    logging.error(f"Error in internet search: {e}")

            # Step End: No information found fallback (only if no mode found answer)
            if not answer_found:
                clarification = None
                if not user_provided_clarification:
                    clarification = self.intent_predictor.maybe_build_intent_clarification(
                        question=processing_question,
                        chat_history=chat_history,
                        reason="low_signal",
                        doc_count=last_doc_count,
                        top_score=last_top_score,
                    )
                if clarification:
                    answer = clarification["message"]
                    source_documents = []
                    confidence = clarification.get("confidence", 0.0)
                    answer_found = True
                    logger.info("Clarification prompt sent after low-signal retrieval")
                else:
                    logger.info("⛔ No answer found from specified mode sources")
                    if is_company:
                        answer = ErrorHandler.get_message("no_information", "Tidak ditemukan informasi yang relevan dari sumber perusahaan")
                    elif is_general:
                        answer = ErrorHandler.get_message("no_information", "Tidak dapat menghasilkan jawaban yang relevan")
                    elif is_browse:
                        answer = ErrorHandler.get_message("offline_internet", "Tidak ditemukan informasi yang relevan dari pencarian web")
                    else:
                        answer = ErrorHandler.get_message("no_information", "Tidak ditemukan informasi yang relevan")
                    source_documents = []
                    confidence = 0

            # Ensure source_documents is empty for fallback / non-document answers
            if self._is_error_fallback_message(answer):
                source_documents = []
            # elif not filtered_docs:
            #     source_documents = []
            
            # confidence already reflects the highest stage-specific value
        except Exception as e:
            logging.error(f"Error processing question: {e}")
            answer = ErrorHandler.get_message("process", "Tidak Diketahui")

        # Translate answer to user's language before returning
        translated_answer = translation_service.translate_response_to_user_language(answer, original_language)

        # Always save chat history regardless of the outcome
        try:
            logging.info(f"Source documents: {source_documents}")
            self.chat_service.save_chat_history(chat_id, chat_detail_id,  original_question, translated_answer, source_documents, user_id, options=options, attachments=attachments)
        except Exception as e:
            logging.error(f"Error saving chat history: {e}")

        return {
            "answer": translated_answer,
            "source_documents": source_documents,
            "attachment": result_attachment,
            "confidence": confidence
        }

    # Proxy methods for cache management
    def clear_cache(self) -> None:
        """Clear all caches (search results, document metadata, etc.)."""
        self.vectorstore_service.clear_cache()

    def refresh_document_metadata(self) -> None:
        """Refresh document metadata cache from database."""
        self.vectorstore_service.refresh_document_metadata()

    def invalidate_document_cache(self, document_source: Optional[str] = None) -> None:
        """Invalidate cache entries for a specific document or all documents."""
        self.vectorstore_service.invalidate_document_cache(document_source)

    def _log_realtime_context(self, question: str) -> None:
        """Log realtime context information for time-sensitive questions."""
        question_lower = question.lower()
        
        # Check for time-sensitive indicators
        time_indicators = [
            'hari ini', 'today', 'sekarang', 'now', 'saat ini', 'currently',
            'terbaru', 'latest', 'recent', 'terkini', 'update', 'berita',
            'tahun ini', 'this year', 'bulan ini', 'this month',
            'kapan', 'when', 'jadwal', 'schedule', 'berapa lama', 'how long'
        ]
        
        if any(indicator in question_lower for indicator in time_indicators):
            current_time = get_current_datetime_string("%A, %d %B %Y pukul %H:%M %Z")
            logger.info(f"⏰ Time-sensitive question detected. Current context: {current_time}")
            
            # Log specific time context based on question type
            if any(term in question_lower for term in ['berita', 'news', 'terbaru', 'latest']):
                logger.info(f"📰 News/update context - ensuring realtime information")
            elif any(term in question_lower for term in ['jadwal', 'schedule', 'appointment']):
                logger.info(f"📅 Scheduling context - current date/time critical")
            elif any(term in question_lower for term in ['tahun', 'year', 'bulan', 'month']):
                logger.info(f"📆 Temporal context - year/date awareness required")
        else:
            logger.debug(f"📝 Regular question - basic time context applied")
