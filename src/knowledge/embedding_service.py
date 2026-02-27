from __future__ import annotations

import torch
from sentence_transformers import SentenceTransformer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class EmbeddingService:
    """BGE-M3 embedding service wrapper with lazy loading."""

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str | None = None) -> None:
        """Initialize embedding service.

        Args:
            model_name: HuggingFace model name for BGE-M3.
            device: Device to run model on. Auto-detects if None (cuda if available, else cpu).
        """
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> None:
        """Lazy load the SentenceTransformer model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, device=self.device)

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed a list of texts using BGE-M3.

        Args:
            texts: List of texts to embed.
            batch_size: Batch size for encoding.

        Returns:
            List of embedding vectors (1024-dim for BGE-M3).
        """
        self._load_model()
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query text.

        Args:
            query: Query text to embed.

        Returns:
            Embedding vector (1024-dim for BGE-M3).
        """
        embeddings = self.embed_texts([query], batch_size=1)
        return embeddings[0]

    def get_chroma_embedding_function(self) -> Callable[[list[str]], list[list[float]]]:
        """Get a ChromaDB-compatible embedding function.

        Returns:
            Callable that takes a list of texts and returns list of embeddings.
        """

        def embedding_function(texts: list[str]) -> list[list[float]]:
            return self.embed_texts(texts)

        return embedding_function
