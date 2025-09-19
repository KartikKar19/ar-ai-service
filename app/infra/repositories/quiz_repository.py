from fastapi import Depends
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.infra.db.mongo import get_db

class QuizRepository:
    def __init__(self, db):
        self.quizzes = db["quizzes"]
        self.attempts = db["quiz_attempts"]
        self.user_interactions = db["user_interactions"]
    
    async def create_quiz(self, quiz_data: Dict[str, Any]) -> ObjectId:
        now = datetime.now(timezone.utc)
        quiz_data.update({
            "created_at": now,
            "updated_at": now
        })
        result = await self.quizzes.insert_one(quiz_data)
        return result.inserted_id
    
    async def get_quiz(self, quiz_id: ObjectId) -> Optional[Dict[str, Any]]:
        return await self.quizzes.find_one({"_id": quiz_id})
    
    async def get_user_quizzes(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.quizzes.find({"generated_for_user": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=None)
    
    async def create_attempt(self, attempt_data: Dict[str, Any]) -> ObjectId:
        now = datetime.now(timezone.utc)
        attempt_data.update({
            "started_at": now,
            "created_at": now
        })
        result = await self.attempts.insert_one(attempt_data)
        return result.inserted_id
    
    async def update_attempt(self, attempt_id: ObjectId, update_data: Dict[str, Any]):
        update_data["updated_at"] = datetime.now(timezone.utc)
        await self.attempts.update_one(
            {"_id": attempt_id},
            {"$set": update_data}
        )
    
    async def get_attempt(self, attempt_id: ObjectId) -> Optional[Dict[str, Any]]:
        return await self.attempts.find_one({"_id": attempt_id})
    
    async def get_user_attempts(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.attempts.find({"user_id": user_id}).sort("started_at", -1)
        return await cursor.to_list(length=None)
    
    async def log_user_interaction(self, interaction_data: Dict[str, Any]):
        interaction_data["timestamp"] = datetime.now(timezone.utc)
        await self.user_interactions.insert_one(interaction_data)
    
    async def get_user_interactions(
        self, 
        user_id: str, 
        limit: int = 100,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = {"user_id": user_id}
        if subject:
            query["subject"] = subject
        
        cursor = self.user_interactions.find(query).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=None)
    
    @staticmethod
    def dep(db=Depends(get_db)):
        return QuizRepository(db)