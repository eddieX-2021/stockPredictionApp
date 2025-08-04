# stockPredictionApp

A full-stack, machine learning–powered web application that forecasts stock price movements by combining historical data, financial sentiment analysis, and news headlines. Built with a Python/FastAPI backend and a Next.js frontend, the app delivers real-time predictions and sentiment insights to help users make data-driven investment decisions.

---

## Table of Contents

1. [Getting Started](#getting-started)  
2. [Project Overview](#project-overview)  
3. [Backend Features](#backend-features)  
4. [Frontend Features](#frontend-features)  
5. [Tech Stack](#tech-stack)  
6. [Future Improvements](#future-improvements)  
7. [Credits](#credits)  

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/your-org/stockPredictionApp.git
cd stockPredictionApp
```

### 2. Backend setup
```bash
# 2.1 Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
.\.venv\Scripts\activate     # Windows

# 2.2 Install Python dependencies
pip install -r requirements.txt

# 2.3 Launch FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend setup
```bash
cd frontend

# 3.1 Install Node.js dependencies
npm install

# 3.2 Start development server
npm run dev
```

---

## Project Overview

Our Stock Prediction App combines financial data, news sentiment, and cutting-edge machine learning models to forecast future stock prices. It features:
- A FastAPI backend for data ingestion, feature engineering, model inference, and sentiment analysis.
- A Next.js/Tailwind-CSS frontend with intelligent search, interactive charts, and real-time prediction display.

---

## Backend Features

- **Stock Price Prediction:**  
  - Models: Linear Regression, Decision Tree, Random Forest, Gradient Boosting, XGBoost, CatBoost, AdaBoost, SVR, Stacking Ensemble  
  - Trained on historical price & technical indicators to predict next-day direction (and price).

- **News & Headline Sentiment:**  
  - Fetches recent headlines via NewsAPI.  
  - Trains a headline sentiment model (~76% accuracy).

- **Reddit Sentiment:**  
  - Uses PRAW to pull Reddit posts by ticker/keyword.  
  - Classifies sentiment with TF-IDF + XGBoost (~76% accuracy).

- **Financial Statement Analysis:**  
  - Retrieves annual reports via yfinance.  
  - Correlates YOY metrics for feature selection.  
  - Current model accuracy ~52% (work in progress).

---

## Frontend Features

- **Search Bar with Auto-Suggestion:**  
  - Powered by Finnhub API for real-time ticker/company lookup.

- **Dynamic Prediction Dashboard:**  
  - Recharts visualizations of predicted vs. actual price.  
  - Sentiment tag cloud & summary panels.  
  - Sectioned view for each model’s output + price forecast.

---

## Tech Stack

- **Languages & Frameworks:**  
  - Python 3.9+ · FastAPI · Uvicorn  
  - JavaScript/TypeScript · Next.js · React  

- **Data & ML:**  
  - scikit-learn · XGBoost · CatBoost · SVR · pandas · NumPy  
  - yfinance · NewsAPI · PRAW  

- **UI & Styling:**  
  - Tailwind CSS · Recharts  

- **Deployment:**  
  - Render.com (backend) · Vercel (frontend)  

---

## Future Improvements

- **UI Enhancements:** Theme support, chart filters, animations.  
- **Custom Timeframes:** User-selectable 1D, 1W, 1M, 1Y ranges.  
- **Ensemble Signals:** Unified score combining price, news, and financial models.  
- **Real-Time Streaming:** WebSocket updates for live data & sentiment.  
- **Backtesting Module:** Historical performance evaluation & metrics.

---

## Credits

- [AnkurZing — Financial News Sentiment (Kaggle)](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-for-financial-news)  
- [US Stocks Fundamentals (Kaggle)](https://www.kaggle.com/datasets/usfundamentals/us-stocks-fundamentals)

---
