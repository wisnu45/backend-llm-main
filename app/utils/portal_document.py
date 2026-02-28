"""
    Helper modul untuk mengecek aksesibilitas dokumen berdasarkan user.  
    Modul ini berisi fungsi untuk memastikan apakah seorang user memiliki izin terhadap 
    sebuah dokumen portal sesuai aturan yang berlaku.
"""

import logging
from typing import Union, Optional, Any
from flask import request, g, has_request_context
import jwt
import os
import requests

from app.utils.database import safe_db_query
from app.utils.portal import create_user_token

def sync_user_portal_document(user_id, username):
    """
    Fungsi untuk memastikan apakah seorang user memiliki izin terhadap 
    dokumen portal sesuai aturan yang berlaku.

    Args:
        user_id (uuid): id user
        username (string): username portal account
    """
    # Generate Token dan Ambil List Dokumen
    try:
        token = create_user_token(username)
        url = f"https://portal.combiphar.com/Documents/GetDocumentList?q={token}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = json.loads(response.text)
    except Exception as e:
        logging.error(f"Failed to fetch document list: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Failed to fetch document list: {e}")
        return False
    
    list_file = []
    if isinstance(data, dict):
        list_file = data.get('data') or data.get('items') or []
    elif isinstance(data, list):
        list_file = data
    else:
        list_file = []

    if not isinstance(list_file, list):
        list_file = []

    # Hapus dahulu semua akses dokumen agar always up-to-date dokumen
    delete_query = "DELETE FROM users_documents WHERE users_id = %s"
    safe_db_query(delete_query, [user_id])

    # Ambil semua dokumen yang terpublish
    documents = []
    for file in list_file:
        is_published = file.get('IsPublished', False)
        if not is_published :
            continue

        orig_filename = file.get('FileName')
        documents.append(orig_filename)

    # Insert Batch document yang dimiliki user ke users_documents
    if(len(documents) > 0) : 
        placeholders = ",".join(["%s"] * len(documents))

        query = f"""
            SELECT id
            FROM documents
            WHERE metadata::json->>'FileName' IN ({placeholders})
            AND source_type = 'portal'
        """
        results, _ = safe_db_query(query, tuple(documents))
        
        insert_data = []
        for u in results:
            insert_data.append((user_id, u[0]))

        if insert_data : 
            query = "INSERT INTO users_documents (users_id, documents_id) VALUES %s"
            safe_db_query(query, insert_data, many=True)

    return True
