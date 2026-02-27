from __future__ import annotations

import chromadb
from chromadb.config import Settings

from src.config import RAGConfig
from src.knowledge.embedding_service import EmbeddingService
from src.knowledge.text_chunker import TextChunk


class RAGRetriever:
    """RAG retrieval using ChromaDB for vector similarity search."""

    def __init__(self, config: RAGConfig, embedding_service: EmbeddingService) -> None:
        """Initialize the RAG retriever with ChromaDB persistent client.

        Args:
            config: RAG configuration containing vector_db_path
            embedding_service: Service for generating embeddings
        """
        self.config = config
        self.embedding_service = embedding_service

        # Create persistent client
        self.client = chromadb.PersistentClient(
            path=str(config.vector_db_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection with cosine similarity for BGE-M3
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )

    def index_documents(self, chunks: list[TextChunk], batch_size: int = 100) -> None:
        """Index document chunks into the vector database.

        Args:
            chunks: List of text chunks to index
            batch_size: Number of chunks to embed and add in each batch
        """
        if not chunks:
            return

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            # Extract text content for embedding
            texts = [chunk.text for chunk in batch]

            # Generate embeddings
            # Generate embeddings
            embeddings = self.embedding_service.embed_texts(texts)

            # Prepare data for ChromaDB
            ids = [f"doc_{chunk.metadata.get('chunk_id', f'{i}_{j}')}" for j, chunk in enumerate(batch)]
            metadatas = [chunk.metadata for chunk in batch]
            documents = texts

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: dict | None = None
    ) -> list[dict]:
        """Search for similar documents based on query.

        Args:
            query: Search query text
            n_results: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results with text, metadata, and distance
        """
        # Embed the query
        # Embed the query
        query_embedding = self.embedding_service.embed_query(query)

        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filters,
            include=["metadatas", "documents", "distances"]
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })

        return formatted_results

    def format_for_context(self, results: list[dict], format: str = "simple") -> str:
        """Format search results for context injection.

        Args:
            results: List of search results from search()
            format: Format type - "simple", "cited", or "detailed"

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        if format == "simple":
            return "\n\n".join([r["text"] for r in results])

        elif format == "cited":
            formatted = []
            for i, r in enumerate(results, 1):
                source = r["metadata"].get("source", r["id"])
                formatted.append(f"[{i}] Source: {source}\n{r['text']}")
            return "\n\n".join(formatted)

        elif format == "detailed":
            formatted = []
            for i, r in enumerate(results, 1):
                meta_lines = [f"  {k}: {v}" for k, v in r["metadata"].items()]
                formatted.append(
                    f"[{i}] ID: {r['id']}\n"
                    f"Distance: {r['distance']:.4f}\n"
                    f"Metadata:\n" + "\n".join(meta_lines) + "\n"
                    f"Text:\n{r['text']}"
                )
            return "\n\n---\n\n".join(formatted)

        else:
            raise ValueError(f"Unknown format: {format}. Use 'simple', 'cited', or 'detailed'.")

    def get_collection_stats(self) -> dict:
        """Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        count = self.collection.count()
        return {
            "document_count": count,
            "collection_name": self.collection.name,
            "vector_db_path": str(self.config.vector_db_path)
        }
