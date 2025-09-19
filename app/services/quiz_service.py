import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import logging

from app.core.config import settings
from app.domain.dtos.quiz import (
    QuizGenerationRequest, QuizOut, QuizQuestion, QuestionType, 
    QuizDifficulty, QuizAttempt, QuizSubmissionRequest, QuizResultResponse
)
from app.infra.repositories.quiz_repository import QuizRepository

logger = logging.getLogger(__name__)

class QuizService:
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            temperature=0.3
        )
    
    async def generate_adaptive_quiz(
        self, 
        request: QuizGenerationRequest, 
        user_id: str,
        quiz_repo: QuizRepository
    ) -> QuizOut:
        """Generate personalized quiz based on user interactions"""
        try:
            # Analyze user interactions to identify focus areas
            focus_areas = self._analyze_user_interactions(request.user_interactions)
            
            # Generate questions using LLM
            questions = await self._generate_questions(
                focus_areas=focus_areas,
                subject=request.scene,
                difficulty=request.difficulty,
                question_count=request.question_count,
                question_types=request.question_types
            )
            
            # Create quiz object
            quiz_data = {
                "id": str(uuid.uuid4()),
                "title": f"Personalized Quiz - {request.subject or 'General'}",
                "description": f"Adaptive quiz based on your recent learning activities",
                "questions": [q.dict() for q in questions],
                "generated_for_user": user_id,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=7)
            }
            
            # Save to database
            quiz_id = await quiz_repo.create_quiz(quiz_data)
            quiz_data["id"] = str(quiz_id)
            
            return QuizOut(**quiz_data)
            
        except Exception as e:
            logger.error(f"Error generating adaptive quiz: {e}")
            raise
    
    def _analyze_user_interactions(self, interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user interactions to identify learning patterns and gaps"""
        focus_areas = {
            "topics": {},
            "difficulty_preference": "medium",
            "question_types": [],
            "weak_areas": [],
            "strong_areas": []
        }
        
        for interaction in interactions:
            interaction_type = interaction.get("type", "")
            subject = interaction.get("subject", "general")
            
            # Count topic frequency
            if subject not in focus_areas["topics"]:
                focus_areas["topics"][subject] = 0
            focus_areas["topics"][subject] += 1
            
            # Identify weak areas (questions asked repeatedly, incorrect answers)
            if interaction_type == "question" and interaction.get("repeated", False):
                topic = interaction.get("topic", subject)
                if topic not in focus_areas["weak_areas"]:
                    focus_areas["weak_areas"].append(topic)
            
            # Identify strong areas (quick correct answers, advanced topics)
            if interaction_type == "quiz_answer" and interaction.get("correct", False):
                topic = interaction.get("topic", subject)
                if topic not in focus_areas["strong_areas"]:
                    focus_areas["strong_areas"].append(topic)
        
        return focus_areas
    
    async def _generate_questions(
        self,
        focus_areas: Dict[str, Any],
        subject: Optional[str],
        difficulty: QuizDifficulty,
        question_count: int,
        question_types: List[QuestionType]
    ) -> List[QuizQuestion]:
        """Generate quiz questions using LLM"""
        
        # Prepare context for LLM
        context = f"""
        Subject: {subject or 'General'}
        Difficulty: {difficulty.value}
        Question Count: {question_count}
        Question Types: {[qt.value for qt in question_types]}
        
        User Learning Focus:
        - Main topics: {list(focus_areas['topics'].keys())[:3]}
        - Weak areas: {focus_areas['weak_areas'][:3]}
        - Strong areas: {focus_areas['strong_areas'][:3]}
        """
        
        system_prompt = """You are an expert educational assessment creator.
Generate quiz questions that are:
1. Educationally valuable and aligned with learning objectives
2. Appropriate for the specified difficulty level
3. Focused on the user's learning areas and gaps
4. Varied in format to maintain engagement

Return your response as a valid JSON array of question objects with this structure:
{
    "id": "unique_id",
    "question": "question text",
    "question_type": "multiple_choice|true_false|short_answer",
    "options": ["option1", "option2", "option3", "option4"] (for multiple choice only),
    "correct_answer": "correct answer",
    "explanation": "explanation of the correct answer",
    "difficulty": "easy|medium|hard",
    "subject": "subject area",
    "tags": ["tag1", "tag2"]
}
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
Generate {question_count} quiz questions based on this context:

{context}

Focus on creating questions that help reinforce learning in weak areas while building on strong areas.
Make sure questions are clear, unambiguous, and educationally valuable.
""")
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            questions_data = json.loads(response.content)
            
            questions = []
            for i, q_data in enumerate(questions_data[:question_count]):
                question = QuizQuestion(
                    id=q_data.get("id", str(uuid.uuid4())),
                    question=q_data["question"],
                    question_type=QuestionType(q_data["question_type"]),
                    options=q_data.get("options"),
                    correct_answer=q_data["correct_answer"],
                    explanation=q_data["explanation"],
                    difficulty=QuizDifficulty(q_data.get("difficulty", difficulty.value)),
                    subject=q_data.get("subject", subject or "general"),
                    tags=q_data.get("tags", [])
                )
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions with LLM: {e}")
            # Fallback: create simple questions
            return self._create_fallback_questions(subject, difficulty, question_count)
    
    def _create_fallback_questions(
        self, 
        subject: Optional[str], 
        difficulty: QuizDifficulty, 
        count: int
    ) -> List[QuizQuestion]:
        """Create fallback questions if LLM generation fails"""
        questions = []
        
        for i in range(count):
            question = QuizQuestion(
                id=str(uuid.uuid4()),
                question=f"Sample question {i+1} about {subject or 'general topic'}",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=["Option A", "Option B", "Option C", "Option D"],
                correct_answer="Option A",
                explanation="This is a sample explanation.",
                difficulty=difficulty,
                subject=subject or "general",
                tags=["sample"]
            )
            questions.append(question)
        
        return questions
    
    async def submit_quiz(
        self,
        request: QuizSubmissionRequest,
        user_id: str,
        quiz_repo: QuizRepository
    ) -> QuizResultResponse:
        """Process quiz submission and calculate results"""
        try:
            # Get quiz data
            quiz = await quiz_repo.get_quiz(request.quiz_id)
            if not quiz:
                raise ValueError("Quiz not found")
            
            # Calculate score
            questions = quiz["questions"]
            correct_count = 0
            feedback = []
            areas_for_improvement = []
            
            for question in questions:
                q_id = question["id"]
                user_answer = request.answers.get(q_id, "")
                correct_answer = question["correct_answer"]
                
                is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
                if is_correct:
                    correct_count += 1
                
                feedback.append({
                    "question_id": q_id,
                    "question": question["question"],
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "explanation": question["explanation"]
                })
                
                if not is_correct:
                    areas_for_improvement.extend(question.get("tags", []))
            
            # Calculate final score
            total_questions = len(questions)
            score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
            
            # Save attempt
            attempt_data = {
                "quiz_id": request.quiz_id,
                "user_id": user_id,
                "answers": request.answers,
                "score": score,
                "completed_at": datetime.now(timezone.utc)
            }
            await quiz_repo.create_attempt(attempt_data)
            
            # Remove duplicates from areas for improvement
            areas_for_improvement = list(set(areas_for_improvement))
            
            return QuizResultResponse(
                score=score,
                total_questions=total_questions,
                correct_answers=correct_count,
                feedback=feedback,
                areas_for_improvement=areas_for_improvement
            )
            
        except Exception as e:
            logger.error(f"Error processing quiz submission: {e}")
            raise

# Global quiz service instance
quiz_service = QuizService()