import os
import joblib

# Load artifacts
BASE = os.path.join(os.path.dirname(__file__), '..', 'models')
VECT = joblib.load(os.path.join(BASE, 'vectorizer.joblib'))
MODEL = joblib.load(os.path.join(BASE, 'xgb_model.joblib'))

_LABELS = {0: 'negative', 1: 'neutral', 2: 'positive'}

def predict_sentiments(headlines: list[str]) -> list[str]:
    """
    Given a list of headlines, returns a list of
    'negative' | 'neutral' | 'positive' predictions.
    
    Returns empty list if no headlines provided.
    """
    # Handle empty input
    if not headlines or len(headlines) == 0:
        print(" No headlines provided, returning empty predictions")
        return []
    
    # Filter out None/empty strings
    valid_headlines = [h for h in headlines if h and isinstance(h, str) and h.strip()]
    
    if not valid_headlines:
        print(" No valid headlines after filtering, returning empty predictions")
        return []
    
    try:
        X = VECT.transform(valid_headlines)
        preds = MODEL.predict(X)
        return [_LABELS[p] for p in preds]
    except Exception as e:
        print(f" Error predicting sentiments: {e}")
        # Return neutral predictions as fallback
        return ['neutral'] * len(valid_headlines)