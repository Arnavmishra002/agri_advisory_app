from gtts import gTTS
import os
from django.conf import settings

def convert_text_to_speech(text, lang='en'):
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        # Create a temporary file path for the audio
        audio_file_name = "speech.mp3"
        audio_file_path = os.path.join(settings.BASE_DIR, "media", audio_file_name)

        # Ensure the media directory exists
        os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)

        tts.save(audio_file_path)
        # Return the URL or path relative to MEDIA_URL
        return os.path.join(settings.MEDIA_URL, audio_file_name)
    except Exception as e:
        print(f"Error converting text to speech: {e}")
        return None
