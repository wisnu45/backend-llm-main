"""Excel-aware attachment helper using OpenAI Chat Completions API.

This service reads a small sample from an Excel file and asks OpenAI to
generate a short metadata description (in Bahasa Indonesia) suitable for
the repository's `auto_description` usage.
"""

import logging
import os
from typing import Optional

try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas may not be importable in all test envs
    pd = None

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from app.utils.setting import get_openai_api_key
from app.utils.llm_timeout import get_llm_timeout


class FileExcelService:
    """Provide short metadata/descriptions for Excel files using OpenAI.

    Usage:
      svc = FileExcelService()
      desc = svc.generate_summary("/path/to/file.xlsx")

    Returns: description string or None on error/disabled.
    """

    def __init__(self) -> None:
        self.model = os.getenv("OPENAI_EXCEL_MODEL", os.getenv("EXCEL_MODEL", "gpt-4o-mini"))
        self.max_tokens = int(os.getenv("OPENAI_EXCEL_MAX_TOKENS", os.getenv("EXCEL_MAX_TOKENS", "900")))
        self.enabled = os.getenv("ENABLE_EXCEL_ATTACHMENTS", "1").strip().lower() not in {"0", "false", "no"}
        self.client: Optional[OpenAI] = None

        if not self.enabled:
            logging.info("FileExcelService disabled via ENABLE_EXCEL_ATTACHMENTS flag")
            return

        if pd is None:
            logging.warning("pandas not available; FileExcelService will be disabled")
            self.enabled = False
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
        except Exception as exc:  # pragma: no cover - defensive
            logging.warning(f"FileExcelService initialization failed: {exc}")
            self.enabled = False

    def generate_summary(self, file_path: str, filename: Optional[str] = None, nrows: int = 5, question: Optional[str] = None) -> Optional[str]:
        """Return a short, one-sentence description for an Excel file (in Bahasa Indonesia).

        Reads up to `nrows` rows from the Excel file to provide a sample to the model.
        If `question` is provided, the model will focus the description on that prompt.
        """
        if not self.enabled or not self.client:
            return None

        if not file_path or not os.path.exists(file_path):
            logging.warning(f"FileExcelService.generate_summary called with missing file: {file_path}")
            return None

        try:
            df = pd.read_excel(file_path, nrows=nrows)
        except Exception as exc:  # pragma: no cover - best effort
            logging.error(f"FileExcelService cannot read excel file {file_path}: {exc}")
            return None

        try:
            filename = filename or "-"
            columns = ", ".join(df.columns.tolist()) if not df.empty else "(tidak ada kolom terdeteksi)"
            sample_data = df.to_string(index=False) if not df.empty else "(tidak ada baris sampel)"

            focus_prompt = (question or "Buat deskripsi metadata singkat untuk file dataset ini.").strip()

            user_content = (
                f"NAMA FILE: \"{filename}\"\n"
                f"KOLOM: {columns}\n"
                f"SAMPEL DATA (hingga {nrows} baris):\n{sample_data}\n\n"
                "Tugasmu adalah membuat Metadata Description untuk sistem RAG.\n"
                "Ikuti format output berikut secara ketat:\n\n"
                "1. Deskripsi: Jelaskan topik data, rentang waktu (jika ada), dan entitas utama dalam 1 kalimat bahasa Indonesia.\n"
                "2. Kolom Filter: Tuliskan ULANG semua nama kolom yang bisa digunakan untuk memfilter data (seperti Kategori, Kota, Brand, Status, dll). Jangan gunakan kata 'dll', sebutkan semuanya.\n\n"
                f"Fokus tambahan: {focus_prompt}"
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Anda adalah asisten yang membuat deskripsi metadata singkat dan akurat untuk file dataset.",
                    },
                    {"role": "user", "content": user_content},
                ],
                max_tokens=self.max_tokens,
                temperature=0.0,
            )

            choice = response.choices[0] if response.choices else None
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None) if message else None
            if isinstance(content, str) and content.strip():
                return content.strip()
        except (AuthenticationError, RateLimitError, APIError) as exc:
            logging.error(f"FileExcelService OpenAI error: {exc}")
        except Exception as exc:  # pragma: no cover - best effort logging
            logging.error(f"FileExcelService unexpected error: {exc}")

        return None
