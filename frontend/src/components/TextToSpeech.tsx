import React, { useState } from 'react';
import axios from 'axios';

interface TextToSpeechProps {
  language: string;
}

const TextToSpeech: React.FC<TextToSpeechProps> = ({ language }) => {
  const [text, setText] = useState<string>('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(event.target.value);
  };

  const handleSpeak = async () => {
    if (text.trim() === '') {
      setError(language === 'hi' ? "कृपया बोलने के लिए कुछ टेक्स्ट दर्ज करें।" : "Please enter some text to convert to speech.");
      return;
    }
    setLoading(true);
    setError(null);
    setAudioUrl(null);

    try {
      const response = await axios.post(
        `http://localhost:8000/api/text-to-speech/speak/`,
        { text: text, language: language }, // Pass language to backend
        { responseType: 'json' }
      );
      if (response.data && response.data.audio_url) {
        setAudioUrl(response.data.audio_url);
      } else {
        setError(language === 'hi' ? "सर्वर से कोई ऑडियो यूआरएल प्राप्त नहीं हुआ।" : "No audio URL received from the server.");
      }
    } catch (err) {
      setError(language === 'hi' ? "टेक्स्ट को भाषण में बदलने में विफल रहा।" : "Failed to convert text to speech.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-to-speech-widget">
      <h2>{language === 'hi' ? "टेक्स्ट टू वॉयस" : "Text to Voice"}</h2>
      <textarea
        value={text}
        onChange={handleTextChange}
        placeholder={language === 'hi' ? "बोलने के लिए टेक्स्ट दर्ज करें..." : "Enter text to convert to speech..."}
        rows={4}
        cols={50}
      />
      <button onClick={handleSpeak} disabled={loading}>
        {loading ? (language === 'hi' ? "जेनरेट हो रहा है..." : "Generating...") : (language === 'hi' ? "बोलें" : "Speak")}
      </button>
      {error && <p className="error-message">{error}</p>}
      {audioUrl && (
        <audio controls autoPlay src={audioUrl}>
          {language === 'hi' ? "आपका ब्राउज़र ऑडियो तत्व का समर्थन नहीं करता है।" : "Your browser does not support the audio element."}
        </audio>
      )}
    </div>
  );
};

export default TextToSpeech;
