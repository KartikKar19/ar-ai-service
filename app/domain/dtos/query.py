from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class QueryType(str, Enum):
    GENERAL = "general"
    PROCEDURAL = "procedural"
    ASSESSMENT = "assessment"

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    query_type: QueryType = QueryType.GENERAL
    context: Optional[Dict[str, Any]] = None
    scene: Optional[str] = None # CHANGE THIS LINE
    max_results: int = Field(default=5, ge=1, le=20)
    
class QueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    query_type: QueryType
    processing_time: float

class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ConversationRequest(BaseModel):
    messages: List[ConversationMessage]
    context: Optional[Dict[str, Any]] = None