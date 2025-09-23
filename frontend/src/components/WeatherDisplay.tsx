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

const WeatherDisplay: React.FC = () => {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [location, setLocation] = useState<string>('London'); // Default location
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWeather = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`http://localhost:8000/api/weather/current/?location=${location}`);
        setWeather(response.data);
      } catch (err) {
        setError('Failed to fetch weather data.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchWeather();
  }, [location]);

  const handleLocationChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setLocation(event.target.value);
  };

  if (loading) return <div className="weather-widget">Loading weather...</div>;
  if (error) return <div className="weather-widget error">Error: {error}</div>;
  if (!weather) return <div className="weather-widget">No weather data available.</div>;

  return (
    <div className="weather-widget">
      <h2>Weather in {weather.location.name}</h2>
      <input
        type="text"
        value={location}
        onChange={handleLocationChange}
        placeholder="Enter city or ZIP code"
      />
      <p>Temperature: {weather.current.temp_c}°C ({weather.current.temp_f}°F)</p>
      <p>Condition: {weather.current.condition.text}</p>
      <img src={weather.current.condition.icon} alt={weather.current.condition.text} />
      <p>Humidity: {weather.current.humidity}%</p>
      <p>Wind: {weather.current.wind_kph} km/h {weather.current.wind_dir}</p>
    </div>
  );
};

export default WeatherDisplay;
