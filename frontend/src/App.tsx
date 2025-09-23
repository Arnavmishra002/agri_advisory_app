import React from 'react';
import logo from './logo.svg';
import './App.css';
import WeatherDisplay from './components/WeatherDisplay';
import TextToSpeech from './components/TextToSpeech';
import MarketPricesDisplay from './components/MarketPricesDisplay';

function App() {
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
      </header>
      <main>
        <WeatherDisplay />
        <TextToSpeech />
        <MarketPricesDisplay />
      </main>
    </div>
  );
}

export default App;
