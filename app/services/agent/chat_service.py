"""
Chat Management Service

This module handles chat history management, session operations,
and chat-related database interactions.
"""

import json
import logging
import time
from typing import Dict, List, Tuple, Any, Optional

from app.utils.database import safe_db_query

logger = logging.getLogger('agent')


class ChatService:
    """
    Service for managing chat history, sessions, and related operations.
    """

    def __init__(self):
        """Initialize the chat service."""
        self.chat_histories: Dict[str, List[Tuple[str, str]]] = {}

    def load_chat_history_from_db(self, chat_id: str) -> List[Tuple[str, str]]:
        """
        Load chat history (Q/A) from database for a given chat_id.
        Returns list of (question, answer) tuples.
        """
        try:
            query = """
                SELECT question, answer FROM chat_details
                WHERE chat_id = %s
                ORDER BY created_at ASC
            """
            result = safe_db_query(query, (chat_id,))

            # Check if result is properly unpacked
            if isinstance(result, tuple) and len(result) == 2:
                results, _ = result
                if results and isinstance(results, list):
                    # Convert all rows to string to ensure type safety
                    return [(str(row[0]), str(row[1])) for row in results]

            # If we reached here, either results aren't in expected format or are empty
            logging.warning(f"No chat history found for session {chat_id} or invalid results format: {type(result)}")
            return []
        except Exception as e:
            logging.error(f"Error loading chat history from db for session {chat_id}: {e}")
            return []

    def save_chat(self, chat_id: str, question: str, answer: str, user_id: str, options: Optional[Dict[str, Any]] = None):
        """
        Save chat data intialize new or update existing chat.

        Args:
            chat_id (str): Session identifier
            question (str): User question
            answer (str): Generated answer
            documents (List[Any]): Source documents (dict or tuple)
            user_id (str): User identifier
            options (Optional[Dict[str, Any]]): Additional data to store in the chat.

        """
        # Pastikan baris chats ada (create if missing) dan subjek terisi
        # Subject: gunakan subject existing jika ada, kalau kosong pakai question (max 200 chars)
        session_title = None
        try:
            sel_chat = "SELECT subject FROM chats WHERE id = %s AND user_id = %s LIMIT 1"
            rows, _ = safe_db_query(sel_chat, (chat_id, user_id))
            if rows and isinstance(rows, list):
                session_title = rows[0][0]
        except Exception as e:
            logging.warning(f"Gagal mengambil title sesi: {e}")

        if not session_title or not str(session_title).strip():
            session_title = (question or "")[:200] if question else "Percakapan"

        try:
            # Upsert chats row for this session/user
            upsert_chat = (
                "INSERT INTO chats (id, user_id, subject, pinned, created_at, options) "
                "VALUES (%s, %s, %s, FALSE, CURRENT_TIMESTAMP, %s) "
                "ON CONFLICT (id) DO UPDATE SET subject = COALESCE(NULLIF(EXCLUDED.subject, ''), chats.subject), options = EXCLUDED.options, updated_at = CURRENT_TIMESTAMP"
            )
            safe_db_query(upsert_chat, (chat_id, user_id, session_title, json.dumps(options) if options else None))
        except Exception as e:
            logging.error(f"Gagal upsert chats untuk sesi {chat_id}: {e}")


    def save_chat_history(self, chat_id: str, chat_detail_id: str, question: str, answer: str, documents: List[Any], user_id: str, options: Optional[Dict[str, Any]] = None, attachments: Optional[List[str]] = None) -> None:
        """
        Save chat history to database with consistent formatting for both document and web sources.

        Args:
            chat_id (str): Session identifier
            question (str): User question
            answer (str): Generated answer
            documents (List[Any]): Source documents (dict or tuple)
            user_id (str): User identifier
            options (Optional[Dict[str, Any]]): Additional data to store in the chat.
        """
        try:
            sources = []
            def _format_score(value):
                if value is None:
                    return None
                if isinstance(value, (int, float)):
                    try:
                        return round(float(value), 3)
                    except Exception:
                        return float(value)
                if isinstance(value, dict):
                    formatted = {}
                    for k, v in value.items():
                        if isinstance(v, (int, float)):
                            formatted[k] = round(float(v), 3)
                        else:
                            formatted[k] = v
                    return formatted or None
                return value

            for doc in documents:
                # Handle dict format (from ask/source_documents) - both document and web sources
                if isinstance(doc, dict):
                    # Extract URL and title from multiple possible locations
                    metadata = doc.get("metadata", {})
                    url = (doc.get("url") or metadata.get("url") or metadata.get("document_source", ""))

                    # Clean URL from any unwanted characters
                    url = self._clean_url(url)

                    # Extract title with fallback options
                    title = (doc.get("title") or
                            metadata.get("title") or
                            metadata.get("document_name") or
                            f"Source - {url[:50]}..." if url else "No Title")

                    # Determine source type
                    source_type = metadata.get("source_type", "document")
                    if metadata.get("source") == "internet_search":
                        source_type = "website"

                    # Create consistent entry format
                    entry = {
                        "content": doc.get("content", doc.get("page_content", "")),
                        "metadata": {
                            **metadata,
                            "title": title,
                            "url": url,
                            "source_type": source_type,
                            "has_valid_url": bool(url and url.startswith('http') and url != 'https://duckduckgo.com/search'),
                            "is_web_source": metadata.get("source") == "internet_search"
                        },
                        "score": _format_score(doc.get("score")),
                        "url": url,  # Also store at top level for easy access
                        "title": title,
                        "source_type": source_type
                    }

                # Handle tuple format (from vectordb)
                elif isinstance(doc, tuple) and len(doc) == 2:
                    doc_obj, score = doc
                    metadata = getattr(doc_obj, "metadata", {})
                    url = metadata.get("url", metadata.get("document_source", ""))

                    # Clean URL from any unwanted characters
                    url = self._clean_url(url)

                    title = metadata.get("title", metadata.get("document_name", "Document Source"))

                    entry = {
                        "content": getattr(doc_obj, "page_content", getattr(doc_obj, "content", "")),
                        "metadata": {
                            **metadata,
                            "has_valid_url": bool(url and url.startswith('http')),
                            "is_web_source": False
                        },
                        "score": _format_score(score),
                        "url": url,
                        "title": title,
                        "source_type": metadata.get("source_type", "document")
                    }
                else:
                    entry = {
                        "content": str(doc),
                        "metadata": {"source_type": "text", "is_web_source": False},
                        "url": "",
                        "title": "Text Source",
                        "source_type": "text"
                    }

                sources.append(entry)

            sources_json = json.dumps(sources, ensure_ascii=False)

            # Handle attachments
            attachments_json = None
            logging.warning(f"{json.dumps(attachments)}")
            try:
                # Jika None maka ubah jadi list kosong
                if not attachments:
                    attachments = []
                    path_list = []
                
                # Masukkan hanya path saja
                path_list = [str(f['path']) for f in attachments if f is not None]
                attachments_json = json.dumps(path_list)
            except Exception as e:
                logging.warning(f"❌ Gagal Manage documents untuk save ke db chat_details dan documents {e}")
                attachments_json = "[]"

            # Save to chats table
            self.save_chat(
                chat_id=chat_id,
                question=question,
                answer=None,
                user_id=user_id,
                options=options
            )

            # Insert into chat_details table
            query = """
                INSERT INTO chat_details (id, chat_id, question, answer, source_documents, attachments, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            params = (chat_detail_id, chat_id, question, answer, sources_json, attachments_json)
            result = safe_db_query(query, params)

            if not result or (isinstance(result, tuple) and result[1] == 0):
                logging.warning(f"❌ Gagal menyimpan detail chat untuk sesi {chat_id}")

            # Log source statistics for debugging
            web_sources = sum(1 for s in sources if s.get("metadata", {}).get("is_web_source", False))
            doc_sources = len(sources) - web_sources
            url_count = sum(1 for s in sources if s.get("url") and s["url"].startswith("http"))

            logging.info(f"💾 Chat history saved for session {chat_id}: {len(sources)} sources ({web_sources} web, {doc_sources} doc, {url_count} URLs)")

        except Exception as e:
            logging.error(f"❌ Error saving chat history: {e}")
            logging.error(f"Documents structure: {[type(doc) for doc in documents]}")
            # Log first document for debugging
            if documents:
                logging.error(f"First document sample: {documents[0]}")

    def update_chat_history(self, chat_id: str, question: str, answer: str) -> None:
        """
        Update in-memory chat history for a session.
        
        Args:
            chat_id (str): Session identifier
            question (str): User question
            answer (str): Generated answer
        """
        try:
            # Ensure session exists in memory
            if chat_id not in self.chat_histories:
                self.chat_histories[chat_id] = []
            
            # Add new Q&A pair if it's not already the last entry (avoid duplicates)
            if not self.chat_histories[chat_id] or self.chat_histories[chat_id][-1] != (question, answer):
                self.chat_histories[chat_id].append((question, answer))
                
        except Exception as e:
            logging.warning(f"Failed to update in-memory chat history for session {chat_id}: {e}")

    def get_chat_history(self, chat_id: str) -> List[Tuple[str, str]]:
        """
        Get chat history for a session, loading from database if not in memory.
        
        Args:
            chat_id (str): Session identifier
            
        Returns:
            List[Tuple[str, str]]: List of (question, answer) tuples
        """
        try:
            if chat_id not in self.chat_histories:
                self.chat_histories[chat_id] = self.load_chat_history_from_db(chat_id)
            
            return self.chat_histories[chat_id]
        except Exception as e:
            logging.error(f"Error getting chat history for session {chat_id}: {e}")
            return []

    def ensure_chat_history_loaded(self, chat_id: str) -> None:
        """
        Ensure chat history is loaded for a session.
        
        Args:
            chat_id (str): Session identifier
        """
        try:
            if chat_id not in self.chat_histories:
                self.chat_histories[chat_id] = self.load_chat_history_from_db(chat_id)
        except Exception as e:
            logging.warning(f"Failed to load chat history for session {chat_id}: {e}")
            self.chat_histories[chat_id] = []

    def _clean_url(self, url: str) -> str:
        """
        Clean URL from unwanted characters and formatting issues.
        Args:
            url: Raw URL string
        Returns:
            Cleaned URL string
        """
        import re
        
        if not url:
            return ""

        # Convert to string and strip whitespace
        original_url = str(url).strip()

        # Remove trailing punctuation and unwanted closing characters
        # Use regex to strip any trailing ')', ']', '}', '.', ',', ':', ';'
        cleaned_url = re.sub(r'[)\]\}\.,:;]+$', '', original_url)

        # Remove enclosing parentheses if present
        if cleaned_url.startswith('(') and cleaned_url.endswith(')'):
            cleaned_url = cleaned_url[1:-1]

        # Final strip for whitespace
        cleaned_url = cleaned_url.strip()

        # Normalize common tracking parameters to improve deduplication
        try:
            from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
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

        return cleaned_url
