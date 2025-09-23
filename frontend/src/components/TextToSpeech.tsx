import React, { useState } from 'react';
import axios from 'axios';

const TextToSpeech: React.FC = () => {
  const [text, setText] = useState<string>('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(event.target.value);
  };

  const handleSpeak = async () => {
    if (text.trim() === '') {
      setError("Please enter some text to convert to speech.");
      return;
    }
    setLoading(true);
    setError(null);
    setAudioUrl(null);

    try {
      const response = await axios.post(
        `http://localhost:8000/api/text-to-speech/speak/`,
        { text: text },
        { responseType: 'json' } // Ensure response is treated as JSON
      );
      if (response.data && response.data.audio_url) {
        setAudioUrl(response.data.audio_url);
      } else {
        setError("No audio URL received from the server.");
      }
    } catch (err) {
      setError("Failed to convert text to speech.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-to-speech-widget">
      <h2>Text to Voice</h2>
      <textarea
        value={text}
        onChange={handleTextChange}
        placeholder="Enter text to convert to speech..."
        rows={4}
        cols={50}
      />
      <button onClick={handleSpeak} disabled={loading}>
        {loading ? "Generating..." : "Speak"}
      </button>
      {error && <p className="error-message">{error}</p>}
      {audioUrl && (
        <audio controls autoPlay src={audioUrl}>
          Your browser does not support the audio element.
        </audio>
      )}
    </div>
  );
};

export default TextToSpeech;
