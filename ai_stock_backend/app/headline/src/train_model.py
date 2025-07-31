import os
import re
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from xgboost import XGBClassifier

HERE    = os.path.dirname(os.path.abspath(__file__))
BASE    = os.path.normpath(os.path.join(HERE, '..'))        # app/headline
DATA_FP = os.path.join(BASE, 'data', 'all-data.csv')
MODELS  = os.path.join(BASE, 'models')

if not os.path.exists(DATA_FP):
    raise FileNotFoundError(f"Cannot find CSV at {DATA_FP}. "
                            "Make sure your all-data.csv lives in app/headline/data/")

# read & clean
df  = pd.read_csv(DATA_FP,
                  encoding='ISO-8859-1',
                  header=None,
                  names=['Sentiment','Headline'])

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)  # remove punctuation/numbers
    return text

# read and clean
# df  = pd.read_csv('../data/all-data.csv',encoding='ISO-8859-1', header=None)
df.columns = ['Sentiment', 'Headline']
df['News'] = df['Headline'].apply(clean_text)
#label
label_map = {'negative':0,'neutral':1,'positive':2}
df['label'] = df['Sentiment'].map(label_map)
vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=5000)
X_tfidf = vectorizer.fit_transform(df['News'])
y       = df['label']

# 3) Train XGB
model = XGBClassifier(
    use_label_encoder=False,
    eval_metric='mlogloss',
    random_state=42
)
model.fit(X_tfidf, y)

# 4) Export artifacts
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'models'),
            exist_ok=True)
joblib.dump(vectorizer,
            os.path.join(os.path.dirname(__file__), '..',
                         'models', 'vectorizer.joblib'))
joblib.dump(model,
            os.path.join(os.path.dirname(__file__), '..',
                         'models', 'xgb_model.joblib'))

print("✅ Trained & saved vectorizer + XGB model")