"""
OpenAI Embeddings Utility
"""

import os
import logging
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from openai import AuthenticationError, RateLimitError, APIError

from app.utils.setting import get_openai_api_key
from app.utils.llm_timeout import get_llm_timeout

logger = logging.getLogger(__name__)


class OpenAIEmbeddingService:
    """
    Service for managing OpenAI embeddings with configurable models and dimensions.
    
    Supported models:
    - text-embedding-3-small (1536 dimensions, cost-effective)
    - text-embedding-3-large (3072 dimensions, highest performance)  
    - text-embedding-ada-002 (1536 dimensions, legacy)
    """
    
    # Model configurations
    MODEL_CONFIGS = {
        "text-embedding-3-small": {
            "dimensions": 1536,
            "max_tokens": 8191,
            "description": "Cost-effective embedding model with good performance"
        },
        "text-embedding-3-large": {
            "dimensions": 3072,
            "max_tokens": 8191,
            "description": "High-performance embedding model with maximum accuracy"
        },
        "text-embedding-ada-002": {
            "dimensions": 1536,
            "max_tokens": 8191,
            "description": "Legacy embedding model (deprecated but still functional)"
        }
    }
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None
    ):
        """
        Initialize the OpenAI embedding service.
        
        Args:
            model: OpenAI embedding model name
            api_key: OpenAI API key (if not provided, uses OPENAI_API_KEY env var)
            dimensions: Custom dimensions (only supported for text-embedding-3-* models)
        """
        self.model = model

        resolved_api_key = api_key if api_key else get_openai_api_key()
        self.api_key = resolved_api_key

        if not self.api_key:
            raise ValueError("OpenAI API key is required. Configure it via Settings (api_key) or set the OPENAI_API_KEY environment variable.")
        
        # Validate model
        if model not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model: {model}. Supported models: {list(self.MODEL_CONFIGS.keys())}")
        
        # Set dimensions
        if dimensions:
            if model.startswith("text-embedding-3-"):
                self.dimensions = dimensions
                logger.info(f"Using custom dimensions: {dimensions} for model {model}")
            else:
                logger.warning(f"Custom dimensions not supported for {model}, using default: {self.MODEL_CONFIGS[model]['dimensions']}")
                self.dimensions = self.MODEL_CONFIGS[model]["dimensions"]
        else:
            self.dimensions = self.MODEL_CONFIGS[model]["dimensions"]
        
        # Initialize OpenAI embeddings
        try:
            embedding_kwargs = {
                "model": self.model,
                "openai_api_key": self.api_key,
                "show_progress_bar": False,
                "chunk_size": 1000  # Process in batches
            }
            timeout_value = get_llm_timeout()
            if timeout_value is not None:
                embedding_kwargs["timeout"] = timeout_value
            
            # Add dimensions parameter only for text-embedding-3-* models if custom dimensions specified
            if dimensions and model.startswith("text-embedding-3-"):
                embedding_kwargs["dimensions"] = dimensions

            try:
                self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
            except TypeError:
                if "timeout" in embedding_kwargs:
                    embedding_kwargs.pop("timeout", None)
                    self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
                else:
                    raise
            
            logger.info(f"✅ OpenAI embeddings initialized successfully")
            logger.info(f"   Model: {self.model}")
            logger.info(f"   Dimensions: {self.dimensions}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI embeddings: {e}")
            raise
    
    def get_embeddings_instance(self) -> OpenAIEmbeddings:
        """
        Get the LangChain OpenAIEmbeddings instance.
        
        Returns:
            OpenAIEmbeddings instance for use with LangChain
        """
        return self.embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        try:
            return self.embeddings.embed_query(text)
        except (AuthenticationError, RateLimitError, APIError) as e:
            logger.error(f"❌ OpenAI API error during embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to embed query: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            return self.embeddings.embed_documents(texts)
        except (AuthenticationError, RateLimitError, APIError) as e:
            logger.error(f"❌ OpenAI API error during embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to embed documents: {e}")
            raise
    
    @classmethod
    def get_model_info(cls, model: str) -> dict:
        """
        Get information about a specific model.
        
        Args:
            model: Model name
            
        Returns:
            Dictionary with model information
        """
        return cls.MODEL_CONFIGS.get(model, {})
    
    @classmethod
    def list_available_models(cls) -> List[str]:
        """
        List all available embedding models.
        
        Returns:
            List of model names
        """
        return list(cls.MODEL_CONFIGS.keys())


def get_openai_embeddings(
    model: str = None,
    api_key: Optional[str] = None,
    dimensions: Optional[int] = None
) -> OpenAIEmbeddings:
    """
    Factory function to create OpenAI embeddings instance.
    Uses environment variables for default configuration.
    
    Args:
        model: OpenAI embedding model (defaults to text-embedding-3-small)
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        dimensions: Custom dimensions for text-embedding-3-* models
        
    Returns:
        OpenAIEmbeddings instance
    """
    # Use environment variable or default model
    if not model:
        model = "text-embedding-3-small"
    
    # Create service and return embeddings instance
    service = OpenAIEmbeddingService(
        model=model,
        api_key=api_key,
        dimensions=dimensions
    )
    
    return service.get_embeddings_instance()


def get_embedding_dimensions(model: str = None) -> int:
    """
    Get the embedding dimensions for a specific model.
    
    Args:
        model: Model name (defaults to text-embedding-3-small)

    Returns:
        Number of dimensions
    """
    if not model:
        model = "text-embedding-3-small"
    
    config = OpenAIEmbeddingService.MODEL_CONFIGS.get(model, {})
    return config.get("dimensions", 1536)  # Default to 1536 if model not found
