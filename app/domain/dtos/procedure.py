from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class StepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class ProcedureStep(BaseModel):
    id: str
    title: str
    description: str
    instruction: str
    expected_action: str
    hints: List[str] = Field(default_factory=list)
    validation_criteria: Dict[str, Any] = Field(default_factory=dict)
    order: int

class ProcedureOut(BaseModel):
    id: str
    title: str
    description: str
    subject: str
    difficulty_level: str
    estimated_duration: int  # minutes
    steps: List[ProcedureStep]
    created_by: str

class UserProcedureSession(BaseModel):
    id: str
    procedure_id: str
    user_id: str
    current_step: int
    step_statuses: Dict[str, StepStatus]
    started_at: str
    completed_at: Optional[str] = None
    score: Optional[float] = None

class StepValidationRequest(BaseModel):
    session_id: str
    step_id: str
    user_action: Dict[str, Any]

class StepValidationResponse(BaseModel):
    is_correct: bool
    feedback: str
    hints: List[str] = Field(default_factory=list)
    next_step: Optional[ProcedureStep] = None