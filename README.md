# Stock Prediction App

A full-stack stock research dashboard built with FastAPI and Next.js. The app is being repositioned from a pure stock-price prediction demo into a Phase 1 equity research workbench that organizes price data, fundamentals, earnings context, risk indicators, news sentiment, and the existing prediction model in one place.

The prediction model is experimental and is shown as one quantitative signal. This project is for educational and research purposes only and does not provide financial advice.

## Problem Being Solved

Individual investors often have to jump between several sites to compare price performance, business fundamentals, earnings, risk, and model-driven signals. This app brings those research inputs into a cleaner dashboard while preserving the original stock prediction work.

## Current Phase 1 Features

- Ticker search with suggestions through the Next.js API route and Finnhub when configured.
- Company overview with ticker, sector, industry, market cap, price, and update time when available.
- Rule-based research snapshot using existing price, financial, valuation, liquidity, news, and risk data.
- Historical price-performance ranges with a lightweight chart and moving-average context.
- Financial-performance table with revenue, EPS, net income, cash flow, cash, and debt fields when available.
- Earnings section for EPS, revenue, dates, and explicit unavailable states for unsupported surprise data.
- Risk indicators based on volatility, drawdown, beta, balance-sheet strength, and reported fundamentals.
- Existing prediction model preserved as an experimental quantitative signal.
- News sentiment preserved as an optional supporting signal.
- Reddit sentiment is disabled/omitted because live Reddit access is unreliable under token/rate limits.
- Disabled Phase 2 AI entry points are visible but do not call an AI API.
- Light/dark theme support with a user toggle and system-default behavior.
- Free external links to Yahoo Finance and SEC filing search for deeper research.

## Simple Architecture Overview

- `next-app/` contains the Next.js frontend and ticker search API route.
- `ai_stock_backend/` contains the FastAPI backend, analysis aggregation, model code, data fetchers, and local caches.
- The frontend calls the backend `/analysis?stock=SYMBOL` endpoint for the dashboard.
- The backend builds a structured response from price history, yfinance profile/financial data, optional news sentiment, existing model output, and deterministic calculations.

## Technology Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, Uvicorn
- Data and ML: yfinance, pandas, NumPy, scikit-learn, XGBoost/CatBoost where available in the existing model code
- Storage: local model cache and SQLite analysis cache already present in the project

## Data Flow

1. User enters a ticker on the homepage.
2. The stock route requests `/analysis?stock=SYMBOL` from the FastAPI backend.
3. Backend normalizes the ticker and attempts optional data sections independently.
4. Available sections are returned with warnings for missing or failed optional data.
5. Frontend renders available cards, charts, tables, links, warnings, and empty states without fabricating data.

## Local Setup

Backend:

```bash
cd ai_stock_backend
python -m venv ../venv
../venv/python.exe -m pip install -r requirements.txt
../venv/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Frontend:

```bash
cd next-app
npm install
npm run dev
```

Open `http://localhost:3000` and search for a ticker such as `MU`, `AAPL`, or `MSFT`.

## Environment Variables

Frontend:

- `FINNHUB_API_KEY` - optional server-side key for ticker search suggestions.
- `NEXT_PUBLIC_API_BASE_URL` - backend base URL, defaults to `http://127.0.0.1:8001` in the stock page.

Backend:

- News/Reddit keys may exist from older experiments, but Phase 1 does not require Reddit and does not add paid AI or data-service keys.

Do not commit secret values.

## Testing Commands

Frontend build/type check:

```bash
cd next-app
npm run build
```

Backend helper tests:

```bash
cd ai_stock_backend
../venv/python.exe -m unittest app.services.test_analysis_phase1
```

The checked-in virtual environment uses `venv/python.exe` at the repository root, not `venv/Scripts/python.exe`.

Backend syntax check:

```bash
cd ai_stock_backend
../venv/python.exe -m py_compile app/services/analysis.py app/main.py app/api/routes.py
```

## Manual Verification

Suggested Phase 1 smoke test:

1. Start the backend and frontend locally.
2. Search for `MU`, `AAPL`, and `MSFT`.
3. Try one invalid ticker and confirm the page shows a useful unavailable/error state.
4. Confirm the company overview, price chart, financial performance, earnings, risk, and prediction sections render when data exists.
5. Confirm optional sections such as news or missing fundamentals do not block the rest of the dashboard.
6. Confirm Reddit is shown as disabled or omitted and does not affect loading.
7. Open the Yahoo Finance and SEC links and confirm they match the selected ticker.
8. Resize to a mobile width and check that tables/charts remain readable.
9. Confirm Phase 2 AI controls are disabled and do not call an AI API.

## Screenshots

Screenshot placeholders:

- Homepage ticker search
- Company overview and research snapshot
- Price performance chart
- Financial performance and earnings sections
- Prediction / quantitative signal section

## Known Limitations

- The prediction model is experimental and should not be treated as guaranteed or as measured investment accuracy.
- yfinance and free profile fields may be delayed, incomplete, or unavailable for some tickers.
- Earnings surprise data is shown only when available; the app does not invent surprise values.
- Reddit sentiment is intentionally disabled in Phase 1.
- News sentiment can fail or return no headlines without blocking the rest of the dashboard.
- The dashboard is not a substitute for reading SEC filings, company reports, or professional advice.
- A root `package-lock.json` and `next-app/package-lock.json` both exist; `next.config.ts` pins the Turbopack root to the frontend app.

## Future Roadmap

Phase 2 may add AI-assisted features, but they are not implemented yet:

- AI explanations for financial metrics
- AI earnings analysis
- AI risk analysis
- SEC filing analysis
- Bull, base, and bear scenarios
- Evidence-grounded company Q&A
- More structured financial data
- Optional asynchronous analysis jobs
- Optional free or low-cost deployment improvements

Any future AI or data provider should preserve the project requirement that Phase 1 remains free to run and clear about limitations.
