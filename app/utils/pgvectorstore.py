"""
PGVector Store utilities for PostgreSQL with pgvector extension.
Native PostgreSQL vector operations for document similarity search.
"""
import os
import logging
import numpy as np
from typing import List, Dict, Tuple, Any, Optional, Union
import uuid
from langchain_core.documents import Document
from app.utils.database import safe_db_query, getConnection
from app.utils.embedding import get_openai_embeddings, get_embedding_dimensions
from psycopg2.extras import Json
from pgvector.psycopg2 import register_vector

logger = logging.getLogger(__name__)

class PGVectorStore:
    """
    PostgreSQL vector store implementation using pgvector extension.
    Provides similar functionality to ChromaDB but using PostgreSQL.
    """
    
    def __init__(self, collection_name: str = "combiphar_docs", embedding_function=None):
        """
        Initialize PGVector store.
        
        Args:
            collection_name: Name of the collection (used for metadata)
            embedding_function: Function to generate embeddings
        """
        self.collection_name = collection_name
        
        # Use OpenAI embeddings by default
        if embedding_function is None:
            self.embedding_function = get_openai_embeddings()
        else:
            self.embedding_function = embedding_function
            
        # Get embedding dimensions dynamically based on the model
        self.embedding_dimension = get_embedding_dimensions()
        
        # Register pgvector with psycopg2
        try:
            conn = getConnection()
            register_vector(conn)
            conn.close()
            logger.info("✅ PGVector extension registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register pgvector extension: {e}")
            raise

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
        **kwargs
    ) -> List[str]:
        """
        Add texts to the vector store.
        
        Args:
            texts: List of text content to add
            metadatas: List of metadata dicts for each text
            ids: List of IDs for each text (generated if None)
            
        Returns:
            List of IDs for the added texts
        """
        try:
            if not texts:
                return []
                
            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in texts]
                
            # Generate embeddings
            embeddings = self.embedding_function.embed_documents(texts)
            
            # Prepare data for insertion
            insert_data = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                document_id = metadata.get('document_id')
                chunk_index = metadata.get('chunk_index', 0)
                
                if not document_id:
                    logger.warning(f"No document_id in metadata for text {i}, skipping")
                    continue
                    
                # Convert embedding to numpy array for proper pgvector handling
                embedding_array = np.array(embedding) if not isinstance(embedding, np.ndarray) else embedding
                
                insert_data.append((
                    ids[i],
                    document_id,
                    text,
                    embedding_array,
                    Json(metadata),  # Wrap metadata dict with Json for execute_values compatibility
                    chunk_index
                ))
            
            if not insert_data:
                logger.warning("No valid data to insert")
                return []
            
            # Insert into database
            # Use execute_values compatible format - %s placeholder for the entire VALUES clause
            query = """
                INSERT INTO documents_vectors (id, document_id, content, embedding, metadata, chunk_index)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    chunk_index = EXCLUDED.chunk_index,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            rowcount, _ = safe_db_query(query, insert_data, many=True)
            logger.info(f"✅ Added {rowcount} text embeddings to vector store")
            
            return ids[:len(insert_data)]
            
        except Exception as e:
            logger.error(f"❌ Error adding texts to vector store: {e}")
            raise

    def add_documents(
        self,
        documents: List[Document],
        ids: Optional[List[str]] = None,
        **kwargs
    ) -> List[str]:
        """
        Add Document objects to the vector store.
        
        Args:
            documents: List of Document objects to add
            ids: List of IDs for each document (generated if None)
            
        Returns:
            List of IDs for the added documents
        """
        try:
            if not documents:
                return []
                
            # Extract texts and metadatas from Document objects
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            
            # Call the existing add_texts method
            return self.add_texts(texts=texts, metadatas=metadatas, ids=ids, **kwargs)
            
        except Exception as e:
            logger.error(f"❌ Error adding documents to vector store: {e}")
            raise

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict] = None,
        **kwargs
    ) -> List[Tuple[Document, float]]:
        """
        Search for similar documents with similarity scores.
        
        Args:
            query: Query text
            k: Number of documents to return
            filter: Optional filter dict,
            **kwargs: Additional keyword arguments
            
        Returns:
            List of tuples (Document, similarity_score)
        """
        try:
            # User data who request documents
            user_data = kwargs.get("user_data", None)
            logger.info(f"👤 User Info: {user_data}")
            if not user_data :
                return []

            # Generate query embedding
            query_embedding = self.embedding_function.embed_query(query)

            display_query = kwargs.get("display_query") or query
            display_query_str = " ".join(str(display_query).split())
            logger.info(f"🔍 Performing similarity search for query: {display_query_str}")

            sanitized_query = " ".join(str(query).split())
            if display_query_str != sanitized_query:
                logger.debug(f"Using refined search hint: {sanitized_query}")
            
            # Get similarity threshold from kwargs override or environment default
            try:
                similarity_threshold = float(
                    kwargs.get("similarity_threshold", os.getenv("VECTOR_DOC_MIN_SCORE", "0.1"))
                )
            except Exception:
                similarity_threshold = float(os.getenv("VECTOR_DOC_MIN_SCORE", "0.1"))
            logger.info(f"🔍 Using similarity threshold: {similarity_threshold}")

            # Logic to determine document access based on user role and type
            role_name = user_data.get("role_name", "")
            is_portal_user = user_data.get("is_portal", False)
            user_id = user_data.get("user_id")

            # Determine which document sources are allowed for this search
            filter_params = filter if isinstance(filter, dict) else kwargs.get("filter")
            allowed_source_types: List[str] = []

            if isinstance(filter_params, dict):
                raw_sources = filter_params.get("source_types") or filter_params.get("source_type")
                if isinstance(raw_sources, str):
                    raw_sources = [raw_sources]
                if isinstance(raw_sources, (list, tuple, set)):
                    for source in raw_sources:
                        if not source:
                            continue
                        normalized = str(source).strip().lower()
                        if not normalized:
                            continue
                        allowed_source_types.append(normalized)

            valid_sources = {"portal", "admin", "user", "website"}
            deduped_sources: List[str] = []
            seen_sources = set()
            for src in allowed_source_types:
                if src not in valid_sources or src in seen_sources:
                    continue
                deduped_sources.append(src)
                seen_sources.add(src)

            allowed_source_types = deduped_sources or ["portal", "website", "admin"]

            logger.info(f"🔐 Requested document sources: {allowed_source_types}")

            params = [np.array(query_embedding), np.array(query_embedding), similarity_threshold]
            permission_conditions: List[str] = []
            is_admin = role_name == "admin"
            include_portal = "portal" in allowed_source_types

            if include_portal and not is_admin:
                if is_portal_user:
                    logger.info(f"Portal user {user_id} accessing affiliated portal documents.")
                    try:
                        doc_ids_query = """
                            SELECT documents_id 
                            FROM users_documents 
                            WHERE users_id = %s
                        """
                        access_docs, _ = safe_db_query(doc_ids_query, [user_id])

                        allowed_doc_ids: List[str] = []
                        for row in access_docs or []:
                            doc_id = row[0]
                            if not doc_id:
                                continue
                            try:
                                doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(str(doc_id))
                                allowed_doc_ids.append(str(doc_uuid))
                            except (ValueError, TypeError) as validation_error:
                                logger.warning(
                                    f"Skipping invalid document ID {doc_id} for user {user_id}: {validation_error}"
                                )
                                continue

                        if allowed_doc_ids:
                            permission_conditions.append("(d.source_type <> 'portal' OR d.id::text = ANY(%s))")
                            params.append(allowed_doc_ids)
                            logger.info(f"Portal user {user_id} has access to {len(allowed_doc_ids)} documents.")
                        else:
                            logger.warning(f"Portal user {user_id} has no affiliated portal documents. Removing portal source.")
                            allowed_source_types = [src for src in allowed_source_types if src != "portal"]
                    except Exception as e:
                        logger.error(f"Failed to get document permissions for portal user {user_id}: {e}")
                        allowed_source_types = [src for src in allowed_source_types if src != "portal"]
                else:
                    logger.info(f"User {user_id} is not a portal user or admin. Removing portal source access.")
                    allowed_source_types = [src for src in allowed_source_types if src != "portal"]

            logger.info(f"🔐 Effective document sources after permission checks: {allowed_source_types}")

            if not allowed_source_types:
                logger.warning(f"User {user_id} has no accessible document sources after permission filtering; falling back to non-portal sources.")
                allowed_source_types = ["website", "admin", "user"]

            if len(allowed_source_types) == 1:
                permission_conditions.append("d.source_type = %s")
                params.append(allowed_source_types[0])
            else:
                placeholders = ", ".join(["%s"] * len(allowed_source_types))
                permission_conditions.append(f"d.source_type IN ({placeholders})")
                params.extend(allowed_source_types)

            # Prepare the search query
            logging.info(f"Permission conditions: {permission_conditions}")
            conditions = " AND ".join(permission_conditions)
            where_clause = f" AND {conditions}" if conditions else ""
            search_query = f"""
                SELECT 
                    dv.id,
                    dv.document_id,
                    dv.content,
                    1 - (dv.embedding <=> %s) as similarity,
                    dv.metadata,
                    dv.chunk_index,
                    d.original_filename as document_name,
                    d.storage_path as document_source,
                    d.metadata as document_metadata
                FROM documents_vectors dv
                JOIN documents d ON dv.document_id = d.id
                WHERE 1 - (dv.embedding <=> %s) > %s {where_clause}
                ORDER BY CASE
                    WHEN d.source_type = 'portal' THEN 1
                    WHEN d.source_type = 'website' THEN 2
                    WHEN d.source_type = 'admin' THEN 3
                    WHEN d.source_type = 'user' THEN 4
                    ELSE 5
                END, dv.embedding <=> %s
                LIMIT %s
            """
            
            # Add limit to params
            params.extend([np.array(query_embedding), k])

            # Execute search
            results, columns = safe_db_query(search_query, tuple(params))
            if not results:
                logger.info("🔍 No similar documents found for query")
                return []
            
            logger.info(f"🔍 Retrieved {len(results)} raw results from database")

            # Convert results to Document objects with scores
            docs_with_scores = []
            for row in results:
                row_dict = dict(zip(columns, row))
                
                # Create document metadata
                doc_metadata = {
                    'id': str(row_dict['id']),
                    'document_id': str(row_dict['document_id']),
                    'document_source': row_dict['document_source'],
                    'document_name': row_dict['document_name'],
                    'chunk_index': row_dict['chunk_index'],
                    'similarity': row_dict['similarity']
                }
                
                # Merge with stored metadata
                if row_dict['metadata']:
                    doc_metadata.update(row_dict['metadata'])
                if row_dict['document_metadata']:
                    doc_metadata.update(row_dict['document_metadata'])
                
                # Create Document object
                doc = Document(
                    page_content=row_dict['content'],
                    metadata=doc_metadata
                )
                
                docs_with_scores.append((doc, row_dict['similarity']))
            
            logger.info(f"🔍 Found {len(docs_with_scores)} similar documents for query")
            return docs_with_scores
            
        except Exception as e:
            logger.error(f"❌ Error in similarity search: {e}")
            return []

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict] = None,
        **kwargs
    ) -> List[Document]:
        """
        Search for similar documents.
        
        Args:
            query: Query text
            k: Number of documents to return
            filter: Optional filter dict
            
        Returns:
            List of Document objects
        """
        docs_with_scores = self.similarity_search_with_score(query, k, filter, **kwargs)
        return [doc for doc, _ in docs_with_scores]

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filter: Optional[Dict] = None,
        **kwargs
    ) -> List[Document]:
        """
        Maximal Marginal Relevance search for diverse results.
        
        Args:
            query: Query text
            k: Number of documents to return
            fetch_k: Number of documents to fetch initially
            lambda_mult: Lambda parameter for MMR
            filter: Optional filter dict
            
        Returns:
            List of Document objects
        """
        try:
            # First get more candidates
            docs_with_scores = self.similarity_search_with_score(query, fetch_k, filter, **kwargs)
            
            if len(docs_with_scores) <= k:
                return [doc for doc, _ in docs_with_scores]
            
            # Get embeddings for all candidate documents
            query_embedding = np.array(self.embedding_function.embed_query(query))
            doc_embeddings = []
            
            for doc, _ in docs_with_scores:
                # Re-embed the document content for MMR calculation
                doc_embedding = self.embedding_function.embed_query(doc.page_content)
                doc_embeddings.append(np.array(doc_embedding))
            
            # MMR algorithm
            selected_indices = []
            remaining_indices = list(range(len(docs_with_scores)))
            
            for _ in range(min(k, len(docs_with_scores))):
                if not remaining_indices:
                    break
                    
                best_score = float('-inf')
                best_idx = None
                
                for idx in remaining_indices:
                    # Relevance score (cosine similarity with query)
                    relevance = np.dot(query_embedding, doc_embeddings[idx]) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(doc_embeddings[idx])
                    )
                    
                    # Diversity score (maximum similarity with already selected docs)
                    diversity = 0.0
                    if selected_indices:
                        similarities = []
                        for selected_idx in selected_indices:
                            sim = np.dot(doc_embeddings[idx], doc_embeddings[selected_idx]) / (
                                np.linalg.norm(doc_embeddings[idx]) * np.linalg.norm(doc_embeddings[selected_idx])
                            )
                            similarities.append(sim)
                        diversity = max(similarities)
                    
                    # MMR score
                    mmr_score = lambda_mult * relevance - (1 - lambda_mult) * diversity
                    
                    if mmr_score > best_score:
                        best_score = mmr_score
                        best_idx = idx
                
                if best_idx is not None:
                    selected_indices.append(best_idx)
                    remaining_indices.remove(best_idx)
            
            # Return selected documents
            selected_docs = [docs_with_scores[idx][0] for idx in selected_indices]
            logger.info(f"🔍 MMR search returned {len(selected_docs)} diverse documents")
            return selected_docs
            
        except Exception as e:
            logger.error(f"❌ Error in MMR search: {e}")
            # Fallback to regular similarity search
            return self.similarity_search(query, k, filter, **kwargs)

    def hybrid_search(
        self,
        query: str,
        k: int = 4,
        vector_weight: float = 0.6,
        **kwargs
    ) -> List[Tuple[Document, float]]:
        """
        Hybrid search combining vector similarity and text search.
        
        Args:
            query: Query text
            k: Number of documents to return
            vector_weight: Weight for vector vs text search (0-1)
            
        Returns:
            List of tuples (Document, combined_score)
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_function.embed_query(query)
            
            # Get similarity threshold and vector weight (allow override from kwargs)
            try:
                similarity_threshold = float(
                    kwargs.get("similarity_threshold", os.getenv("VECTOR_DOC_MIN_SCORE", "0.1"))
                )
            except Exception:
                similarity_threshold = float(os.getenv("VECTOR_DOC_MIN_SCORE", "0.1"))
            env_vector_weight = float(os.getenv("HYBRID_VECTOR_WEIGHT", str(vector_weight)))
            
            # Use the search_hybrid_vectors function
            search_query = """
                SELECT * FROM search_hybrid_vectors(%s, %s, %s, %s, %s)
            """
            
            results, columns = safe_db_query(
                search_query,
                (np.array(query_embedding), query, similarity_threshold, k, env_vector_weight)
            )
            
            # Convert results to Document objects with scores
            docs_with_scores = []
            for row in results:
                row_dict = dict(zip(columns, row))
                
                # Create document metadata
                doc_metadata = {
                    'id': str(row_dict['id']),
                    'document_id': str(row_dict['document_id']),
                    'document_source': row_dict['document_source'],
                    'document_name': row_dict['document_name'],
                    'chunk_index': row_dict['chunk_index'],
                    'similarity': row_dict['similarity'],
                    'text_rank': row_dict['text_rank'],
                    'combined_score': row_dict['combined_score']
                }
                
                # Merge with stored metadata
                if row_dict['metadata']:
                    doc_metadata.update(row_dict['metadata'])
                if row_dict['document_metadata']:
                    doc_metadata.update(row_dict['document_metadata'])
                
                # Create Document object
                doc = Document(
                    page_content=row_dict['content'],
                    metadata=doc_metadata
                )
                
                docs_with_scores.append((doc, row_dict['combined_score']))
            
            logger.info(f"🔍 Hybrid search found {len(docs_with_scores)} documents")
            return docs_with_scores
            
        except Exception as e:
            logger.error(f"❌ Error in hybrid search: {e}")
            # Fallback to regular similarity search
            return self.similarity_search_with_score(query, k, None, **kwargs)

    def delete_by_document_id(self, document_id: str) -> bool:
        """
        Delete all vectors for a specific document.
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = "DELETE FROM documents_vectors WHERE document_id = %s"
            rowcount, _ = safe_db_query(query, (document_id,))
            
            logger.info(f"🗑️ Deleted {rowcount} vectors for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting vectors for document {document_id}: {e}")
            return False

    def delete_collection(self) -> bool:
        """
        Delete all vectors in the collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            query = "DELETE FROM documents_vectors"
            rowcount, _ = safe_db_query(query)
            
            logger.info(f"🗑️ Deleted all {rowcount} vectors from collection")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting collection: {e}")
            return False

    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> bool:
        """
        Delete vectors that match the given metadata filter.
        
        Args:
            metadata_filter: Dictionary of metadata key-value pairs to match
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not metadata_filter:
                logger.warning("Empty metadata filter provided, skipping deletion")
                return False
                
            # Build WHERE conditions for metadata filtering
            conditions = []
            params = []
            
            for key, value in metadata_filter.items():
                # Use JSON extraction operator to check metadata values
                conditions.append("metadata->%s = %s")
                params.extend([key, Json(value)])
            
            where_clause = " AND ".join(conditions)
            query = f"DELETE FROM documents_vectors WHERE {where_clause}"
            
            rowcount, _ = safe_db_query(query, params)
            
            logger.info(f"🗑️ Deleted {rowcount} vectors matching metadata filter: {metadata_filter}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting vectors by metadata {metadata_filter}: {e}")
            return False

    def as_retriever(self, search_kwargs: Optional[Dict] = None):
        """
        Create a retriever interface compatible with LangChain.
        
        Args:
            search_kwargs: Search parameters
            
        Returns:
            PGVectorRetriever object
        """
        return PGVectorRetriever(
            vectorstore=self,
            search_kwargs=search_kwargs or {}
        )

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            # Get total count
            count_query = "SELECT COUNT(*) FROM documents_vectors"
            count_results, _ = safe_db_query(count_query)
            total_vectors = count_results[0][0] if count_results else 0
            
            # Get document count
            doc_count_query = "SELECT COUNT(DISTINCT document_id) FROM documents_vectors"
            doc_results, _ = safe_db_query(doc_count_query)
            total_documents = doc_results[0][0] if doc_results else 0
            
            return {
                'total_vectors': total_vectors,
                'total_documents': total_documents,
                'collection_name': self.collection_name,
                'embedding_dimension': self.embedding_dimension
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting collection stats: {e}")
            return {}

    @staticmethod
    def test_connection() -> bool:
        """
        Test PGVector database connection and extension availability.
        
        Returns:
            True if connection and pgvector extension are working, False otherwise
        """
        try:
            # Test basic database connection
            conn = getConnection()
            
            # Register pgvector extension
            register_vector(conn)
            
            # Test if pgvector extension is available
            cursor = conn.cursor()
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            result = cursor.fetchone()
            
            if not result:
                logger.error("❌ PGVector extension is not installed")
                return False
            
            # Test if documents_vectors table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'documents_vectors'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.warning("⚠️ documents_vectors table does not exist")
                return False
            
            # Test basic vector operations
            cursor.execute("SELECT '[1,2,3]'::vector")
            vector_test = cursor.fetchone()
            
            if not vector_test:
                logger.error("❌ Vector operations not working")
                return False
            
            cursor.close()
            conn.close()
            
            logger.info("✅ PGVector connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ PGVector connection test failed: {e}")
            return False


class PGVectorRetriever:
    """
    Retriever interface for PGVectorStore compatible with LangChain.
    """
    
    def __init__(self, vectorstore: PGVectorStore, search_kwargs: Dict = None):
        self.vectorstore = vectorstore
        self.search_kwargs = search_kwargs or {'k': 7}
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Query text
            
        Returns:
            List of relevant Document objects
        """
        # Use hybrid search by default for better results
        search_type = self.search_kwargs.get('search_type', 'hybrid')
        k = self.search_kwargs.get('k', 7)
        
        if search_type == 'mmr':
            return self.vectorstore.max_marginal_relevance_search(query, k=k)
        elif search_type == 'hybrid':
            docs_with_scores = self.vectorstore.hybrid_search(query, k=k)
            return [doc for doc, _ in docs_with_scores]
        else:
            return self.vectorstore.similarity_search(query, k=k)
    
    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """
        Async version of get_relevant_documents (fallback to sync).
        
        Args:
            query: Query text
            
        Returns:
            List of relevant Document objects
        """
        return self.get_relevant_documents(query)


def get_vectorstore() -> Optional[PGVectorStore]:
    """
    Get vectorstore instance using PGVector with PostgreSQL.
    Returns configured PGVector vectorstore or None if unavailable.
    """
    try:
        # Initialize OpenAI embeddings
        embeddings = get_openai_embeddings()

        # Create PGVector store
        vectorstore = PGVectorStore(
            collection_name="combiphar_docs",
            embedding_function=embeddings
        )

        logger.info("✅ PGVector store initialized successfully")
        return vectorstore

    except Exception as e:
        logger.error(f"❌ Failed to initialize PGVector store: {e}")
        logger.error("💡 Make sure PostgreSQL with pgvector extension is running and accessible")
        return None
