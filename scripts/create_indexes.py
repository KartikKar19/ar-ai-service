"""
Script to create MongoDB indexes for the AI service
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def create_indexes():
    load_dotenv(".env")
    
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB", "arhack_ai")
    
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    
    # Documents collection indexes
    await db["documents"].create_index("uploaded_by")
    await db["documents"].create_index("status")
    await db["documents"].create_index("subject")
    await db["documents"].create_index("created_at")
    await db["documents"].create_index([("title", "text"), ("description", "text")])
    
    # Chunks collection indexes
    await db["chunks"].create_index("document_id")
    await db["chunks"].create_index("chunk_index")
    
    # Quizzes collection indexes
    await db["quizzes"].create_index("generated_for_user")
    await db["quizzes"].create_index("created_at")
    await db["quizzes"].create_index("expires_at")
    
    # Quiz attempts collection indexes
    await db["quiz_attempts"].create_index("user_id")
    await db["quiz_attempts"].create_index("quiz_id")
    await db["quiz_attempts"].create_index("started_at")
    
    # User interactions collection indexes
    await db["user_interactions"].create_index("user_id")
    await db["user_interactions"].create_index("timestamp")
    await db["user_interactions"].create_index("type")
    await db["user_interactions"].create_index("subject")
    
    print("MongoDB indexes created successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())