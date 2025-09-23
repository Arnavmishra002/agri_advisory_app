import React, { useState, useEffect } from 'react';
import axios from 'axios';

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}

interface SpeechRecognitionEvent extends Event {
  readonly results: SpeechRecognitionResultList;
  readonly resultIndex: number;
  readonly interpretation: any;
  readonly emma: Document | null;
}

interface SpeechRecognitionResultList {
  [index: number]: SpeechRecognitionResult;
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  [index: number]: SpeechRecognitionAlternative;
  readonly length: number;
  isFinal: boolean;
  item(index: number): SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  readonly error: SpeechRecognitionErrorCode;
  readonly message: string;
}

type SpeechRecognitionErrorCode =
  | "no-speech"
  | "aborted"
  | "audio-capture"
  | "network"
  | "not-allowed"
  | "service-not-allowed"
  | "bad-grammar"
  | "language-not-supported";

interface Message {
  text: string;
  sender: 'user' | 'bot';
}

interface ChatbotProps {
  language: string;
}

const Chatbot: React.FC<ChatbotProps> = ({ language }) => {
  const [messages, setMessages] = useState<Message[]>(
    [{ text: language === 'hi' ? "नमस्ते! मैं कृषि मित्र हूँ। आज मैं आपकी कैसे सहायता कर सकता हूँ?" : "Hello! I'm Krishimitra. How can I help you today?", sender: 'bot' }]
  );
  const [inputText, setInputText] = useState<string>('');
  const [isListening, setIsListening] = useState<boolean>(false);
  const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api/advisories/chatbot/';

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = React.useMemo(() => SpeechRecognition ? new SpeechRecognition() : null, [SpeechRecognition]);

  useEffect(() => {
    // Reset greeting message when language changes
    const initialGreeting = language === 'hi' 
      ? "नमस्ते! मैं कृषि मित्र हूँ। आज मैं आपकी कैसे सहायता कर सकता हूँ?" 
      : "Hello! I'm Krishimitra. How can I help you today?";
    setMessages([{ text: initialGreeting, sender: 'bot' }]);
  }, [language]);

  useEffect(() => {
    if (recognition) {
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = Array.from(event.results)
          .map((result: SpeechRecognitionResult) => result[0])
          .map((result) => result.transcript)
          .join('');
        setInputText(transcript);
        setIsListening(false);
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error("Speech recognition error", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };
    }
  }, [language, recognition]);

  const handleSendMessage = async () => {
    if (inputText.trim() === '') return;

    const newUserMessage: Message = { text: inputText, sender: 'user' };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setInputText('');

    try {
      const response = await axios.post(API_URL, {
        query: inputText,
        language: language, // Send selected language to backend
      });
      const botResponse: Message = { text: response.data.response, sender: 'bot' };
      setMessages((prevMessages) => [...prevMessages, botResponse]);
    } catch (error) {
      console.error("Error fetching chatbot response:", error);
      const errorMessageText = language === 'hi'
        ? "क्षमा करें, मुझे सलाहकार सेवा से जुड़ने में समस्या हो रही है। कृपया बाद में पुनः प्रयास करें।"
        : "Sorry, I'm having trouble connecting to the advisory service. Please try again later.";
      const errorMessage: Message = { text: errorMessageText, sender: 'bot' };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    }
  };

  const toggleListening = () => {
    if (recognition) {
      if (isListening) {
        recognition.stop();
        setIsListening(false);
      } else {
        recognition.start();
        setIsListening(true);
      }
    } else {
      alert(language === 'hi' ? "आपके ब्राउज़र में स्पीच रिकॉग्निशन समर्थित नहीं है।" : "Speech recognition is not supported in your browser.");
    }
  };

  return (
    <div className="chat-container">
      <div className="message-list">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleSendMessage();
            }
          }}
          placeholder={language === 'hi' ? "अपनी कृषि संबंधी प्रश्न पूछें..." : "Ask your agricultural query..."}
        />
        <button onClick={toggleListening} className={isListening ? 'listening' : ''} disabled={!recognition}>
          {isListening ? (language === 'hi' ? "सुन रहा है..." : "Listening...") : (language === 'hi' ? "वॉयस इनपुट" : "Voice Input")}
        </button>
        <button onClick={handleSendMessage}>
          {language === 'hi' ? "भेजें" : "Send"}
        </button>
      </div>
    </div>
  );
};

export default Chatbot;
