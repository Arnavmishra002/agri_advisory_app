import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface WeatherData {
  location: {
    name: string;
    region: string;
    country: string;
    lat: number;
    lon: number;
    tz_id: string;
    localtime_epoch: number;
    localtime: string;
  };
  current: {
    last_updated_epoch: number;
    last_updated: string;
    temp_c: number;
    temp_f: number;
    is_day: number;
    condition: {
      text: string;
      icon: string;
      code: number;
    };
    wind_mph: number;
    wind_kph: number;
    wind_degree: number;
    wind_dir: string;
    pressure_mb: number;
    pressure_in: number;
    precip_mm: number;
    precip_in: number;
    humidity: number;
    cloud: number;
    feelslike_c: number;
    feelslike_f: number;
    vis_km: number;
    vis_miles: number;
    uv: number;
    gust_mph: number;
    gust_kph: number;
  };
}

interface WeatherDisplayProps {
  latitude: number | null;
  longitude: number | null;
  language: string;
}

const WeatherDisplay: React.FC<WeatherDisplayProps> = ({ latitude, longitude, language }) => {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWeather = async () => {
      if (latitude === null || longitude === null) {
        setError(language === 'hi' ? "स्थान उपलब्ध नहीं है।" : "Location not available.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`http://localhost:8000/api/weather/current/?lat=${latitude}&lon=${longitude}&lang=${language}`);
        setWeather(response.data);
      } catch (err) {
        setError(language === 'hi' ? "मौसम डेटा प्राप्त करने में विफल रहा।" : "Failed to fetch weather data.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchWeather();
  }, [latitude, longitude, language]);

  if (loading) return <div className="weather-widget">{language === 'hi' ? "मौसम लोड हो रहा है..." : "Loading weather..."}</div>;
  if (error) return <div className="weather-widget error">{language === 'hi' ? `त्रुटि: ${error}` : `Error: ${error}`}</div>;
  if (!weather) return <div className="weather-widget">{language === 'hi' ? "कोई मौसम डेटा उपलब्ध नहीं है।" : "No weather data available."}</div>;

  return (
    <div className="weather-widget">
      <h2>{language === 'hi' ? `मौसम ${weather.location.name} में` : `Weather in ${weather.location.name}`}</h2>
      <div className="weather-details">
        <div className="weather-main">
          <img src={weather.current.condition.icon} alt={weather.current.condition.text} className="weather-icon" />
          <p className="temperature">{weather.current.temp_c}°C</p>
        </div>
        <p className="condition">{weather.current.condition.text}</p>
        <div className="weather-info-grid">
          <p><strong>{language === 'hi' ? "महसूस होता है" : "Feels like"}:</strong> {weather.current.feelslike_c}°C</p>
          <p><strong>{language === 'hi' ? "आर्द्रता" : "Humidity"}:</strong> {weather.current.humidity}%</p>
          <p><strong>{language === 'hi' ? "हवा" : "Wind"}:</strong> {weather.current.wind_kph} km/h {weather.current.wind_dir}</p>
          <p><strong>{language === 'hi' ? "दबाव" : "Pressure"}:</strong> {weather.current.pressure_mb} mb</p>
        </div>
      </div>
    </div>
  );
};

export default WeatherDisplay;
