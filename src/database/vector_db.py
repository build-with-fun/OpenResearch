"""
Vector database module using ChromaDB for research storage.
Stores, retrieves, and performs semantic similarity search on research data.
"""

from __future__ import annotations

import uuid
import logging
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorDatabase:
    def __init__(self, persist_dir: str = "./chroma_db") -> None:
        """
        Initialize ChromaDB vector database.

        Args:
            persist_dir: Directory to persist the database
        """
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=persist_dir)

        # Collection for research data
        self.collection_name = "research_data"
        self.collection = None

    def create_collection(self, collection_name: Optional[str] = None):
        """Create a fresh collection, deleting any existing one."""
        name = collection_name or self.collection_name

        # Delete existing collection if it exists
        try:
            self.client.delete_collection(name)
        except Exception:
            pass  # Collection may not exist — that's fine

        self.collection = self.client.create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        return self.collection

    def add_documents(
        self, documents: List[Dict], collection_name: Optional[str] = None
    ) -> int:
        """
        Add documents to the vector database.

        Args:
            documents: List of dicts with 'content' and 'embedding' keys
            collection_name: Optional collection name

        Returns:
            Number of documents added
        """
        if not self.collection:
            self.create_collection(collection_name)

        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents_text: List[str] = []
        metadatas: List[Dict] = []

        for doc in documents:
            content = doc.get("content", doc.get("page_content", ""))
            embedding = doc.get("embedding", [])

            if not embedding or len(embedding) == 0:
                continue

            ids.append(str(uuid.uuid4()))
            embeddings.append(embedding)
            documents_text.append(content)

            # Metadata — convert all values to strings for ChromaDB
            metadata = {
                "source": doc.get("source", doc.get("url", "unknown")),
                "query": doc.get("query", ""),
                "index": str(doc.get("index", 0)),
                "timestamp": str(
                    doc.get("timestamp", datetime.now(timezone.utc).timestamp())
                ),
                "content_hash": doc.get("content_hash", ""),
            }
            metadatas.append(metadata)

        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents_text,
                metadatas=metadatas,
            )
            logger.info("Added %d documents to vector DB", len(ids))

        return len(ids)

    def query_similar(
        self, query: str, query_embedding: List[float], n_results: int = 50
    ) -> Dict:
        """
        Query for similar documents using embedding.

        Args:
            query: Query text (for reference)
            query_embedding: Query embedding vector
            n_results: Number of results to return

        Returns:
            Dictionary with similar documents
        """
        if not self.collection:
            return {"documents": [], "metadatas": [], "distances": []}

        total = self.collection.count()
        effective_n = min(n_results, total if total else 100)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_n,
            include=["documents", "metadatas", "distances"],
        )

        return results

    def get_all_documents(self, limit: int = 1000) -> Dict:
        """Get documents from the collection (up to limit)."""
        if not self.collection:
            return {"documents": []}

        count = self.collection.count()
        return self.collection.get(
            limit=min(limit, count),
            include=["documents", "metadatas"],
        )

    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection."""
        if not self.collection:
            return {"count": 0}

        return {
            "count": self.collection.count(),
            "name": self.collection.name,
        }

    def reset_collection(self, collection_name: Optional[str] = None) -> None:
        """Reset/clear the collection."""
        name = collection_name or self.collection_name
        try:
            self.client.delete_collection(name)
        except Exception:
            pass  # Collection may not exist
        self.collection = None

    def batch_add_with_embeddings(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
    ) -> int:
        """
        Batch add texts with pre-computed embeddings.

        Args:
            texts: List of text content
            embeddings: List of embedding vectors
            metadatas: Optional list of metadata dicts

        Returns:
            Number of documents added

        Raises:
            ValueError: If texts and embeddings have different lengths
        """
        if not self.collection:
            self.create_collection()

        if len(texts) != len(embeddings):
            raise ValueError(
                f"Length mismatch: {len(texts)} texts vs {len(embeddings)} embeddings"
            )

        if metadatas is None:
            metadatas = [{} for _ in texts]

        # Convert metadata values to strings for ChromaDB
        str_metadatas = []
        for meta in metadatas:
            str_meta = {k: str(v) for k, v in meta.items()}
            str_metadatas.append(str_meta)

        ids = [str(uuid.uuid4()) for _ in texts]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=str_metadatas,
        )

        logger.info("Batch added %d documents", len(texts))
        return len(texts)

    def close(self) -> None:
        """Gracefully close the database client (release resources)."""
        # ChromaDB's PersistentClient handles cleanup on GC,
        # but we explicitly null out the reference for clarity.
        self.collection = None
        self.client = None


# Thread-safe singleton
_vector_db: Optional[VectorDatabase] = None
_db_lock = threading.Lock()


def get_vector_db(persist_dir: str = "./chroma_db") -> VectorDatabase:
    """Get or create thread-safe singleton vector database instance."""
    global _vector_db
    if _vector_db is None:
        with _db_lock:
            if _vector_db is None:
                _vector_db = VectorDatabase(persist_dir)
    return _vector_db
