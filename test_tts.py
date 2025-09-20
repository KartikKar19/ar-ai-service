#!/usr/bin/env python3
"""
Simple test script for TTS functionality
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.services.tts_service import TTSService
from app.core.config import settings

async def test_tts():
    """Test TTS service functionality"""
    try:
        print("Testing TTS Service...")
        print(f"OpenAI API Key configured: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
        
        # Initialize TTS service
        tts_service = TTSService()
        
        # Test text
        test_text = "Hello! This is a test of the text-to-speech functionality for the AR learning platform."
        
        print(f"\nGenerating audio for: '{test_text}'")
        print(f"Voice: alloy")
        
        # Generate speech
        audio_base64 = await tts_service.generate_speech(
            text=test_text,
            voice="alloy"
        )
        
        if audio_base64:
            print(f"✅ TTS generation successful!")
            print(f"Audio data length: {len(audio_base64)} characters (base64)")
            print(f"Estimated audio file size: ~{len(audio_base64) * 3 // 4} bytes")
            
            # Test with different voice
            print(f"\nTesting with voice: nova")
            audio_base64_nova = await tts_service.generate_speech(
                text="This is the same text with a different voice.",
                voice="nova"
            )
            
            if audio_base64_nova:
                print(f"✅ Nova voice generation successful!")
                print(f"Audio data length: {len(audio_base64_nova)} characters (base64)")
            else:
                print("❌ Nova voice generation failed")
                
        else:
            print("❌ TTS generation failed")
            
    except Exception as e:
        print(f"❌ Error testing TTS: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tts())