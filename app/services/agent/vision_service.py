"""Vision-aware attachment helper using OpenAI Chat Completions API."""

import base64
import logging
import mimetypes
import os
from typing import Optional

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from app.utils.setting import get_openai_api_key
from app.utils.llm_timeout import get_llm_timeout


class VisionService:
    """Provide textual descriptions for image attachments via OpenAI vision models."""

    def __init__(self) -> None:
        self.model = os.getenv("OPENAI_VISION_MODEL", os.getenv("VISION_MODEL", "gpt-4o-mini"))
        self.max_tokens = int(os.getenv("OPENAI_VISION_MAX_TOKENS", os.getenv("VISION_MAX_TOKENS", "900")))
        self.enabled = os.getenv("ENABLE_VISION_ATTACHMENTS", "1").strip().lower() not in {"0", "false", "no"}
        self.client: Optional[OpenAI] = None

        if not self.enabled:
            logging.info("VisionService disabled via ENABLE_VISION_ATTACHMENTS flag")
            return

        try:
            api_key = get_openai_api_key()
            client_kwargs = {"api_key": api_key}
            timeout_value = get_llm_timeout()
            if timeout_value is not None:
                client_kwargs["timeout"] = timeout_value
            try:
                self.client = OpenAI(**client_kwargs)
            except TypeError:
                if "timeout" in client_kwargs:
                    client_kwargs.pop("timeout", None)
                    self.client = OpenAI(**client_kwargs)
                else:
                    raise
        except Exception as exc:  # pragma: no cover - defensive guard
            logging.warning(f"VisionService initialization failed: {exc}")
            self.enabled = False

    def describe_image(self, image_path: str, question: Optional[str] = None) -> Optional[str]:
        """Return a natural-language summary of an image using Chat Completions vision."""
        if not self.enabled or not self.client:
            return None

        if not image_path or not os.path.exists(image_path):
            logging.warning(f"VisionService.describe_image called with missing file: {image_path}")
            return None

        try:
            with open(image_path, "rb") as file_obj:
                encoded = base64.b64encode(file_obj.read()).decode("utf-8")

            mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
            data_url = f"data:{mime_type};base64,{encoded}"

            focus_prompt = (question or "Jelaskan isi gambar ini secara detail.").strip()
            user_content = [
                {
                    "type": "text",
                    "text": (
                        "Ekstrak teks penting (angka, tabel, paragraf) dari gambar lalu jelaskan poin utama "
                        "dalam Bahasa Indonesia. Fokuskan jawaban pada pertanyaan pengguna berikut:\n"
                        f"{focus_prompt}"
                    ),
                },
                {"type": "image_url", "image_url": {"url": data_url}},
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Anda adalah asisten yang ahli membaca dokumen bergambar dan menyalin teks penting secara akurat.",
                    },
                    {"role": "user", "content": user_content},
                ],
                max_tokens=self.max_tokens,
                temperature=0.2,
            )

            choice = response.choices[0] if response.choices else None
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None) if message else None
            if isinstance(content, str) and content.strip():
                return content.strip()
        except (AuthenticationError, RateLimitError, APIError) as exc:
            logging.error(f"VisionService OpenAI error: {exc}")
        except Exception as exc:  # pragma: no cover - best effort logging
            logging.error(f"VisionService unexpected error: {exc}")

        return None

    def describe_image_base64(self, image_base64: str, question: Optional[str] = None, mime_type: Optional[str] = None) -> Optional[str]:
        """Return a natural-language summary of an image using Chat Completions vision, from base64 string."""
        if not self.enabled or not self.client:
            return None

        if not image_base64 or not isinstance(image_base64, str):
            logging.warning("VisionService.describe_image_base64 called with missing or invalid base64 string")
            return None

        try:
            mime_type_val = mime_type or "image/png"
            data_url = f"data:{mime_type_val};base64,{image_base64}"

            focus_prompt = (question or "Jelaskan isi gambar ini secara detail.").strip()
            user_content = [
                {
                    "type": "text",
                    "text": (
                        "Ekstrak teks penting (angka, tabel, paragraf) dari gambar lalu jelaskan poin utama "
                        "dalam Bahasa Indonesia. Fokuskan jawaban pada pertanyaan pengguna berikut:\n"
                        f"{focus_prompt}"
                    ),
                },
                {"type": "image_url", "image_url": {"url": data_url}},
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Anda adalah asisten yang ahli membaca dokumen bergambar dan menyalin teks penting secara akurat.",
                    },
                    {"role": "user", "content": user_content},
                ],
                max_tokens=self.max_tokens,
                temperature=0.2,
            )

            choice = response.choices[0] if response.choices else None
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None) if message else None
            if isinstance(content, str) and content.strip():
                return content.strip()
        except (AuthenticationError, RateLimitError, APIError) as exc:
            logging.error(f"VisionService OpenAI error: {exc}")
        except Exception as exc:  # pragma: no cover - best effort logging
            logging.error(f"VisionService unexpected error: {exc}")

        return None
        