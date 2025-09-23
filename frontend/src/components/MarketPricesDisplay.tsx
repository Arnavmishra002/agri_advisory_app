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

const MarketPricesDisplay: React.FC = () => {
  const [marketPrices, setMarketPrices] = useState<MarketPricesData | null>(null);
  const [location, setLocation] = useState<string>('Delhi'); // Default location
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMarketPrices = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`http://localhost:8000/api/market-prices/prices/?location=${location}`);
        setMarketPrices(response.data);
      } catch (err) {
        setError('Failed to fetch market prices.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchMarketPrices();
  }, [location]);

  const handleLocationChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setLocation(event.target.value);
  };

  if (loading) return <div className="market-prices-widget">Loading market prices...</div>;
  if (error) return <div className="market-prices-widget error">Error: {error}</div>;
  if (!marketPrices || Object.keys(marketPrices).length === 0) return <div className="market-prices-widget">No market data available for {location}.</div>;

  return (
    <div className="market-prices-widget">
      <h2>Real-time Market Prices in {location}</h2>
      <select onChange={handleLocationChange} value={location}>
        <option value="Delhi">Delhi</option>
        <option value="Mumbai">Mumbai</option>
      </select>
      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Unit</th>
            <th>Date</th>
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
  );
};

export default MarketPricesDisplay;
