from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Callable

import numpy as np
import pytz
import yfinance as yf

from app.mlm_predict.train_model import train_stock_models
from app.services.fetch_data import fetch_raw_stock_data
from app.services.json_safe import json_safe


_YF_CACHE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "yfinance_cache")
)
try:
    os.makedirs(_YF_CACHE_DIR, exist_ok=True)
    if hasattr(yf, "set_tz_cache_location"):
        yf.set_tz_cache_location(_YF_CACHE_DIR)
except Exception:
    pass


SCORE_WEIGHTS = {
    "valuation": 0.22,
    "fundamentals": 0.18,
    "trend": 0.16,
    "balance_sheet": 0.12,
    "risk": 0.10,
    "liquidity": 0.08,
    "analyst": 0.06,
    "news": 0.04,
    "dividend": 0.04,
}


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        n = float(value)
        if not np.isfinite(n):
            return None
        return n
    except Exception:
        return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp_score(value: float | int) -> int:
    return int(round(_clamp(float(value), 0, 100)))


def _average_known(values: list[int | float | None], fallback: int = 50) -> int:
    known = [float(v) for v in values if v is not None]
    if not known:
        return fallback
    return _clamp_score(sum(known) / len(known))


def _pct_change(latest: Any, prev: Any) -> float | None:
    latest_n = _as_float(latest)
    prev_n = _as_float(prev)
    if latest_n is None or prev_n in (None, 0):
        return None
    return ((latest_n - prev_n) / abs(prev_n)) * 100


def _get_any(obj: dict[str, Any] | None, *keys: str) -> Any:
    if not obj:
        return None

    lower_map = {k.lower(): k for k in obj.keys()}
    for key in keys:
        if key in obj:
            return obj[key]
        found = lower_map.get(key.lower())
        if found:
            return obj[found]
    return None


def _has_known_value(obj: Any) -> bool:
    if isinstance(obj, dict):
        return any(_has_known_value(value) for value in obj.values())
    if isinstance(obj, list):
        return any(_has_known_value(value) for value in obj)
    return _as_float(obj) is not None or (isinstance(obj, str) and bool(obj.strip()))


def _score_from_change(change_pct: float | None, good_when_positive: bool = True) -> int:
    if change_pct is None:
        return 50
    direction = change_pct if good_when_positive else -change_pct
    if direction >= 20:
        return 90
    if direction >= 10:
        return 75
    if direction >= 0:
        return 60
    if direction >= -10:
        return 40
    return 25


def _score_from_ratio(value: float | None, good_max: float, fair_max: float, bad_max: float) -> int:
    if value is None or value <= 0:
        return 50
    if value <= good_max:
        return 85
    if value <= fair_max:
        return 65
    if value <= bad_max:
        return 40
    return 20


def _run_section(
    warnings: list[str],
    sources: list[str],
    name: str,
    fn: Callable[[], dict[str, Any] | None],
) -> dict[str, Any] | None:
    try:
        result = fn()
        if result is not None:
            sources.append(name)
        return result
    except Exception as exc:
        message = str(exc).replace("\r", " ").replace("\n", " ")
        if len(message) > 220:
            message = message[:217] + "..."
        warnings.append(f"{name} unavailable: {message}")
        return None

def _price_trend(ticker: str) -> dict[str, Any]:
    eastern = pytz.timezone("US/Eastern")
    end_date = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=365 * 5)).strftime(
        "%Y-%m-%d"
    )

    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None or stock_data.empty:
        raise ValueError("No price history returned")

    close = stock_data["Close"]
    volume = stock_data["Volume"]
    current = _as_float(close.iloc[-1])
    previous = _as_float(close.iloc[-2]) if len(close) > 1 else None

    def ret(days: int) -> float | None:
        if len(close) <= days:
            return None
        base = _as_float(close.iloc[-days])
        if current is None or base in (None, 0):
            return None
        return ((current - base) / base) * 100

    sma20 = _as_float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
    sma50_series = close.rolling(50).mean() if len(close) >= 50 else None
    sma50 = _as_float(sma50_series.iloc[-1]) if sma50_series is not None else None
    sma200 = _as_float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

    returns = close.pct_change().dropna()
    volatility_20d = None
    if len(returns) >= 20:
        volatility_20d = _as_float(returns.tail(20).std() * np.sqrt(252) * 100)

    latest_volume = _as_float(volume.iloc[-1])
    avg_volume_20d = _as_float(volume.tail(20).mean()) if len(volume) >= 20 else None
    volume_ratio = (
        latest_volume / avg_volume_20d
        if latest_volume is not None and avg_volume_20d not in (None, 0)
        else None
    )

    day_change_pct = _pct_change(current, previous)
    returns_map = {
        "1d": day_change_pct,
        "5d": ret(5),
        "1m": ret(21),
        "3m": ret(63),
        "6m": ret(126),
        "1y": ret(252),
        "5y": ret(252 * 5),
    }

    rolling_high = close.cummax()
    drawdown = (close - rolling_high) / rolling_high
    max_drawdown_1y = None
    if len(drawdown.dropna()) >= 20:
        max_drawdown_1y = _as_float(drawdown.tail(min(len(drawdown), 252)).min() * 100)

    history = []
    for index, row in stock_data.tail(252 * 5).iterrows():
        close_value = _as_float(row.get("Close"))
        if close_value is None:
            continue
        sma50_value = None
        if sma50_series is not None and index in sma50_series.index:
            sma50_value = _as_float(sma50_series.loc[index])
        history.append({
            "date": index.date().isoformat() if hasattr(index, "date") else str(index),
            "close": close_value,
            "volume": _as_float(row.get("Volume")),
            "sma50": sma50_value,
        })

    range_days = {
        "1m": 21,
        "3m": 63,
        "6m": 126,
        "1y": 252,
        "5y": 252 * 5,
    }
    ranges = {}
    for key, days in range_days.items():
        points = history[-days:] if len(history) >= min(days, 21) else []
        if not points:
            continue
        prices = [point["close"] for point in points if point.get("close") is not None]
        if not prices:
            continue
        ranges[key] = {
            "label": key.upper(),
            "start_date": points[0]["date"],
            "end_date": points[-1]["date"],
            "return_pct": _pct_change(prices[-1], prices[0]),
            "high": max(prices),
            "low": min(prices),
            "points": points,
        }

    bullish_checks = 0
    total_checks = 0
    for value in (returns_map["5d"], returns_map["1m"], returns_map["3m"]):
        if value is not None:
            total_checks += 1
            bullish_checks += int(value > 0)
    for avg in (sma20, sma50, sma200):
        if avg is not None and current is not None:
            total_checks += 1
            bullish_checks += int(current > avg)

    trend_score = round((bullish_checks / total_checks) * 100) if total_checks else 50
    trend_label = "Bullish" if trend_score >= 65 else "Bearish" if trend_score <= 35 else "Mixed"

    liquidity_score = 50
    if avg_volume_20d is not None:
        if avg_volume_20d >= 5_000_000:
            liquidity_score = 90
        elif avg_volume_20d >= 1_000_000:
            liquidity_score = 75
        elif avg_volume_20d >= 250_000:
            liquidity_score = 55
        else:
            liquidity_score = 30

    return {
        "price": {
            "current": current,
            "previous_close": previous,
            "day_change_pct": day_change_pct,
            "currency": "USD",
        },
        "trend": {
            "label": trend_label,
            "score": trend_score,
            "returns": returns_map,
            "moving_averages": {
                "sma20": sma20,
                "sma50": sma50,
                "sma200": sma200,
                "price_above_sma20": current is not None and sma20 is not None and current > sma20,
                "price_above_sma50": current is not None and sma50 is not None and current > sma50,
                "price_above_sma200": current is not None and sma200 is not None and current > sma200,
            },
        },
        "volume_liquidity": {
            "score": liquidity_score,
            "latest_volume": latest_volume,
            "avg_volume_20d": avg_volume_20d,
            "volume_ratio": volume_ratio,
            "volume_signal": "High volume"
            if volume_ratio is not None and volume_ratio >= 1.5
            else "Normal volume",
        },
        "risk": {
            "volatility_20d_pct": volatility_20d,
            "max_drawdown_1y_pct": max_drawdown_1y,
        },
        "price_history": {
            "available_ranges": list(ranges.keys()),
            "ranges": ranges,
        },
    }


def _prediction(ticker: str) -> dict[str, Any]:
    eastern = pytz.timezone("US/Eastern")
    end_date = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=365 * 5)).strftime(
        "%Y-%m-%d"
    )

    result = train_stock_models(ticker, start_date, end_date, verbose=False, use_cache=True)
    if result is None:
        raise ValueError("Prediction model did not return a result")

    prediction = result["predict"](result["latest_features"])

    price_start = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=90)).strftime(
        "%Y-%m-%d"
    )
    stock_data = fetch_raw_stock_data(ticker, price_start, end_date)
    if stock_data is None or stock_data.empty:
        raise ValueError("Unable to fetch current price for prediction")

    current_price = float(stock_data["Close"].iloc[-1])
    predicted_change_pct = float(prediction["final_prediction_pct"])
    predicted_price = current_price * (1 + predicted_change_pct / 100)
    direction = prediction["direction"]
    direction_confidence = float(prediction["direction_confidence"])
    confidence = direction_confidence if direction == "UP" else 1 - direction_confidence

    return {
        "stock": ticker,
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "direction": direction,
        "confidence": round(confidence, 4),
        "predicted_change_pct": round(predicted_change_pct, 2),
        "system_confidence": result["confidence"],
        "model_info": {
            "direction_model": result["direction"]["best_model_name"],
            "magnitude_model": result["magnitude"]["best_model_name"],
            "cached": result["cached"],
        },
    }


def _news(ticker: str) -> dict[str, Any]:
    from app.headline.src.fetch_news import get_top_headlines
    from app.headline.src.predictor import predict_sentiments

    headlines = get_top_headlines(ticker)
    sentiments = predict_sentiments(headlines) if headlines else []

    items = [
        {"headline": headline, "sentiment": sentiment}
        for headline, sentiment in zip(headlines, sentiments)
    ]
    counts = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
    for item in items:
        s = str(item["sentiment"]).lower()
        if "pos" in s:
            counts["positive"] += 1
        elif "neg" in s:
            counts["negative"] += 1
        else:
            counts["neutral"] += 1
        counts["total"] += 1

    total = counts["total"]
    score = 50 if total == 0 else _clamp_score(50 + ((counts["positive"] - counts["negative"]) / total) * 40)
    return {"items": items, "sentiment_counts": counts, "score": score}

def _merge_statement_frame(frame: Any, latest: dict[str, Any], prev: dict[str, Any]) -> None:
    if frame is None or getattr(frame, "empty", True):
        return
    if getattr(frame, "shape", (0, 0))[1] < 1:
        return

    periods = list(frame.columns[:2])
    for index, period in enumerate(periods):
        target = latest if index == 0 else prev
        col = frame[period]
        for metric, value in col.items():
            target[str(metric)] = _as_float(value)


def _fetch_yfinance_statement_pair(ticker: str) -> dict[str, dict[str, Any]] | None:
    tk = yf.Ticker(ticker.upper())
    latest: dict[str, Any] = {}
    prev: dict[str, Any] = {}

    frames = [
        getattr(tk, "financials", None),
        getattr(tk, "balance_sheet", None),
        getattr(tk, "cashflow", None),
    ]
    for frame in frames:
        _merge_statement_frame(frame, latest, prev)

    if not latest:
        quarterly_frames = [
            getattr(tk, "quarterly_financials", None),
            getattr(tk, "quarterly_balance_sheet", None),
            getattr(tk, "quarterly_cashflow", None),
        ]
        for frame in quarterly_frames:
            _merge_statement_frame(frame, latest, prev)

    if not latest:
        return None
    return {"latest": latest, "prev": prev}


def _previous_from_growth(latest: float | None, growth: float | None) -> float | None:
    if latest is None or growth is None or growth <= -0.95:
        return None
    return latest / (1 + growth)


def _first_row_value(row: Any, *keys: str) -> float | None:
    for key in keys:
        if key in row.index:
            value = _as_float(row.get(key))
            if value is not None:
                return value
    return None


def _local_fundamental_financials(ticker: str) -> dict[str, dict[str, Any]] | None:
    try:
        import joblib
        import pandas as pd
        from pathlib import Path

        base = Path(__file__).resolve().parents[1] / "financial_statement"
        tickers_path = base / "data" / "sec_company_tickers.csv"
        data_path = base / "model_data.parquet"
        model_path = base / "models" / "stock_dir_model_logreg_tuned.pkl"
        if not tickers_path.exists() or not data_path.exists():
            return None

        tickers = pd.read_csv(tickers_path)
        match = tickers[tickers["ticker"].astype(str).str.upper() == ticker.upper()]
        if match.empty:
            return None

        alias_columns = [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "Revenues",
            "EarningsPerShareDiluted",
            "EarningsPerShareBasic",
            "NetIncomeLoss",
            "ProfitLoss",
            "GrossProfit",
            "OperatingIncomeLoss",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            "NetCashProvidedByUsedInOperatingActivities",
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "Assets",
            "Liabilities",
            "LongTermDebt",
            "ShortTermBorrowings",
            "LongTermDebtCurrent",
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            "StockholdersEquity",
            "CommonStockholdersEquity",
        ]
        feature_columns: list[str] = []
        if model_path.exists():
            artifact = joblib.load(model_path)
            feature_columns = [
                feature[:-4]
                for feature in artifact.get("features", [])
                if isinstance(feature, str) and feature.endswith("_chg")
            ]

        try:
            import pyarrow.parquet as pq
            schema_columns = set(pq.ParquetFile(data_path).schema.names)
            selected = [column for column in [*alias_columns, *feature_columns] if column in schema_columns]
        except Exception:
            selected = [*alias_columns, *feature_columns]

        columns = list(dict.fromkeys(["company_id", "year", *selected]))
        data = pd.read_parquet(data_path, columns=columns)

        company_id = str(match.iloc[0]["company_id"])
        rows = data[data["company_id"].astype(str) == company_id].sort_values("year")
        if len(rows) < 1:
            return None

        latest_row = rows.iloc[-1]
        prev_row = rows.iloc[-2] if len(rows) >= 2 else None

        def build(row: Any) -> dict[str, Any]:
            row_dict = {str(k): _as_float(v) for k, v in row.items() if _as_float(v) is not None}
            operating_cash_flow = _first_row_value(
                row,
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
                "NetCashProvidedByUsedInOperatingActivities",
            )
            capex = _first_row_value(row, "PaymentsToAcquirePropertyPlantAndEquipment")
            long_debt = _first_row_value(row, "LongTermDebt") or 0
            short_debt = _first_row_value(row, "ShortTermBorrowings") or 0
            current_debt = _first_row_value(row, "LongTermDebtCurrent") or 0
            aliases = {
                "Total Revenue": _first_row_value(row, "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"),
                "Diluted EPS": _first_row_value(row, "EarningsPerShareDiluted"),
                "Basic EPS": _first_row_value(row, "EarningsPerShareBasic"),
                "Net Income": _first_row_value(row, "NetIncomeLoss", "ProfitLoss"),
                "Gross Profit": _first_row_value(row, "GrossProfit"),
                "Operating Income": _first_row_value(row, "OperatingIncomeLoss"),
                "Operating Cash Flow": operating_cash_flow,
                "Free Cash Flow": (operating_cash_flow - capex) if operating_cash_flow is not None and capex is not None else None,
                "Total Assets": _first_row_value(row, "Assets"),
                "Total Liabilities": _first_row_value(row, "Liabilities"),
                "Total Debt": long_debt + short_debt + current_debt,
                "Cash And Cash Equivalents": _first_row_value(
                    row,
                    "CashAndCashEquivalentsAtCarryingValue",
                    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                ),
                "Stockholders Equity": _first_row_value(row, "StockholdersEquity", "CommonStockholdersEquity"),
            }
            for key, value in aliases.items():
                if value is not None:
                    row_dict[key] = value
            return row_dict

        return {
            "latest": build(latest_row),
            "prev": build(prev_row) if prev_row is not None else {},
        }
    except Exception:
        return None

def _profile_financials(ticker: str) -> dict[str, dict[str, Any]] | None:
    info = _safe_info(ticker)
    if not info:
        return None

    shares = _as_float(info.get("sharesOutstanding"))
    book_value = _as_float(info.get("bookValue"))
    revenue_growth = _as_float(info.get("revenueGrowth"))
    earnings_growth = _as_float(info.get("earningsGrowth"))

    latest = {
        "Total Revenue": _as_float(info.get("totalRevenue")),
        "Diluted EPS": _as_float(info.get("trailingEps")) or _as_float(info.get("forwardEps")),
        "Net Income": _as_float(info.get("netIncomeToCommon")),
        "Gross Profit": _as_float(info.get("grossProfits")),
        "Operating Cash Flow": _as_float(info.get("operatingCashflow")),
        "Free Cash Flow": _as_float(info.get("freeCashflow")),
        "Total Debt": _as_float(info.get("totalDebt")),
        "Cash And Cash Equivalents": _as_float(info.get("totalCash")),
        "Stockholders Equity": (book_value * shares) if book_value is not None and shares is not None else None,
    }
    prev = {
        "Total Revenue": _previous_from_growth(latest["Total Revenue"], revenue_growth),
        "Diluted EPS": _previous_from_growth(latest["Diluted EPS"], earnings_growth),
        "Free Cash Flow": None,
        "Operating Cash Flow": None,
    }

    if not any(value is not None for value in latest.values()):
        return None
    return {"latest": latest, "prev": prev}


def _financials(ticker: str) -> dict[str, Any]:
    from app.financial_statement.src.fetch_fin import fetch_financials
    from app.financial_statement.src.predictor import predict_stock_movement

    errors: list[str] = []
    source = "old_financial_statement_fetch"
    raw = None

    try:
        raw = fetch_financials(ticker)
    except Exception as exc:
        errors.append(f"old financial statement fetch failed: {exc}")

    if not raw:
        try:
            raw = _fetch_yfinance_statement_pair(ticker)
            source = "yfinance_statement_fallback"
        except Exception as exc:
            errors.append(f"yfinance statement fallback failed: {exc}")

    if not raw:
        raw = _local_fundamental_financials(ticker)
        source = "local_sec_parquet_fallback"
        if raw:
            errors.append("live statements were unavailable; used local SEC/parquet fundamentals")

    if not raw:
        raw = _profile_financials(ticker)
        source = "yahoo_profile_fallback"
        if raw:
            errors.append("annual statements were incomplete; used Yahoo profile metrics")

    if not raw:
        raise ValueError("No financial statement or profile fundamentals returned")

    model: dict[str, Any] = {"direction": None, "confidence": None, "available": False}
    try:
        direction, confidence = predict_stock_movement(ticker, raw)
        model = {
            "direction": direction,
            "confidence": confidence,
            "available": True,
            "name": "financial_statement_direction_model",
        }
    except Exception as exc:
        model = {
            "direction": None,
            "confidence": None,
            "available": False,
            "error": str(exc),
            "name": "financial_statement_direction_model",
        }
        errors.append(f"financial statement model unavailable: {exc}")

    latest = raw.get("latest", {})
    prev = raw.get("prev", {})

    metrics = {
        "revenue": ("Total Revenue",),
        "eps": ("Diluted EPS", "Basic EPS"),
        "net_income": ("Net Income", "Net Income Common Stockholders"),
        "gross_profit": ("Gross Profit",),
        "operating_income": ("Operating Income", "Total Operating Income As Reported"),
        "operating_cash_flow": ("Operating Cash Flow", "Total Cash From Operating Activities"),
        "free_cash_flow": ("Free Cash Flow",),
        "total_assets": ("Total Assets",),
        "total_liabilities": ("Total Liabilities Net Minority Interest", "Total Liabilities"),
        "total_debt": ("Total Debt",),
        "cash": ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"),
        "stockholders_equity": ("Stockholders Equity", "Total Equity Gross Minority Interest"),
    }

    highlights = {}
    for name, keys in metrics.items():
        latest_value = _get_any(latest, *keys)
        prev_value = _get_any(prev, *keys)
        highlights[name] = {
            "latest": _as_float(latest_value),
            "previous": _as_float(prev_value),
            "change_pct": _pct_change(latest_value, prev_value),
        }

    revenue = highlights["revenue"]["latest"]
    gross_profit = highlights["gross_profit"]["latest"]
    operating_income = highlights["operating_income"]["latest"]
    net_income = highlights["net_income"]["latest"]
    fcf = highlights["free_cash_flow"]["latest"]

    margins = {
        "gross_margin_pct": (gross_profit / revenue * 100) if revenue not in (None, 0) and gross_profit is not None else None,
        "operating_margin_pct": (operating_income / revenue * 100) if revenue not in (None, 0) and operating_income is not None else None,
        "net_margin_pct": (net_income / revenue * 100) if revenue not in (None, 0) and net_income is not None else None,
        "free_cash_flow_margin_pct": (fcf / revenue * 100) if revenue not in (None, 0) and fcf is not None else None,
    }

    margin_score = _average_known([
        85 if margins["gross_margin_pct"] is not None and margins["gross_margin_pct"] >= 40 else 60 if margins["gross_margin_pct"] is not None and margins["gross_margin_pct"] >= 20 else 40 if margins["gross_margin_pct"] is not None else None,
        85 if margins["operating_margin_pct"] is not None and margins["operating_margin_pct"] >= 20 else 60 if margins["operating_margin_pct"] is not None and margins["operating_margin_pct"] >= 10 else 35 if margins["operating_margin_pct"] is not None else None,
        85 if margins["free_cash_flow_margin_pct"] is not None and margins["free_cash_flow_margin_pct"] >= 15 else 60 if margins["free_cash_flow_margin_pct"] is not None and margins["free_cash_flow_margin_pct"] >= 5 else 35 if margins["free_cash_flow_margin_pct"] is not None else None,
    ])

    growth_scores = [
        _score_from_change(highlights["revenue"]["change_pct"]),
        _score_from_change(highlights["eps"]["change_pct"]),
        _score_from_change(highlights["operating_cash_flow"]["change_pct"]),
        _score_from_change(highlights["free_cash_flow"]["change_pct"]),
    ]
    fundamentals_score = round(_average_known(growth_scores) * 0.65 + margin_score * 0.35)

    return {
        "raw": raw,
        "source": source,
        "errors": errors,
        "highlights": highlights,
        "margins": margins,
        "model": model,
        "score": _clamp_score(fundamentals_score),
    }


def _safe_info(ticker: str) -> dict[str, Any]:
    try:
        return dict(yf.Ticker(ticker).info or {})
    except Exception:
        return {}


def _timestamp_to_iso(value: Any) -> str | None:
    n = _as_float(value)
    if n is None or n <= 0:
        return None
    try:
        return datetime.fromtimestamp(n, tz=pytz.utc).date().isoformat()
    except Exception:
        return None


def _company_profile(ticker: str, info: dict[str, Any], price: dict[str, Any] | None) -> dict[str, Any]:
    market_cap = _as_float(info.get("marketCap"))
    return {
        "name": info.get("longName") or info.get("shortName") or ticker,
        "ticker": ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "exchange": info.get("exchange") or info.get("fullExchangeName"),
        "currency": (price or {}).get("currency") or info.get("currency") or "USD",
        "current_price": _as_float((price or {}).get("current")) or _as_float(info.get("currentPrice")) or _as_float(info.get("regularMarketPrice")),
        "daily_change_pct": _as_float((price or {}).get("day_change_pct")),
        "market_cap": market_cap,
        "website": info.get("website"),
        "links": {
            "yahoo_finance": f"https://finance.yahoo.com/quote/{ticker}",
            "sec_search": f"https://www.sec.gov/edgar/search/#/q={ticker}",
        },
    }


def _earnings(info: dict[str, Any], financials: dict[str, Any] | None) -> dict[str, Any] | None:
    highlights = (financials or {}).get("highlights") or {}
    eps = highlights.get("eps") or {}
    revenue = highlights.get("revenue") or {}
    reported_eps = _as_float(eps.get("latest")) or _as_float(info.get("trailingEps"))
    previous_eps = _as_float(eps.get("previous"))
    estimated_eps = _as_float(info.get("forwardEps"))
    reported_revenue = _as_float(revenue.get("latest")) or _as_float(info.get("totalRevenue"))
    previous_revenue = _as_float(revenue.get("previous"))
    next_start = _timestamp_to_iso(info.get("earningsTimestampStart"))
    next_end = _timestamp_to_iso(info.get("earningsTimestampEnd"))
    recent_date = _timestamp_to_iso(info.get("earningsTimestamp"))

    if not _has_known_value(
        [reported_eps, estimated_eps, reported_revenue, previous_eps, previous_revenue, recent_date, next_start, next_end]
    ):
        return None

    return {
        "reported_eps": reported_eps,
        "estimated_eps": estimated_eps,
        "eps_change_pct": _pct_change(reported_eps, previous_eps),
        "reported_revenue": reported_revenue,
        "revenue_change_pct": _pct_change(reported_revenue, previous_revenue),
        "recent_earnings_date": recent_date,
        "next_earnings_date": next_start or next_end,
        "next_earnings_date_range": {
            "start": next_start,
            "end": next_end,
        },
        "surprise": {
            "eps_surprise_pct": None,
            "revenue_surprise_pct": None,
            "status": "unavailable",
            "note": "EPS and revenue surprise are omitted unless the free provider returns estimate and actual values.",
        },
        "history": [
            {"period": "latest annual", "eps": reported_eps, "revenue": reported_revenue},
            {"period": "previous annual", "eps": previous_eps, "revenue": previous_revenue},
        ],
    }


def _fair_value_label(margin_of_safety_pct: float | None) -> str:
    if margin_of_safety_pct is None:
        return "Unknown"
    if margin_of_safety_pct >= 25:
        return "Deeply undervalued"
    if margin_of_safety_pct >= 10:
        return "Undervalued"
    if margin_of_safety_pct >= -10:
        return "Fair value"
    if margin_of_safety_pct >= -25:
        return "Overvalued"
    return "Very overvalued"


def _valuation(ticker: str, current_price: float | None, financials: dict[str, Any] | None) -> dict[str, Any] | None:
    info = _safe_info(ticker)
    highlights = (financials or {}).get("highlights") or {}

    trailing_pe = _as_float(info.get("trailingPE"))
    forward_pe = _as_float(info.get("forwardPE"))
    peg_ratio = _as_float(info.get("pegRatio"))
    price_to_book = _as_float(info.get("priceToBook"))
    price_to_sales = _as_float(info.get("priceToSalesTrailing12Months"))
    dividend_yield = _as_float(info.get("dividendYield"))
    beta = _as_float(info.get("beta"))
    market_cap = _as_float(info.get("marketCap"))
    shares = _as_float(info.get("sharesOutstanding"))
    target_mean_price = _as_float(info.get("targetMeanPrice"))
    current_price = current_price or _as_float(info.get("currentPrice")) or _as_float(info.get("regularMarketPrice"))

    fcf = _as_float((highlights.get("free_cash_flow") or {}).get("latest")) or _as_float(info.get("freeCashflow"))
    eps = _as_float((highlights.get("eps") or {}).get("latest")) or _as_float(info.get("trailingEps")) or _as_float(info.get("forwardEps"))
    cash = _as_float((highlights.get("cash") or {}).get("latest")) or _as_float(info.get("totalCash"))
    debt = _as_float((highlights.get("total_debt") or {}).get("latest")) or _as_float(info.get("totalDebt"))
    revenue_growth_pct = _as_float((highlights.get("revenue") or {}).get("change_pct"))
    fcf_growth_pct = _as_float((highlights.get("free_cash_flow") or {}).get("change_pct"))
    info_growth = _as_float(info.get("earningsGrowth")) or _as_float(info.get("revenueGrowth"))

    if not _has_known_value(
        [
            current_price,
            trailing_pe,
            forward_pe,
            peg_ratio,
            price_to_book,
            price_to_sales,
            dividend_yield,
            beta,
            market_cap,
            shares,
            target_mean_price,
            fcf,
            eps,
            cash,
            debt,
            revenue_growth_pct,
            fcf_growth_pct,
            info_growth,
        ]
    ):
        return None

    if fcf_growth_pct is not None:
        growth_rate = _clamp(fcf_growth_pct / 100, -0.02, 0.12)
    elif revenue_growth_pct is not None:
        growth_rate = _clamp(revenue_growth_pct / 100, -0.02, 0.12)
    elif info_growth is not None:
        growth_rate = _clamp(info_growth, -0.02, 0.12)
    else:
        growth_rate = 0.04

    discount_rate = 0.10
    terminal_growth = 0.025
    projection_years = 5
    net_cash = (cash or 0) - (debt or 0)

    dcf_fair_value = None
    if fcf is not None and fcf > 0 and shares not in (None, 0):
        projected = [fcf * ((1 + growth_rate) ** year) for year in range(1, projection_years + 1)]
        present_values = [cash_flow / ((1 + discount_rate) ** year) for year, cash_flow in enumerate(projected, start=1)]
        terminal_value = projected[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
        present_terminal = terminal_value / ((1 + discount_rate) ** projection_years)
        equity_value = sum(present_values) + present_terminal + net_cash
        dcf_fair_value = equity_value / shares

    fair_pe = _clamp(15 + (growth_rate * 100), 8, 35)
    earnings_power_value = eps * fair_pe if eps is not None and eps > 0 else None

    estimates = {
        "dcf_fair_value": dcf_fair_value,
        "earnings_power_value": earnings_power_value,
        "analyst_target_mean": target_mean_price,
    }
    weighted_parts = [(dcf_fair_value, 0.45), (earnings_power_value, 0.35), (target_mean_price, 0.20)]
    available = [(value, weight) for value, weight in weighted_parts if value is not None and value > 0]
    fair_value = None
    if available:
        fair_value = sum(value * weight for value, weight in available) / sum(weight for _, weight in available)

    margin_of_safety_pct = None
    if fair_value is not None and current_price not in (None, 0):
        margin_of_safety_pct = ((fair_value - current_price) / current_price) * 100

    pe = forward_pe or trailing_pe
    ratio_score = _average_known([
        _score_from_ratio(pe, 18, 28, 45),
        _score_from_ratio(peg_ratio, 1.0, 1.8, 3.0),
        _score_from_ratio(price_to_sales, 3, 7, 12),
        _score_from_ratio(price_to_book, 3, 8, 15),
    ])
    fair_value_score = 50 if margin_of_safety_pct is None else _clamp_score(50 + margin_of_safety_pct * 1.4)
    score = _clamp_score(fair_value_score * 0.65 + ratio_score * 0.35)
    label = _fair_value_label(margin_of_safety_pct)

    return {
        "label": label,
        "score": score,
        "fair_value": {
            "current_price": current_price,
            "estimated_fair_value": fair_value,
            "margin_of_safety_pct": margin_of_safety_pct,
            "verdict": label,
            "estimates": estimates,
            "assumptions": {
                "growth_rate_pct": growth_rate * 100,
                "discount_rate_pct": discount_rate * 100,
                "terminal_growth_pct": terminal_growth * 100,
                "projection_years": projection_years,
                "fair_pe_multiple": fair_pe,
                "net_cash": net_cash,
            },
            "equation": "Fair value = 45% DCF value + 35% EPS x fair PE + 20% analyst target; margin of safety = (fair value - price) / price.",
        },
        "metrics": {
            "market_cap": market_cap,
            "trailing_pe": trailing_pe,
            "forward_pe": forward_pe,
            "peg_ratio": peg_ratio,
            "price_to_book": price_to_book,
            "price_to_sales": price_to_sales,
            "enterprise_to_ebitda": _as_float(info.get("enterpriseToEbitda")),
            "dividend_yield": dividend_yield,
            "beta": beta,
            "analyst_recommendation": info.get("recommendationKey"),
            "target_mean_price": target_mean_price,
        },
        "note": "Rule-based valuation screen for research context, not a professional appraisal.",
    }

def _balance_sheet(info: dict[str, Any], financials: dict[str, Any] | None) -> dict[str, Any] | None:
    highlights = (financials or {}).get("highlights") or {}
    cash = _as_float((highlights.get("cash") or {}).get("latest")) or _as_float(info.get("totalCash"))
    debt = _as_float((highlights.get("total_debt") or {}).get("latest")) or _as_float(info.get("totalDebt"))
    equity = _as_float((highlights.get("stockholders_equity") or {}).get("latest"))
    assets = _as_float((highlights.get("total_assets") or {}).get("latest"))
    liabilities = _as_float((highlights.get("total_liabilities") or {}).get("latest"))
    current_ratio = _as_float(info.get("currentRatio"))
    quick_ratio = _as_float(info.get("quickRatio"))
    debt_to_equity = _as_float(info.get("debtToEquity"))
    if debt_to_equity is not None and debt_to_equity > 20:
        debt_to_equity = debt_to_equity / 100

    if not _has_known_value([cash, debt, equity, assets, liabilities, current_ratio, quick_ratio, debt_to_equity]):
        return None

    debt_to_cash = debt / cash if debt is not None and cash not in (None, 0) else None
    liabilities_to_assets = liabilities / assets if liabilities is not None and assets not in (None, 0) else None
    equity_ratio = equity / assets if equity is not None and assets not in (None, 0) else None

    score = _average_known([
        _score_from_ratio(debt_to_cash, 1.0, 2.5, 5.0),
        _score_from_ratio(debt_to_equity, 0.8, 1.5, 3.0),
        85 if current_ratio is not None and current_ratio >= 1.5 else 60 if current_ratio is not None and current_ratio >= 1.0 else 30 if current_ratio is not None else None,
        85 if equity_ratio is not None and equity_ratio >= 0.45 else 60 if equity_ratio is not None and equity_ratio >= 0.25 else 35 if equity_ratio is not None else None,
    ])

    strengths = []
    concerns = []
    if cash is not None and debt is not None:
        if cash >= debt:
            strengths.append("Cash covers total debt")
        else:
            concerns.append("Debt is higher than cash")
    if current_ratio is not None:
        if current_ratio >= 1.5:
            strengths.append("Current ratio is healthy")
        elif current_ratio < 1:
            concerns.append("Current ratio is below 1")
    if debt_to_equity is not None and debt_to_equity > 2:
        concerns.append("Debt-to-equity is elevated")

    return {
        "score": score,
        "metrics": {
            "cash": cash,
            "total_debt": debt,
            "net_cash": (cash or 0) - (debt or 0) if cash is not None or debt is not None else None,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "debt_to_cash": debt_to_cash,
            "debt_to_equity": debt_to_equity,
            "liabilities_to_assets": liabilities_to_assets,
            "equity_ratio": equity_ratio,
        },
        "strengths": strengths,
        "concerns": concerns,
    }


def _dividend(info: dict[str, Any]) -> dict[str, Any] | None:
    dividend_yield = _as_float(info.get("dividendYield"))
    payout_ratio = _as_float(info.get("payoutRatio"))
    five_year_avg_yield = _as_float(info.get("fiveYearAvgDividendYield"))
    dividend_rate = _as_float(info.get("dividendRate"))

    if not _has_known_value([dividend_yield, payout_ratio, five_year_avg_yield, dividend_rate]):
        return None

    if dividend_yield is None or dividend_yield <= 0:
        score = 50
        label = "No meaningful dividend"
    else:
        yield_pct = dividend_yield * 100
        yield_score = 85 if 1.5 <= yield_pct <= 5 else 65 if yield_pct < 1.5 else 45
        payout_score = 80 if payout_ratio is not None and payout_ratio <= 0.65 else 55 if payout_ratio is not None and payout_ratio <= 0.9 else 35 if payout_ratio is not None else 50
        score = _average_known([yield_score, payout_score])
        label = "Healthy dividend" if score >= 70 else "Dividend needs review" if score >= 50 else "Dividend risk"

    return {
        "score": score,
        "label": label,
        "metrics": {
            "dividend_yield": dividend_yield,
            "dividend_rate": dividend_rate,
            "payout_ratio": payout_ratio,
            "five_year_avg_yield": five_year_avg_yield,
        },
    }


def _analyst(info: dict[str, Any], current_price: float | None) -> dict[str, Any] | None:
    target_mean = _as_float(info.get("targetMeanPrice"))
    target_high = _as_float(info.get("targetHighPrice"))
    target_low = _as_float(info.get("targetLowPrice"))
    opinion_count = _as_float(info.get("numberOfAnalystOpinions"))
    recommendation = info.get("recommendationKey")

    if not _has_known_value([target_mean, target_high, target_low, opinion_count, recommendation]):
        return None

    target_upside_pct = None
    if target_mean is not None and current_price not in (None, 0):
        target_upside_pct = ((target_mean - current_price) / current_price) * 100

    recommendation_score = {
        "strong_buy": 90,
        "buy": 75,
        "hold": 55,
        "underperform": 35,
        "sell": 20,
    }.get(str(recommendation or "").lower(), 50)
    target_score = 50 if target_upside_pct is None else _clamp_score(50 + target_upside_pct * 1.2)
    coverage_score = 60 if opinion_count is not None and opinion_count >= 10 else 50

    return {
        "score": _average_known([recommendation_score, target_score, coverage_score]),
        "recommendation": recommendation,
        "metrics": {
            "target_mean_price": target_mean,
            "target_high_price": target_high,
            "target_low_price": target_low,
            "target_upside_pct": target_upside_pct,
            "number_of_analyst_opinions": opinion_count,
        },
    }

def _risk_score(trend_risk: dict[str, Any] | None, valuation: dict[str, Any] | None, balance_sheet: dict[str, Any] | None) -> dict[str, Any]:
    volatility = _as_float((trend_risk or {}).get("volatility_20d_pct"))
    max_drawdown = _as_float((trend_risk or {}).get("max_drawdown_1y_pct"))
    beta = _as_float(((valuation or {}).get("metrics") or {}).get("beta"))
    balance_score = _as_float((balance_sheet or {}).get("score"))

    score = 70
    factors = []
    if volatility is not None:
        if volatility > 60:
            score -= 25
            factors.append("High recent volatility")
        elif volatility > 35:
            score -= 10
            factors.append("Elevated recent volatility")
        else:
            score += 5
            factors.append("Recent volatility looks manageable")

    if max_drawdown is not None:
        if max_drawdown < -45:
            score -= 15
            factors.append("Large one-year drawdown")
        elif max_drawdown > -20:
            score += 5
            factors.append("Drawdown has been contained")

    if beta is not None:
        if beta > 1.5:
            score -= 15
            factors.append("High beta versus market")
        elif beta < 0.8:
            score += 5
            factors.append("Lower beta versus market")

    if balance_score is not None:
        if balance_score < 40:
            score -= 10
            factors.append("Balance sheet adds risk")
        elif balance_score > 70:
            score += 5
            factors.append("Balance sheet reduces risk")

    if not factors:
        return {
            "score": 50,
            "factors": ["Risk data is limited for this ticker."],
        }

    return {"score": _clamp_score(score), "factors": factors}

def _verdict(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Mixed"
    if score >= 35:
        return "Weak"
    return "High risk"


def _weighted_score(scores: dict[str, int]) -> int:
    return _clamp_score(sum(scores.get(name, 50) * weight for name, weight in SCORE_WEIGHTS.items()))


def build_stock_analysis(ticker: str) -> dict[str, Any]:
    ticker = ticker.upper().strip()
    warnings: list[str] = []
    sources: list[str] = []

    market = _run_section(warnings, sources, "price_trend", lambda: _price_trend(ticker)) or {}
    prediction = _run_section(warnings, sources, "prediction", lambda: _prediction(ticker))
    news = _run_section(warnings, sources, "news", lambda: _news(ticker))
    financials = _run_section(warnings, sources, "financials", lambda: _financials(ticker))
    info = _safe_info(ticker)
    if info:
        sources.append("yahoo_profile")

    current_price = _as_float((market.get("price") or {}).get("current"))
    company = _company_profile(ticker, info, market.get("price"))
    earnings = _run_section(warnings, sources, "earnings", lambda: _earnings(info, financials))
    valuation = _run_section(warnings, sources, "valuation", lambda: _valuation(ticker, current_price, financials))
    balance_sheet = _run_section(warnings, sources, "balance_sheet", lambda: _balance_sheet(info, financials))
    dividend = _run_section(warnings, sources, "dividend", lambda: _dividend(info))
    analyst = _run_section(warnings, sources, "analyst", lambda: _analyst(info, current_price))
    risk = _risk_score(market.get("risk"), valuation, balance_sheet)

    category_scores = {
        "trend": int((market.get("trend") or {}).get("score") or 50),
        "liquidity": int((market.get("volume_liquidity") or {}).get("score") or 50),
        "fundamentals": int((financials or {}).get("score") or 50),
        "valuation": int((valuation or {}).get("score") or 50),
        "balance_sheet": int((balance_sheet or {}).get("score") or 50),
        "dividend": int((dividend or {}).get("score") or 50),
        "analyst": int((analyst or {}).get("score") or 50),
        "risk": int(risk.get("score") or 50),
        "news": int((news or {}).get("score") or 50),
    }
    overall_score = _weighted_score(category_scores)

    key_points = []
    trend_label = (market.get("trend") or {}).get("label")
    if trend_label:
        key_points.append(f"Trend is {str(trend_label).lower()} with a {category_scores['trend']}/100 trend score.")
    if financials:
        rev_change = financials["highlights"]["revenue"]["change_pct"]
        if rev_change is not None:
            key_points.append(f"Revenue changed {rev_change:.1f}% versus the previous annual period.")
    if valuation:
        mos = (valuation.get("fair_value") or {}).get("margin_of_safety_pct")
        if mos is not None:
            key_points.append(f"Valuation model says {valuation['label'].lower()} with {mos:.1f}% margin of safety.")
        else:
            key_points.append(f"Valuation screen: {valuation['label'].lower()}.")
    if balance_sheet:
        key_points.append(f"Balance sheet strength scores {category_scores['balance_sheet']}/100.")
    if prediction:
        key_points.append(f"Old ML model bias: {prediction['direction']} ({prediction['predicted_change_pct']}%).")
    if not key_points:
        key_points.append("Only limited data was available for this ticker.")

    response = {
        "ticker": ticker,
        "generated_at": datetime.now(pytz.utc).isoformat(),
        "summary": {
            "overall_score": overall_score,
            "verdict": _verdict(overall_score),
            "key_points": key_points[:6],
            "disclaimer": "Educational analysis only, not financial advice.",
        },
        "company": company,
        "price": market.get("price"),
        "trend": market.get("trend"),
        "volume_liquidity": market.get("volume_liquidity"),
        "price_history": market.get("price_history") or {"available_ranges": [], "ranges": {}},
        "technicals": {
            "moving_averages": (market.get("trend") or {}).get("moving_averages"),
            "returns": (market.get("trend") or {}).get("returns"),
        },
        "prediction": prediction,
        "news": news or {"items": [], "sentiment_counts": {"positive": 0, "negative": 0, "neutral": 0, "total": 0}, "score": 50},
        "financials": financials,
        "earnings": earnings,
        "valuation": valuation,
        "balance_sheet": balance_sheet,
        "dividend": dividend,
        "analyst": analyst,
        "risk": risk,
        "scores": {"overall": overall_score, **category_scores},
        "score_model": {
            "version": "phase-1-rule-based-v1",
            "weights": SCORE_WEIGHTS,
            "method": "Weighted 0-100 research snapshot from valuation, fundamentals, trend, balance sheet, risk, liquidity, analyst, news, and dividend signals.",
        },
        "reddit": {
            "disabled": True,
            "reason": "Live Reddit fetching is disabled to avoid token/rate-limit crashes.",
        },
        "data_quality": {"sources": sources, "warnings": warnings},
    }
    return json_safe(response)
