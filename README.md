# Stock Prediction App

## Project Overview

This project is a free stock research dashboard built with a Next.js frontend and a Python/FastAPI backend. It combines market data, SEC and Yahoo/yfinance financial data, rule-based calculations, price trends, risk indicators, relevant news, and the original experimental prediction models into one dashboard.

The app is educational research software. It is not financial advice.

## Features

- Company overview with ticker, exchange, industry, market cap, quote timestamp, and source links.
- Price history and trend view with return ranges, moving-average context, volume, and data freshness labels.
- Financial performance table for available revenue, EPS, income, cash flow, cash, and debt values.
- Earnings section with reported EPS/revenue, estimates when available, and date metadata.
- Balance sheet section with same-period SEC data when available and clearly labeled Yahoo fallback values.
- Valuation screen with the current rule-based DCF/EPS/analyst blended reference.
- Risk indicators with separate risk level and risk safety score.
- Dividend and analyst information when available from free sources.
- Relevant news headlines with rule-based filtering for unrelated stories.
- Preserved experimental signals from the traditional stock-price ML model, news sentiment model, and financial-statement prediction model.
- Structured research snapshot endpoint for future integrations: `GET /api/stocks/{symbol}/research-snapshot`.

## Architecture

- `next-app/` contains the Next.js, React, TypeScript, and Tailwind frontend.
- `ai_stock_backend/` contains the FastAPI backend, yfinance/Yahoo data access, SEC companyfacts balance-sheet logic, financial calculations, scoring, caching, and model routes.
- Existing ML code remains in `ai_stock_backend/app/mlm_predict`, `ai_stock_backend/app/headline`, and `ai_stock_backend/app/financial_statement`.
- The dashboard endpoint is `GET /analysis?stock=SYMBOL`.
- The reusable structured snapshot endpoint is `GET /api/stocks/{symbol}/research-snapshot`.
- The project is designed to run on free data sources and local caches. No AI provider key is required.

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
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8001"
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open `http://127.0.0.1:3000` and search for a ticker such as `AAPL`, `MU`, or `MSFT`.

Useful checks:

```bash
cd ai_stock_backend
../venv/python.exe -m unittest app.services.test_analysis_phase1
../venv/python.exe -m py_compile app/services/analysis.py app/main.py app/api/routes.py
```

```bash
cd next-app
npm run build
```

## Data Limitations

- Yahoo/yfinance quotes, profile fields, and price history may be delayed, incomplete, or unavailable.
- Free quote data is not guaranteed to be real-time. Verify live prices with an exchange or brokerage before trading.
- SEC fields vary between companies, and financial periods may not always align cleanly across statements.
- Yahoo fallback balance-sheet fields may mix periods and are labeled when used.
- Analyst targets and recommendations are external reference data, not intrinsic value.
- Prediction model confidence values are model-provided experimental signals, not guaranteed probabilities.
- Reddit remains disabled because live access is unreliable under token and rate limits.
- This project is not a substitute for SEC filings, company reports, professional research, or financial advice.

## Future ChatGPT App

A separate ChatGPT App is planned, but it is still under development and will be maintained in a separate repository.

The future app is expected to use the OpenAI Apps SDK and a remote MCP server. It will retrieve structured research snapshots from this project, then let ChatGPT explain financial performance, price trends, valuation, risks, earnings, conflicting signals, and conditional bull/base/bear scenarios.

That future product will run inside ChatGPT instead of embedding a paid AI API into this website. This repository does not currently implement the ChatGPT App, MCP server, or generative AI workflow.

## Project Status

Phase 1 dashboard polish is the current focus. The existing score and valuation methodology is preserved for now and may be refined later. ChatGPT App integration is future work.