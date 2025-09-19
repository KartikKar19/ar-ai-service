from fastapi import APIRouter, HTTPException
from app.infra.db.mongo import get_db
from app.infra.db.chroma_client import chroma_client

router = APIRouter()

@router.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "ai-service"}

@router.get("/readyz")
async def readyz():
    """Check if all dependencies are ready"""
    try:
        # Check MongoDB
        db = get_db()
        await db.command("ping")
        
        # Check ChromaDB
        stats = chroma_client.get_collection_stats()
        
        return {
            "status": "ready",
            "mongodb": "connected",
            "chromadb": "connected",
            "vector_store_docs": stats.get("total_documents", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {e}")