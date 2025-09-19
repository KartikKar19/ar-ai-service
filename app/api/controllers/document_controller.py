import os
import uuid
from pathlib import Path
from typing import List, Optional
import aiofiles

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from app.core.config import settings
from app.domain.dtos.document import DocumentUploadRequest, DocumentOut, DocumentType, ChunkOut
from app.infra.repositories.document_repository import DocumentRepository
from app.services.document_processor import DocumentProcessor
from app.core.api_key_auth import verify_api_key

router = APIRouter()

@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    tags: str = Form(""),  # Comma-separated tags
    doc_repo: DocumentRepository = Depends(DocumentRepository.dep),
    current_user: dict = Depends(verify_api_key)
):
    """Upload and process a document"""
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension == ".pdf":
            file_type = DocumentType.PDF
        elif file_extension == ".docx":
            file_type = DocumentType.DOCX
        elif file_extension == ".txt":
            file_type = DocumentType.TXT
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Only PDF, DOCX, and TXT files are allowed."
            )
        
        # Validate file size
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
        
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_path = upload_dir / f"{file_id}{file_extension}"
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create document record
        document_id = await doc_repo.create_document(
            title=title,
            description=description,
            subject=subject,
            tags=tag_list,
            file_type=file_type,
            file_size=file.size,
            file_path=str(file_path),
            uploaded_by=current_user["user_id"]
        )
        
        # Process document synchronously
        document_processor = DocumentProcessor()
        await document_processor.process_document(
            str(document_id),
            str(file_path),
            file_type,
            doc_repo
        )
        
        # Return document info
        doc = await doc_repo.get_document(document_id)
        return DocumentOut(
            id=str(doc["_id"]),
            title=doc["title"],
            description=doc["description"],
            subject=doc["subject"],
            tags=doc["tags"],
            file_type=DocumentType(doc["file_type"]),
            file_size=doc["file_size"],
            status=doc["status"],
            chunks_count=doc.get("chunks_count"),
            uploaded_by=doc["uploaded_by"],
            created_at=doc["created_at"],
            processed_at=doc.get("processed_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@router.get("/", response_model=List[DocumentOut])
async def get_user_documents(
    doc_repo: DocumentRepository = Depends(DocumentRepository.dep),
    current_user: dict = Depends(verify_api_key)
):
    """Get all documents uploaded by the current user"""
    try:
        docs = await doc_repo.get_user_documents(current_user["user_id"])
        return [
            DocumentOut(
                id=str(doc["_id"]),
                title=doc["title"],
                description=doc["description"],
                subject=doc["subject"],
                tags=doc["tags"],
                file_type=DocumentType(doc["file_type"]),
                file_size=doc["file_size"],
                status=doc["status"],
                chunks_count=doc.get("chunks_count"),
                uploaded_by=doc["uploaded_by"],
                created_at=doc["created_at"],
                processed_at=doc.get("processed_at")
            )
            for doc in docs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: str,
    doc_repo: DocumentRepository = Depends(DocumentRepository.dep),
    current_user: dict = Depends(verify_api_key)
):
    """Get specific document details"""
    try:
        from bson import ObjectId
        doc = await doc_repo.get_document(ObjectId(document_id))
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # User-based authorization
        if doc["uploaded_by"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return DocumentOut(
            id=str(doc["_id"]),
            title=doc["title"],
            description=doc["description"],
            subject=doc["subject"],
            tags=doc["tags"],
            file_type=DocumentType(doc["file_type"]),
            file_size=doc["file_size"],
            status=doc["status"],
            chunks_count=doc.get("chunks_count"),
            uploaded_by=doc["uploaded_by"],
            created_at=doc["created_at"],
            processed_at=doc.get("processed_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    doc_repo: DocumentRepository = Depends(DocumentRepository.dep),
    current_user: dict = Depends(verify_api_key)
):
    """Delete a document and its chunks"""
    try:
        from bson import ObjectId
        doc = await doc_repo.get_document(ObjectId(document_id))
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # User-based authorization
        if doc["uploaded_by"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete from vector store
        from app.infra.db.chroma_client import chroma_client
        await chroma_client.delete_document(document_id)
        
        # Delete file
        file_path = Path(doc["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        await doc_repo.delete_document(ObjectId(document_id))
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@router.get("/{document_id}/chunks", response_model=List[ChunkOut])
async def get_document_chunks(
    document_id: str,
    doc_repo: DocumentRepository = Depends(DocumentRepository.dep),
    current_user: dict = Depends(verify_api_key)
):
    """Get all chunks for a document"""
    try:
        from bson import ObjectId
        doc = await doc_repo.get_document(ObjectId(document_id))
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # User-based authorization
        if doc["uploaded_by"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        chunks = await doc_repo.get_document_chunks(document_id)
        
        return [
            ChunkOut(
                id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                content=chunk["content"],
                chunk_index=chunk["chunk_index"],
                metadata=chunk["metadata"]
            )
            for chunk in chunks
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chunks: {str(e)}")