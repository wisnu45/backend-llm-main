"""
Optimized Conversation Chain Pipeline for LLM Completions

This module provides a streamlined, dedicated pipeline for handling conversational chains
when sending requests to LLM completions. It consolidates all conversation handling logic
into a single, efficient pathway.
"""

import os
import json
import logging
import time
import re
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict

from flask import request, has_request_context
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from openai import AuthenticationError, RateLimitError, APIError

from app.utils.database import safe_db_query
from app.utils.setting import get_openai_api_key
from app.utils.time_provider import get_current_datetime_string
from app.utils.llm_timeout import init_chat_openai
from app.services.agent.error_handler import ErrorHandler
from app.services.agent.translation_service import translation_service

logger = logging.getLogger('agent.conversation_chain')

@dataclass
class ConversationContext:
    """Structured conversation context for the chain pipeline."""
    chat_id: str
    user_id: str
    current_question: str
    chat_history: List[Tuple[str, str]]
    language: str
    options: Dict[str, Any]
    filtered_docs: Optional[List[Document]] = None
    source_documents: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    original_question: Optional[str] = None  # Store original question before translation

@dataclass
class ChainResponse:
    """Standardized response from the conversation chain."""
    answer: str
    source_documents: List[Dict[str, Any]]
    confidence: float
    grounding_score: Optional[float] = None
    processing_time: float = 0.0
    chain_type: str = "default"

class ConversationChainPipeline:
    """
    Optimized conversation chain pipeline that handles all LLM completion flows
    in a single, streamlined pathway. This eliminates redundant code and provides
    a unified interface for conversational AI processing.
    """
    
    def __init__(self, llm_model: str = "gpt-4o"):
        """Initialize the conversation chain pipeline."""
        self.llm_model = llm_model
        self.llm = None
        self._init_llm()
        
        # Configuration
        self.grounded_min_score = float(os.getenv("GROUNDED_MIN_SCORE", "0.10"))
        self.vector_doc_min_score = float(os.getenv("VECTOR_DOC_MIN_SCORE", "0.10"))
        self.default_reference_max = int(os.getenv("DEFAULT_REFERENCE_MAX", "3"))
        
        # Pipeline templates - optimized for conversation flow
        self._init_templates()
    
    def _init_llm(self) -> None:
        """Initialize the language model with optimized settings for conversations."""
        try:
            api_key = get_openai_api_key()
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            
            # Optimized parameters for conversational flow
            llm_kwargs = {
                "temperature": 0.1,  # Slightly higher for more natural conversations
                "model": self.llm_model,
                "top_p": 0.95,  # Better for conversational responses
                "frequency_penalty": 0.2,  # Reduce repetition in conversations
                "presence_penalty": 0.1,   # Encourage topic diversity
                "api_key": api_key,
            }
            
            self.llm = init_chat_openai(llm_kwargs, max_tokens=2048)
                    
            logger.info(f"🧠 Conversation chain LLM initialized: {self.llm_model}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize conversation chain LLM: {e}")
            self.llm = None
    
    def _init_templates(self) -> None:
        """Initialize optimized prompt templates for conversation chains."""
        
        # Streamlined conversation template
        self.conversation_template = ChatPromptTemplate.from_messages([
            ("system", """
Anda adalah asisten AI yang berpartisipasi dalam percakapan alami dan berkelanjutan.

WAKTU SAAT INI: {current_datetime}

KONTEKS PERCAKAPAN:
{chat_history_context}

DOKUMEN REFERENSI:
{context}

INSTRUKSI PERCAKAPAN:
- Jawab dalam bahasa {language} dengan gaya percakapan yang natural
- Gunakan konteks percakapan sebelumnya untuk memberikan jawaban yang koheren
- Rujuk dokumen hanya jika relevan dengan pertanyaan saat ini
- Pertahankan konsistensi dengan percakapan sebelumnya
- Berikan jawaban yang langsung dan jelas tanpa pengulangan berlebihan
- Gunakan informasi waktu saat ini untuk memberikan konteks yang akurat

PANDUAN FORMAT:
- Gunakan **bold** untuk informasi penting
- Gunakan bullet points jika diperlukan untuk kejelasan
- Jaga gaya percakapan yang ramah dan profesional
- Hindari repetisi informasi yang sudah disebutkan sebelumnya
"""),
            ("user", "{question}")
        ])
        
        # Direct conversation template (without documents)
        self.direct_template = ChatPromptTemplate.from_messages([
            ("system", """
Anda adalah asisten AI dalam percakapan langsung tanpa referensi dokumen.

WAKTU SAAT INI: {current_datetime}

KONTEKS PERCAKAPAN:
{chat_history_context}

INSTRUKSI:
- Jawab dalam bahasa {language} berdasarkan pengetahuan umum
- Gunakan konteks percakapan untuk menjaga kontinuitas
- Berikan jawaban yang natural dan sesuai konteks
- Akui jika informasi tidak tersedia atau di luar kemampuan
- Gunakan informasi waktu saat ini untuk memberikan konteks yang akurat dan relevan
"""),
            ("user", "{question}")
        ])
        
        # Company policy conversation template
        self.company_template = ChatPromptTemplate.from_messages([
            ("system", """
Anda mewakili kebijakan perusahaan dalam percakapan formal.

WAKTU SAAT INI: {current_datetime}

KONTEKS PERCAKAPAN:
{chat_history_context}

KEBIJAKAN PERUSAHAAN:
{context}

INSTRUKSI:
- Gunakan bahasa {language} dengan gaya formal dan profesional
- Rujuk kebijakan perusahaan yang relevan
- Jaga konsistensi dengan informasi sebelumnya dalam percakapan
- Berikan panduan yang dapat ditindaklanjuti
- Tekankan aspek kepatuhan dan prosedur
- Gunakan informasi waktu saat ini untuk konteks temporal yang tepat
"""),
            ("user", "{question}")
        ])
    
    def _build_conversation_context(self, chat_history: List[Tuple[str, str]], limit: int = 3) -> str:
        """Build optimized conversation context for the chain."""
        if not chat_history:
            return "Ini adalah awal percakapan."
        
        try:
            try:
                turns = int(os.getenv("CHAIN_HISTORY_TURNS", "5"))
            except Exception:
                turns = 5
            try:
                max_chars = int(os.getenv("CHAIN_HISTORY_MAX_CHARS", "1600"))
            except Exception:
                max_chars = 1600
            try:
                max_answer_chars = int(os.getenv("CHAIN_HISTORY_MAX_ANSWER_CHARS", "260"))
            except Exception:
                max_answer_chars = 260

            turns = max(1, min(turns, 12))
            max_chars = max(200, min(max_chars, 7000))
            max_answer_chars = max(80, min(max_answer_chars, 1500))

            # Get recent context but ensure it's focused
            recent = chat_history[-turns:]
            context_parts = []
            total_chars = 0
            
            for i, (q, a) in enumerate(recent):
                q_clean = str(q).strip()
                a_clean = str(a).strip()

                # Skip low-signal short user replies (confirmation tokens, option letters)
                q_norm = re.sub(r"\s+", " ", q_clean.lower()).strip()
                q_norm = re.sub(r"[^\w\s]", " ", q_norm)
                q_norm = re.sub(r"\s+", " ", q_norm).strip()
                if (
                    len(q_norm) <= 2
                    or q_norm in {"benar", "ya", "iya", "ok", "oke", "y", "a", "b", "c"}
                ):
                    continue
                
                # Truncate very long answers to maintain focus
                if len(a_clean) > max_answer_chars:
                    a_clean = a_clean[:max_answer_chars] + "..."
                
                # Number the exchange for clarity
                chunk = f"[{i+1}] User: {q_clean}\nAssistant: {a_clean}"
                if total_chars + len(chunk) > max_chars:
                    break
                context_parts.append(chunk)
                total_chars += len(chunk)
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.warning(f"Error building conversation context: {e}")
            return "Konteks percakapan tidak tersedia."
    
    def _build_document_context(self, docs: List[Document]) -> str:
        """Build focused document context for the conversation."""
        if not docs:
            return "Tidak ada dokumen referensi."

        import uuid
        
        context_parts = []
        for i, doc in enumerate(docs[:5]):  # Limit to most relevant docs
            content = getattr(doc, "page_content", getattr(doc, "content", ""))
            metadata = getattr(doc, "metadata", {})
            
            # Get source info
            source = metadata.get("Title", metadata.get("title", metadata.get("original_filename", "-")))

            if isinstance(source, str) and source.strip():
                filename = os.path.basename(source.strip())
                name_part = filename.rsplit(".", 1)[0] if "." in filename else filename
                try:
                    uuid.UUID(name_part)
                    source = "-"
                except (ValueError, AttributeError):
                    source = source.strip()
            else:
                source = "-"
            
            # Truncate very long content
            if len(content) > 500:
                content = content[:500] + "..."
            
            context_parts.append(f"[{source}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _get_intelligent_datetime_context(self, question: str) -> str:
        """Get contextually appropriate datetime information based on the question."""
        question_lower = question.lower()
        
        # Determine what datetime format is most useful for this question
        if any(term in question_lower for term in ['hari ini', 'today', 'sekarang', 'now', 'saat ini']):
            # For "today" queries, provide detailed date and time
            return get_current_datetime_string("%A, %d %B %Y pukul %H:%M %Z")
            
        elif any(term in question_lower for term in ['tahun', 'year', 'kapan', 'when', 'berapa lama']):
            # For year-related queries, emphasize the current year
            return get_current_datetime_string("Tahun %Y, bulan %B")
            
        elif any(term in question_lower for term in ['berita', 'news', 'terbaru', 'latest', 'update']):
            # For news/update queries, provide timestamp context
            return get_current_datetime_string("Per %d %B %Y pukul %H:%M %Z")
            
        elif any(term in question_lower for term in ['jadwal', 'schedule', 'appointment', 'meeting']):
            # For scheduling queries, provide day and date
            return get_current_datetime_string("%A, %d %B %Y")
            
        else:
            # Default format for general conversations
            return get_current_datetime_string("%A, %d %B %Y")
    
    def _select_template(self, context: ConversationContext) -> ChatPromptTemplate:
        """Select the appropriate template based on conversation context."""
        options = context.options or {}
        
        if options.get("is_company", False):
            return self.company_template
        elif context.filtered_docs:
            return self.conversation_template
        else:
            return self.direct_template
    
    def _assess_grounding(self, docs: List[Document], answer: str) -> float:
        """Simple grounding assessment for conversation responses."""
        if not docs or not answer:
            return 0.0
        
        # Count content overlap as a simple grounding metric
        answer_lower = answer.lower()
        overlap_score = 0.0
        
        for doc in docs:
            content = getattr(doc, "page_content", getattr(doc, "content", "")).lower()
            if not content:
                continue
            
            # Simple word overlap calculation
            content_words = set(content.split())
            answer_words = set(answer_lower.split())
            
            if len(content_words) > 0:
                overlap = len(content_words.intersection(answer_words))
                overlap_score += overlap / len(content_words)
        
        # Normalize by number of documents
        return min(overlap_score / len(docs), 1.0) if docs else 0.0
    
    def _format_source_documents(self, docs: List[Document], answer: str, question: Optional[str] = None) -> List[Dict[str, Any]]:
        """Format source documents for conversation responses."""
        if not docs:
            return []
        
        grounding_score = self._assess_grounding(docs, answer)
        
        if grounding_score < self.grounded_min_score:
            logger.debug(f"Suppressing sources due to low grounding: {grounding_score:.3f}")
            return []
        
        formatted_docs_with_scores: List[Tuple[Dict[str, Any], int, int]] = []
        seen_keys = set()

        entity_terms: List[str] = []
        base_text = (question or "").lower()
        if base_text:
            tokens = re.findall(r"\w+", base_text)
            stopwords = {
                "siapa",
                "apa",
                "dimana",
                "kapan",
                "bagaimana",
                "mengapa",
                "yang",
                "dan",
                "di",
                "ke",
                "dari",
                "untuk",
                "dengan",
                "pada",
                "adalah",
                "atau",
                "ini",
                "itu",
                "sebagai",
                "dalam",
            }
            entity_terms = [t for t in tokens if len(t) >= 3 and t not in stopwords]

        base_url = ""
        if has_request_context():
            try:
                base_url = request.host_url.rstrip("/").replace("http://", "https://")
            except Exception:
                base_url = ""

        for idx, doc in enumerate(docs):
            metadata = getattr(doc, "metadata", {}) or {}

            dedup_key = (
                metadata.get("source_type", "document"),
                metadata.get("title", metadata.get("document_name", "Document"))
            )

            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            content_text = getattr(doc, "page_content", getattr(doc, "content", ""))
            search_text = " ".join(
                [
                    str(metadata.get("title") or ""),
                    str(metadata.get("document_name") or ""),
                    content_text,
                ]
            ).lower()

            entity_score = 0
            if entity_terms:
                for term in entity_terms:
                    if term in search_text:
                        entity_score += 1

            url = metadata.get("url", "")
            if not url or not isinstance(url, str):
                url = ""

            if (not url or not url.startswith("http")) and isinstance(metadata, dict):
                document_id = metadata.get("document_id") or metadata.get("id")
                if document_id:
                    if base_url:
                        url = f"{base_url}/storage/{document_id}"
                    else:
                        url = f"/storage/{document_id}"

            formatted_doc = {
                "content": content_text,
                "metadata": metadata,
                "title": metadata.get("title", metadata.get("document_name", "Document")),
                "url": url,
                "source_type": metadata.get("source_type", "document")
            }

            formatted_docs_with_scores.append((formatted_doc, entity_score, idx))

        if entity_terms and formatted_docs_with_scores:
            max_entity = max(score for _, score, _ in formatted_docs_with_scores)
            if max_entity > 0:
                formatted_docs_with_scores = [
                    item for item in formatted_docs_with_scores if item[1] > 0
                ]
                formatted_docs_with_scores.sort(
                    key=lambda item: (-item[1], item[2])
                )

        trimmed = formatted_docs_with_scores[: self.default_reference_max]
        return [doc for doc, score, idx in trimmed]
    
    def process_conversation(self, context: ConversationContext) -> ChainResponse:
        """
        Main conversation processing pipeline.
        This is the single entry point for all conversational LLM completions.
        """
        start_time = time.time()
        
        try:
            if not self.llm:
                return ChainResponse(
                    answer=ErrorHandler.get_message("offline", "LLM tidak tersedia"),
                    source_documents=[],
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    chain_type="error"
                )
            
            # Build conversation context
            chat_history_context = self._build_conversation_context(context.chat_history)
            
            # Build document context if available
            document_context = ""
            if context.filtered_docs:
                document_context = self._build_document_context(context.filtered_docs)
            
            # Select appropriate template
            template = self._select_template(context)
            
            # Get intelligent datetime context based on the question
            current_datetime = self._get_intelligent_datetime_context(context.current_question)
            
            # Prepare variables for template
            template_vars = {
                "question": context.current_question,
                "chat_history_context": chat_history_context,
                "context": document_context,
                # Keep internal prompts consistent: always Indonesian.
                # User-facing language is handled by TranslationService at the API boundary.
                "language": "Bahasa Indonesia",
                "current_datetime": current_datetime
            }
            
            # Format and invoke LLM
            formatted_messages = template.format_messages(**template_vars)
            
            logger.debug(f"🔗 Processing conversation chain for chat_id: {context.chat_id}")
            
            # LLM completion
            result = self.llm.invoke(formatted_messages)
            answer = str(getattr(result, "content", result))
            
            # Assess grounding and format sources
            grounding_score = None
            source_documents = []
            confidence = 0.7  # Base confidence for conversation
            
            if context.filtered_docs:
                grounding_score = self._assess_grounding(context.filtered_docs, answer)
                source_documents = self._format_source_documents(
                    context.filtered_docs, answer, context.current_question
                )
                confidence = 0.8 if source_documents else 0.6
            
            # Determine chain type
            chain_type = "company" if context.options.get("is_company") else "conversation"
            if not context.filtered_docs:
                chain_type = "direct"
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Conversation chain completed in {processing_time:.2f}s")
            
            return ChainResponse(
                answer=answer,
                source_documents=source_documents,
                confidence=confidence,
                grounding_score=grounding_score,
                processing_time=processing_time,
                chain_type=chain_type
            )
            
        except (AuthenticationError, RateLimitError, APIError) as e:
            logger.error(f"❌ OpenAI API error in conversation chain: {e}")
            return ChainResponse(
                answer=ErrorHandler.get_message("token_empty", "Kesalahan API"),
                source_documents=[],
                confidence=0.0,
                processing_time=time.time() - start_time,
                chain_type="error"
            )
            
        except Exception as e:
            logger.error(f"❌ Error in conversation chain: {e}")
            return ChainResponse(
                answer=ErrorHandler.get_message("process", "Kesalahan pemrosesan"),
                source_documents=[],
                confidence=0.0,
                processing_time=time.time() - start_time,
                chain_type="error"
            )
    
    def save_conversation_state(self, context: ConversationContext, response: ChainResponse, chat_detail_id: str) -> None:
        """Save conversation state to database efficiently."""
        try:
            # Generate new chat_id if not provided or empty (first chat)
            if not context.chat_id or context.chat_id.strip() == "":
                import uuid
                context.chat_id = str(uuid.uuid4())
                logger.info(f"🆕 Generated new chat_id in conversation chain: {context.chat_id}")
            
            # Note: Translation is already handled in the agent.py level before calling this method
            # The response passed here should already contain the translated answer
            
            # Update options with chain metadata
            enriched_options = {
                **(context.options or {}),
                "chain_type": response.chain_type,
                "confidence": response.confidence,
                "processing_time": response.processing_time,
                "original_language": context.language  # Store original language for reference
            }
            
            # Save to chats table (upsert session)
            session_title = context.current_question[:200] if context.current_question else "Percakapan"
            
            upsert_chat = """
                INSERT INTO chats (id, user_id, subject, pinned, created_at, options) 
                VALUES (%s, %s, %s, FALSE, CURRENT_TIMESTAMP, %s) 
                ON CONFLICT (id) DO UPDATE SET 
                    subject = COALESCE(NULLIF(EXCLUDED.subject, ''), chats.subject), 
                    options = EXCLUDED.options, 
                    updated_at = CURRENT_TIMESTAMP
            """
            
            safe_db_query(upsert_chat, (
                context.chat_id, 
                context.user_id, 
                session_title, 
                json.dumps(enriched_options)
            ))
            
            # Save conversation detail
            sources_json = json.dumps(response.source_documents, ensure_ascii=False)
            attachments_json = json.dumps([f.get('storage_path', '') for f in (context.attachments or [])], ensure_ascii=False)
            
            # Use original question if available, otherwise use current question
            question_to_save = context.original_question or context.current_question
            
            insert_detail = """
                INSERT INTO chat_details (id, chat_id, question, answer, source_documents, attachments, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            
            safe_db_query(insert_detail, (
                chat_detail_id,
                context.chat_id,
                question_to_save,  # Save original question in user's language
                response.answer,   # Save translated answer in user's language
                sources_json,
                attachments_json
            ))
            
            logger.debug(f"💾 Conversation state saved for chat_id: {context.chat_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save conversation state: {e}")
    
    def load_conversation_history(self, chat_id: str, limit: int = 5) -> List[Tuple[str, str]]:
        """Load conversation history efficiently."""
        try:
            # Return empty history if chat_id is not provided or empty (first chat)
            if not chat_id or chat_id.strip() == "":
                logger.debug("🔄 Empty chat_id provided, returning empty history for first conversation")
                return []
            
            query = """
                SELECT question, answer FROM chat_details 
                WHERE chat_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            
            result = safe_db_query(query, (chat_id, limit))
            
            if isinstance(result, tuple) and len(result) == 2:
                rows, _ = result
                if rows and isinstance(rows, list):
                    # Query returns newest-first; reverse to keep chronological order.
                    ordered = list(reversed(rows))
                    return [(str(row[0]), str(row[1])) for row in ordered]
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Failed to load conversation history: {e}")
            return []

# Export the main interface
__all__ = ['ConversationChainPipeline', 'ConversationContext', 'ChainResponse']
