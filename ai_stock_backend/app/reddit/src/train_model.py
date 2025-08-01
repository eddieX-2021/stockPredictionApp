import os
import re
import joblib
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Utility to clean text
def clean_headline(text: str) -> str:
    text = str(text)                # cast floats/NaN → 'nan'
    text = text.lower()             # safe now
    text = re.sub(r'[^a-z\s]', '', text)
    return text.strip()

# Paths
HERE    = os.path.dirname(os.path.abspath(__file__))
BASE    = os.path.normpath(os.path.join(HERE, '..'))
DATA_FP = os.path.join(BASE, 'data', 'Combined_News_DJIA.csv')
MODELS  = os.path.join(BASE, 'models')

if not os.path.exists(DATA_FP):
    raise FileNotFoundError(f"Dataset not found at {DATA_FP}")


df = pd.read_csv(DATA_FP)

train_df = df[df['Date'] < '20150101']
test_df = df[df['Date'] > '20141231']

headlines_train = train_df.iloc[:, 2:27].applymap(clean_headline)
headlines_test  = test_df.iloc[:, 2:27].applymap(clean_headline)

X_train = headlines_train.apply(lambda row: ' '.join(row), axis=1)
X_test  = headlines_test .apply(lambda row: ' '.join(row), axis=1)

y_train = train_df['Label']
y_test  = test_df ['Label']


vectorizer = CountVectorizer(ngram_range=(2,2))
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec  = vectorizer.transform(X_test)


model = RandomForestClassifier(
    n_estimators=200,
    criterion='entropy',
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_vec, y_train)

os.makedirs(MODELS, exist_ok=True)
joblib.dump(vectorizer, os.path.join(MODELS, 'vectorizer.joblib'))
joblib.dump(model,      os.path.join(MODELS, 'random_forest.joblib'))

print("✅ Trained & saved CountVectorizer + RandomForest model")