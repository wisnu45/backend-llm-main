"""
LLM prompt template service for creating and formatting prompts safely.
Handles prompt template creation, message formatting, and error handling.
"""
import time
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

import app.services.agent.system_prompts as system_prompts

logger = logging.getLogger('agent.prompt_service')

class PromptService:
    """
    Service for creating and formatting LLM prompts with robust error handling.
    """

    def __init__(self):
        """Initialize the prompt service."""
        pass

    def create_robust_prompt_template(self, system_template: str, user_template: Optional[str] = None, **template_vars):
        """
        Create a robust ChatPromptTemplate with proper error handling and variable safety.
        
        Args:
            system_template: System message template string
            user_template: User message template string (optional, defaults to "{input}")
            **template_vars: Variables to be safely included in the template
            
        Returns:
            ChatPromptTemplate instance with safe variable handling
        """
        try:
            # Agent-specific variables that should NOT be formatted immediately
            agent_reserved_vars = {'input', 'agent_scratchpad'}

            # Set default values for common variables to prevent NameError
            safe_vars = {
                'current_year': time.localtime().tm_year,
                'current_month': time.localtime().tm_mon,
                'current_day': time.localtime().tm_mday,
                'context': '',
                'question': '',
                'combined_context': '',
                'search_results': '',
                'chat_history_context': '',
                'valid_sources': 0,
                'user_question': '',
                'enhanced_question': '',
                'expanded_context': '',
                'last_question': '',
                'last_answer_preview': '',
                'original_question': '',
                'query': '',
                **template_vars  # Override defaults with provided values
            }

            # Helper: escape all braces but preserve {identifier} placeholders.
            # This keeps JSON examples safe (e.g. {"a": 1}) while allowing template
            # variables like {question}, {chat_history}, {user_reply}, etc.
            _placeholder_re = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")

            def _escape_preserve(text: str) -> str:
                if not isinstance(text, str):
                    return str(text)
                escaped = text.replace('{', '{{').replace('}', '}}')
                return _placeholder_re.sub(r"{\1}", escaped)

            # Check if this is an agent template (contains agent-reserved variables)
            is_agent_template = any(f'{{{var}}}' in (system_template or '') for var in agent_reserved_vars)
            is_agent_template = is_agent_template or (user_template and any(f'{{{var}}}' in user_template for var in agent_reserved_vars))

            # Sanitize templates
            sanitized_system = _escape_preserve(system_template)
            sanitized_user = _escape_preserve(user_template or "{input}")

            if is_agent_template:
                # For agent templates, do not format reserved placeholders now
                # Optionally inline non-reserved variables to reduce formatting later
                processed_system = sanitized_system
                for var_name, var_value in list(safe_vars.items()):
                    if var_name not in agent_reserved_vars and f'{{{var_name}}}' in processed_system:
                        processed_system = processed_system.replace(f'{{{var_name}}}', str(var_value))

                messages = [
                    ("system", processed_system),
                    ("user", sanitized_user),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            else:
                # For regular templates, defer all formatting to format_messages
                messages = [
                    ("system", sanitized_system),
                    ("user", sanitized_user)
                ]

            return ChatPromptTemplate.from_messages(messages)

        except KeyError as e:
            logging.error(f"❌ Missing template variable: {e}")
            # Fallback to a simple template
            fallback_system = system_prompts.DEFAULT_ASSISTANT_PROMPT_WITH_HELP
            return ChatPromptTemplate.from_messages([
                ("system", fallback_system),
                ("user", "Please help me.")
            ])
        except Exception as e:
            logging.error(f"❌ Error creating prompt template: {e}")
            # Fallback to a minimal template
            return ChatPromptTemplate.from_messages([
                ("system", system_prompts.DEFAULT_ASSISTANT_PROMPT),
                ("user", "Please help me.")
            ])

    def safe_format_messages(self, prompt_template, **format_vars):
        """
        Safely format messages with proper error handling.
        
        Args:
            prompt_template: ChatPromptTemplate instance
            **format_vars: Variables for formatting
            
        Returns:
            Formatted messages list or fallback messages
        """
        try:
            # Check if the template is actually a ChatPromptTemplate
            if not hasattr(prompt_template, 'format_messages'):
                logging.error(f"❌ Invalid prompt template type: {type(prompt_template)}")
                # Create a fallback template
                fallback_template = ChatPromptTemplate.from_messages([
                    ("system", system_prompts.DEFAULT_ASSISTANT_PROMPT),
                    ("user", "{input}")
                ])
                return fallback_template.format_messages(input=format_vars.get('input', format_vars.get('question', 'Please help me.')))

            # Always format and return messages; provide safe defaults.
            safe_defaults = {
                'input': format_vars.get('input', format_vars.get('question', 'Please help me.')),
                'agent_scratchpad': format_vars.get('agent_scratchpad', []),
            }
            merged = {**safe_defaults, **format_vars}

            # Fill in any missing variables required by the prompt template.
            # This prevents KeyError and avoids falling back to unrelated prompts.
            required_vars = getattr(prompt_template, 'input_variables', None)
            if required_vars:
                for name in required_vars:
                    if name not in merged:
                        merged[name] = [] if name == 'agent_scratchpad' else ''

            formatted_messages = prompt_template.format_messages(**merged)
            return formatted_messages

        except KeyError as e:
            logging.error(f"❌ Missing format variable: {e}")
            # Provide default values for common missing variables
            safe_format_vars = {
                'input': format_vars.get('question', 'Please help me.'),
                'question': format_vars.get('input', 'Please help me.'),
                'context': '',
                'combined_context': '',
                'chat_history_context': '',
                'current_year': time.localtime().tm_year,
                'current_month': time.localtime().tm_mon,
                'current_day': time.localtime().tm_mday,
                'agent_scratchpad': [],
                **format_vars
            }

            try:
                return prompt_template.format_messages(**safe_format_vars)
            except Exception as inner_e:
                logging.error(f"❌ Failed to format with safe variables: {inner_e}")
                # Create fallback messages
                fallback_template = ChatPromptTemplate.from_messages([
                    ("system", system_prompts.DEFAULT_ASSISTANT_PROMPT),
                    ("user", "{input}")
                ])
                return fallback_template.format_messages(input=format_vars.get('input', format_vars.get('question', 'Please help me.')))

        except Exception as e:
            logging.error(f"❌ Error formatting messages: {e}")
            logging.error(f"Template type: {type(prompt_template)}")
            # Return minimal fallback
            fallback_template = ChatPromptTemplate.from_messages([
                ("system", system_prompts.DEFAULT_ASSISTANT_PROMPT),
                ("user", "Please help me.")
            ])
            return fallback_template.format_messages()

    def create_generation_prompt(self, context: str, chat_history_context: str = "", language: str = "id") -> ChatPromptTemplate:
        """
        Create a standard prompt template for document-based generation.
        
        Args:
            context: Document context string
            chat_history_context: Chat history context string
            language: Detected language code (default: 'id')
            
        Returns:
            ChatPromptTemplate for document generation
        """
        return self.create_robust_prompt_template(
            system_template=system_prompts.GENERATION_PROMPT,
            user_template="{question}",
            context=context,
            chat_history_context=chat_history_context,
            language=language
        )

    def create_grounding_assessment_prompt(self) -> ChatPromptTemplate:
        """
        Create a prompt template for assessing answer grounding in documents.
        
        Returns:
            ChatPromptTemplate for grounding assessment
        """
        return self.create_robust_prompt_template(
            system_template=system_prompts.GROUNDING_ASSESSMENT_PROMPT,
            user_template="DOKUMEN:\n{documents}\n\nJAWABAN:\n{answer}\n\nSkor grounding:"
        )

    def create_relevance_check_prompt(self) -> ChatPromptTemplate:
        """
        Create a prompt template for checking answer relevance.
        
        Returns:
            ChatPromptTemplate for relevance checking
        """
        return self.create_robust_prompt_template(
            system_template=system_prompts.RELEVANCE_CHECK_PROMPT,
            user_template="PERTANYAAN: {question}\n\nJAWABAN: {answer}\n\nStatus:"
        )

    def create_context_enhancement_prompt(self, last_question: str, last_answer: str) -> ChatPromptTemplate:
        """
        Create a prompt template for enhancing questions with context.
        
        Args:
            last_question: Previous question from chat history
            last_answer: Previous answer from chat history
            
        Returns:
            ChatPromptTemplate for context enhancement
        """
        # Truncate last answer for context
        last_answer_preview = last_answer[:300] + "..." if len(last_answer) > 300 else last_answer

        return self.create_robust_prompt_template(
            system_template=system_prompts.CONTEXT_ENHANCEMENT_PROMPT,
            user_template="PERTANYAAN BARU: {question}\n\nBuat pertanyaan pencarian yang lengkap dan jelas:",
            last_question=last_question,
            last_answer_preview=last_answer_preview
        )

    def create_relation_analysis_prompt(self, last_question: str, last_answer: str) -> ChatPromptTemplate:
        """
        Create a prompt template for analyzing question relationships.
        
        Args:
            last_question: Previous question from chat history
            last_answer: Previous answer from chat history
            
        Returns:
            ChatPromptTemplate for relation analysis
        """
        # Truncate last answer for analysis
        last_answer_preview = last_answer[:300] + "..." if len(last_answer) > 300 else last_answer

        return self.create_robust_prompt_template(
            system_template=system_prompts.RELATION_ANALYSIS_PROMPT,
            user_template="PERTANYAAN BARU: {question}",
            last_question=last_question,
            last_answer_preview=last_answer_preview
        )

    def create_translation_prompt(self, target_language: str) -> ChatPromptTemplate:
        """Create a prompt template for high-fidelity translations."""
        return self.create_robust_prompt_template(
            system_template=system_prompts.TRANSLATION_PROMPT,
            user_template="{input}",
            target_language=target_language
        )

    def create_arithmetic_explanation_prompt(self, expression: str, result: float) -> str:
        """
        Create an explanation for arithmetic calculations.
        
        Args:
            expression: The arithmetic expression
            result: The calculated result
            
        Returns:
            Formatted explanation string
        """
        try:
            import re
            
            def _format_number_brief(value: float) -> str:
                try:
                    if abs(value - round(value)) < 1e-9:
                        return str(int(round(value)))
                    s = f"{value:.6f}"
                    s = s.rstrip("0").rstrip(".")
                    return s
                except Exception:
                    return str(value)

            pretty = expression.replace("**", "^").replace("*", "×").replace("/", "÷")
            ans = _format_number_brief(result)

            # Heuristic operator detection
            has_mul = "×" in pretty
            has_add = "+" in pretty
            has_sub = "-" in pretty and not pretty.strip().startswith("-")
            has_div = "÷" in pretty
            has_pow = "^" in pretty

            explanation = [f"{pretty} = {ans}."]
            if has_pow:
                explanation.append("Pangkat berarti mengalikan bilangan basis dengan dirinya sendiri sejumlah pangkatnya.")
            if has_mul:
                # Try repeated addition if both operands small integers
                m = re.match(r"\s*(\d+)\s*×\s*(\d+)\s*$", pretty)
                if m:
                    a, b = int(m.group(1)), int(m.group(2))
                    if a <= 10 and b <= 10:
                        explanation.append(f"Karena {a} dikali {b} adalah penjumlahan {a} sebanyak {b} kali: "
                                           f"{'+'.join([str(a)]*b)} = {ans}.")
                else:
                    explanation.append("Perkalian dapat dipahami sebagai penjumlahan berulang.")
            if has_div:
                explanation.append("Pembagian membagi bilangan menjadi bagian yang sama besar.")
            if has_add and not has_mul and not has_div and not has_pow:
                explanation.append("Penjumlahan menggabungkan nilai-nilai menjadi satu total.")
            if has_sub and not has_mul and not has_div and not has_pow:
                explanation.append("Pengurangan mengurangi suatu nilai dari nilai lainnya.")

            return " ".join(explanation)
        except Exception:
            ans = _format_number_brief(result) if 'result' in locals() else str(result)
            return f"Hasilnya {ans}."

    def get_markdown_guide(self) -> str:
        """
        Get the markdown formatting guide.
        
        Returns:
            Markdown formatting guide string
        """
        return system_prompts.MARKDOWN_GUIDE
