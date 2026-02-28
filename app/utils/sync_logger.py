"""
Utilities for logging document synchronization operations and results.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.utils.database import safe_db_query


class SyncLogger:
    """Utility class for logging document synchronization operations."""
    
    def __init__(self):
        self.sync_log_id: Optional[str] = None
        self.document_results: List[Dict[str, Any]] = []
        
    def start_sync_log(
        self,
        sync_type: str = 'portal',
        trigger_source: Optional[str] = None,
        triggered_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new sync log entry.
        
        Args:
            sync_type: Type of sync (portal, website, manual)
            trigger_source: Source of trigger (api, cron, startup)
            triggered_by: User or system that triggered the sync
            metadata: Additional metadata
            
        Returns:
            Sync log ID
        """
        try:
            insert_query = """
                INSERT INTO sync_logs (
                    sync_type, status, trigger_source, triggered_by, 
                    started_at, metadata
                )
                VALUES (%s, %s, %s, %s, NOW(), %s)
                RETURNING id
            """
            
            metadata_json = json.dumps(metadata or {})
            
            result, _ = safe_db_query(insert_query, (
                sync_type,
                'running',
                trigger_source,
                triggered_by,
                metadata_json
            ))
            
            if result and isinstance(result, list) and len(result) > 0:
                self.sync_log_id = str(result[0][0])
                logging.info(f"Started sync log: {self.sync_log_id}")
                return self.sync_log_id
            else:
                logging.error("Failed to create sync log entry")
                return ""
                
        except Exception as e:
            logging.error(f"Error starting sync log: {e}")
            return ""
    
    def log_document_result(
        self,
        document_title: Optional[str] = None,
        document_filename: Optional[str] = None,
        document_id: Optional[str] = None,
        status: str = 'failed',
        error_message: Optional[str] = None,
        file_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        item_type: str = 'document',
        item_url: Optional[str] = None,
        item_source: Optional[str] = None,
    ) -> bool:
        """
        Log the result of processing a single document.
        
        Args:
            document_title: Title of the document
            document_filename: Original filename
            document_id: Document ID from portal or system
            status: Processing status (success, failed)
            error_message: Error message if failed
            file_size: File size in bytes
            metadata: Additional document metadata
            
        Returns:
            True if logged successfully, False otherwise
        """
        if not self.sync_log_id:
            logging.warning("Cannot log document result: no active sync log")
            return False
            
        try:
            insert_query = """
                INSERT INTO sync_log_details (
                    sync_log_id,
                    item_type,
                    item_url,
                    item_source,
                    document_title,
                    document_filename,
                    document_id,
                    status,
                    error_message,
                    file_size,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            metadata_json = json.dumps(metadata or {})
            
            try:
                safe_db_query(insert_query, (
                    self.sync_log_id,
                    item_type,
                    item_url,
                    item_source,
                    document_title,
                    document_filename,
                    document_id,
                    status,
                    error_message,
                    file_size,
                    metadata_json
                ))
            except Exception:
                # Backwards compatibility for databases that haven't applied
                # the website logging migration yet.
                fallback_query = """
                    INSERT INTO sync_log_details (
                        sync_log_id, document_title, document_filename,
                        document_id, status, error_message, file_size, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                safe_db_query(fallback_query, (
                    self.sync_log_id,
                    document_title,
                    document_filename,
                    document_id,
                    status,
                    error_message,
                    file_size,
                    metadata_json
                ))
            
            # Track results for summary
            self.document_results.append({
                'status': status,
                'item_type': item_type,
                'item_url': item_url,
                'document_title': document_title,
                'document_filename': document_filename,
                'error_message': error_message
            })
            
            return True
            
        except Exception as e:
            logging.error(f"Error logging document result: {e}")
            return False
    
    def finish_sync_log(
        self,
        status: str = 'success',
        error_message: Optional[str] = None,
        runtime_seconds: Optional[float] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Finish the sync log with final status and statistics.
        
        Args:
            status: Final status (success, partial_success, failed)
            error_message: Global error message if applicable
            runtime_seconds: Total runtime in seconds
            additional_metadata: Additional metadata to merge
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not self.sync_log_id:
            logging.warning("Cannot finish sync log: no active sync log")
            return False
            
        try:
            normalized_status = (status or '').strip().lower()
            if normalized_status == 'succeeded':
                normalized_status = 'success'

            # Calculate statistics per item type
            items = self.document_results or []
            document_items = [r for r in items if (r.get('item_type') or 'document') == 'document']
            website_items = [r for r in items if (r.get('item_type') or 'document') == 'website']

            total_documents = len(document_items)
            successful_documents = len([r for r in document_items if r.get('status') == 'success'])
            failed_documents = len([r for r in document_items if r.get('status') == 'failed'])

            total_website_documents = len(website_items)
            successful_website_documents = len([r for r in website_items if r.get('status') == 'success'])
            failed_website_documents = len([r for r in website_items if r.get('status') == 'failed'])

            failed_total = failed_documents + failed_website_documents
            successful_total = successful_documents + successful_website_documents
            
            # Determine final status if not explicitly provided
            if normalized_status == 'success' and failed_total > 0:
                if successful_total > 0:
                    normalized_status = 'partial_success'
                else:
                    normalized_status = 'failed'
            
            # Prepare metadata
            final_metadata = {
                'document_summary': {
                    'total': total_documents,
                    'successful': successful_documents,
                    'failed': failed_documents
                },
                'website_summary': {
                    'total': total_website_documents,
                    'successful': successful_website_documents,
                    'failed': failed_website_documents,
                },
                'overall_summary': {
                    'total': total_documents + total_website_documents,
                    'successful': successful_total,
                    'failed': failed_total,
                },
                'failed_documents': [
                    {
                        'title': r['document_title'],
                        'filename': r['document_filename'],
                        'url': r.get('item_url'),
                        'error': r['error_message']
                    }
                    for r in document_items if r.get('status') == 'failed'
                ],
                'failed_website_items': [
                    {
                        'title': r.get('document_title') or r.get('item_url'),
                        'url': r.get('item_url'),
                        'error': r.get('error_message')
                    }
                    for r in website_items if r.get('status') == 'failed'
                ]
            }
            
            if additional_metadata:
                final_metadata.update(additional_metadata)
            
            update_query = """
                UPDATE sync_logs
                SET status = %s,
                    total_documents = %s,
                    successful_documents = %s,
                    failed_documents = %s,
                    total_website_documents = %s,
                    successful_website_documents = %s,
                    failed_website_documents = %s,
                    finished_at = NOW(),
                    runtime_seconds = %s,
                    error_message = %s,
                    metadata = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            
            metadata_json = json.dumps(final_metadata)
            
            try:
                safe_db_query(update_query, (
                    normalized_status,
                    total_documents,
                    successful_documents,
                    failed_documents,
                    total_website_documents,
                    successful_website_documents,
                    failed_website_documents,
                    runtime_seconds,
                    error_message,
                    metadata_json,
                    self.sync_log_id
                ))
            except Exception:
                # Backwards compatibility when website aggregate columns are missing.
                fallback_update = """
                    UPDATE sync_logs
                    SET status = %s,
                        total_documents = %s,
                        successful_documents = %s,
                        failed_documents = %s,
                        finished_at = NOW(),
                        runtime_seconds = %s,
                        error_message = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """
                safe_db_query(fallback_update, (
                    normalized_status,
                    total_documents,
                    successful_documents,
                    failed_documents,
                    runtime_seconds,
                    error_message,
                    metadata_json,
                    self.sync_log_id
                ))
            
            logging.info(
                f"Finished sync log {self.sync_log_id}: {normalized_status} "
                f"(doc={successful_documents}/{total_documents}, web={successful_website_documents}/{total_website_documents})"
            )
            
            # Reset for next use
            self.sync_log_id = None
            self.document_results = []
            
            return True
            
        except Exception as e:
            logging.error(f"Error finishing sync log: {e}")
            return False

    @staticmethod
    def _build_sync_log_filters(
        sync_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_website_columns: bool = True,
    ) -> Tuple[str, List[Any]]:
        where_conditions = []
        params: List[Any] = []

        if sync_type:
            where_conditions.append('sl.sync_type = %s')
            params.append(sync_type)

        if status:
            normalized_status = str(status).strip().lower()
            if normalized_status == 'success':
                where_conditions.append("sl.status IN ('success', 'succeeded')")
            elif normalized_status == 'succeeded':
                where_conditions.append("sl.status IN ('success', 'succeeded')")
            else:
                where_conditions.append('sl.status = %s')
                params.append(normalized_status)

        if start_date:
            where_conditions.append('sl.started_at >= %s')
            params.append(start_date)

        if end_date:
            where_conditions.append('sl.started_at <= %s')
            params.append(end_date)

        if search:
            search_term = f"%{search}%"

            detail_search_conditions = [
                "sld.document_id ILIKE %s",
                "sld.document_title ILIKE %s",
                "sld.document_filename ILIKE %s",
                "sld.error_message ILIKE %s",
            ]
            detail_param_count = 4
            if include_website_columns:
                detail_search_conditions.extend([
                    "sld.item_url ILIKE %s",
                    "sld.item_source ILIKE %s",
                ])
                detail_param_count += 2

            where_conditions.append(
                f"""
                (
                    sl.error_message ILIKE %s
                    OR sl.triggered_by ILIKE %s
                    OR CAST(sl.id AS TEXT) ILIKE %s
                    OR EXISTS (
                        SELECT 1
                        FROM sync_log_details sld
                        WHERE sld.sync_log_id = sl.id
                          AND (
                              {' OR '.join(detail_search_conditions)}
                          )
                    )
                )
                """
            )
            params.extend([search_term] * (3 + detail_param_count))

        where_clause = ''
        if where_conditions:
            where_clause = ' WHERE ' + ' AND '.join(where_conditions)

        return where_clause, params

    @staticmethod
    def get_sync_logs(
        page: int = 1,
        page_size: int = 10,
        sync_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve sync logs with pagination and filtering.
        
        Args:
            page: Page number (1-based)
            page_size: Number of logs per page
            sync_type: Filter by sync type
            status: Filter by status
            search: Search term for logs and details
            start_date: Filter logs starting from this date
            end_date: Filter logs up to this date
            
        Returns:
            Tuple of (logs list, total count)
        """
        def _query_with_schema(include_website_fields: bool) -> Tuple[List[Dict[str, Any]], int]:
            where_clause, params = SyncLogger._build_sync_log_filters(
                sync_type=sync_type,
                status=status,
                search=search,
                start_date=start_date,
                end_date=end_date,
                include_website_columns=include_website_fields,
            )

            count_query = f'SELECT COUNT(*) FROM sync_logs sl{where_clause}'
            count_result, _ = safe_db_query(count_query, params)
            total = count_result[0][0] if count_result and isinstance(count_result, list) else 0

            if include_website_fields:
                query = f"""
                    SELECT sl.id, sl.sync_type, sl.status,
                           sl.total_documents, sl.successful_documents, sl.failed_documents,
                           sl.total_website_documents, sl.successful_website_documents, sl.failed_website_documents,
                           sl.trigger_source, sl.triggered_by, sl.started_at,
                           sl.finished_at, sl.runtime_seconds, sl.error_message, sl.metadata
                    FROM sync_logs sl{where_clause}
                    ORDER BY sl.started_at DESC
                    LIMIT %s OFFSET %s
                """
            else:
                query = f"""
                    SELECT sl.id, sl.sync_type, sl.status,
                           sl.total_documents, sl.successful_documents, sl.failed_documents,
                           sl.trigger_source, sl.triggered_by, sl.started_at,
                           sl.finished_at, sl.runtime_seconds, sl.error_message, sl.metadata
                    FROM sync_logs sl{where_clause}
                    ORDER BY sl.started_at DESC
                    LIMIT %s OFFSET %s
                """

            query_params = list(params)
            query_params.extend([page_size, (page - 1) * page_size])
            result, _ = safe_db_query(query, query_params)

            logs: List[Dict[str, Any]] = []
            if result and isinstance(result, list):
                for row in result:
                    if include_website_fields:
                        log_data = {
                            'id': str(row[0]),
                            'sync_type': row[1],
                            'status': row[2],
                            'total_documents': row[3],
                            'successful_documents': row[4],
                            'failed_documents': row[5],
                            'total_website_documents': row[6],
                            'successful_website_documents': row[7],
                            'failed_website_documents': row[8],
                            'trigger_source': row[9],
                            'triggered_by': row[10],
                            'started_at': row[11].isoformat() if row[11] else None,
                            'finished_at': row[12].isoformat() if row[12] else None,
                            'runtime_seconds': row[13],
                            'error_message': row[14],
                            'metadata': row[15],
                        }
                    else:
                        log_data = {
                            'id': str(row[0]),
                            'sync_type': row[1],
                            'status': row[2],
                            'total_documents': row[3],
                            'successful_documents': row[4],
                            'failed_documents': row[5],
                            'total_website_documents': 0,
                            'successful_website_documents': 0,
                            'failed_website_documents': 0,
                            'trigger_source': row[6],
                            'triggered_by': row[7],
                            'started_at': row[8].isoformat() if row[8] else None,
                            'finished_at': row[9].isoformat() if row[9] else None,
                            'runtime_seconds': row[10],
                            'error_message': row[11],
                            'metadata': row[12],
                        }
                    logs.append(log_data)

            return logs, total

        try:
            return _query_with_schema(True)
        except Exception as exc:
            logging.warning("Falling back to legacy sync_logs schema: %s", exc)
            try:
                return _query_with_schema(False)
            except Exception as final_exc:
                logging.error(f"Error retrieving sync logs: {final_exc}")
                return [], 0

    @staticmethod
    def delete_sync_logs(
        sync_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Delete sync logs with optional filtering.

        Returns:
            Number of deleted log entries.
        """
        try:
            where_clause, params = SyncLogger._build_sync_log_filters(
                sync_type=sync_type,
                status=status,
                search=search,
                start_date=start_date,
                end_date=end_date,
                include_website_columns=True,
            )
            query = f"DELETE FROM sync_logs sl{where_clause}"
            deleted_count, _ = safe_db_query(query, params)
            return deleted_count if isinstance(deleted_count, int) else 0
        except Exception as exc:
            logging.warning("Falling back to legacy delete filters for sync_logs: %s", exc)
            where_clause, params = SyncLogger._build_sync_log_filters(
                sync_type=sync_type,
                status=status,
                search=search,
                start_date=start_date,
                end_date=end_date,
                include_website_columns=False,
            )
            query = f"DELETE FROM sync_logs sl{where_clause}"
            deleted_count, _ = safe_db_query(query, params)
            return deleted_count if isinstance(deleted_count, int) else 0
    
    @staticmethod
    def get_sync_log_details(sync_log_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Get detailed information about a specific sync log.
        
        Args:
            sync_log_id: ID of the sync log
            
        Returns:
            Tuple of (sync log info, document details list)
        """
        try:
            # Get sync log info
            try:
                log_query = """
                    SELECT id, sync_type, status, total_documents, successful_documents,
                           failed_documents,
                           total_website_documents, successful_website_documents, failed_website_documents,
                           trigger_source, triggered_by, started_at,
                           finished_at, runtime_seconds, error_message, metadata
                    FROM sync_logs
                    WHERE id = %s
                """
                log_result, _ = safe_db_query(log_query, (sync_log_id,))
                include_website_fields = True
            except Exception as exc:
                logging.warning("Falling back to legacy sync_logs detail schema: %s", exc)
                log_query = """
                    SELECT id, sync_type, status, total_documents, successful_documents,
                           failed_documents, trigger_source, triggered_by, started_at,
                           finished_at, runtime_seconds, error_message, metadata
                    FROM sync_logs
                    WHERE id = %s
                """
                log_result, _ = safe_db_query(log_query, (sync_log_id,))
                include_website_fields = False
            
            sync_log = None
            if log_result and isinstance(log_result, list) and len(log_result) > 0:
                row = log_result[0]
                if include_website_fields:
                    sync_log = {
                        'id': str(row[0]),
                        'sync_type': row[1],
                        'status': row[2],
                        'total_documents': row[3],
                        'successful_documents': row[4],
                        'failed_documents': row[5],
                        'total_website_documents': row[6],
                        'successful_website_documents': row[7],
                        'failed_website_documents': row[8],
                        'trigger_source': row[9],
                        'triggered_by': row[10],
                        'started_at': row[11].isoformat() if row[11] else None,
                        'finished_at': row[12].isoformat() if row[12] else None,
                        'runtime_seconds': row[13],
                        'error_message': row[14],
                        'metadata': row[15],
                    }
                else:
                    sync_log = {
                        'id': str(row[0]),
                        'sync_type': row[1],
                        'status': row[2],
                        'total_documents': row[3],
                        'successful_documents': row[4],
                        'failed_documents': row[5],
                        'total_website_documents': 0,
                        'successful_website_documents': 0,
                        'failed_website_documents': 0,
                        'trigger_source': row[6],
                        'triggered_by': row[7],
                        'started_at': row[8].isoformat() if row[8] else None,
                        'finished_at': row[9].isoformat() if row[9] else None,
                        'runtime_seconds': row[10],
                        'error_message': row[11],
                        'metadata': row[12],
                    }
            
            # Get document details
            try:
                details_query = """
                    SELECT item_type, item_url, item_source,
                           document_title, document_filename, document_id, status,
                           error_message, file_size, metadata, processed_at
                    FROM sync_log_details
                    WHERE sync_log_id = %s
                    ORDER BY processed_at ASC
                """
                details_result, _ = safe_db_query(details_query, (sync_log_id,))
                include_item_fields = True
            except Exception as exc:
                logging.warning("Falling back to legacy sync_log_details schema: %s", exc)
                details_query = """
                    SELECT document_title, document_filename, document_id, status,
                           error_message, file_size, metadata, processed_at
                    FROM sync_log_details
                    WHERE sync_log_id = %s
                    ORDER BY processed_at ASC
                """
                details_result, _ = safe_db_query(details_query, (sync_log_id,))
                include_item_fields = False
            
            document_details = []
            if details_result and isinstance(details_result, list):
                for row in details_result:
                    if include_item_fields:
                        detail = {
                            'item_type': row[0],
                            'item_url': row[1],
                            'item_source': row[2],
                            'document_title': row[3],
                            'document_filename': row[4],
                            'document_id': row[5],
                            'status': row[6],
                            'error_message': row[7],
                            'file_size': row[8],
                            'metadata': row[9],
                            'processed_at': row[10].isoformat() if row[10] else None,
                        }
                    else:
                        detail = {
                            'item_type': 'document',
                            'item_url': None,
                            'item_source': None,
                            'document_title': row[0],
                            'document_filename': row[1],
                            'document_id': row[2],
                            'status': row[3],
                            'error_message': row[4],
                            'file_size': row[5],
                            'metadata': row[6],
                            'processed_at': row[7].isoformat() if row[7] else None,
                        }
                    document_details.append(detail)
            
            return sync_log, document_details
            
        except Exception as e:
            logging.error(f"Error retrieving sync log details: {e}")
            return None, []
