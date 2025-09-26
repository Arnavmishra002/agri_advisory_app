import React, { useState, useEffect } from 'react';
import './App.css';
import WeatherDisplay from './components/WeatherDisplay';
import MarketPricesDisplay from './components/MarketPricesDisplay';
import Chatbot from './components/Chatbot';
import TrendingCropsDisplay from './components/TrendingCropsDisplay';

function App() {
  const [language, setLanguage] = useState<string>('en');
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLatitude(position.coords.latitude);
          setLongitude(position.coords.longitude);
        },
        (error) => {
          console.error("Error getting geolocation:", error);
          // Optionally set default location or show an error message
        }
      );
    } else {
      console.log("Geolocation is not supported by this browser.");
      // Optionally set default location or show a message
    }
  }, []);

  const handleLanguageChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setLanguage(event.target.value);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>Krishimitra</h1>
        <div className="language-selector">
          <label htmlFor="language-select">Language: </label>
          <select id="language-select" onChange={handleLanguageChange} value={language}>
            <option value="en">English</option>
            <option value="hi">हिंदी</option>
          </select>
        </div>
      </header>
      <main className="app-main-content">
        <div className="dashboard-grid">
          <WeatherDisplay latitude={latitude} longitude={longitude} language={language} />
          <MarketPricesDisplay latitude={latitude} longitude={longitude} language={language} />
          <Chatbot language={language} />
          <TrendingCropsDisplay latitude={latitude} longitude={longitude} language={language} />
        </div>
      </main>
    </div>
  );
}

export default App;
