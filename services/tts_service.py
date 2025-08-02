# services/tts_service.py
import os
import re
import tempfile
import hashlib
import logging
from typing import Optional, Dict
from pathlib import Path

from gtts import gTTS
from pydub import AudioSegment
from config.settings import settings, TTS_CONFIG

logger = logging.getLogger(__name__)

class TTSService:
    """Enhanced Text-to-Speech service with caching and audio processing"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "ai_tutor_audio"
        self.temp_dir.mkdir(exist_ok=True)
        self.cache = {}  # In-memory cache for file paths
        
    def clean_text_for_speech(self, text: str) -> str:
        """Clean text for better speech synthesis"""
        if not text:
            return ""
        
        # Remove emojis and special characters
        for char in TTS_CONFIG["excluded_chars"]:
            text = text.replace(char, "")
        
        # Apply cleanup patterns
        for pattern, replacement in TTS_CONFIG["cleanup_patterns"]:
            text = re.sub(pattern, replacement, text)
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Replace some markdown-style formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
        text = re.sub(r'`([^`]+)`', r'\1', text)        # Code
        text = re.sub(r'#{1,6}\s*', '', text)           # Headers
        
        # Handle lists
        text = re.sub(r'^[-•]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
        
        # Clean up mathematical expressions
        text = re.sub(r'\$([^$]+)\$', r'\1', text)
        
        return text.strip()
    
    def generate_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        cleaned_text = self.clean_text_for_speech(text)
        return hashlib.md5(cleaned_text.encode()).hexdigest()[:12]
    
    def text_to_speech(self, text: str, language: str = None, slow: bool = False) -> Optional[str]:
        """Convert text to speech with caching"""
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for TTS")
                return None
            
            # Use configured language if not specified
            if language is None:
                language = settings.tts_language
            
            # Clean the text
            cleaned_text = self.clean_text_for_speech(text)
            if not cleaned_text:
                logger.warning("No content left after cleaning text for TTS")
                return None
            
            # Check cache
            cache_key = self.generate_cache_key(cleaned_text)
            if cache_key in self.cache and os.path.exists(self.cache[cache_key]):
                logger.debug(f"Using cached audio: {cache_key}")
                return self.cache[cache_key]
            
            # Generate filename
            filename = f"speech_{cache_key}.mp3"
            file_path = self.temp_dir / filename
            
            # Generate speech
            logger.debug(f"Generating TTS for: {cleaned_text[:50]}...")
            tts = gTTS(
                text=cleaned_text,
                lang=language,
                slow=slow
            )
            
            # Save to temporary file
            temp_path = file_path.with_suffix('.tmp')
            tts.save(str(temp_path))
            
            # Process audio if needed (adjust speed, volume, etc.)
            if settings.tts_speed != 1.0:
                audio = AudioSegment.from_mp3(str(temp_path))
                
                # Adjust playback speed
                if settings.tts_speed != 1.0:
                    # Change frame rate to adjust speed
                    new_sample_rate = int(audio.frame_rate * settings.tts_speed)
                    audio = audio._spawn(audio.raw_data, overrides={
                        "frame_rate": new_sample_rate
                    }).set_frame_rate(audio.frame_rate)
                
                audio.export(str(file_path), format="mp3")
                os.remove(temp_path)
            else:
                # Move temp file to final location
                temp_path.rename(file_path)
            
            # Cache the result
            self.cache[cache_key] = str(file_path)
            
            logger.debug(f"Generated TTS audio: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            # Clean up any partial files
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    os.remove(temp_path)
                except:
                    pass
            if 'file_path' in locals() and file_path.exists():
                try:
                    os.remove(file_path)
                except:
                    pass
            return None
    
    def cleanup_file(self, file_path: str) -> None:
        """Clean up a specific audio file"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                
                # Remove from cache
                cache_key = None
                for key, path in self.cache.items():
                    if path == file_path:
                        cache_key = key
                        break
                
                if cache_key:
                    del self.cache[cache_key]
                
                logger.debug(f"Cleaned up audio file: {file_path}")
                
        except Exception as e:
            logger.error(f"File cleanup error: {e}")
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> None:
        """Clean up old audio files"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            files_removed = 0
            for file_path in self.temp_dir.glob("speech_*.mp3"):
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        files_removed += 1
                        
                        # Remove from cache
                        cache_key = None
                        for key, path in self.cache.items():
                            if path == str(file_path):
                                cache_key = key
                                break
                        
                        if cache_key:
                            del self.cache[cache_key]
                            
                except Exception as e:
                    logger.error(f"Error removing old file {file_path}: {e}")
            
            if files_removed > 0:
                logger.info(f"Cleaned up {files_removed} old audio files")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def cleanup_all(self) -> None:
        """Clean up all generated audio files"""
        try:
            files_removed = 0
            for file_path in self.temp_dir.glob("speech_*.mp3"):
                try:
                    file_path.unlink()
                    files_removed += 1
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {e}")
            
            # Clear cache
            self.cache.clear()
            
            logger.info(f"Cleaned up {files_removed} audio files")
            
        except Exception as e:
            logger.error(f"Full cleanup error: {e}")
    
    def get_cache_info(self) -> Dict:
        """Get information about the current cache"""
        return {
            "cached_files": len(self.cache),
            "temp_directory": str(self.temp_dir),
            "total_files": len(list(self.temp_dir.glob("speech_*.mp3")))
        }

# Global TTS service instance
tts_service = TTSService()