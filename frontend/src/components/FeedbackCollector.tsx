import React, { useState } from 'react';
import axios from 'axios';

interface FeedbackCollectorProps {
  user_id: string;
  session_id: string;
  prediction_type: string;
  input_data: any;
  system_prediction: any;
  language: string;
  onFeedbackSubmitted?: () => void;
}

const FeedbackCollector: React.FC<FeedbackCollectorProps> = ({
  user_id,
  session_id,
  prediction_type,
  input_data,
  system_prediction,
  language,
  onFeedbackSubmitted
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState<number>(0);
  const [feedbackText, setFeedbackText] = useState<string>('');
  const [actualResult, setActualResult] = useState<any>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitted, setSubmitted] = useState<boolean>(false);

  const handleSubmitFeedback = async () => {
    if (feedbackRating === 0) {
      alert(language === 'hi' ? 'कृपया रेटिंग दें' : 'Please provide a rating');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await axios.post('http://localhost:8000/api/advisories/collect_feedback/', {
        user_id,
        session_id,
        prediction_type,
        input_data,
        system_prediction,
        actual_result: actualResult,
        feedback_rating: feedbackRating,
        feedback_text: feedbackText,
        latitude: null, // Could be added from geolocation
        longitude: null
      });

      if (response.status === 200) {
        setSubmitted(true);
        if (onFeedbackSubmitted) {
          onFeedbackSubmitted();
        }
        // Hide feedback form after 3 seconds
        setTimeout(() => {
          setIsVisible(false);
          setSubmitted(false);
        }, 3000);
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert(language === 'hi' ? 'फीडबैक सबमिट करने में त्रुटि' : 'Error submitting feedback');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRatingClick = (rating: number) => {
    setFeedbackRating(rating);
  };

  const renderStars = () => {
    const stars = [];
    for (let i = 1; i <= 5; i++) {
      stars.push(
        <button
          key={i}
          type="button"
          className={`star-button ${i <= feedbackRating ? 'filled' : ''}`}
          onClick={() => handleRatingClick(i)}
          disabled={submitted}
        >
          ★
        </button>
      );
    }
    return stars;
  };

  if (!isVisible && !submitted) {
    return (
      <div className="feedback-trigger">
        <button 
          onClick={() => setIsVisible(true)}
          className="feedback-trigger-button"
        >
          {language === 'hi' ? 'फीडबैक दें' : 'Give Feedback'}
        </button>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="feedback-success">
        <div className="success-message">
          {language === 'hi' ? 'धन्यवाद! आपका फीडबैक सफलतापूर्वक सबमिट हो गया।' : 'Thank you! Your feedback has been submitted successfully.'}
        </div>
      </div>
    );
  }

  return (
    <div className="feedback-collector">
      <div className="feedback-header">
        <h3>{language === 'hi' ? 'फीडबैक दें' : 'Provide Feedback'}</h3>
        <button 
          onClick={() => setIsVisible(false)}
          className="close-button"
        >
          ×
        </button>
      </div>

      <div className="feedback-content">
        <div className="prediction-summary">
          <h4>{language === 'hi' ? 'सिस्टम की भविष्यवाणी:' : 'System Prediction:'}</h4>
          <div className="prediction-details">
            <pre>{JSON.stringify(system_prediction, null, 2)}</pre>
          </div>
        </div>

        <div className="rating-section">
          <label>{language === 'hi' ? 'इस भविष्यवाणी को कैसे रेट करेंगे?' : 'How would you rate this prediction?'}</label>
          <div className="star-rating">
            {renderStars()}
          </div>
          <div className="rating-labels">
            <span className="rating-label">
              {language === 'hi' ? 'बहुत खराब' : 'Very Poor'}
            </span>
            <span className="rating-label">
              {language === 'hi' ? 'बहुत अच्छा' : 'Excellent'}
            </span>
          </div>
        </div>

        <div className="actual-result-section">
          <label htmlFor="actual-result">
            {language === 'hi' ? 'वास्तविक परिणाम (यदि कोई हो):' : 'Actual Result (if any):'}
          </label>
          <textarea
            id="actual-result"
            value={JSON.stringify(actualResult, null, 2)}
            onChange={(e) => {
              try {
                setActualResult(JSON.parse(e.target.value));
              } catch {
                setActualResult({});
              }
            }}
            placeholder={language === 'hi' ? 'वास्तविक परिणाम यहाँ दर्ज करें...' : 'Enter actual result here...'}
            rows={4}
          />
        </div>

        <div className="feedback-text-section">
          <label htmlFor="feedback-text">
            {language === 'hi' ? 'अतिरिक्त टिप्पणी:' : 'Additional Comments:'}
          </label>
          <textarea
            id="feedback-text"
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder={language === 'hi' ? 'अपनी टिप्पणी यहाँ लिखें...' : 'Write your comments here...'}
            rows={3}
          />
        </div>

        <div className="feedback-actions">
          <button
            onClick={handleSubmitFeedback}
            disabled={isSubmitting || feedbackRating === 0}
            className="submit-feedback-button"
          >
            {isSubmitting 
              ? (language === 'hi' ? 'सबमिट हो रहा है...' : 'Submitting...')
              : (language === 'hi' ? 'फीडबैक सबमिट करें' : 'Submit Feedback')
            }
          </button>
          <button
            onClick={() => setIsVisible(false)}
            className="cancel-button"
            disabled={isSubmitting}
          >
            {language === 'hi' ? 'रद्द करें' : 'Cancel'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackCollector;
