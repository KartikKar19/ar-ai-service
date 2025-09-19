from fastapi import Depends
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.infra.db.mongo import get_db
from app.domain.dtos.document import DocumentStatus, DocumentType

class DocumentRepository:
    def __init__(self, db):
        self.documents = db["documents"]
        self.chunks = db["chunks"]
    
    async def create_document(
        self,
        title: str,
        description: Optional[str],
        subject: Optional[str],
        tags: List[str],
        file_type: DocumentType,
        file_size: int,
        file_path: str,
        uploaded_by: str
    ) -> ObjectId:
        now = datetime.now(timezone.utc)
        doc = {
            "title": title,
            "description": description,
            "subject": subject,
            "tags": tags,
            "file_type": file_type.value,
            "file_size": file_size,
            "file_path": file_path,
            "status": DocumentStatus.UPLOADING.value,
            "chunks_count": 0,
            "uploaded_by": uploaded_by,
            "created_at": now,
            "updated_at": now,
            "processed_at": None
        }
        result = await self.documents.insert_one(doc)
        return result.inserted_id
    
    async def update_document_status(
        self, 
        document_id: ObjectId, 
        status: DocumentStatus,
        chunks_count: Optional[int] = None
    ):
        update_data = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if status == DocumentStatus.COMPLETED:
            update_data["processed_at"] = datetime.now(timezone.utc)
        
        if chunks_count is not None:
            update_data["chunks_count"] = chunks_count
        
        await self.documents.update_one(
            {"_id": document_id},
            {"$set": update_data}
        )
    
    async def get_document(self, document_id: ObjectId) -> Optional[Dict[str, Any]]:
        return await self.documents.find_one({"_id": document_id})
    
    async def get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.documents.find({"uploaded_by": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=None)
    
    async def delete_document(self, document_id: ObjectId):
        # Delete document and its chunks
        await self.documents.delete_one({"_id": document_id})
        await self.chunks.delete_many({"document_id": str(document_id)})
    
    async def create_chunks(self, chunks_data: List[Dict[str, Any]]):
        if chunks_data:
            await self.chunks.insert_many(chunks_data)
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        cursor = self.chunks.find({"document_id": document_id}).sort("chunk_index", 1)
        return await cursor.to_list(length=None)
    
    @staticmethod
    def dep(db=Depends(get_db)):
        return DocumentRepository(db)