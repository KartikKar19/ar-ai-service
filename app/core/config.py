from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Extra
from dotenv import load_dotenv
load_dotenv()  # Load .env file if it exists
class Settings(BaseSettings):
    # Database
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "arhack_ai"
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    # OpenAI
    OPENAI_API_KEY: str  # Will be loaded from .env file
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Auth Service
    AUTH_SERVICE_URL: str = "http://localhost:8001"
    JWT_SECRET: str = "change-me"
    
    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "./uploads"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # ✅ Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra=Extra.allow  # allows extra keys like AUTH0_CLIENT_ID in .env
    )

    # Redis / Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

settings = Settings()
