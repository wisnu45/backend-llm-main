"""
Pandas Service (Step 1)

Flow mirip `chain_excel.py` namun mengikuti gaya arsitektur `vectorstore_service.py`.

Step 1: Ambil daftar file Excel dari database (source_type='admin') dengan
mime_type yang sesuai dan metadata.Description tidak null/empty, memakai
safe_db_query dan pola logging yang konsisten.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple

from app.utils.database import safe_db_query
from app.utils.setting import get_openai_api_key
from app.utils.llm_timeout import get_llm_timeout, init_chat_openai
from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from langchain_core.documents import Document
from .file_excel_service import FileExcelService


logger = logging.getLogger('agent')


# MIME types yang didukung untuk Excel/Spreadsheet
SUPPORTED_EXCEL_MIMES = [
	'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
	'application/vnd.ms-excel',
	'application/vnd.oasis.opendocument.spreadsheet',
]


class PandasService:
	"""Service untuk operasi berbasis Pandas terhadap dokumen Excel.

	Catatan: Implementasi berjenjang (step-by-step). Pada Step 1 ini,
	hanya menyiapkan pengambilan daftar file dari database sesuai kriteria.
	"""

	def __init__(self) -> None:
		self.model = (
			os.getenv("OPENAI_PANDAS_MODEL", os.getenv("PANDAS_MODEL", "gpt-4o-mini"))
		)
		self.max_token = int(
			os.getenv("OPENAI_PANDAS_MAX_TOKENS", os.getenv("PANDAS_MAX_TOKENS", "300"))
		)
		self.enabled = (
			os.getenv("ENABLE_PANDAS_SELECTION", "1").strip().lower() not in {"0", "false", "no"}
		)
		self.client: Optional[OpenAI] = None

		if not self.enabled:
			logger.info("PandasService selection disabled via ENABLE_PANDAS_SELECTION flag")
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
			logger.warning(f"PandasService: OpenAI init failed: {exc}")
			self.enabled = False

	def list_described_files(self, limit: int = 200) -> List[Dict[str, Any]]:
		"""Ambil daftar dokumen Excel (source_type='admin') yang memiliki metadata.Description.

		Returns list of dicts berisi informasi dasar untuk tahap seleksi berikutnya.
		"""
		try:
			query = """
				SELECT 
					id,
					original_filename,
					stored_filename,
					mime_type,
					storage_path,
					metadata->>'Summary' AS summary,
					created_at
				FROM documents
				WHERE source_type = %s
				  AND mime_type = ANY(%s)
				  AND COALESCE(NULLIF(BTRIM(metadata->>'Summary'), ''), NULL) IS NOT NULL
				ORDER BY created_at DESC
				LIMIT %s
			"""

			params = [
				'admin',
				SUPPORTED_EXCEL_MIMES,
				int(limit),
			]
			results, columns = safe_db_query(query, params)

			docs: List[Dict[str, Any]] = []
			if isinstance(results, list) and results:
				# Buat mapping index kolom agar robust terhadap perubahan SELECT order
				col_idx = {name: i for i, name in enumerate(columns)} if columns else {}

				for row in results:
					try:
						doc = {
							'id': str(row[col_idx.get('id', 0)]),
							'original_filename': row[col_idx.get('original_filename', 1)],
							'stored_filename': row[col_idx.get('stored_filename', 2)],
							'mime_type': row[col_idx.get('mime_type', 3)],
							'storage_path': row[col_idx.get('storage_path', 4)],
							'summary': row[col_idx.get('summary', 5)],
							'created_at': row[col_idx.get('created_at', 6)],
						}
						docs.append(doc)
					except Exception as map_exc:  # pragma: no cover - defensive mapping
						logger.warning(f"PandasService: gagal memetakan baris dokumen: {map_exc}")
						continue

			logger.info(f"PandasService: ditemukan {len(docs)} dokumen Excel berdeskripsi untuk source_type=admin")
			return docs

		except Exception as e:
			logger.error(f"PandasService.list_described_files error: {e}", exc_info=True)
			return []

	def select_file_by_question(self, question: str, limit: int = 200) -> Optional[Dict[str, Any]]:
		"""Pilih satu file paling relevan berdasarkan deskripsi menggunakan OpenAI.

		- Mengambil daftar file via list_described_files()
		- Menyusun katalog singkat (ID, nama file, deskripsi)
		- Meminta model menjawab HANYA dengan salah satu ID yang tersedia atau NONE
		- Mengembalikan dict dokumen terpilih atau None jika tidak ada
		"""
		if not question or not isinstance(question, str):
			return None

		if not self.enabled or not self.client:
			return None

		docs = self.list_described_files(limit=limit)
		if not docs:
			return None

		# Susun katalog; batasi panjang deskripsi agar hemat token
		def _shorten(text: Optional[str], n: int = 200) -> str:
			if not text:
				return ""
			text = str(text).strip()
			return text if len(text) <= n else text[: n - 3] + "..."

		allowed_ids = [d.get('id') for d in docs if d.get('id')]
		catalog_lines: List[str] = []
		for d in docs:
			line = f"- ID: {d.get('id')} | Nama: {d.get('original_filename')} | Deskripsi: {_shorten(d.get('summary'))}"
			catalog_lines.append(line)
		catalog_text = "\n".join(catalog_lines)

		user_prompt = (
			"Kamu adalah asisten yang memilih satu file paling relevan untuk menjawab pertanyaan.\n"
			"Daftar file (ID, Nama, Deskripsi):\n"
			f"{catalog_text}\n\n"
			f"Pertanyaan pengguna: \"{question.strip()}\"\n\n"
			"Instruksi: Balas HANYA dengan satu ID persis seperti di daftar di atas.\n"
			"Jika tidak ada yang relevan, balas dengan NONE. Jangan tambahkan teks lain."
		)

		try:
			response = self.client.chat.completions.create(
				model=self.model,
				messages=[
					{"role": "system", "content": "Anda adalah sistem seleksi yang presisi; selalu balas HANYA ID atau NONE."},
					{"role": "user", "content": user_prompt},
				],
				max_tokens=self.max_token,
				temperature=0.0,
			)

			choice = response.choices[0] if response.choices else None
			message = getattr(choice, "message", None)
			content = getattr(message, "content", None) if message else None
			answer = (content or "").strip() if isinstance(content, str) else ""
			if not answer:
				return None

			# Normalisasi jawaban dan ambil ID yang valid
			ans = answer.split()[-1] if " " in answer else answer
			ans = ans.strip().strip("`\"' ")
			selected_id: Optional[str] = None
			if ans in allowed_ids:
				selected_id = ans
			else:
				# fallback: cari id yang muncul dalam jawaban
				for _id in allowed_ids:
					if _id and _id in answer:
						selected_id = _id
						break

			if not selected_id or selected_id.upper() == "NONE":
				return None

			# Kembalikan dokumen yang cocok
			for d in docs:
				if d.get('id') == selected_id:
					return d
			return None

		except (AuthenticationError, RateLimitError, APIError) as exc:
			logger.error(f"PandasService selection OpenAI error: {exc}")
			return None
		except Exception as exc:  # pragma: no cover - best effort logging
			logger.error(f"PandasService selection unexpected error: {exc}")
			return None

	def answer_with_pandas_agent(self, question: str, limit: int = 200) -> List[Tuple[Document, float]]:
		"""Jalankan Pandas DataFrame Agent pada file terpilih untuk menjawab pertanyaan.

		Output disamakan dengan vectorstore_service.retrieve_attachments_with_score():
		List[Tuple[Document, float]] dimana Document.page_content berisi jawaban agent,
		dan metadata menyertakan informasi dokumen (document_id, document_source, document_name, stored_filename).
		Skor dikembalikan 1.0.
		"""
		try:
			if not question or not isinstance(question, str):
				return []

			selected = self.select_file_by_question(question, limit=limit)
			if not selected:
				return []

			# Resolve file path mirip api/storage.py
			storage_path = selected.get('storage_path')
			if not storage_path:
				logger.warning("PandasService: selected file missing storage_path")
				return []
			if os.path.isabs(storage_path):
				resolved_path = storage_path
			else:
				resolved_path = os.path.join(os.getcwd(), storage_path)

			if not os.path.exists(resolved_path):
				logger.warning(f"PandasService: file not found at {resolved_path}")
				return []

			# Import on-demand untuk menghindari dependency error saat modul tidak dipakai
			try:
				import pandas as pd  # type: ignore
				from langchain_experimental.agents import create_pandas_dataframe_agent  # type: ignore
			except Exception as imp_exc:
				logger.error(f"PandasService: import error for pandas/agent stack: {imp_exc}")
				return []

			# Baca Excel menjadi DataFrame
			try:
				df = pd.read_excel(resolved_path)
			except Exception as read_exc:
				logger.error(f"PandasService: failed to read excel at {resolved_path}: {read_exc}")
				return []

			# Siapkan OpenAI API key untuk LangChain jika belum tersedia
			try:
				api_key = get_openai_api_key()
				if api_key and not os.getenv("OPENAI_API_KEY"):
					os.environ["OPENAI_API_KEY"] = api_key
			except Exception:
				pass

			# Buat LLM & Agent
			agent_model = os.getenv("OPENAI_PANDAS_AGENT_MODEL", os.getenv("PANDAS_AGENT_MODEL", "gpt-4o-mini"))
			try:
				llm = init_chat_openai({"model": agent_model, "temperature": 0})
			except Exception as llm_exc:
				logger.error(f"PandasService: failed to init ChatOpenAI: {llm_exc}")
				return []
            
			try:
				agent = create_pandas_dataframe_agent(
					llm,
					df,
					verbose=True,
					allow_dangerous_code=True,
    				max_iterations=10,
                    agent_type="openai-tools",
                    prefix=(
						"You are a data analyst. Analyze a data frame and provide clear, concise, and complete answer that is untruncated. \n"
						"Provide the final answer in a clear and structured format. Remember clear and structured format not users request."
					)
				)
			except Exception as ag_exc:
				logger.error(f"PandasService: failed to create pandas agent: {ag_exc}")
				return []

			try:
				invoke_result = agent.invoke({"input": question})
				if isinstance(invoke_result, dict):
					answer = invoke_result.get("output") or invoke_result.get("answer") or ""
				else:
					answer = str(invoke_result)
			except Exception as run_exc:
				logger.error(f"PandasService: agent invoke failed: {run_exc}")
				return []

			meta: Dict[str, Any] = {
				"document_id": selected.get('id'),
				"document_source": selected.get('storage_path'),
				"document_name": selected.get('original_filename'),
				"stored_filename": selected.get('stored_filename'),
				"mime_type": selected.get('mime_type'),
				"agent": "pandas-dataframe",
			}
			doc = Document(page_content=str(answer or "").strip(), metadata=meta)
			return [(doc, 1.0)]

		except Exception as e:
			logger.error(f"PandasService.answer_with_pandas_agent error: {e}", exc_info=True)
			return []

	def answer_from_path_if_relevant(self, path: str, filename: Optional[str], question: str, limit: int = 200) -> Optional[List[Tuple[Document, float]]]:
		"""Generate summary from a given Excel path, judge relevance to the question, then answer via Pandas agent.

		Flow:
		1) Use FileExcelService to generate a short summary from Excel file.
		2) Ask OpenAI (same selector client) whether the summary is relevant to the question.
		   The model must reply ONLY with "RELEVAN" or "NONE".
		3) If NOT relevant -> return None. If relevant -> run Pandas agent like answer_with_pandas_agent.

		Returns list of (Document, score) on success, or None if not relevant or on failure.
		"""
		try:
			if not path or not str(path).strip() or not question or not isinstance(question, str):
				return None

			resolved_path = str(path).strip()
			if not os.path.isabs(resolved_path):
				resolved_path = os.path.join(os.getcwd(), resolved_path)

			if not os.path.exists(resolved_path):
				logger.warning(f"PandasService: file not found at {resolved_path}")
				return None

			# 1) Generate summary using FileExcelService (mirrors file_excel_service.py)
			try:
				fes = FileExcelService()
				summary = fes.generate_summary(resolved_path, filename=filename or os.path.basename(resolved_path), question=question)
			except Exception as summ_exc:
				logger.error(f"PandasService: failed to generate summary from path: {summ_exc}")
				summary = None

			if not summary or not str(summary).strip():
				return None

			# 2) Ask selector model to judge relevance based on summary and question
			if not self.enabled or not self.client:
				return None

			judge_prompt = (
				"Kamu adalah sistem seleksi relevansi.\n"
				"Ringkasan file: \n" + str(summary).strip() + "\n\n"
				f"Pertanyaan pengguna: \"{question.strip()}\"\n\n"
				"Instruksi: Balas HANYA \"RELEVAN\" jika ringkasan cocok dengan pertanyaan, selain itu balas \"NONE\"."
			)

			try:
				response = self.client.chat.completions.create(
					model=self.model,
					messages=[
						{"role": "system", "content": "Balas hanya dengan RELEVAN atau NONE."},
						{"role": "user", "content": judge_prompt},
					],
					max_tokens=16,
					temperature=0.0,
				)
				choice = response.choices[0] if response.choices else None
				message = getattr(choice, "message", None)
				content = getattr(message, "content", None) if message else None
				verdict = (content or "").strip().upper()
			except (AuthenticationError, RateLimitError, APIError) as exc:
				logger.error(f"PandasService relevance OpenAI error: {exc}")
				return None
			except Exception as exc:
				logger.error(f"PandasService relevance judge failed: {exc}")
				return None

			if verdict != "RELEVAN":
				return None

			# 3) Run Pandas agent on the provided path (similar to answer_with_pandas_agent but using given path)
			try:
				import pandas as pd  # type: ignore
				from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent  # type: ignore
			except Exception as imp_exc:
				logger.error(f"PandasService: import error for pandas/agent stack: {imp_exc}")
				return None

			try:
				df = pd.read_excel(resolved_path)
			except Exception as read_exc:
				logger.error(f"PandasService: failed to read excel at {resolved_path}: {read_exc}")
				return None

			try:
				api_key = get_openai_api_key()
				if api_key and not os.getenv("OPENAI_API_KEY"):
					os.environ["OPENAI_API_KEY"] = api_key
			except Exception:
				pass

			agent_model = os.getenv("OPENAI_PANDAS_AGENT_MODEL", os.getenv("PANDAS_AGENT_MODEL", "gpt-4o-mini"))
			try:
				llm = init_chat_openai({"model": agent_model, "temperature": 0})
			except Exception as llm_exc:
				logger.error(f"PandasService: failed to init ChatOpenAI: {llm_exc}")
				return None

			try:
				agent = create_pandas_dataframe_agent(
					llm,
					df,
					verbose=True,
					allow_dangerous_code=True,
					max_iterations=10,
                    agent_type="openai-tools",
                    prefix=(
						"You are a data analyst. Analyze a data frame and provide clear, concise, and complete answer that is untruncated. \n"
						"Provide the final answer in a clear and structured format. Remember clear and structured format not users request."
					)
				)
			except Exception as ag_exc:
				logger.error(f"PandasService: failed to create pandas agent: {ag_exc}")
				return None

			try:
				invoke_result = agent.invoke({"input": question})
				if isinstance(invoke_result, dict):
					answer = invoke_result.get("output") or invoke_result.get("answer") or ""
				else:
					answer = str(invoke_result)
			except Exception as run_exc:
				logger.error(f"PandasService: agent invoke failed: {run_exc}")
				return None

			return answer

		except Exception as e:
			logger.error(f"PandasService.answer_from_path_if_relevant error: {e}", exc_info=True)
			return None
    
    
