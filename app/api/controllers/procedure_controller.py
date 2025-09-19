from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List

from app.core.security import verify_token
from app.domain.dtos.procedure import (
    ProcedureOut, UserProcedureSession, 
    StepValidationRequest, StepValidationResponse
)
from app.services.procedure_service import procedure_service
from app.infra.repositories.quiz_repository import QuizRepository

router = APIRouter()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    return verify_token(token)

@router.get("/{procedure_id}", response_model=ProcedureOut)
async def get_procedure(
    procedure_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get procedure details"""
    try:
        procedure = await procedure_service.get_procedure(procedure_id)
        if not procedure:
            raise HTTPException(status_code=404, detail="Procedure not found")
        
        return procedure
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving procedure: {str(e)}")

@router.post("/{procedure_id}/start", response_model=UserProcedureSession)
async def start_procedure(
    procedure_id: str,
    current_user: dict = Depends(get_current_user),
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Start a new procedure session"""
    try:
        session = await procedure_service.start_procedure_session(
            procedure_id,
            current_user["user_id"],
            quiz_repo
        )
        
        return session
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting procedure: {str(e)}")

@router.post("/validate-step", response_model=StepValidationResponse)
async def validate_step(
    request: StepValidationRequest,
    current_user: dict = Depends(get_current_user),
    quiz_repo: QuizRepository = Depends(QuizRepository.dep)
):
    """Validate a user's action for a procedure step"""
    try:
        response = await procedure_service.validate_step(request, quiz_repo)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating step: {str(e)}")

@router.get("/", response_model=List[ProcedureOut])
async def list_procedures(
    current_user: dict = Depends(get_current_user),
    subject: str = None
):
    """List available procedures"""
    try:
        # For now, return sample procedures
        # In production, this would query the knowledge graph
        procedures = [
            await procedure_service.get_procedure("jet_engine_basics"),
            await procedure_service.get_procedure("biology_dissection"),
            await procedure_service.get_procedure("chemistry_titration")
        ]
        
        # Filter by subject if provided
        if subject:
            procedures = [p for p in procedures if p and p.subject.lower() == subject.lower()]
        
        return [p for p in procedures if p is not None]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing procedures: {str(e)}")