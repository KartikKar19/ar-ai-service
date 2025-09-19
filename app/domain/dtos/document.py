from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"

class DocumentStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentUploadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    subject: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)

class DocumentOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    subject: Optional[str]
    tags: List[str]
    file_type: DocumentType
    file_size: int
    status: DocumentStatus
    chunks_count: Optional[int] = None
    uploaded_by: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

class ChunkOut(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: dict