import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface MarketPrice {
  price: number;
  unit: string;
  date: string;
}

interface MarketPricesData {
  [product: string]: MarketPrice;
}

interface MarketPricesDisplayProps {
  latitude: number | null;
  longitude: number | null;
  language: string;
}

const MarketPricesDisplay: React.FC<MarketPricesDisplayProps> = ({ latitude, longitude, language }) => {
  const [marketPrices, setMarketPrices] = useState<MarketPricesData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMarketPrices = async () => {
      if (latitude === null || longitude === null) {
        setError(language === 'hi' ? "स्थान उपलब्ध नहीं है।" : "Location not available.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`http://localhost:8000/api/market-prices/prices/?lat=${latitude}&lon=${longitude}&lang=${language}`);
        setMarketPrices(response.data);
      } catch (err) {
        setError(language === 'hi' ? "बाजार मूल्य प्राप्त करने में विफल रहा।" : "Failed to fetch market prices.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchMarketPrices();
  }, [latitude, longitude, language]);

  if (loading) return <div className="market-prices-widget">{language === 'hi' ? "बाजार मूल्य लोड हो रहे हैं..." : "Loading market prices..."}</div>;
  if (error) return <div className="market-prices-widget error">{language === 'hi' ? `त्रुटि: ${error}` : `Error: ${error}`}</div>;
  if (!marketPrices || Object.keys(marketPrices).length === 0) return <div className="market-prices-widget">{language === 'hi' ? "आपके स्थान के लिए कोई बाजार डेटा उपलब्ध नहीं है।" : "No market data available for your location."}</div>;

  return (
    <div className="market-prices-widget">
      <h2>{language === 'hi' ? "आपके स्थान में वास्तविक समय बाजार मूल्य" : "Real-time Market Prices in Your Location"}</h2>
      <div className="market-prices-table-container">
        <table>
          <thead>
            <tr>
              <th>{language === 'hi' ? "उत्पाद" : "Product"}</th>
              <th>{language === 'hi' ? "मूल्य" : "Price"}</th>
              <th>{language === 'hi' ? "इकाई" : "Unit"}</th>
              <th>{language === 'hi' ? "तारीख" : "Date"}</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(marketPrices).map(([product, data]) => (
              <tr key={product}>
                <td>{product}</td>
                <td>{data.price}</td>
                <td>{data.unit}</td>
                <td>{data.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default MarketPricesDisplay;
