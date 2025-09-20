from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import List
import io
import base64

from app.core.security import verify_token
from app.domain.dtos.query import QueryRequest, QueryResponse, ConversationRequest
from app.services.rag_engine import rag_engine
from app.services.tts_service import tts_service
from app.infra.repositories.quiz_repository import QuizRepository

router = APIRouter()

@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Ask a question using the RAG system"""
    try:
        # Log user interaction
        await quiz_repo.log_user_interaction({
            "user_id": request.user_id,
            "type": "question",
            "question": request.question,
            "query_type": request.query_type.value,
            "subject": request.subject_filter,
            "include_audio": request.include_audio,
            "voice": request.voice
        })
        
        # Process query through RAG engine with TTS support
        response = await rag_engine.query(
            query=request.question,
            user_id=request.user_id,
            include_sources=request.include_sources,
            subject_filter=request.subject_filter,
            include_audio=request.include_audio,
            voice=request.voice
        )
        
        # Log the response for analytics
        await quiz_repo.log_user_interaction({
            "user_id": request.user_id,
            "type": "answer_received",
            "question": request.question,
            "answer": response.get("answer", ""),
            "confidence": response.get("confidence", 0.0),
            "processing_time": response.get("processing_time", 0.0),
            "sources_count": len(response.get("sources", [])),
            "audio_generated": response.get("audio_base64") is not None,
            "voice_used": response.get("voice_used")
        })
        
        return QueryResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@router.post("/conversation", response_model=QueryResponse)
async def conversation(
    request: ConversationRequest,
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Handle multi-turn conversation"""
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # Get the latest user message
        latest_message = request.messages[-1]
        if latest_message.role != "user":
            raise HTTPException(status_code=400, detail="Latest message must be from user")
        
        # Convert to QueryRequest
        query_request = QueryRequest(
            question=latest_message.content,
            context=request.context
        )
        
        # Log conversation
        await quiz_repo.log_user_interaction({
            "user_id": None,
            "type": "conversation",
            "messages": [msg.dict() for msg in request.messages],
            "context": request.context
        })
        
        # Process through RAG engine
        response = await rag_engine.query(query_request, None)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing conversation: {str(e)}")

@router.get("/stats")
async def get_query_stats(
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Get user's query statistics"""
    try:
        interactions = await quiz_repo.get_user_interactions(None, limit=1000)
        
        # Calculate stats
        total_questions = len([i for i in interactions if i.get("type") == "question"])
        subjects = {}
        avg_confidence = 0
        confidence_count = 0
        
        for interaction in interactions:
            if interaction.get("subject"):
                subject = interaction["subject"]
                subjects[subject] = subjects.get(subject, 0) + 1
            
            if interaction.get("confidence"):
                avg_confidence += interaction["confidence"]
                confidence_count += 1
        
        if confidence_count > 0:
            avg_confidence /= confidence_count
        
        return {
            "total_questions": total_questions,
            "subjects": subjects,
            "average_confidence": avg_confidence,
            "total_interactions": len(interactions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")

@router.post("/tts")
async def generate_tts(
    request: dict,
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Generate TTS audio for given text"""
    try:
        text = request.get("text", "")
        voice = request.get("voice", "alloy")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        if len(text) > 4000:
            raise HTTPException(status_code=400, detail="Text too long (max 4000 characters)")
        
        # Valid OpenAI TTS voices
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice not in valid_voices:
            raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {valid_voices}")
        
        audio_base64 = await tts_service.generate_speech(text=text, voice=voice)
        
        if not audio_base64:
            raise HTTPException(status_code=500, detail="Failed to generate TTS audio")
        
        # Log TTS usage
        await quiz_repo.log_user_interaction({
            "user_id": None,
            "type": "tts_generated",
            "text_length": len(text),
            "voice": voice
        })
        
        return {
            "audio_base64": audio_base64,
            "voice": voice,
            "text_length": len(text),
            "format": "mp3"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TTS: {str(e)}")

@router.post("/tts/stream")
async def generate_tts_stream(
    request: dict
):
    """Generate TTS audio and return as streaming audio file"""
    try:
        text = request.get("text", "")
        voice = request.get("voice", "alloy")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        if len(text) > 4000:
            raise HTTPException(status_code=400, detail="Text too long (max 4000 characters)")
        
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice not in valid_voices:
            raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {valid_voices}")
        
        audio_base64 = await tts_service.generate_speech(text=text, voice=voice)
        
        if not audio_base64:
            raise HTTPException(status_code=500, detail="Failed to generate TTS audio")
        
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(audio_base64)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=tts_audio.mp3"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TTS stream: {str(e)}")