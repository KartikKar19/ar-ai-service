import io
import base64
from typing import Optional
from openai import AsyncOpenAI
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def generate_speech(
        self, 
        text: str, 
        voice: str = "alloy",
        model: str = "tts-1",
        response_format: str = "mp3"
    ) -> Optional[str]:
        """
        Generate speech from text using OpenAI TTS
        Returns base64 encoded audio data
        """
        try:
            # Limit text length for TTS (OpenAI has a 4096 character limit)
            if len(text) > 4000:
                text = text[:4000] + "..."
                logger.warning("Text truncated for TTS due to length limit")
            
            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format=response_format
            )
            
            # Get audio content as bytes
            audio_content = response.content
            
            # Convert to base64 for JSON response
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
            
            logger.info(f"Generated TTS audio for {len(text)} characters using voice '{voice}'")
            return audio_base64
            
        except Exception as e:
            logger.error(f"Error generating TTS audio: {e}")
            return None
    
    async def generate_speech_file(
        self, 
        text: str, 
        output_path: str,
        voice: str = "alloy",
        model: str = "tts-1"
    ) -> bool:
        """
        Generate speech and save to file
        Returns True if successful, False otherwise
        """
        try:
            if len(text) > 4000:
                text = text[:4000] + "..."
                logger.warning("Text truncated for TTS due to length limit")
            
            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            
            # Save to file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"TTS audio saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating TTS file: {e}")
            return False

# Global TTS service instance
tts_service = TTSService()