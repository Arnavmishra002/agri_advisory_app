import React, { useState, useEffect } from 'react';
import axios from 'axios';
import FeedbackCollector from './FeedbackCollector';

interface Message {
  text: string;
  sender: 'user' | 'bot';
  ml_enhanced?: boolean;
  prediction_data?: any;
  session_id?: string;
}

interface ChatbotProps {
  language: string;
}

const Chatbot: React.FC<ChatbotProps> = ({ language }) => {
  const [messages, setMessages] = useState<Message[]>(
    [{ text: language === 'hi' ? "नमस्ते! मैं कृषि मित्र हूँ। मैं आपको फसल की सिफारिश, मिट्टी और मौसम के आधार पर सलाह दे सकता हूँ।" : "Hello! I'm Krishimitra. I can help you with crop recommendations, soil analysis, and weather-based farming advice.", sender: 'bot' }]
  );
  const [inputText, setInputText] = useState<string>('');
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isLoadingBotResponse, setIsLoadingBotResponse] = useState<boolean>(false);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [userId, setUserId] = useState<string>('');
  const [showFeedback, setShowFeedback] = useState<boolean>(false);
  const [lastPrediction, setLastPrediction] = useState<any>(null);
  const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api/advisories/chatbot/';

  // @ts-ignore
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = React.useMemo(() => SpeechRecognition ? new SpeechRecognition() : null, [SpeechRecognition]);
  const messagesEndRef = React.useRef<HTMLDivElement>(null); // Ref for scrolling

  useEffect(() => {
    // Generate unique user ID and session ID
    const generatedUserId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const generatedSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setUserId(generatedUserId);
    setCurrentSessionId(generatedSessionId);
    
    // Reset greeting message when language changes
    const initialGreeting = language === 'hi' 
      ? "नमस्ते! मैं कृषि मित्र हूँ। मैं आपको फसल की सिफारिश, मिट्टी और मौसम के आधार पर सलाह दे सकता हूँ।" 
      : "Hello! I'm Krishimitra. I can help you with crop recommendations, soil analysis, and weather-based farming advice.";
    setMessages([{ text: initialGreeting, sender: 'bot' }]);
  }, [language]);

  useEffect(() => {
    if (recognition) {
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';

      // @ts-ignore
      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = Array.from(event.results as unknown as SpeechRecognitionResult[])
          .map((result) => result[0])
          .map((result) => result.transcript)
          .join('');
        setInputText(transcript);
        setIsListening(false);
      };

      // @ts-ignore
      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error("Speech recognition error", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };
    }
  }, [language, recognition]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoadingBotResponse]); // Scroll when messages or loading state changes

  const handleSendMessage = async () => {
    if (inputText.trim() === '') return;

    const newUserMessage: Message = { text: inputText, sender: 'user' };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setInputText('');
    setIsLoadingBotResponse(true); // Set loading to true

    try {
      const response = await axios.post(API_URL, {
        query: inputText,
        language: language,
        user_id: userId,
        session_id: currentSessionId
      });
      
      const botResponse: Message = { 
        text: response.data.response, 
        sender: 'bot',
        ml_enhanced: response.data.ml_enhanced,
        session_id: response.data.session_id
      };
      
      setMessages((prevMessages) => [...prevMessages, botResponse]);
      
      // Check if this is a prediction that can be rated
      if (response.data.ml_enhanced && (inputText.toLowerCase().includes('crop') || inputText.toLowerCase().includes('fertilizer'))) {
        setLastPrediction({
          prediction_type: inputText.toLowerCase().includes('crop') ? 'crop_recommendation' : 'fertilizer_recommendation',
          input_data: { query: inputText, language: language },
          system_prediction: response.data.response
        });
        setShowFeedback(true);
      }
    } catch (error) {
      console.error("Error fetching chatbot response:", error);
      const errorMessageText = language === 'hi'
        ? "क्षमा करें, मुझे सलाहकार सेवा से जुड़ने में समस्या हो रही है। कृपया बाद में पुनः प्रयास करें।"
        : "Sorry, I'm having trouble connecting to the advisory service. Please try again later.";
      const errorMessage: Message = { text: errorMessageText, sender: 'bot' };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setIsLoadingBotResponse(false); // Set loading to false
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
            <div className="message-content">
              {msg.text}
              {msg.ml_enhanced && (
                <div className="ml-badge">
                  {language === 'hi' ? 'ML संवर्धित' : 'ML Enhanced'}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoadingBotResponse && (
          <div className="message bot loading-message">
            <span>.</span><span>.</span><span>.</span>
          </div>
        )}
        <div ref={messagesEndRef} /> {/* Element to scroll to */}
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
          placeholder={language === 'hi' ? "फसल सिफारिश, मिट्टी या मौसम के बारे में पूछें..." : "Ask about crop recommendations, soil, or weather..."}
        />
        <button onClick={toggleListening} className={isListening ? 'listening' : ''} disabled={!recognition}>
          {isListening ? (language === 'hi' ? "सुन रहा है..." : "Listening...") : (language === 'hi' ? "वॉयस इनपुट" : "Voice Input")}
        </button>
        <button onClick={handleSendMessage}>
          {language === 'hi' ? "भेजें" : "Send"}
        </button>
      </div>
      
      {showFeedback && lastPrediction && (
        <div className="feedback-section">
          <FeedbackCollector
            user_id={userId}
            session_id={currentSessionId}
            prediction_type={lastPrediction.prediction_type}
            input_data={lastPrediction.input_data}
            system_prediction={lastPrediction.system_prediction}
            language={language}
            onFeedbackSubmitted={() => {
              setShowFeedback(false);
              setLastPrediction(null);
            }}
          />
        </div>
      )}
    </div>
  );
};

export default Chatbot;
