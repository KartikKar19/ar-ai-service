from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List

from app.domain.dtos.quiz import QuizGenerationRequest, QuizOut, QuizSubmissionRequest, QuizResultResponse
from app.services.quiz_service import quiz_service
from app.core.api_key_auth import verify_api_key
from app.infra.repositories.quiz_repository import QuizRepository

router = APIRouter()

@router.post("", response_model=QuizOut, dependencies=[Depends(verify_api_key)])
async def generate_quiz_simple(
    request: QuizGenerationRequest,
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Generate an adaptive quiz - simplified endpoint"""
    try:
        # If no interactions provided, get recent interactions from database
        if not request.user_interactions:
            request.user_interactions = await quiz_repo.get_user_interactions(
                limit=50,
                subject=request.subject
            )
        
        quiz = await quiz_service.generate_adaptive_quiz(
            request,
            user_id="test-user",  # Replace with actual auth later
            quiz_repo=quiz_repo
        )
        return quiz
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")

@router.post("/generate", response_model=QuizOut, dependencies=[Depends(verify_api_key)])
async def generate_quiz(
    request: QuizGenerationRequest,
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Generate an adaptive quiz based on user interactions and based on the topic"""
    try:
        # If no interactions provided, get recent interactions from database
        if not request.user_interactions:
            request.user_interactions = await quiz_repo.get_user_interactions(
                limit=50,
                subject=request.subject
            )
        quiz = await quiz_service.generate_adaptive_quiz(
            request,
            user_id=None,
            quiz_repo=quiz_repo
        )
        # Transform to custom output structure
        output = {
            "user_id": quiz.generated_for_user,
            "tag": []
        }
        for idx, q in enumerate(quiz.questions, start=1):
            output["tag"].append({
                "quiz_no": idx,
                "question": q.question,
                "choices": q.options if q.options else []
            })
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")

@router.post("/submit", response_model=QuizResultResponse, dependencies=[Depends(verify_api_key)])
async def submit_quiz(
    request: QuizSubmissionRequest,
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Submit quiz answers and get results"""
    try:
        result = await quiz_service.submit_quiz(
            request,
            user_id=None,
            quiz_repo=quiz_repo
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting quiz: {str(e)}")

@router.get("/all", response_model=List[QuizOut], dependencies=[Depends(verify_api_key)])
async def get_user_quizzes(
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Get all quizzes for the current user"""
    try:
        quizzes_data = await quiz_repo.get_user_quizzes(None)
        quizzes = []
        for quiz_data in quizzes_data:
            quiz = QuizOut(
                id=str(quiz_data["_id"]),
                title=quiz_data["title"],
                description=quiz_data["description"],
                questions=quiz_data["questions"],
                generated_for_user=quiz_data["generated_for_user"],
                created_at=quiz_data["created_at"],
                expires_at=quiz_data.get("expires_at")
            )
            quizzes.append(quiz)
        return quizzes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving quizzes: {str(e)}")

@router.get("/{quiz_id}", response_model=QuizOut, dependencies=[Depends(verify_api_key)])
async def get_quiz(
    quiz_id: str,
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Get specific quiz details"""
    try:
        from bson import ObjectId
        quiz_data = await quiz_repo.get_quiz(ObjectId(quiz_id))
        if not quiz_data:
            raise HTTPException(status_code=404, detail="Quiz not found")
        # Check if user has access to this quiz
        # No user-based authorization; all quizzes accessible
        quiz = QuizOut(
            id=str(quiz_data["_id"]),
            title=quiz_data["title"],
            description=quiz_data["description"],
            questions=quiz_data["questions"],
            generated_for_user=quiz_data["generated_for_user"],
            created_at=quiz_data["created_at"],
            expires_at=quiz_data.get("expires_at")
        )
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving quiz: {str(e)}")

@router.get("/attempts/history", dependencies=[Depends(verify_api_key)])
async def get_quiz_history(
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Get user's quiz attempt history"""
    try:
        attempts = await quiz_repo.get_user_attempts(None)
        return {
            "attempts": attempts,
            "total_attempts": len(attempts),
            "average_score": sum(a.get("score", 0) for a in attempts) / len(attempts) if attempts else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving quiz history: {str(e)}")