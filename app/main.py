from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.router import api_router
from app.core.logging import configure_logging
from app.core.config import settings
from app.infra.db.mongo import init_client, close_client
from app.infra.db.chroma_client import chroma_client
from app.infra.db.neo4j_client import neo4j_client

def create_app() -> FastAPI:
    configure_logging()
    
    app = FastAPI(
        title="AR-Learn AI Service",
        description="AI service with RAG pipeline, document ingestion, and adaptive learning features",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(api_router, prefix="/v1")
    
    @app.on_event("startup")
    async def startup_event():
        # Initialize databases
        await init_client()
        await chroma_client.connect()
        await neo4j_client.connect()
        
        # Create upload directory
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        print(f"AI Service started on port with the following configuration:")
        print(f"- MongoDB: {settings.MONGO_URI}")
        print(f"- ChromaDB: {settings.CHROMA_PERSIST_DIR}")
        print(f"- Neo4j: {settings.NEO4J_URI}")
        print(f"- Upload directory: {settings.UPLOAD_DIR}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        await close_client()
        await neo4j_client.close()
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)