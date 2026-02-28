"""Utilities for ingesting Combiphar-affiliated website content into the knowledge base."""
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin, urlsplit

import requests
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.agent.search_service import SearchService
from app.utils.database import safe_db_query
from app.utils.document import data_path
from app.utils.pgvectorstore import get_vectorstore
from app.utils.setting import get_setting_value_by_name
from app.utils.time_provider import get_current_datetime

logger = logging.getLogger(__name__)

_COMBIPHAR_DOMAINS = {"combiphar.com", "www.combiphar.com"}
_DEFAULT_WEBSITES = ["https://www.combiphar.com/id"]
_MAX_PAGES_PER_SITE = 200


def _slugify(value: str, fallback: str = "page") -> str:
    """Convert arbitrary text into a filesystem-friendly slug."""
    if not isinstance(value, str):
        value = str(value or "")
    value = value.lower().strip()
    if not value:
        return fallback

    slug = "".join(ch if ch.isalnum() else "_" for ch in value)
    slug = "_".join(part for part in slug.split("_") if part)
    return slug or fallback


def _normalize_website_list(raw_setting: Any) -> List[str]:
    """Return a clean list of website URLs from settings or defaults."""
    if isinstance(raw_setting, str):
        websites = [w.strip() for w in raw_setting.split(',') if w.strip()]
    elif isinstance(raw_setting, Sequence):
        websites = [str(w).strip() for w in raw_setting if str(w).strip()]
    else:
        websites = []

    return websites or list(_DEFAULT_WEBSITES)


def _collect_combiphar_pages(search_service: SearchService, base_url: str, limit: int) -> List[Dict[str, Any]]:
    """Collect pages from the Combiphar corporate site via official API."""
    results: List[Dict[str, Any]] = []
    seen_urls = set()

    parsed = urlsplit(base_url)
    scheme = parsed.scheme or 'https'
    netloc = parsed.netloc or 'www.combiphar.com'
    base_prefix = f"{scheme}://{netloc.strip('/')}/"

    try:
        response = requests.get(
            "https://www.combiphar.com/back/api/v1/pages",
            timeout=10
        )
        response.raise_for_status()
        payload = response.json()
        pages = ((payload.get("data") or {}).get("pages") or {}).get("data")
    except Exception as exc:  # pragma: no cover - network failure is logged
        logger.error(f"❌ Failed to fetch Combiphar page list: {exc}")
        return results

    if not isinstance(pages, list):
        return results

    for page in pages:
        if len(results) >= limit:
            break
        translations = page.get('translated_locales') or {}
        for locale, translation in translations.items():
            if len(results) >= limit:
                break
            if not isinstance(translation, dict):
                continue

            slug = translation.get('slug')
            title = translation.get('title') or page.get('title') or 'Combiphar Page'
            locale_code = (locale or '').lower().strip()

            if not slug:
                continue

            path = f"{locale_code}/{slug}" if locale_code else slug
            url = urljoin(base_prefix, path.strip('/'))

            if url in seen_urls:
                continue

            content = search_service._fetch_combiphar_content(url)
            if not content:
                continue

            seen_urls.add(url)
            results.append({
                "url": url,
                "title": title,
                "locale": locale_code or None,
                "source": netloc,
                "content": content
            })

    return results


def _collect_generic_site_pages(search_service: SearchService, base_url: str, limit: int) -> List[Dict[str, Any]]:
    """Collect pages from affiliated microsites using sitemap discovery."""
    results: List[Dict[str, Any]] = []
    seen_urls = set()
    parsed = urlsplit(base_url)
    scheme = parsed.scheme or 'https'
    netloc = parsed.netloc
    if not netloc:
        return results

    base_root = f"{scheme}://{netloc.strip('/')}/"

    try:
        candidates = search_service._discover_site_pages(base_root, [], limit=limit * 2)
    except Exception as exc:  # pragma: no cover - discovery failures logged
        logger.warning(f"⚠️ Failed to discover pages for {base_url}: {exc}")
        candidates = []

    if not candidates:
        candidates = [base_root.rstrip('/')]

    for url in candidates:
        if len(results) >= limit:
            break
        if not isinstance(url, str):
            continue
        normalized = url.strip()
        if not normalized or normalized in seen_urls:
            continue

        content = search_service._fetch_generic_site_content(normalized)
        if not content:
            continue

        seen_urls.add(normalized)
        results.append({
            "url": normalized,
            "title": normalized,
            "locale": None,
            "source": netloc,
            "content": content
        })

    return results


def _delete_existing_document(vectorstore, document_id: uuid.UUID, stored_filename: str, storage_path: Optional[str]) -> None:
    """Remove existing website document artifacts from vectors, DB, and filesystem."""
    try:
        if stored_filename:
            vectorstore.delete_by_metadata({"stored_filename": stored_filename})
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(f"⚠️ Failed to delete vectors for {stored_filename}: {exc}")

    try:
        safe_db_query("DELETE FROM documents WHERE id = %s", (document_id,))
    except Exception as exc:
        logger.warning(f"⚠️ Failed to delete document record {document_id}: {exc}")

    try:
        path_candidates = []
        if storage_path:
            path_candidates.append(os.path.join('.', storage_path))
        if stored_filename:
            path_candidates.append(data_path('documents', 'website', stored_filename))

        for candidate in path_candidates:
            if candidate and os.path.exists(candidate):
                os.remove(candidate)
    except Exception as exc:
        logger.warning(f"⚠️ Failed to remove file for {stored_filename}: {exc}")


def _split_chunks(text: str, splitter: RecursiveCharacterTextSplitter) -> List[str]:
    """Split text into cleaned chunks for embedding."""
    chunks = splitter.split_text(text or "")
    return [chunk.strip() for chunk in chunks if chunk and chunk.strip()]


def pull_combiphar_websites(
    max_pages_per_site: int = _MAX_PAGES_PER_SITE,
    sync_logger: Any = None,
) -> Dict[str, Any]:
    """Ingest Combiphar websites into the shared document and vector store."""
    summary = {
        "processed": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": []
    }
    ingested_urls: List[str] = []

    vectorstore = get_vectorstore()
    if not vectorstore:
        logger.error("❌ Vector store unavailable, aborting website ingestion.")
        return {"message": "Vector store unavailable", "summary": summary, "ingested_urls": ingested_urls}

    search_service = SearchService(llm=None, prompt_service=None)

    websites_setting = get_setting_value_by_name("combiphar_websites")
    websites = _normalize_website_list(websites_setting)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    storage_folder = data_path('documents', 'website')
    os.makedirs(storage_folder, exist_ok=True)

    logger.info(f"🌐 Starting website ingestion for {len(websites)} site(s)")

    for site in websites:
        if not isinstance(site, str):
            continue
        site = site.strip()
        if not site:
            continue

        try:
            parsed = urlsplit(site)
        except Exception:
            logger.warning(f"⚠️ Skipping invalid URL: {site}")
            continue

        host = (parsed.netloc or '').lower()
        pages: List[Dict[str, Any]]
        if host in _COMBIPHAR_DOMAINS:
            pages = _collect_combiphar_pages(search_service, site, max_pages_per_site)
        else:
            pages = _collect_generic_site_pages(search_service, site, max_pages_per_site)

        logger.info(f"📄 Discovered {len(pages)} candidate pages for {site}")

        for page in pages:
            try:
                url = page.get("url")
                content = (page.get("content") or "").strip()
                if not url or not content:
                    summary["skipped"] += 1
                    continue

                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                now = get_current_datetime().isoformat()

                metadata_payload = {
                    "url": url,
                    "title": page.get("title"),
                    "locale": page.get("locale"),
                    "source": page.get("source"),
                    "content_hash": content_hash,
                    "last_fetched_at": now
                }

                existing_query = """
                    SELECT id, stored_filename, metadata, storage_path
                    FROM documents
                    WHERE source_type = 'website' AND metadata::json->>'url' = %s
                """
                existing_results, _ = safe_db_query(existing_query, (url,))

                document_db_id = None
                stored_filename = None
                storage_path = None
                was_update = False

                if isinstance(existing_results, list) and existing_results:
                    existing_row = existing_results[0]
                    document_db_id = existing_row[0]
                    stored_filename = existing_row[1]
                    existing_metadata = existing_row[2] if len(existing_row) > 2 else {}
                    storage_path = existing_row[3] if len(existing_row) > 3 else None

                    previous_hash = ""
                    if isinstance(existing_metadata, dict):
                        previous_hash = existing_metadata.get("content_hash", "")

                    file_candidates = []
                    if storage_path:
                        if os.path.isabs(storage_path):
                            file_candidates.append(storage_path)
                        else:
                            file_candidates.append(os.path.join('.', storage_path))
                    if stored_filename:
                        file_candidates.append(os.path.join(storage_folder, stored_filename))

                    file_exists = any(os.path.isfile(path) for path in file_candidates)

                    vectors_exist = False
                    if document_db_id:
                        try:
                            vector_count_rows, _ = safe_db_query(
                                "SELECT COUNT(*) FROM documents_vectors WHERE document_id = %s",
                                (document_db_id,),
                            )
                            if isinstance(vector_count_rows, list) and vector_count_rows:
                                vectors_exist = (vector_count_rows[0][0] or 0) > 0
                        except Exception as vector_err:
                            logger.warning(
                                f"Failed to verify embeddings for website document {document_db_id}: {vector_err}"
                            )

                    artifacts_intact = file_exists and vectors_exist

                    if previous_hash == content_hash and artifacts_intact:
                        summary["skipped"] += 1
                        continue

                    was_update = True
                    _delete_existing_document(vectorstore, document_db_id, stored_filename, storage_path)
                    document_db_id = None
                    stored_filename = None
                    storage_path = None

                slug_base = _slugify(urlsplit(url).path or page.get("title") or host)
                locale_suffix = page.get("locale")
                if locale_suffix:
                    slug_base = f"{slug_base}_{_slugify(locale_suffix)}"
                original_filename = f"{slug_base[:120]}.txt"

                temp_path = os.path.join(storage_folder, original_filename)
                with open(temp_path, 'w', encoding='utf-8') as handle:
                    handle.write(content)
                size_bytes = os.path.getsize(temp_path)

                stored_filename = f"{uuid.uuid4()}.txt"
                new_path = os.path.join(storage_folder, stored_filename)
                if temp_path != new_path:
                    os.replace(temp_path, new_path)
                storage_path = os.path.relpath(new_path, '.')

                insert_query = """
                    INSERT INTO documents
                    (source_type, original_filename, stored_filename, mime_type, size_bytes, metadata, storage_path, uploaded_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                result, _ = safe_db_query(
                    insert_query,
                    (
                        'website',
                        original_filename,
                        stored_filename,
                        'text/plain',
                        size_bytes,
                        json.dumps(metadata_payload),
                        storage_path,
                        None
                    )
                )

                if isinstance(result, list) and result:
                    document_db_id = result[0][0]
                elif isinstance(result, int) and result > 0 and stored_filename:
                    confirm_query = "SELECT id FROM documents WHERE stored_filename = %s ORDER BY created_at DESC LIMIT 1"
                    confirm_result, _ = safe_db_query(confirm_query, (stored_filename,))
                    if isinstance(confirm_result, list) and confirm_result:
                        document_db_id = confirm_result[0][0]

                if not document_db_id:
                    logger.error(f"❌ Failed to persist document record for {url}")
                    summary["errors"].append(f"Failed to insert document for {url}")
                    if sync_logger:
                        sync_logger.log_document_result(
                            document_title=page.get("title") or url,
                            document_filename=original_filename,
                            document_id=None,
                            status='failed',
                            error_message=f"Failed to insert document for {url}",
                            file_size=size_bytes,
                            metadata={
                                'source_type': 'website',
                                'url': url,
                                'source': host,
                                'stage': 'insert_document'
                            },
                            item_type='website',
                            item_url=url,
                            item_source=host,
                        )
                    continue

                chunks = _split_chunks(content, splitter)
                if not chunks:
                    summary["skipped"] += 1
                    continue

                docs: List[Document] = []
                chunk_total = len(chunks)
                display_name = original_filename or page.get("title") or url
                prefix = f"{display_name}\n\n" if display_name else ""
                for index, chunk in enumerate(chunks):
                    metadata = {
                        "document_id": str(document_db_id),
                        "chat_id": None,
                        "source_type": "website",
                        "uploaded_by": None,
                        "original_filename": original_filename,
                        "stored_filename": stored_filename,
                        "storage_path": storage_path,
                        "mime_type": 'text/plain',
                        "chunk_index": index,
                        "chunk_total": chunk_total,
                        "created_at": now,
                        "url": url,
                        "title": page.get("title"),
                        "locale": page.get("locale"),
                        "source": page.get("source")
                    }
                    content = f"{prefix}{chunk}" if prefix else chunk
                    docs.append(Document(page_content=content, metadata=metadata))

                try:
                    vectorstore.add_documents(docs)
                except Exception as exc:
                    logger.error(f"❌ Failed to add website chunks to vector store for {url}: {exc}")
                    summary["errors"].append(f"Vectorstore error for {url}: {exc}")
                    if sync_logger:
                        sync_logger.log_document_result(
                            document_title=page.get("title") or url,
                            document_filename=original_filename,
                            document_id=str(document_db_id) if document_db_id else None,
                            status='failed',
                            error_message=f"Vectorstore error for {url}: {exc}",
                            file_size=size_bytes,
                            metadata={
                                'source_type': 'website',
                                'url': url,
                                'source': host,
                                'stage': 'vectorstore_add'
                            },
                            item_type='website',
                            item_url=url,
                            item_source=host,
                        )
                    continue

                summary["processed"] += 1
                if was_update:
                    summary["updated"] += 1
                else:
                    summary["created"] += 1
                ingested_urls.append(url)

                if sync_logger:
                    sync_logger.log_document_result(
                        document_title=page.get("title") or url,
                        document_filename=original_filename,
                        document_id=str(document_db_id) if document_db_id else None,
                        status='success',
                        error_message=None,
                        file_size=size_bytes,
                        metadata={
                            'source_type': 'website',
                            'url': url,
                            'source': host,
                            'was_update': was_update,
                            'chunks_count': len(docs),
                        },
                        item_type='website',
                        item_url=url,
                        item_source=host,
                    )

            except Exception as exc:  # pragma: no cover - ingestion resilience
                logger.error(f"❌ Error processing page {page.get('url')}: {exc}")
                summary["errors"].append(f"{page.get('url')}: {exc}")

                url = page.get('url') if isinstance(page, dict) else None
                if sync_logger and url:
                    sync_logger.log_document_result(
                        document_title=page.get("title") or url,
                        document_filename=None,
                        document_id=None,
                        status='failed',
                        error_message=str(exc),
                        file_size=None,
                        metadata={
                            'source_type': 'website',
                            'url': url,
                            'source': host,
                            'stage': 'exception'
                        },
                        item_type='website',
                        item_url=url,
                        item_source=host,
                    )

    summary["skipped"] = max(summary["skipped"], 0)

    return {
        "message": "Website ingestion completed",
        "summary": summary,
        "ingested_urls": ingested_urls
    }
