"""
Database utilities module
Combines database.py and db_utils.py functionality
"""

import os
import psycopg2
import logging
from psycopg2 import OperationalError, InterfaceError
from psycopg2.extras import execute_values


def getConnection(timeout: int = 1) -> psycopg2.extensions.connection:
    """
    Establish database connection with timeout
    """
    try:
        # Always operate in UTC at the DB session level.
        # This ensures TIMESTAMP WITH TIME ZONE values are interpreted consistently.
        pg_options = os.getenv("DB_PGOPTIONS", "-c timezone=UTC")
        # Ensure we consistently resolve unqualified table names to the schema
        # where our SQL scripts create tables.
        if "search_path" not in (pg_options or ""):
            pg_options = f"{pg_options} -c search_path=public"
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_DATABASE"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
            connect_timeout=timeout,  # set timeout koneksi (detik)
            options=pg_options,
        )
        return conn
    except (OperationalError, InterfaceError) as e:
        logging.error(f"Database connection failed: {e}")
        # Raise the original psycopg2 exception untuk ditangkap global handler
        raise
    except Exception as e:
        logging.error(f"Unexpected error during DB connection: {e}")
        # Convert ke ConnectionError untuk global handler
        raise ConnectionError(f"Database connection failed: {e}")


def safe_db_operation(operation_func, *args, **kwargs):
    """
    Wrapper function untuk operasi database yang aman
    Akan menangkap dan mengkonversi database errors
    """
    try:
        return operation_func(*args, **kwargs)
    except (OperationalError, InterfaceError) as e:
        logging.error(f"Database operation failed: {e}")
        # Re-raise untuk ditangkap global handler
        raise
    except Exception as e:
        logging.error(f"Unexpected error during database operation: {e}")
        # Convert ke ConnectionError
        raise ConnectionError(f"Database operation failed: {e}")


def with_db_connection(func):
    """
    Wrapping operasi database
    Akan menangkap dan melempar database errors ke global handler
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OperationalError, InterfaceError) as e:
            logging.error(f"Database error in {func.__name__}: {e}")
            # Re-raise untuk ditangkap global error handler
            raise
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")
            # Convert ke ConnectionError
            raise ConnectionError(f"Operation failed: {e}")
    return wrapper


def safe_db_query(query, params=None, many=False):
    """
    Execute database query dengan error handling
    """
    conn = None
    cursor = None
    try:
        conn = getConnection()
        cursor = conn.cursor()

        if many: 
            execute_values(cursor, query, params)
        else:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

        # If the query returns rows (e.g. SELECT, or INSERT/UPDATE ... RETURNING),
        # cursor.description will be populated.
        returns_rows = cursor.description is not None

        results = []
        columns = []
        if returns_rows:
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Decide whether to commit based on what PostgreSQL actually executed.
        # This also correctly handles CTEs (WITH ...) that perform DML.
        status_message = (cursor.statusmessage or "").strip()
        operation = status_message.split(None, 1)[0].upper() if status_message else ""
        if operation and operation != "SELECT":
            conn.commit()

        if returns_rows:
            return results, columns

        # For queries that don't return rows (INSERT/UPDATE/DELETE without RETURNING)
        return cursor.rowcount, []

    except (OperationalError, InterfaceError) as e:
        logging.error(f"Database error in safe_db_query: {e}")
        if conn:
            conn.rollback()
        # Re-raise untuk global handler
        raise
    except Exception as e:
        logging.error(f"Unexpected error in safe_db_query: {e}")
        if conn:
            conn.rollback()
        raise ConnectionError(f"Database query failed: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

class Connection:
    """Database connection class for compatibility"""
    pass
