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
    """
    X = VECT.transform(headlines)
    preds = MODEL.predict(X)
    return [_LABELS[p] for p in preds]
