import React, { useState } from 'react';
import axios from 'axios';

interface ImageUploadProps {
  language: string;
}

interface GeolocationData {
  latitude: number;
  longitude: number;
  accuracy: number;
}

const ImageUpload: React.FC<ImageUploadProps> = ({ language }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [geolocation, setGeolocation] = useState<GeolocationData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    } else {
      setSelectedFile(null);
      setPreviewUrl(null);
    }
    setError(null);
  };

  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setGeolocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          });
        },
        (geoError) => {
          console.error("Geolocation error:", geoError);
          setError(language === 'hi' ? "स्थान प्राप्त करने में विफल रहा।" : "Failed to get location.");
          setGeolocation(null);
        }
      );
    } else {
      setError(language === 'hi' ? "आपके ब्राउज़र में जियोलोकेशन समर्थित नहीं है।" : "Geolocation is not supported by your browser.");
      setGeolocation(null);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      setError(language === 'hi' ? "कृपया एक छवि चुनें।" : "Please select an image.");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('image', selectedFile);
    if (geolocation) {
      formData.append('latitude', geolocation.latitude.toString());
      formData.append('longitude', geolocation.longitude.toString());
    }

    try {
      const response = await axios.post(
        `http://localhost:8000/api/advisories/detect_pest_disease/`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      // Handle response, e.g., display detection results
      console.log("Detection Result:", response.data);
      alert(JSON.stringify(response.data, null, 2));
    } catch (err) {
      setError(language === 'hi' ? "छवि अपलोड करने या कीट/रोग का पता लगाने में विफल रहा।" : "Failed to upload image or detect pest/disease.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="image-upload-widget">
      <h2>{language === 'hi' ? "छवि अपलोड करें" : "Upload Image"}</h2>
      <input type="file" accept="image/*" onChange={handleFileChange} />
      <button onClick={handleGetLocation} disabled={loading}>
        {language === 'hi' ? "स्थान प्राप्त करें" : "Get Current Location"}
      </button>
      {geolocation && (
        <p className="geolocation-info">
          {language === 'hi' ? "स्थान:" : "Location:"} {geolocation.latitude.toFixed(4)}, {geolocation.longitude.toFixed(4)}
        </p>
      )}
      {previewUrl && <img src={previewUrl} alt="Preview" className="image-preview" />}
      <button onClick={handleSubmit} disabled={loading || !selectedFile}>
        {loading ? (language === 'hi' ? "अपलोड हो रहा है..." : "Uploading...") : (language === 'hi' ? "अपलोड और पता लगाएं" : "Upload & Detect")}
      </button>
      {error && <p className="error-message">{error}</p>}
    </div>
  );
};

export default ImageUpload;
