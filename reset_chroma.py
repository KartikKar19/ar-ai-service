#!/usr/bin/env python3
"""
Script to reset ChromaDB collection with correct embedding dimensions
Run this if you're still getting embedding dimension errors
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.infra.db.chroma_client import chroma_client
from app.core.config import settings

async def reset_collection():
    """Reset the ChromaDB collection"""
    try:
        print("🔄 Resetting ChromaDB collection...")
        await chroma_client.connect()
        print("✅ ChromaDB collection reset successfully!")
        print(f"📊 Collection stats: {chroma_client.get_collection_stats()}")
        print("\n⚠️  Note: You'll need to re-upload your documents now.")
    except Exception as e:
        print(f"❌ Error resetting collection: {e}")

if __name__ == "__main__":
    print("🔧 ChromaDB Collection Reset Tool")
    print("=================================")
    print(f"📁 ChromaDB directory: {settings.CHROMA_PERSIST_DIR}")
    print(f"🤖 Embedding model: {settings.EMBEDDING_MODEL}")
    print()
    
    asyncio.run(reset_collection())