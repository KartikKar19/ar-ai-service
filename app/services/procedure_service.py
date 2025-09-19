import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

from app.domain.dtos.procedure import (
    ProcedureOut, ProcedureStep, UserProcedureSession, 
    StepStatus, StepValidationRequest, StepValidationResponse
)
from app.infra.db.neo4j_client import neo4j_client
from app.infra.repositories.quiz_repository import QuizRepository

logger = logging.getLogger(__name__)

class ProcedureService:
    def __init__(self):
        pass
    
    async def get_procedure(self, procedure_id: str) -> Optional[ProcedureOut]:
        """Get procedure details from knowledge graph"""
        try:
            # This would typically query Neo4j for procedure details
            # For now, return a sample procedure
            return self._get_sample_procedure(procedure_id)
        except Exception as e:
            logger.error(f"Error getting procedure {procedure_id}: {e}")
            return None
    
    async def start_procedure_session(
        self, 
        procedure_id: str, 
        user_id: str,
        quiz_repo: QuizRepository
    ) -> UserProcedureSession:
        """Start a new procedure session for user"""
        try:
            procedure = await self.get_procedure(procedure_id)
            if not procedure:
                raise ValueError("Procedure not found")
            
            session_id = str(uuid.uuid4())
            
            # Initialize step statuses
            step_statuses = {}
            for step in procedure.steps:
                step_statuses[step.id] = StepStatus.PENDING
            
            # Mark first step as active
            if procedure.steps:
                step_statuses[procedure.steps[0].id] = StepStatus.ACTIVE
            
            session = UserProcedureSession(
                id=session_id,
                procedure_id=procedure_id,
                user_id=user_id,
                current_step=0,
                step_statuses=step_statuses,
                started_at=datetime.now(timezone.utc).isoformat()
            )
            
            # Log interaction
            await quiz_repo.log_user_interaction({
                "user_id": user_id,
                "type": "procedure_started",
                "procedure_id": procedure_id,
                "session_id": session_id,
                "subject": procedure.subject
            })
            
            return session
            
        except Exception as e:
            logger.error(f"Error starting procedure session: {e}")
            raise
    
    async def validate_step(
        self, 
        request: StepValidationRequest,
        quiz_repo: QuizRepository
    ) -> StepValidationResponse:
        """Validate user action for a procedure step"""
        try:
            # Get session info (in real implementation, this would be stored in DB)
            # For now, we'll use Neo4j to validate the step
            
            validation_result = await neo4j_client.validate_step_action(
                request.step_id, 
                request.user_action
            )
            
            is_correct = validation_result.get("valid", False)
            feedback = validation_result.get("message", "")
            
            # Generate hints if action is incorrect
            hints = []
            if not is_correct:
                hints = [
                    "Look carefully at the component you selected",
                    "Check the instruction again",
                    "Try identifying the correct part based on its position"
                ]
            
            # Log interaction
            await quiz_repo.log_user_interaction({
                "user_id": "current_user",  # Would get from session
                "type": "step_validation",
                "session_id": request.session_id,
                "step_id": request.step_id,
                "action": request.user_action,
                "correct": is_correct
            })
            
            # Get next step if current is correct
            next_step = None
            if is_correct:
                next_step = self._get_next_step(request.step_id)
            
            return StepValidationResponse(
                is_correct=is_correct,
                feedback=feedback,
                hints=hints,
                next_step=next_step
            )
            
        except Exception as e:
            logger.error(f"Error validating step: {e}")
            return StepValidationResponse(
                is_correct=False,
                feedback="Error validating your action. Please try again.",
                hints=["Please try again"]
            )
    
    def _get_sample_procedure(self, procedure_id: str) -> ProcedureOut:
        """Return sample procedure for demonstration"""
        steps = [
            ProcedureStep(
                id="step_1",
                title="Identify the Compressor",
                description="Locate and select the compressor stage of the jet engine",
                instruction="Look for the fan-like component at the front of the engine",
                expected_action="select_compressor",
                hints=[
                    "The compressor is at the front of the engine",
                    "It looks like a large fan with multiple blades",
                    "It's the first major component air encounters"
                ],
                validation_criteria={"component_type": "compressor"},
                order=1
            ),
            ProcedureStep(
                id="step_2",
                title="Identify the Combustion Chamber",
                description="Locate the combustion chamber where fuel is burned",
                instruction="Find the chamber where fuel mixing and ignition occurs",
                expected_action="select_combustion_chamber",
                hints=[
                    "Located after the compressor",
                    "This is where fuel is injected and burned",
                    "Look for the cylindrical chamber in the middle"
                ],
                validation_criteria={"component_type": "combustion_chamber"},
                order=2
            ),
            ProcedureStep(
                id="step_3",
                title="Identify the Turbine",
                description="Locate the turbine that extracts energy from hot gases",
                instruction="Find the component that converts gas energy to rotational energy",
                expected_action="select_turbine",
                hints=[
                    "Located after the combustion chamber",
                    "Connected to the compressor via a shaft",
                    "Has curved blades to capture gas flow energy"
                ],
                validation_criteria={"component_type": "turbine"},
                order=3
            )
        ]
        
        return ProcedureOut(
            id=procedure_id,
            title="Jet Engine Component Identification",
            description="Learn to identify the main components of a jet engine",
            subject="Engineering",
            difficulty_level="Beginner",
            estimated_duration=15,
            steps=steps,
            created_by="system"
        )
    
    def _get_next_step(self, current_step_id: str) -> Optional[ProcedureStep]:
        """Get the next step in the procedure"""
        # This is a simplified implementation
        # In reality, this would query the knowledge graph
        step_order = {
            "step_1": "step_2",
            "step_2": "step_3",
            "step_3": None
        }
        
        next_step_id = step_order.get(current_step_id)
        if next_step_id:
            # Return next step details (simplified)
            sample_procedure = self._get_sample_procedure("sample")
            for step in sample_procedure.steps:
                if step.id == next_step_id:
                    return step
        
        return None

# Global procedure service instance
procedure_service = ProcedureService()