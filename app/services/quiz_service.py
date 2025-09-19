import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import logging

from app.core.config import settings
from app.domain.dtos.quiz import (
    QuizGenerationRequest, QuizOut, QuizQuestion, QuestionType, 
    QuizDifficulty, QuizAttempt, QuizSubmissionRequest, QuizResultResponse
)
from app.infra.repositories.quiz_repository import QuizRepository
from app.services.rag_engine import rag_engine
from app.infra.db.chroma_client import chroma_client

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
                subject=request.subject,
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
        """Generate quiz questions using LLM with RAG context"""
        
        # Step 1: Retrieve relevant content from documents using RAG
        relevant_content = ""
        if subject:
            try:
                # Search for relevant content in the document store
                search_results = await chroma_client.search_similar(
                    query_text=f"Generate questions about {subject}",
                    n_results=5,
                    where={"subject": subject} if subject else None
                )
                
                # Extract content from search results
                if search_results and search_results.get("documents"):
                    documents = search_results["documents"]
                    metadatas = search_results.get("metadatas", [])
                    
                    content_parts = []
                    for i, doc in enumerate(documents[:3]):  # Top 3 results
                        metadata = metadatas[i] if i < len(metadatas) else {}
                        doc_id = metadata.get("document_id", f"doc_{i}")
                        content_parts.append(f"[Document {doc_id}]: {doc}")
                    
                    relevant_content = "\n".join(content_parts)
                    logger.info(f"Retrieved {len(documents)} relevant documents for quiz generation")
                
            except Exception as e:
                logger.warning(f"Failed to retrieve RAG content: {e}")
                relevant_content = ""
        
        # Step 2: Prepare context for LLM including RAG content
        context = f"""
        Subject: {subject or 'General'}
        Difficulty: {difficulty.value}
        Question Count: {question_count}
        Question Types: {[qt.value for qt in question_types]}
        
        User Learning Focus:
        - Main topics: {list(focus_areas['topics'].keys())[:3]}
        - Weak areas: {focus_areas['weak_areas'][:3]}
        - Strong areas: {focus_areas['strong_areas'][:3]}
        
        RELEVANT COURSE CONTENT:
        {relevant_content}
        """
        
        system_prompt = """You are an expert educational assessment creator.
Generate quiz questions that are:
1. Based on the provided course content and materials
2. Educationally valuable and aligned with learning objectives
3. Appropriate for the specified difficulty level
4. Focused on the user's learning areas and gaps
5. Varied in format to maintain engagement

IMPORTANT: 
- Use the RELEVANT COURSE CONTENT provided to create questions that test understanding of the actual material
- If no course content is provided, create general questions about the subject
- Return ONLY a valid JSON array of question objects
- Do not include any other text, explanations, or formatting

The JSON structure must be exactly:
[
    {
        "id": "unique_id",
        "question": "question text based on course content",
        "question_type": "multiple_choice",
        "options": ["option1", "option2", "option3", "option4"],
        "correct_answer": "option1",
        "explanation": "explanation referencing the course material",
        "difficulty": "easy",
        "subject": "subject area",
        "tags": ["tag1", "tag2"]
    }
]

Valid question_type values: "multiple_choice", "true_false", "short_answer"
Valid difficulty values: "easy", "medium", "hard"
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
Generate {question_count} quiz questions based on this context:

{context}

Requirements:
- Create questions that test understanding of the course content provided
- Focus on creating questions that help reinforce learning in weak areas while building on strong areas
- Make sure questions are clear, unambiguous, and educationally valuable
- Base questions on the actual content from the documents when available
- If no specific content is provided, create general questions about {subject or 'the topic'}
""")
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            response_content = response.content.strip()
            
            # Try to extract JSON from the response
            # Sometimes LLM adds extra text before/after JSON
            json_start = response_content.find('[')
            json_end = response_content.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                # No JSON array found, try to find JSON object
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                if json_start != -1 and json_end > 0:
                    json_content = response_content[json_start:json_end]
                    # Wrap single object in array
                    json_content = f"[{json_content}]"
                else:
                    raise ValueError("No valid JSON found in response")
            else:
                json_content = response_content[json_start:json_end]
            
            logger.info(f"Extracted JSON content: {json_content[:200]}...")
            questions_data = json.loads(json_content)
            
            # Ensure it's a list
            if not isinstance(questions_data, list):
                questions_data = [questions_data]
            
            questions = []
            for i, q_data in enumerate(questions_data[:question_count]):
                try:
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
                except Exception as e:
                    logger.warning(f"Skipping malformed question {i}: {e}")
                    continue
            
            if not questions:
                # If no valid questions were parsed, use fallback
                logger.warning("No valid questions parsed from LLM response, using fallback")
                return self._create_fallback_questions(subject, difficulty, question_count)
            
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Response content: {response.content}")
            # Fallback: create simple questions
            return self._create_fallback_questions(subject, difficulty, question_count)
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
        
        # Create subject-specific sample questions
        subject_lower = (subject or "general").lower()
        
        sample_questions = {
            "mathematics": [
                {
                    "question": "What is 2 + 2?",
                    "options": ["3", "4", "5", "6"],
                    "correct_answer": "4",
                    "explanation": "2 + 2 equals 4 by basic arithmetic."
                },
                {
                    "question": "What is the square root of 16?",
                    "options": ["2", "3", "4", "5"],
                    "correct_answer": "4",
                    "explanation": "The square root of 16 is 4 because 4 × 4 = 16."
                }
            ],
            "science": [
                {
                    "question": "What is the chemical symbol for water?",
                    "options": ["H2O", "CO2", "NaCl", "O2"],
                    "correct_answer": "H2O",
                    "explanation": "Water is composed of two hydrogen atoms and one oxygen atom."
                },
                {
                    "question": "What planet is closest to the Sun?",
                    "options": ["Venus", "Earth", "Mercury", "Mars"],
                    "correct_answer": "Mercury",
                    "explanation": "Mercury is the closest planet to the Sun in our solar system."
                }
            ]
        }
        
        # Get appropriate questions for the subject
        if subject_lower in sample_questions:
            available_questions = sample_questions[subject_lower]
        else:
            available_questions = [
                {
                    "question": f"What is a key concept in {subject or 'this field'}?",
                    "options": ["Concept A", "Concept B", "Concept C", "Concept D"],
                    "correct_answer": "Concept A",
                    "explanation": f"This is a fundamental concept in {subject or 'this field'}."
                }
            ]
        
        for i in range(count):
            question_data = available_questions[i % len(available_questions)]
            question = QuizQuestion(
                id=str(uuid.uuid4()),
                question=question_data["question"],
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=question_data["options"],
                correct_answer=question_data["correct_answer"],
                explanation=question_data["explanation"],
                difficulty=difficulty,
                subject=subject or "general",
                tags=["fallback", subject_lower]
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