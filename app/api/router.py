from fastapi import APIRouter
from app.api.controllers.health_controller import router as health_router
from app.api.controllers.document_controller import router as document_router
from app.api.controllers.query_controller import router as query_router
from app.api.controllers.procedure_controller import router as procedure_router
from app.api.controllers.quiz_controller import router as quiz_router

api_router = APIRouter()

# Health checks
api_router.include_router(health_router, tags=["health"])

# Main features
api_router.include_router(document_router, prefix="/documents", tags=["documents"])
api_router.include_router(query_router, prefix="/query", tags=["query"])
api_router.include_router(procedure_router, prefix="/procedures", tags=["procedures"])
api_router.include_router(quiz_router, prefix="/quiz", tags=["quiz"])