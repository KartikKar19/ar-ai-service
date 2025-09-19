from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os

API_KEY = os.getenv("API_KEY", "your-very-secure-secret-key")  # Use .env in production
api_key_header_auth = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header_auth)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return {"user_id": "api_key_user"}
