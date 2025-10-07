import logging
from django.conf import settings
import os

# Optional gTTS import to prevent crashes if module is not available
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("Warning: gTTS module not available. Text-to-speech functionality disabled.")

logger = logging.getLogger(__name__)

def convert_text_to_speech(text: str, lang: str = 'en') -> str | None:
    """
    Converts text to speech using Google Text-to-Speech (gTTS).
    Saves the audio file and returns its URL.
    """
    if not GTTS_AVAILABLE:
        logger.warning("gTTS module not available. Text-to-speech functionality disabled.")
        return None
        
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        # Ensure media directory exists
        media_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        os.makedirs(media_dir, exist_ok=True)
        
        audio_filename = f"tts_{lang}_{hash(text)}.mp3"
        audio_filepath = os.path.join(media_dir, audio_filename)
        tts.save(audio_filepath)
        
        audio_url = os.path.join(settings.MEDIA_URL, 'audio', audio_filename)
        logger.info(f"Text-to-speech generated for language {lang}. URL: {audio_url}")
        return audio_url
    except Exception as e:
        logger.error(f"Error converting text to speech for language {lang}: {e}")
        return None
