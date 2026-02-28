"""
Question Contextualizer Service

Service untuk memahami dan memperkaya pertanyaan user berdasarkan konteks percakapan sebelumnya.
Mendeteksi pertanyaan yang membutuhkan konteks (seperti "syaratnya apa?", "bagaimana caranya?", dll)
dan menggabungkannya dengan topik dari chat history.
"""

import logging
import re
from typing import List, Tuple, Optional, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from openai import AuthenticationError, RateLimitError, APIError

from app.utils.setting import get_openai_api_key
from app.utils.llm_timeout import init_chat_openai
from app.services.agent.error_handler import ErrorHandler

logger = logging.getLogger('agent.question_contextualizer')

class QuestionContextualizer:
    """
    Service untuk menganalisis dan memperkaya pertanyaan user berdasarkan konteks percakapan.
    """
    
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        """
        Initialize question contextualizer with lightweight LLM for fast processing.
        """
        self.llm_model = llm_model
        self.llm = None
        self._init_llm()
        self._init_templates()
        
        # Pattern untuk mendeteksi pertanyaan yang membutuhkan konteks
        self.contextual_patterns = [
            # Pronoun references
            r'\b(itu|ini|tersebut|dia|mereka|nya|mu|ku)\b',
            
            # Incomplete questions starting with question words
            r'^(apa|bagaimana|mengapa|kenapa|kapan|dimana|siapa|berapa)\s+(?:saja\s+)?(syarat|cara|prosedur|langkah|tahap|proses|ketentuan|aturan|kondisi)',
            
            # Questions starting with adjectives/descriptors without clear subject
            r'^(syarat|cara|prosedur|langkah|tahap|proses|ketentuan|aturan|kondisi|persyaratan|kriteria)',
            
            # Short questions with question words but incomplete context
            r'^(apa\s+(?:saja\s+)?(?:syarat|cara|prosedur|langkah|tahap|proses|ketentuan|aturan|kondisi|persyaratan|kriteria))',
            r'^(bagaimana\s+(?:cara\s+)?(?:prosedur|langkah|tahap|proses))',
            r'^(berapa\s+(?:lama|banyak|jumlah))',
            
            # Follow-up questions
            r'^(lalu|terus|kemudian|selanjutnya|dan)\s+',
            r'(nya\s+apa|nya\s+bagaimana|nya\s+berapa|nya\s+kapan)',
            
            # Questions with missing subject
            r'^(bisa|boleh|harus|wajib|perlu)\s+(?!(?:saya|anda|dia|mereka|kita)\s)',
            
            # Time-based follow-ups
            r'^(kapan|berapa\s+lama)\s*$',
            
            # Simple yes/no follow-ups that need context
            r'^(bisa|boleh|harus|wajib|ada|tidak)\s*\??\s*$'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.contextual_patterns]
        
        # Keywords yang menunjukkan topik spesifik
        self.topic_keywords = [
            'cuti', 'izin', 'sakit', 'absen', 'lembur', 'gaji', 'tunjangan',
            'promosi', 'mutasi', 'training', 'pelatihan', 'kinerja', 'evaluasi',
            'kontrak', 'resign', 'pensiun', 'benefits', 'asuransi', 'kesehatan',
            'reimbursement', 'perjalanan', 'dinas', 'meeting', 'rapat', 'project',
            'deadline', 'laporan', 'dokumen', 'surat', 'email', 'sistem'
        ]
    
    def _init_llm(self) -> None:
        """Initialize lightweight LLM for question enhancement."""
        try:
            api_key = get_openai_api_key()
            if not api_key:
                logger.warning("OpenAI API key not available for question contextualizer")
                return
            
            # Use lightweight model for fast processing
            llm_kwargs = {
                "model": self.llm_model,
                "temperature": 0.1,  # Low temperature for consistent results
                "api_key": api_key,
            }
            self.llm = init_chat_openai(llm_kwargs, max_tokens=150)
            logger.info(f"Question contextualizer LLM initialized: {self.llm_model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize question contextualizer LLM: {e}")
            self.llm = None
    
    def _init_templates(self) -> None:
        """Initialize prompt templates for question enhancement."""
        
        self.enhancement_template = ChatPromptTemplate.from_messages([
            ("system", """
Anda adalah asisten yang menganalisis pertanyaan dalam konteks percakapan.

Tugas: Analisis apakah pertanyaan user membutuhkan konteks dari percakapan sebelumnya, dan jika ya, perkaya pertanyaan tersebut.

ATURAN PENTING:
1. Jika pertanyaan sudah jelas dan lengkap, kembalikan pertanyaan asli
2. Jika pertanyaan merujuk konteks sebelumnya (misal: "syaratnya apa?", "bagaimana caranya?"), gabungkan dengan topik dari riwayat
3. Fokus pada topik utama dari percakapan terakhir
4. Buat pertanyaan yang lebih spesifik untuk pencarian dokumen
5. Pertahankan bahasa dan gaya bicara user
6. Jangan menambah informasi yang tidak ada

Format respons JSON:
{{
    "needs_context": true/false,
    "enhanced_question": "pertanyaan yang diperkaya",
    "detected_topic": "topik yang terdeteksi dari konteks",
    "confidence": 0.0-1.0
}}
"""),
            ("user", """
RIWAYAT PERCAKAPAN:
{chat_history}

PERTANYAAN SAAT INI: {current_question}

Analisis dan perkaya pertanyaan jika diperlukan:""")
        ])
    
    def needs_contextualization(self, question: str) -> bool:
        """
        Deteksi cepat apakah pertanyaan membutuhkan konteks berdasarkan pattern matching.
        
        Args:
            question: Pertanyaan user
            
        Returns:
            bool: True jika pertanyaan kemungkinan membutuhkan konteks
        """
        if not question or len(question.strip()) < 3:
            return False
        
        question_clean = question.strip().lower()
        
        # Cek pattern yang menunjukkan butuh konteks
        for pattern in self.compiled_patterns:
            if pattern.search(question_clean):
                logger.debug(f"Question needs context - pattern matched: {pattern.pattern}")
                return True
        
        # Cek jika pertanyaan terlalu pendek dan ambigu
        if len(question_clean.split()) <= 3 and any(word in question_clean for word in ['apa', 'bagaimana', 'berapa', 'kapan', 'dimana']):
            logger.debug("Question needs context - short and ambiguous")
            return True
        
        return False
    
    def extract_topics_from_history(self, chat_history: List[Tuple[str, str]], limit: int = 2) -> List[str]:
        """
        Ekstrak topik utama dari chat history terakhir.
        
        Args:
            chat_history: List of (question, answer) tuples
            limit: Jumlah percakapan terakhir yang dianalisis
            
        Returns:
            List[str]: Topik yang terdeteksi
        """
        if not chat_history:
            return []
        
        topics = []
        recent_history = chat_history[-limit:] if len(chat_history) > limit else chat_history
        
        for question, answer in recent_history:
            # Kombinasi question dan answer untuk analisis topik
            text_to_analyze = f"{question} {answer}".lower()
            
            # Cari keyword topik
            for topic in self.topic_keywords:
                if topic in text_to_analyze and topic not in topics:
                    topics.append(topic)
            
            # Ekstrak noun phrases sederhana (kata benda berurutan)
            words = re.findall(r'\b\w+\b', text_to_analyze)
            for i, word in enumerate(words):
                if word in ['prosedur', 'syarat', 'cara', 'langkah', 'proses', 'ketentuan', 'aturan']:
                    # Cari kata setelahnya yang mungkin topik
                    if i + 1 < len(words):
                        next_word = words[i + 1]
                        topic_candidate = f"{word} {next_word}"
                        if len(next_word) > 2 and topic_candidate not in topics:
                            topics.append(next_word)
        
        return topics[:3]  # Ambil maksimal 3 topik teratas
    
    def enhance_question_fast(self, question: str, chat_history: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Fast question enhancement menggunakan rule-based approach tanpa LLM.
        
        Args:
            question: Pertanyaan user
            chat_history: Riwayat percakapan
            
        Returns:
            Dict dengan enhanced_question dan metadata
        """
        if not self.needs_contextualization(question):
            return {
                "needs_context": False,
                "enhanced_question": question,
                "detected_topic": None,
                "confidence": 0.0,
                "method": "rule_based"
            }
        
        # Ekstrak topik dari history
        topics = self.extract_topics_from_history(chat_history)
        
        if not topics:
            return {
                "needs_context": True,
                "enhanced_question": question,
                "detected_topic": None,
                "confidence": 0.0,
                "method": "rule_based"
            }
        
        # Rule-based enhancement
        question_lower = question.lower().strip()
        main_topic = topics[0]  # Ambil topik utama
        
        enhanced_question = question
        confidence = 0.0
        
        # Pattern-based enhancement rules
        if re.match(r'^(apa|bagaimana)\s+syarat', question_lower):
            enhanced_question = f"apa syarat {main_topic}"
            confidence = 0.8
        elif re.match(r'^syarat', question_lower):
            enhanced_question = f"syarat {main_topic} apa"
            confidence = 0.8
        elif re.match(r'^(bagaimana|gimana)\s+(cara|prosedur)', question_lower):
            enhanced_question = f"bagaimana cara {main_topic}"
            confidence = 0.8
        elif re.match(r'^(cara|prosedur)', question_lower):
            enhanced_question = f"cara {main_topic} bagaimana"
            confidence = 0.8
        elif question_lower in ['apa saja?', 'apa aja?']:
            enhanced_question = f"apa saja yang berkaitan dengan {main_topic}"
            confidence = 0.7
        elif question_lower in ['bagaimana?', 'gimana?']:
            enhanced_question = f"bagaimana {main_topic}"
            confidence = 0.7
        elif question_lower in ['berapa lama?', 'kapan?']:
            enhanced_question = f"berapa lama proses {main_topic}"
            confidence = 0.7
        elif 'nya' in question_lower:
            # Handle questions with possessive pronouns
            enhanced_question = re.sub(r'\bnya\b', main_topic, question, flags=re.IGNORECASE)
            confidence = 0.6
        
        return {
            "needs_context": True,
            "enhanced_question": enhanced_question,
            "detected_topic": main_topic,
            "confidence": confidence,
            "method": "rule_based"
        }
    
    def enhance_question_with_llm(self, question: str, chat_history: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Enhanced question contextualizer menggunakan LLM untuk akurasi lebih tinggi.
        
        Args:
            question: Pertanyaan user
            chat_history: Riwayat percakapan
            
        Returns:
            Dict dengan enhanced_question dan metadata
        """
        if not self.llm:
            logger.debug("LLM not available, using fast enhancement")
            return self.enhance_question_fast(question, chat_history)
        
        # Format chat history
        history_text = ""
        if chat_history:
            recent_history = chat_history[-3:]  # Ambil 3 percakapan terakhir
            for i, (q, a) in enumerate(recent_history, 1):
                history_text += f"Q{i}: {q}\nA{i}: {a}\n\n"
        
        if not history_text:
            return {
                "needs_context": False,
                "enhanced_question": question,
                "detected_topic": None,
                "confidence": 0.0,
                "method": "no_history"
            }
        
        try:
            # Format prompt
            formatted_messages = self.enhancement_template.format_messages(
                chat_history=history_text.strip(),
                current_question=question
            )
            
            # Call LLM
            result = self.llm.invoke(formatted_messages)
            response_text = str(result.content) if hasattr(result, "content") else str(result)
            
            # Parse JSON response
            import json
            try:
                result_data = json.loads(response_text)
                result_data["method"] = "llm"
                return result_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response: {response_text}")
                # Fallback to fast method
                return self.enhance_question_fast(question, chat_history)
        
        except (AuthenticationError, RateLimitError, APIError) as e:
            logger.error(f"OpenAI API error in question contextualizer: {e}")
            return self.enhance_question_fast(question, chat_history)
        except Exception as e:
            logger.error(f"Error in LLM question enhancement: {e}")
            return self.enhance_question_fast(question, chat_history)
    
    def contextualize_question(self, question: str, chat_history: List[Tuple[str, str]], use_llm: bool = True) -> Dict[str, Any]:
        """
        Main method untuk mengkontekstualkan pertanyaan user.
        
        Args:
            question: Pertanyaan asli user
            chat_history: Riwayat percakapan
            use_llm: Gunakan LLM untuk enhancement (default) atau rule-based saja
            
        Returns:
            Dict dengan:
            - original_question: Pertanyaan asli user
            - enhanced_question: Pertanyaan yang diperkaya untuk pencarian
            - needs_context: Apakah pertanyaan membutuhkan konteks
            - detected_topic: Topik yang terdeteksi
            - confidence: Tingkat kepercayaan enhancement (0.0-1.0)
            - method: Metode yang digunakan
        """
        if not question or not question.strip():
            return {
                "original_question": question,
                "enhanced_question": question,
                "needs_context": False,
                "detected_topic": None,
                "confidence": 0.0,
                "method": "empty_question"
            }
        
        # Quick check untuk pertanyaan yang sudah jelas
        question_clean = question.strip()
        if len(question_clean.split()) >= 5 and not self.needs_contextualization(question_clean):
            return {
                "original_question": question,
                "enhanced_question": question,
                "needs_context": False,
                "detected_topic": None,
                "confidence": 0.0,
                "method": "already_clear"
            }
        
        # Enhancement process
        if use_llm and self.llm:
            enhancement_result = self.enhance_question_with_llm(question, chat_history)
        else:
            enhancement_result = self.enhance_question_fast(question, chat_history)
        
        # Add original question to result
        enhancement_result["original_question"] = question
        
        # Log enhancement if significant
        if enhancement_result["needs_context"] and enhancement_result["confidence"] > 0.5:
            logger.info(f"Question enhanced: '{question}' -> '{enhancement_result['enhanced_question']}'")
            logger.info(f"Topic: {enhancement_result.get('detected_topic')}, Confidence: {enhancement_result['confidence']:.2f}")
        
        return enhancement_result

# Export
__all__ = ['QuestionContextualizer']
