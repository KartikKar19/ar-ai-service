import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging
import os

# Disable ChromaDB telemetry to avoid capture() errors
os.environ["ANONYMIZED_TELEMETRY"] = "False"

logger = logging.getLogger(__name__)

class ChromaClient:
    def __init__(self):
        self.client = None
        self.collection = None
        # Create OpenAI embedding function with the correct model
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.EMBEDDING_MODEL
        )
    
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
            
            # Always reset collection to ensure correct embedding function
            try:
                # Try to delete existing collection
                client.delete_collection("documents")
                logger.info("Deleted existing documents collection")
            except ValueError:
                # Collection doesn't exist, which is fine
                logger.info("No existing collection to delete")
            
            # Create new collection with correct embedding function
            collection = client.create_collection(
                name="documents",
                metadata={"description": "AR-Learn document embeddings"},
                embedding_function=self.embedding_function
            )
            logger.info("Created new documents collection with OpenAI embeddings")
            
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
    
    async def reset_collection(self):
        """Reset the collection with correct embedding function"""
        import asyncio
        loop = asyncio.get_event_loop()
        def sync_reset():
            # Delete existing collection
            try:
                self.client.delete_collection("documents")
                logger.info("Deleted existing documents collection")
            except ValueError:
                logger.info("No existing collection to delete")
            
            # Create new collection with correct embedding function
            collection = self.client.create_collection(
                name="documents",
                metadata={"description": "AR-Learn document embeddings"},
                embedding_function=self.embedding_function
            )
            logger.info("Created new documents collection with OpenAI embeddings")
            return collection
        
        self.collection = await loop.run_in_executor(None, sync_reset)

# Global client instance
chroma_client = ChromaClient()