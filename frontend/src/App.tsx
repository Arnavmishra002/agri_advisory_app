import React, { useState } from 'react';
import logo from './logo.svg';
import './App.css';
import WeatherDisplay from './components/WeatherDisplay';
import TextToSpeech from './components/TextToSpeech';
import MarketPricesDisplay from './components/MarketPricesDisplay';
import Chatbot from './components/Chatbot';
import ImageUpload from './components/ImageUpload';

function App() {
  const [language, setLanguage] = useState<string>('en');

  const handleLanguageChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setLanguage(event.target.value);
  };

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.tsx</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
        <div className="language-selector">
          <label htmlFor="language-select">Language: </label>
          <select id="language-select" onChange={handleLanguageChange} value={language}>
            <option value="en">English</option>
            <option value="hi">हिंदी</option>
          </select>
        </div>
      </header>
      <main>
        <WeatherDisplay />
        <TextToSpeech language={language} />
        <MarketPricesDisplay />
        <Chatbot language={language} />
        <ImageUpload language={language} />
      </main>
    </div>
  );
}

export default App;
