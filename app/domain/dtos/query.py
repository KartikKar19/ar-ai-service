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
    subject_filter: Optional[str] = None
    max_results: int = Field(default=5, ge=1, le=20)
    # TTS options
    include_audio: bool = Field(default=False, description="Whether to include TTS audio in response")
    voice: Optional[str] = Field(default="alloy", description="TTS voice: alloy, echo, fable, onyx, nova, shimmer")
    
class QueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    query_type: QueryType
    processing_time: float
    # TTS fields
    audio_base64: Optional[str] = Field(default=None, description="Base64 encoded audio (MP3)")
    audio_duration: Optional[float] = Field(default=None, description="Audio duration in seconds (estimated)")
    voice_used: Optional[str] = Field(default=None, description="TTS voice used for audio generation")

class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ConversationRequest(BaseModel):
    messages: List[ConversationMessage]
    context: Optional[Dict[str, Any]] = None