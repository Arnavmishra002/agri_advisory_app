import React, { useState } from 'react';
import './App.css';

interface Message {
  text: string;
  sender: 'user' | 'bot';
}

function App() {
  const [messages, setMessages] = useState<Message[]>(
    [{ text: "Hello! I'm Krishimitra. How can I help you today?", sender: 'bot' }]
  );
  const [inputText, setInputText] = useState<string>('');
  const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api/advisories/chatbot/';

  const handleSendMessage = async () => {
    if (inputText.trim() === '') return;

    const newUserMessage: Message = { text: inputText, sender: 'user' };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setInputText('');

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: inputText }),
      });
      const data = await response.json();
      const botResponse: Message = { text: data.response, sender: 'bot' };
      setMessages((prevMessages) => [...prevMessages, botResponse]);
    } catch (error) {
      console.error("Error fetching chatbot response:", error);
      const errorMessage: Message = { text: "Sorry, I'm having trouble connecting to the advisory service. Please try again later.", sender: 'bot' };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Krishimitra</h1>
      </header>
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
            placeholder="Ask your agricultural query..."
          />
          <button onClick={handleSendMessage}>Send</button>
        </div>
      </div>
    </div>
  );
}

export default App;
