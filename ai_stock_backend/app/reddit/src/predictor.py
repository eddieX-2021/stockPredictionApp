import os
import re
import joblib
from typing import List



def clean_headline(text: str) -> str:
    """
    Lowercase, strip non-letters, collapse whitespace.
    """
    text = str(text)
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    return text.strip()

HERE    = os.path.dirname(os.path.abspath(__file__))
BASE    = os.path.normpath(os.path.join(HERE, '..'))
MODELS  = os.path.join(BASE, 'models')

vectorizer = joblib.load(os.path.join(MODELS, 'vectorizer.joblib'))
model      = joblib.load(os.path.join(MODELS, 'random_forest.joblib'))

label_map = {0: 'negative', 1: 'neutral', 2: 'positive'}


def predict_sentiments(texts: List[str]) -> List[str]:
    """
    Clean & vectorize `texts`, predict sentiments.
    Returns list of 'negative'|'neutral'|'positive'.
    """
    cleaned = [clean_headline(t) for t in texts]
    X = vectorizer.transform(cleaned)
    preds = model.predict(X)
    return [label_map.get(p, 'neutral') for p in preds]