from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    VOICE = "voice"

class QuizDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class QuizQuestion(BaseModel):
    id: str
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None  # For multiple choice
    correct_answer: str
    explanation: str
    difficulty: QuizDifficulty
    subject: str
    tags: List[str] = Field(default_factory=list)

class QuizGenerationRequest(BaseModel):
    user_interactions: List[Dict[str, Any]] = Field(default_factory=list)
    subject: Optional[str] = None  # Changed from scene to subject
    difficulty: QuizDifficulty = QuizDifficulty.MEDIUM
    question_count: int = Field(default=5, ge=1, le=20)
    question_types: List[QuestionType] = Field(default_factory=lambda: [QuestionType.MULTIPLE_CHOICE])
class QuizOut(BaseModel):
    id: str
    title: str
    description: str
    questions: List[QuizQuestion]
    generated_for_user: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

class QuizAttempt(BaseModel):
    id: str
    quiz_id: str
    user_id: str
    answers: Dict[str, str]  # question_id -> answer
    score: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

class QuizSubmissionRequest(BaseModel):
    quiz_id: str
    answers: Dict[str, str]

class QuizResultResponse(BaseModel):
    score: float
    total_questions: int
    correct_answers: int
    feedback: List[Dict[str, Any]]
    areas_for_improvement: List[str]