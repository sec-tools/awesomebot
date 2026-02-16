"""Memory-efficient RAG service using ChromaDB with lazy loading."""
import os
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class RAGService:
    """
    Lightweight RAG service for document retrieval.
    Lazy-loads the embedding model to save memory when RAG isn't used.
    """
    
    _instance: Optional["RAGService"] = None
    
    def __new__(cls) -> "RAGService":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = 50
        self.max_docs = 3
        
        # Lazy-loaded embedder
        self._embedder: Optional["SentenceTransformer"] = None
        self._embedder_last_used: Optional[datetime] = None
        
        # Initialize ChromaDB with persistent storage
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        self.chroma_client = chromadb.Client(ChromaSettings(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            anonymized_telemetry=False,
        ))
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        self._initialized = True
    
    @property
    def embedder(self) -> "SentenceTransformer":
        """
        Lazy-load the embedding model on first use.
        Updates last-used timestamp for potential cleanup.
        """
        if self._embedder is None:
            print("📦 Loading embedding model (first use)...")
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device='cpu'  # Explicit CPU for predictable memory usage
            )
            print("✅ Embedding model loaded")
        
        self._embedder_last_used = datetime.now()
        return self._embedder
    
    def unload_embedder(self) -> None:
        """
        Unload the embedding model to free memory.
        Call this during low-memory conditions or idle periods.
        """
        if self._embedder is not None:
            print("🧹 Unloading embedding model to free memory...")
            del self._embedder
            self._embedder = None
            self._embedder_last_used = None
            
            # Force garbage collection
            import gc
            gc.collect()
            print("✅ Embedding model unloaded")
    
    def is_embedder_loaded(self) -> bool:
        """Check if embedder is currently loaded."""
        return self._embedder is not None
    
    async def add_document(self, doc_id: str, text: str, metadata: dict = None) -> int:
        """
        Add document to RAG index.
        
        Args:
            doc_id: Unique document identifier
            text: Document text content
            metadata: Optional metadata dict
            
        Returns:
            Number of chunks added
        """
        # Split into chunks
        chunks = self._chunk_text(text)
        
        if not chunks:
            return 0
        
        # Generate embeddings (lazy loads model if needed)
        embeddings = self.embedder.encode(chunks, show_progress_bar=False)
        
        # Prepare data for ChromaDB
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_id": doc_id, "chunk_index": i, **(metadata or {})} 
            for i in range(len(chunks))
        ]
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=chunks,
            metadatas=metadatas
        )
        
        return len(chunks)
    
    async def search(self, query: str, n_results: int = None) -> List[str]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query text
            n_results: Number of results (default: self.max_docs)
            
        Returns:
            List of relevant document chunks
        """
        if n_results is None:
            n_results = self.max_docs
        
        # Check if collection is empty first (avoid loading embedder)
        if self.collection.count() == 0:
            return []
        
        # Generate query embedding (lazy loads model if needed)
        query_embedding = self.embedder.encode([query], show_progress_bar=False)[0]
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results
        )
        
        # Extract documents
        if results and results['documents']:
            return results['documents'][0]
        
        return []
    
    async def delete_document(self, doc_id: str) -> None:
        """Delete document from index."""
        # Get all chunk IDs for this document
        results = self.collection.get(
            where={"doc_id": doc_id}
        )
        
        if results and results['ids']:
            self.collection.delete(ids=results['ids'])
    
    async def get_context(self, query: str) -> str:
        """
        Get formatted context for RAG augmentation.
        
        Args:
            query: User query
            
        Returns:
            Formatted context string or empty string
        """
        docs = await self.search(query)
        
        if not docs:
            return ""
        
        context = "\n\n".join([f"[{i+1}] {doc}" for i, doc in enumerate(docs)])
        return f"Relevant context:\n{context}"
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + self.chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start += self.chunk_size - self.chunk_overlap
        
        return chunks
    
    def get_stats(self) -> dict:
        """Get RAG statistics."""
        return {
            "total_chunks": self.collection.count(),
            "chunk_size": self.chunk_size,
            "max_docs": self.max_docs,
            "embedder_loaded": self.is_embedder_loaded(),
            "embedder_last_used": self._embedder_last_used.isoformat() if self._embedder_last_used else None
        }
