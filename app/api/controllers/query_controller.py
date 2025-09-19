from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List

from app.core.security import verify_token
from app.domain.dtos.query import QueryRequest, QueryResponse, ConversationRequest
from app.services.rag_engine import rag_engine
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
            "user_id": None,
            "type": "question",
            "question": request.question,
            "query_type": request.query_type.value,
            "subject": request.subject_filter
        })
        
        # Process query through RAG engine
        response = await rag_engine.query(request, None)
        
        # Log the response for analytics
        await quiz_repo.log_user_interaction({
            "user_id": None,
            "type": "answer_received",
            "question": request.question,
            "answer": response.answer,
            "confidence": response.confidence,
            "processing_time": response.processing_time
        })
        
        return response
        
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