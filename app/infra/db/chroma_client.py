import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ChromaClient:
    def __init__(self):
        self.client = None
        self.collection = None
    
    async def connect(self):
        """Initialize ChromaDB client asynchronously"""
        import asyncio
        loop = asyncio.get_event_loop()
        def sync_connect():
            client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            collection = client.get_or_create_collection(
                name="documents",
                metadata={"description": "AR-Learn document embeddings"}
            )
            return client, collection
        self.client, self.collection = await loop.run_in_executor(None, sync_connect)
        logger.info("Connected to ChromaDB (async)")
    
    async def add_documents(
        self, 
        documents: List[str], 
        metadatas: List[Dict[str, Any]], 
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None
    ):
        """Add documents to vector store"""
        try:
            if embeddings:
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )
            else:
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            logger.info(f"Added {len(documents)} documents to ChromaDB")
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {e}")
            raise
    
    async def search_similar(
        self, 
        query_text: str, 
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search for similar documents"""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where
            )
            
            return {
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
                "ids": results["ids"][0] if results["ids"] else []
            }
        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            raise
    
    async def delete_document(self, document_id: str):
        """Delete document from vector store"""
        try:
            # Delete all chunks for this document
            self.collection.delete(
                where={"document_id": document_id}
            )
            logger.info(f"Deleted document {document_id} from ChromaDB")
        except Exception as e:
            logger.error(f"Error deleting document from ChromaDB: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name
            }
        except Exception as e:
            logger.error(f"Error getting ChromaDB stats: {e}")
            return {"total_documents": 0, "collection_name": "unknown"}

# Global client instance
chroma_client = ChromaClient()