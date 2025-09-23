import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface TrendingCrop {
  name: string;
  description: string;
  benefits: string[];
}

interface TrendingCropsDisplayProps {
  latitude: number | null;
  longitude: number | null;
  language: string;
}

const TrendingCropsDisplay: React.FC<TrendingCropsDisplayProps> = ({ latitude, longitude, language }) => {
  const [trendingCrops, setTrendingCrops] = useState<TrendingCrop[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTrendingCrops = async () => {
      if (latitude === null || longitude === null) {
        setError(language === 'hi' ? "स्थान उपलब्ध नहीं है।" : "Location not available for trending crops.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        // Replace with your actual API endpoint for trending crops
        const response = await axios.get(`http://localhost:8000/api/trending-crops/?lat=${latitude}&lon=${longitude}&lang=${language}`);
        setTrendingCrops(response.data);
      } catch (err) {
        setError(language === 'hi' ? "ट्रेंडिंग फसल डेटा प्राप्त करने में विफल रहा।" : "Failed to fetch trending crop data.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchTrendingCrops();
  }, [latitude, longitude, language]);

  if (loading) return <div className="trending-crops-widget">{language === 'hi' ? "ट्रेंडिंग फसलें लोड हो रही हैं..." : "Loading trending crops..."}</div>;
  if (error) return <div className="trending-crops-widget error">{language === 'hi' ? `त्रुटि: ${error}` : `Error: ${error}`}</div>;
  if (trendingCrops.length === 0) return <div className="trending-crops-widget">{language === 'hi' ? "आपके स्थान के लिए कोई ट्रेंडिंग फसल डेटा उपलब्ध नहीं है।" : "No trending crop data available for your location."}</div>;

  return (
    <div className="trending-crops-widget">
      <h2>{language === 'hi' ? "आपके स्थान के लिए ट्रेंडिंग फसलें" : "Trending Crops for Your Location"}</h2>
      <div className="crop-list">
        {trendingCrops.map((crop, index) => (
          <div key={index} className="crop-item">
            <h3>{crop.name}</h3>
            <p>{crop.description}</p>
            <h4>{language === 'hi' ? "लाभ:" : "Benefits:"}</h4>
            <ul>
              {crop.benefits.map((benefit, bIndex) => (
                <li key={bIndex}>{benefit}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TrendingCropsDisplay;
