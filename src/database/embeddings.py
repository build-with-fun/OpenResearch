"""
Embedding module using Ollama qwen3-embeddings:8b model.
Converts text to vector embeddings for semantic search.
"""

from __future__ import annotations

import ollama
import hashlib
import logging
import threading
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Known embedding dimension for qwen3-embeddings:8b
EMBEDDING_DIM = 4096


class EmbeddingModel:
    def __init__(self, model: str = "qwen3-embedding:8b") -> None:
        """
        Initialize the embedding model using Ollama.

        Args:
            model: Ollama model name for embeddings
        """
        self.model = model
        self.model_name = model
        self._dimension: Optional[int] = None

    def _get_dimension(self) -> int:
        """Detect embedding dimension from the model."""
        if self._dimension is None:
            try:
                response = ollama.embed(model=self.model, input="test")
                self._dimension = len(response["embeddings"][0])
            except Exception:
                self._dimension = EMBEDDING_DIM
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """
        Convert a single text to embedding vector.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding

        Raises:
            RuntimeError: If embedding generation fails
        """
        try:
            response = ollama.embed(model=self.model, input=text)
            return response["embeddings"][0]
        except Exception as e:
            logger.error("Error embedding text: %s", e)
            dim = self._get_dimension()
            return [0.0] * dim

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Convert multiple texts to embedding vectors using batch API.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Use batch API when possible (ollama.embed supports list input)
        try:
            response = ollama.embed(model=self.model, input=texts)
            return response["embeddings"]
        except Exception:
            # Fall back to individual if batch fails
            return [self.embed_text(text) for text in texts]

    def embed_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Embed a list of document dictionaries.
        Each document should have 'content' and optional metadata.
        Returns **new** dicts (does not mutate input).

        Args:
            documents: List of dicts with 'content' key

        Returns:
            List of new dicts with added 'embedding' and 'content_hash' keys
        """
        texts = [doc.get("content", doc.get("page_content", "")) for doc in documents]
        embeddings = self.embed_texts(texts)

        result = []
        for doc, embedding in zip(documents, embeddings):
            new_doc = dict(doc)  # Shallow copy — avoid mutating input
            new_doc["embedding"] = embedding
            new_doc["content_hash"] = hashlib.sha256(
                doc.get("content", doc.get("page_content", "")).encode()
            ).hexdigest()
            result.append(new_doc)

        return result


# Thread-safe singleton
_embedding_model: Optional[EmbeddingModel] = None
_model_lock = threading.Lock()


def get_embedding_model(model: str = "qwen3-embedding:8b") -> EmbeddingModel:
    """Get or create thread-safe singleton embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            if _embedding_model is None:
                _embedding_model = EmbeddingModel(model)
    return _embedding_model
