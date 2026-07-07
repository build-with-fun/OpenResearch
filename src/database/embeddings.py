"""
Embedding module using Ollama qwen3-embedding:8b model.
Converts text to vector embeddings for semantic search.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import List, Dict, Optional

import ollama

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 4096


class EmbeddingModel:
    def __init__(self, model: str = "qwen3-embedding:8b") -> None:
        self.model = model
        self.model_name = model
        self._dimension: Optional[int] = None
        self._warm_up()

    def _warm_up(self):
        try:
            ollama.embed(model=self.model, input="warm-up")
        except Exception:
            pass

    def _get_dimension(self) -> int:
        if self._dimension is None:
            try:
                response = ollama.embed(model=self.model, input="test")
                self._dimension = len(response["embeddings"][0])
            except Exception:
                self._dimension = EMBEDDING_DIM
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        try:
            response = ollama.embed(model=self.model, input=text)
            return response["embeddings"][0]
        except Exception as e:
            logger.error("Error embedding text: %s", e)
            dim = self._get_dimension()
            return [0.0] * dim

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            response = ollama.embed(model=self.model, input=texts)
            return response["embeddings"]
        except Exception:
            return [self.embed_text(text) for text in texts]

    def embed_documents(self, documents: List[Dict]) -> List[Dict]:
        texts = [doc.get("content", doc.get("page_content", "")) for doc in documents]
        embeddings = self.embed_texts(texts)

        result = []
        for doc, embedding in zip(documents, embeddings):
            new_doc = dict(doc)
            new_doc["embedding"] = embedding
            new_doc["content_hash"] = hashlib.sha256(
                doc.get("content", doc.get("page_content", "")).encode()
            ).hexdigest()
            result.append(new_doc)

        return result


_embedding_model: Optional[EmbeddingModel] = None
_model_lock = threading.Lock()


def get_embedding_model(model: str = "qwen3-embedding:8b") -> EmbeddingModel:
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            if _embedding_model is None:
                _embedding_model = EmbeddingModel(model)
    return _embedding_model
