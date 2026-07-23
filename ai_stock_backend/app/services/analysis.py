from __future__ import annotations

import os
import re
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
    "valuation": 0.24,
    "fundamentals": 0.20,
    "trend": 0.18,
    "balance_sheet": 0.14,
    "risk": 0.12,
    "liquidity": 0.06,
    "analyst": 0.04,
    "dividend": 0.02,
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



PRICE_DELAY_NOTE = (
    "Price quotes come from free Yahoo/yfinance endpoints. They can be delayed, "
    "adjusted, or unavailable and are not guaranteed real-time exchange data."
)


def _market_timestamp_to_iso(value: Any) -> str | None:
    n = _as_float(value)
    if n is None:
        return None
    if n > 10_000_000_000:
        n = n / 1000
    try:
        return datetime.fromtimestamp(n, tz=pytz.utc).isoformat()
    except Exception:
        return None


def _index_timestamp_to_iso(value: Any) -> str | None:
    try:
        if hasattr(value, "to_pydatetime"):
            dt = value.to_pydatetime()
        else:
            dt = value
        if getattr(dt, "tzinfo", None) is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(pytz.utc).isoformat()
    except Exception:
        return None


def _fast_info_get(fast_info: Any, key: str) -> Any:
    try:
        if hasattr(fast_info, "get"):
            return fast_info.get(key)
    except Exception:
        pass
    try:
        return getattr(fast_info, key)
    except Exception:
        pass
    try:
        return fast_info[key]
    except Exception:
        return None


def _latest_intraday_quote(ticker_obj: Any) -> dict[str, Any] | None:
    for interval in ("1m", "5m", "15m"):
        try:
            frame = ticker_obj.history(
                period="5d",
                interval=interval,
                prepost=True,
                auto_adjust=False,
            )
        except Exception:
            continue

        if frame is None or getattr(frame, "empty", True) or "Close" not in frame:
            continue

        close = frame["Close"].dropna()
        if close.empty:
            continue

        current = _as_float(close.iloc[-1])
        if current is None:
            continue

        return {
            "current": current,
            "as_of": _index_timestamp_to_iso(close.index[-1]),
            "source": f"yfinance_history_{interval}_prepost",
            "session": "intraday_or_extended",
        }

    return None


def _latest_quote(ticker: str) -> dict[str, Any] | None:
    ticker_obj = yf.Ticker(ticker)
    info: dict[str, Any] = {}
    try:
        info = ticker_obj.info or {}
    except Exception:
        info = {}

    try:
        fast_info = ticker_obj.fast_info
    except Exception:
        fast_info = {}

    candidates: list[dict[str, Any]] = []

    def add_candidate(source: str, price_key: str, time_key: str | None, session: str) -> None:
        price = _as_float(info.get(price_key))
        if price is None:
            return
        candidates.append({
            "current": price,
            "as_of": _market_timestamp_to_iso(info.get(time_key)) if time_key else None,
            "source": source,
            "session": session,
        })

    add_candidate("yfinance_info_post_market", "postMarketPrice", "postMarketTime", "after_hours")
    add_candidate("yfinance_info_pre_market", "preMarketPrice", "preMarketTime", "pre_market")
    add_candidate("yfinance_info_regular_market", "regularMarketPrice", "regularMarketTime", "regular")
    add_candidate("yfinance_info_current_price", "currentPrice", "regularMarketTime", "regular")

    fast_last = _as_float(_fast_info_get(fast_info, "last_price"))
    if fast_last is not None:
        candidates.append({
            "current": fast_last,
            "as_of": None,
            "source": "yfinance_fast_info_last_price",
            "session": "latest_available",
        })

    intraday = _latest_intraday_quote(ticker_obj)
    if intraday:
        candidates.append(intraday)

    timed_candidates = [candidate for candidate in candidates if candidate.get("as_of")]
    if timed_candidates:
        selected = max(timed_candidates, key=lambda candidate: candidate["as_of"])
    elif candidates:
        selected = candidates[0]
    else:
        return None

    previous_close = (
        _as_float(info.get("regularMarketPreviousClose"))
        or _as_float(info.get("previousClose"))
        or _as_float(_fast_info_get(fast_info, "previous_close"))
    )
    currency = info.get("currency") or _fast_info_get(fast_info, "currency") or "USD"

    return {
        **selected,
        "previous_close": previous_close,
        "day_change_pct": _pct_change(selected.get("current"), previous_close),
        "currency": currency,
        "is_realtime": False,
        "delay_note": PRICE_DELAY_NOTE,
    }


def _price_payload_from_history_and_quote(
    history_current: float | None,
    history_previous: float | None,
    quote: dict[str, Any] | None,
) -> dict[str, Any]:
    current = _as_float((quote or {}).get("current"))
    previous = _as_float((quote or {}).get("previous_close"))
    if current is None:
        current = history_current
    if previous is None:
        previous = history_previous

    return {
        "current": current,
        "previous_close": previous,
        "day_change_pct": _pct_change(current, previous),
        "currency": (quote or {}).get("currency") or "USD",
        "source": (quote or {}).get("source") or "yfinance_adjusted_daily_history",
        "session": (quote or {}).get("session") or "latest_close",
        "as_of": (quote or {}).get("as_of"),
        "is_realtime": False,
        "delay_note": PRICE_DELAY_NOTE,
    }

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
    now_eastern = datetime.now(eastern)
    end_date = (now_eastern + timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (now_eastern - timedelta(days=365 * 5)).strftime(
        "%Y-%m-%d"
    )

    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None or stock_data.empty:
        raise ValueError("No price history returned")

    close = stock_data["Close"]
    volume = stock_data["Volume"]
    history_current = _as_float(close.iloc[-1])
    history_previous = _as_float(close.iloc[-2]) if len(close) > 1 else None
    latest_quote = _latest_quote(ticker)
    price_payload = _price_payload_from_history_and_quote(
        history_current,
        history_previous,
        latest_quote,
    )
    current = _as_float(price_payload.get("current"))
    previous = _as_float(price_payload.get("previous_close"))

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
    history_last_trading_date = history[-1]["date"] if history else None
    completed_days_stale = None
    history_warning = None
    if history_last_trading_date:
        try:
            last_date = datetime.strptime(history_last_trading_date, "%Y-%m-%d").date()
            today = now_eastern.date()
            cursor = last_date + timedelta(days=1)
            completed = 0
            while cursor < today:
                if cursor.weekday() < 5:
                    completed += 1
                cursor += timedelta(days=1)
            completed_days_stale = completed
            if completed > 1:
                history_warning = f"Historical daily prices end on {history_last_trading_date}, more than one completed trading day behind the quote."
        except Exception:
            pass

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
        "price": price_payload,
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
            "history_last_trading_date": history_last_trading_date,
            "history_cache_as_of": datetime.now(pytz.utc).isoformat(),
            "trend_calculation_as_of": datetime.now(pytz.utc).isoformat(),
            "quote_as_of": price_payload.get("as_of"),
            "stale_completed_trading_days": completed_days_stale,
            "confidence": "low" if history_warning else "medium",
            "warnings": [history_warning] if history_warning else [],
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

    history_current = _as_float(stock_data["Close"].iloc[-1])
    latest_quote = _latest_quote(ticker)
    price_payload = _price_payload_from_history_and_quote(
        history_current,
        None,
        latest_quote,
    )
    current_price = _as_float(price_payload.get("current"))
    if current_price is None:
        raise ValueError("Unable to resolve current price for prediction")
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
        "current_price_source": price_payload.get("source"),
        "current_price_session": price_payload.get("session"),
        "current_price_as_of": price_payload.get("as_of"),
        "price_delay_note": price_payload.get("delay_note"),
        "model_info": {
            "direction_model": result["direction"]["best_model_name"],
            "magnitude_model": result["magnitude"]["best_model_name"],
            "cached": result["cached"],
        },
    }


def _company_terms(ticker: str, info: dict[str, Any] | None = None) -> set[str]:
    info = info or {}
    terms = {ticker.upper()}
    for field in ("longName", "shortName"):
        name = str(info.get(field) or "").strip()
        if name:
            terms.add(name.lower())
            for token in re.findall(r"[A-Za-z][A-Za-z0-9]+", name):
                if len(token) >= 4 and token.lower() not in {"inc", "corp", "corporation", "company", "class", "ordinary", "limited", "holdings"}:
                    terms.add(token.lower())
    return terms


def _headline_relevance(ticker: str, headline: str, info: dict[str, Any] | None = None) -> dict[str, Any]:
    text = str(headline or "")
    lower = text.lower()
    terms = _company_terms(ticker, info)
    matched = []
    for term in terms:
        if term == ticker.upper():
            if re.search(rf"(?<![A-Z0-9]){re.escape(term)}(?![A-Z0-9])", text.upper()):
                matched.append(term)
        elif term and term in lower:
            matched.append(term)
    score = min(100, 35 * len(set(matched)))
    return {
        "score": score,
        "status": "relevant" if score >= 35 else "excluded_unrelated",
        "matched_terms": sorted(set(matched)),
    }


def _news(ticker: str, info: dict[str, Any] | None = None) -> dict[str, Any]:
    from app.headline.src.fetch_news import get_top_headlines
    from app.headline.src.predictor import predict_sentiments

    raw_headlines = get_top_headlines(ticker) or []
    relevant_items = []
    excluded = []
    for headline in raw_headlines:
        relevance = _headline_relevance(ticker, headline, info)
        item = {"headline": headline, "relevance": relevance, "source": "free_news_fetcher", "published_at": None}
        if relevance["status"] == "relevant":
            relevant_items.append(item)
        else:
            excluded.append(item)

    sentiments = predict_sentiments([item["headline"] for item in relevant_items]) if relevant_items else []
    for item, sentiment in zip(relevant_items, sentiments):
        item["sentiment"] = sentiment

    counts = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
    for item in relevant_items:
        s = str(item.get("sentiment") or "neutral").lower()
        if "pos" in s:
            counts["positive"] += 1
        elif "neg" in s:
            counts["negative"] += 1
        else:
            counts["neutral"] += 1
        counts["total"] += 1

    return {
        "items": relevant_items,
        "sentiment_counts": counts,
        "score": 50,
        "score_excluded_from_phase1": True,
        "excluded_count": len(excluded),
        "relevance_filter": {
            "status": "active",
            "minimum_score": 35,
            "terms": sorted(_company_terms(ticker, info)),
        },
    }
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
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingDiluted",
            "WeightedAverageDilutedSharesOutstanding",
            "DilutedAverageShares",
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
                "Diluted Average Shares": _first_row_value(
                    row,
                    "WeightedAverageNumberOfDilutedSharesOutstanding",
                    "WeightedAverageNumberOfSharesOutstandingDiluted",
                    "WeightedAverageDilutedSharesOutstanding",
                    "DilutedAverageShares",
                ),
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

    profile_shares = _as_float(info.get("sharesOutstanding"))
    book_value = _as_float(info.get("bookValue"))
    revenue_growth = _as_float(info.get("revenueGrowth"))
    earnings_growth = _as_float(info.get("earningsGrowth"))

    latest = {
        "Total Revenue": _as_float(info.get("totalRevenue")),
        "Diluted EPS": _as_float(info.get("trailingEps")) or _as_float(info.get("forwardEps")),
        "Diluted Average Shares": _as_float(info.get("sharesOutstanding")),
        "Net Income": _as_float(info.get("netIncomeToCommon")),
        "Gross Profit": _as_float(info.get("grossProfits")),
        "Operating Cash Flow": _as_float(info.get("operatingCashflow")),
        "Free Cash Flow": _as_float(info.get("freeCashflow")),
        "Total Debt": _as_float(info.get("totalDebt")),
        "Cash And Cash Equivalents": _as_float(info.get("totalCash")),
        "Stockholders Equity": (book_value * profile_shares) if book_value is not None and profile_shares is not None else None,
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
        "diluted_shares": ("Diluted Average Shares",),
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


def _local_cik_for_ticker(ticker: str) -> str | None:
    try:
        import pandas as pd
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "financial_statement" / "data" / "sec_company_tickers.csv"
        if not path.exists():
            return None
        rows = pd.read_csv(path)
        match = rows[rows["ticker"].astype(str).str.upper() == ticker.upper()]
        if match.empty:
            return None
        cik = str(match.iloc[0]["company_id"]).strip()
        return cik.zfill(10)
    except Exception:
        return None


def _latest_fact_for_tags(facts: dict[str, Any], tags: list[str], unit: str, period_end: str | None = None) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for tag in tags:
        units = ((facts.get(tag) or {}).get("units") or {})
        for item in units.get(unit, []):
            end = item.get("end")
            form = item.get("form")
            if form not in ("10-Q", "10-K") or not end:
                continue
            if period_end is not None and end != period_end:
                continue
            value = _as_float(item.get("val"))
            if value is None:
                continue
            candidates.append({"tag": tag, **item, "val": value})
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (str(item.get("end") or ""), str(item.get("filed") or "")), reverse=True)[0]


def _sec_balance_sheet_snapshot(ticker: str) -> dict[str, Any] | None:
    cik = _local_cik_for_ticker(ticker)
    if not cik:
        return None
    try:
        import requests

        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        headers = {"User-Agent": "stockPredictionApp educational local contact@example.com"}
        payload = requests.get(url, headers=headers, timeout=12).json()
    except Exception:
        return None

    facts = ((payload.get("facts") or {}).get("us-gaap") or {})
    if not facts:
        return None

    anchor = _latest_fact_for_tags(facts, ["AssetsCurrent"], "USD")
    if not anchor:
        return None
    period_end = anchor.get("end")
    form = anchor.get("form")
    filed = anchor.get("filed")

    def usd(name: str, tags: list[str]) -> tuple[float | None, str | None]:
        item = _latest_fact_for_tags(facts, tags, "USD", period_end)
        if not item:
            return None, None
        return _as_float(item.get("val")), item.get("tag")

    def shares(tags: list[str]) -> tuple[float | None, str | None]:
        item = _latest_fact_for_tags(facts, tags, "shares", period_end)
        if not item:
            # Outstanding shares are often reported on a date shortly after quarter end.
            item = _latest_fact_for_tags(facts, tags, "shares")
        if not item:
            return None, None
        return _as_float(item.get("val")), item.get("tag")

    cash, cash_tag = usd("cash", ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"])
    marketable, marketable_tag = usd("marketable", ["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"])
    current_assets, current_assets_tag = usd("current_assets", ["AssetsCurrent"])
    current_liabilities, current_liabilities_tag = usd("current_liabilities", ["LiabilitiesCurrent"])
    short_debt, short_debt_tag = usd("short_debt", ["ShortTermBorrowings", "ShortTermDebtCurrent", "LongTermDebtCurrent", "DebtCurrent"])
    long_debt, long_debt_tag = usd("long_debt", ["LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent", "LongTermDebt"])
    lease_current, lease_current_tag = usd("lease_current", ["OperatingLeaseLiabilityCurrent", "FinanceLeaseLiabilityCurrent"])
    lease_noncurrent, lease_noncurrent_tag = usd("lease_noncurrent", ["OperatingLeaseLiabilityNoncurrent", "FinanceLeaseLiabilityNoncurrent"])
    total_shares, shares_tag = shares(["EntityCommonStockSharesOutstanding", "CommonStocksIncludingAdditionalPaidInCapitalSharesOutstanding"])

    short_debt = short_debt or 0
    long_debt = long_debt or 0
    lease_liabilities = (lease_current or 0) + (lease_noncurrent or 0) if lease_current is not None or lease_noncurrent is not None else None
    total_interest_debt = short_debt + long_debt
    total_liquid_assets = (cash or 0) + (marketable or 0) if cash is not None or marketable is not None else None
    source_fields = {
        "cash_and_equivalents": cash_tag,
        "marketable_securities": marketable_tag,
        "current_assets": current_assets_tag,
        "current_liabilities": current_liabilities_tag,
        "short_term_debt": short_debt_tag,
        "long_term_debt": long_debt_tag,
        "lease_current": lease_current_tag,
        "lease_noncurrent": lease_noncurrent_tag,
        "share_count": shares_tag,
    }

    return {
        "period_end": period_end,
        "form": form,
        "filed": filed,
        "cash_and_equivalents": cash,
        "marketable_securities": marketable,
        "total_liquid_assets": total_liquid_assets,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "current_ratio": current_assets / current_liabilities if current_assets is not None and current_liabilities not in (None, 0) else None,
        "short_term_debt": short_debt,
        "long_term_debt": long_debt,
        "total_interest_bearing_debt": total_interest_debt,
        "lease_liabilities": lease_liabilities,
        "strict_cash_net_debt": total_interest_debt - cash if cash is not None else None,
        "liquidity_adjusted_net_cash": total_liquid_assets - total_interest_debt if total_liquid_assets is not None else None,
        "debt_to_cash": total_interest_debt / cash if cash not in (None, 0) else None,
        "debt_to_liquid_assets": total_interest_debt / total_liquid_assets if total_liquid_assets not in (None, 0) else None,
        "share_count": total_shares,
        "share_count_source": shares_tag,
        "source": "sec_companyfacts",
        "source_fields": source_fields,
        "warnings": [] if marketable is not None else ["SEC marketable securities field was unavailable for this period."],
    }


def _fallback_balance_sheet_snapshot(info: dict[str, Any], financials: dict[str, Any] | None) -> dict[str, Any] | None:
    highlights = (financials or {}).get("highlights") or {}
    cash = _as_float((highlights.get("cash") or {}).get("latest")) or _as_float(info.get("totalCash"))
    debt = _as_float((highlights.get("total_debt") or {}).get("latest")) or _as_float(info.get("totalDebt"))
    current_ratio = _as_float(info.get("currentRatio"))
    current_liabilities = _as_float(info.get("totalCurrentLiabilities"))
    current_assets = current_ratio * current_liabilities if current_ratio is not None and current_liabilities is not None else None
    if not _has_known_value([cash, debt, current_ratio, current_assets, current_liabilities]):
        return None
    return {
        "period_end": None,
        "form": None,
        "filed": None,
        "cash_and_equivalents": cash,
        "marketable_securities": None,
        "total_liquid_assets": cash,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "current_ratio": current_ratio,
        "short_term_debt": None,
        "long_term_debt": debt,
        "total_interest_bearing_debt": debt,
        "lease_liabilities": None,
        "strict_cash_net_debt": debt - cash if debt is not None and cash is not None else None,
        "liquidity_adjusted_net_cash": cash - debt if debt is not None and cash is not None else None,
        "debt_to_cash": debt / cash if debt is not None and cash not in (None, 0) else None,
        "debt_to_liquid_assets": debt / cash if debt is not None and cash not in (None, 0) else None,
        "share_count": _as_float(info.get("sharesOutstanding")),
        "share_count_source": "yfinance_profile_sharesOutstanding",
        "source": "yahoo_fallback_mixed_periods",
        "source_fields": {
            "cash_and_equivalents": "financials.cash.latest_or_yfinance.totalCash",
            "total_interest_bearing_debt": "financials.total_debt.latest_or_yfinance.totalDebt",
            "current_ratio": "yfinance.currentRatio",
        },
        "warnings": ["SEC same-period balance sheet was unavailable; using clearly labeled Yahoo/profile fallback that may mix periods."],
    }

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


def _parse_provider_timestamp(value: Any) -> datetime | None:
    n = _as_float(value)
    if n is None or n <= 0:
        return None
    if n > 10_000_000_000:
        n = n / 1000
    try:
        return datetime.fromtimestamp(n, tz=pytz.utc)
    except Exception:
        return None


def _earnings_date_selection(info: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(pytz.utc)
    if now.tzinfo is None:
        now = pytz.utc.localize(now)

    candidates: list[dict[str, Any]] = []
    for key, status in (
        ("earningsTimestamp", "estimated"),
        ("earningsTimestampStart", "estimated"),
        ("earningsTimestampEnd", "estimated"),
    ):
        dt = _parse_provider_timestamp(info.get(key))
        if dt is not None:
            candidates.append({"date": dt, "source_field": key, "status": status})

    for value in info.get("earningsDate") or []:
        dt = _parse_provider_timestamp(value)
        if dt is not None:
            candidates.append({"date": dt, "source_field": "earningsDate", "status": "estimated"})

    unique = {}
    for item in candidates:
        unique[item["date"].isoformat()] = item
    ordered = sorted(unique.values(), key=lambda item: item["date"])

    # yfinance can return today's date as a placeholder. Do not present it as a real recent event.
    past = [item for item in ordered if item["date"] < now and item["date"].date() != now.date()]
    future = [item for item in ordered if item["date"] > now]
    recent = past[-1] if past else None
    next_item = future[0] if future else None
    if recent and next_item and recent["date"].date() == next_item["date"].date():
        recent = None

    return {
        "recent": recent,
        "next": next_item,
        "candidates": [
            {"date": item["date"].isoformat(), "source_field": item["source_field"], "status": item["status"]}
            for item in ordered
        ],
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
    earnings_dates = _earnings_date_selection(info)
    recent_item = earnings_dates.get("recent")
    next_item = earnings_dates.get("next")
    recent_date = recent_item["date"].isoformat() if recent_item else None
    next_date = next_item["date"].isoformat() if next_item else None

    if not _has_known_value(
        [reported_eps, estimated_eps, reported_revenue, previous_eps, previous_revenue, recent_date, next_date]
    ):
        return None

    return {
        "reported_eps": reported_eps,
        "estimated_eps": estimated_eps,
        "eps_change_pct": _pct_change(reported_eps, previous_eps),
        "reported_revenue": reported_revenue,
        "revenue_change_pct": _pct_change(reported_revenue, previous_revenue),
        "recent_earnings_date": recent_date,
        "next_earnings_date": next_date,
        "recent_earnings_date_status": recent_item.get("status") if recent_item else None,
        "next_earnings_date_status": next_item.get("status") if next_item else None,
        "earnings_date_candidates": earnings_dates.get("candidates", []),
        "next_earnings_date_range": {
            "start": next_date,
            "end": next_date,
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


def _valuation(ticker: str, current_price: float | None, financials: dict[str, Any] | None, balance_sheet: dict[str, Any] | None = None) -> dict[str, Any] | None:
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
    profile_shares = _as_float(info.get("sharesOutstanding"))
    target_mean_price = _as_float(info.get("targetMeanPrice"))
    current_price = current_price or _as_float(info.get("currentPrice")) or _as_float(info.get("regularMarketPrice"))

    fcf = _as_float((highlights.get("free_cash_flow") or {}).get("latest")) or _as_float(info.get("freeCashflow"))
    eps = _as_float((highlights.get("eps") or {}).get("latest")) or _as_float(info.get("trailingEps")) or _as_float(info.get("forwardEps"))
    balance_metrics = (balance_sheet or {}).get("metrics") or {}
    cash = _as_float(balance_metrics.get("cash_and_equivalents")) or _as_float((highlights.get("cash") or {}).get("latest")) or _as_float(info.get("totalCash"))
    marketable_securities = _as_float(balance_metrics.get("marketable_securities"))
    total_liquid_assets = _as_float(balance_metrics.get("total_liquid_assets"))
    short_term_debt = _as_float(balance_metrics.get("short_term_debt"))
    long_term_debt = _as_float(balance_metrics.get("long_term_debt"))
    debt = _as_float(balance_metrics.get("total_interest_bearing_debt")) or _as_float((highlights.get("total_debt") or {}).get("latest")) or _as_float(info.get("totalDebt"))
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
            profile_shares,
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
    cash_for_bridge = cash or 0
    marketable_for_bridge = marketable_securities or 0
    liquid_for_bridge = total_liquid_assets if total_liquid_assets is not None else cash_for_bridge + marketable_for_bridge
    debt_for_bridge = debt or 0
    net_cash = liquid_for_bridge - debt_for_bridge
    diluted_shares = _as_float((highlights.get("diluted_shares") or {}).get("latest"))
    current_share_count = _as_float(balance_metrics.get("share_count"))
    shares_for_dcf = current_share_count or diluted_shares or profile_shares
    if current_share_count is not None:
        share_source = str(balance_metrics.get("share_count_source") or "sec_current_total_shares")
    else:
        share_source = "financial_statement_diluted_average_shares" if diluted_shares else "yfinance_profile_shares_outstanding"

    dcf_fair_value = None
    dcf_breakdown: dict[str, Any] = {
        "normalized_free_cash_flow": fcf,
        "forecast_growth_pct": growth_rate * 100,
        "forecast_period_years": projection_years,
        "discount_rate_pct": discount_rate * 100,
        "terminal_growth_pct": terminal_growth * 100,
        "pv_forecast_cash_flows": None,
        "pv_terminal_value": None,
        "enterprise_value": None,
        "cash_and_equivalents": cash,
        "eligible_marketable_securities": marketable_securities,
        "total_liquid_assets": liquid_for_bridge,
        "short_term_interest_bearing_debt": short_term_debt,
        "long_term_interest_bearing_debt": long_term_debt,
        "debt_included_in_bridge": debt,
        "other_adjustments": 0,
        "balance_sheet_period_end": (balance_sheet or {}).get("period_end"),
        "balance_sheet_source": (balance_sheet or {}).get("source"),
        "marketable_securities_included": marketable_securities is not None,
        "debt_subtracted": debt,
        "equity_value": None,
        "total_diluted_shares": shares_for_dcf,
        "share_count_source": share_source if shares_for_dcf is not None else None,
        "per_share_estimate": None,
        "warnings": [],
    }
    if discount_rate <= terminal_growth:
        dcf_breakdown["warnings"].append("Discount rate must be greater than terminal growth.")
    if diluted_shares is None and profile_shares is not None:
        dcf_breakdown["warnings"].append(
            "Diluted shares were unavailable; using yfinance profile sharesOutstanding fallback. For multi-class companies this may be less reliable."
        )
    if fcf is None or fcf <= 0:
        dcf_breakdown["warnings"].append("Free cash flow is missing or non-positive, so DCF is unavailable.")
    if shares_for_dcf in (None, 0):
        dcf_breakdown["warnings"].append("Share count is missing or zero, so DCF is unavailable.")

    if fcf is not None and fcf > 0 and shares_for_dcf not in (None, 0) and discount_rate > terminal_growth:
        projected = [fcf * ((1 + growth_rate) ** year) for year in range(1, projection_years + 1)]
        present_values = [cash_flow / ((1 + discount_rate) ** year) for year, cash_flow in enumerate(projected, start=1)]
        terminal_value = projected[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
        present_terminal = terminal_value / ((1 + discount_rate) ** projection_years)
        enterprise_value = sum(present_values) + present_terminal
        equity_value = enterprise_value + liquid_for_bridge - debt_for_bridge
        dcf_fair_value = equity_value / shares_for_dcf
        dcf_breakdown.update({
            "pv_forecast_cash_flows": sum(present_values),
            "pv_terminal_value": present_terminal,
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "per_share_estimate": dcf_fair_value,
        })

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
                "liquidity_adjusted_net_cash": net_cash,
                "share_count_source": share_source,
            },
            "blended_reference_value": fair_value,
            "intrinsic_estimates": {
                "dcf_value": dcf_fair_value,
                "earnings_power_value": earnings_power_value,
            },
            "analyst_reference": target_mean_price,
            "dcf_breakdown": dcf_breakdown,
            "equation": "Blended reference = 45% DCF value + 35% EPS x fair PE + 20% analyst target; margin = (blended reference - price) / price. Analyst target is not intrinsic value.",
        },
        "metrics": {
            "market_cap": market_cap,
            "shares_used_for_dcf": shares_for_dcf,
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

def _balance_sheet(ticker: str, info: dict[str, Any], financials: dict[str, Any] | None) -> dict[str, Any] | None:
    snapshot = _sec_balance_sheet_snapshot(ticker) or _fallback_balance_sheet_snapshot(info, financials)
    if not snapshot:
        return None

    cash = _as_float(snapshot.get("cash_and_equivalents"))
    liquid_assets = _as_float(snapshot.get("total_liquid_assets"))
    debt = _as_float(snapshot.get("total_interest_bearing_debt"))
    current_ratio = _as_float(snapshot.get("current_ratio"))
    debt_to_cash = _as_float(snapshot.get("debt_to_cash"))
    debt_to_liquid_assets = _as_float(snapshot.get("debt_to_liquid_assets"))
    liquidity_net_cash = _as_float(snapshot.get("liquidity_adjusted_net_cash"))

    liquidity_score = None
    if current_ratio is not None:
        liquidity_score = 90 if current_ratio >= 2 else 75 if current_ratio >= 1.5 else 55 if current_ratio >= 1 else 30
    debt_cash_score = _score_from_ratio(debt_to_cash, 0.5, 1.5, 3.0)
    debt_liquid_score = _score_from_ratio(debt_to_liquid_assets, 0.4, 0.9, 1.5)
    net_cash_score = 85 if liquidity_net_cash is not None and liquidity_net_cash >= 0 else 45 if liquidity_net_cash is not None else None
    score = _average_known([liquidity_score, debt_cash_score, debt_liquid_score, net_cash_score])

    strengths = []
    concerns = []
    if liquid_assets is not None and debt is not None:
        if liquid_assets >= debt:
            strengths.append("Liquid assets cover interest-bearing debt")
        else:
            concerns.append("Interest-bearing debt exceeds liquid assets")
    if cash is not None and debt is not None:
        if cash >= debt:
            strengths.append("Cash alone covers interest-bearing debt")
        else:
            concerns.append("Cash-only net debt is positive")
    if current_ratio is not None:
        if current_ratio >= 1.5:
            strengths.append("Current ratio is healthy for the reported period")
        elif current_ratio < 1:
            concerns.append("Current liabilities exceed current assets")
    if snapshot.get("lease_liabilities") is not None:
        strengths.append("Lease liabilities are reported separately from interest-bearing debt")

    metrics = {
        "period_end": snapshot.get("period_end"),
        "cash_and_equivalents": cash,
        "marketable_securities": _as_float(snapshot.get("marketable_securities")),
        "total_liquid_assets": liquid_assets,
        "current_assets": _as_float(snapshot.get("current_assets")),
        "current_liabilities": _as_float(snapshot.get("current_liabilities")),
        "current_ratio": current_ratio,
        "short_term_debt": _as_float(snapshot.get("short_term_debt")),
        "long_term_debt": _as_float(snapshot.get("long_term_debt")),
        "total_interest_bearing_debt": debt,
        "lease_liabilities": _as_float(snapshot.get("lease_liabilities")),
        "strict_cash_net_debt": _as_float(snapshot.get("strict_cash_net_debt")),
        "liquidity_adjusted_net_cash": liquidity_net_cash,
        "debt_to_cash": debt_to_cash,
        "debt_to_liquid_assets": debt_to_liquid_assets,
        "share_count": _as_float(snapshot.get("share_count")),
        "cash": cash,
        "total_debt": debt,
        "net_cash": liquidity_net_cash,
    }

    return {
        "score": score,
        "period_end": snapshot.get("period_end"),
        "source": snapshot.get("source"),
        "source_fields": snapshot.get("source_fields") or {},
        "warnings": snapshot.get("warnings") or [],
        "leases_included_in_debt": False,
        "metrics": metrics,
        "strengths": strengths,
        "concerns": concerns,
    }

def _normalized_dividend_yield(raw_yield: Any, dividend_rate: Any = None, current_price: Any = None) -> float | None:
    raw = _as_float(raw_yield)
    rate = _as_float(dividend_rate)
    price = _as_float(current_price)
    calculated = rate / price if rate is not None and price not in (None, 0) else None
    if calculated is not None and calculated >= 0:
        if raw is None or raw <= 0 or raw > 0.20 or abs(raw - calculated) > 0.05:
            return calculated
    if raw is None:
        return None
    if raw > 1:
        return raw / 100
    return raw


def _dividend(info: dict[str, Any], current_price: float | None = None) -> dict[str, Any] | None:
    dividend_rate = _as_float(info.get("dividendRate"))
    dividend_yield = _normalized_dividend_yield(info.get("dividendYield"), dividend_rate, current_price)
    payout_ratio = _as_float(info.get("payoutRatio"))
    five_year_avg_yield = _as_float(info.get("fiveYearAvgDividendYield"))
    if five_year_avg_yield is not None and five_year_avg_yield > 1:
        five_year_avg_yield = five_year_avg_yield / 100

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
            "dividend_yield_pct": dividend_yield * 100 if dividend_yield is not None else None,
            "dividend_rate": dividend_rate,
            "payout_ratio": payout_ratio,
            "five_year_avg_yield": five_year_avg_yield,
            "yield_convention": "decimal_internal_display_percent",
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

    components: list[dict[str, Any]] = []

    def add_component(name: str, value: float | None, risk_level: float | None, weight: float, direction: str, note: str) -> None:
        components.append({
            "name": name,
            "value": value,
            "risk_level": _clamp_score(risk_level) if risk_level is not None else None,
            "weight": weight,
            "direction": direction,
            "note": note,
        })

    vol_level = None
    if volatility is not None:
        vol_level = _clamp((volatility - 15) * 1.6, 5, 95)
    add_component("Realized volatility", volatility, vol_level, 0.24, "higher_value_higher_risk", "20-day annualized realized volatility")

    drawdown_level = None
    if max_drawdown is not None:
        drawdown_level = _clamp(abs(min(max_drawdown, 0)) * 1.6, 0, 95)
    add_component("Maximum drawdown", max_drawdown, drawdown_level, 0.20, "more_negative_higher_risk", "Worst one-year drawdown from daily history")

    beta_level = None
    if beta is not None:
        beta_level = _clamp(50 + (beta - 1) * 35, 5, 95)
    add_component("Beta", beta, beta_level, 0.16, "higher_value_higher_risk", "Market beta from free profile data")

    debt_level = None
    if balance_score is not None:
        debt_level = _clamp(100 - balance_score, 0, 100)
    add_component("Debt/liquidity", balance_score, debt_level, 0.20, "lower_balance_score_higher_risk", "Derived from same-period balance-sheet strength")

    add_component("FCF stability", None, None, 0.10, "unavailable_neutral", "Needs multi-period FCF history metadata")
    add_component("Earnings stability", None, None, 0.10, "unavailable_neutral", "Needs multi-period earnings metadata")

    available = [item for item in components if item["risk_level"] is not None]
    if not available:
        return {
            "score": 50,
            "risk_level": 50,
            "risk_safety_score": 50,
            "factors": ["Risk data is limited for this ticker."],
            "components": components,
            "data_window": (trend_risk or {}).get("data_window") or "limited",
        }

    total_weight = sum(float(item["weight"]) for item in available)
    risk_level = sum(float(item["risk_level"]) * float(item["weight"]) for item in available) / total_weight
    risk_level_score = _clamp_score(risk_level)
    safety_score = _clamp_score(100 - risk_level_score)

    factors = []
    if volatility is not None:
        factors.append("Elevated recent volatility" if volatility > 35 else "Recent volatility looks manageable")
    if max_drawdown is not None and max_drawdown < -35:
        factors.append("Large one-year drawdown")
    if beta is not None and beta > 1.3:
        factors.append("Higher beta versus market")
    if balance_score is not None and balance_score > 70:
        factors.append("Balance sheet reduces risk")
    elif balance_score is not None and balance_score < 45:
        factors.append("Balance sheet adds risk")

    return {
        "score": safety_score,
        "risk_level": risk_level_score,
        "risk_safety_score": safety_score,
        "factors": factors or ["Risk profile is mixed."],
        "components": components,
        "data_window": (trend_risk or {}).get("data_window") or "price history and available profile data",
    }

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


def _metric_snapshot(
    value: Any,
    unit: str,
    source: str,
    source_field: str,
    period_type: str,
    fiscal_period: str | None = None,
    fiscal_period_end: str | None = None,
    currency: str | None = "USD",
    confidence: str = "medium",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    valid = _as_float(value) is not None or (isinstance(value, str) and bool(value.strip()))
    return {
        "value": value,
        "unit": unit,
        "currency": currency,
        "source": source,
        "source_field": source_field,
        "period_type": period_type,
        "fiscal_period": fiscal_period,
        "fiscal_period_end": fiscal_period_end,
        "data_timestamp": datetime.now(pytz.utc).isoformat(),
        "confidence": confidence if valid else "unavailable",
        "available": valid,
        "passed_validation": valid and not warnings,
        "warnings": warnings or [],
    }


def _financial_metric_snapshots(financials: dict[str, Any] | None) -> dict[str, Any]:
    if not financials:
        return {}
    source = financials.get("source") or "financials"
    metrics = {}
    labels = {
        "revenue": ("usd", "Fiscal-year revenue"),
        "eps": ("usd_per_share", "Fiscal-year diluted EPS"),
        "net_income": ("usd", "Fiscal-year net income"),
        "operating_income": ("usd", "Fiscal-year operating income"),
        "operating_cash_flow": ("usd", "Fiscal-year operating cash flow"),
        "free_cash_flow": ("usd", "Fiscal-year free cash flow"),
        "cash": ("usd", "Fiscal-year cash if quarterly SEC data is unavailable"),
        "total_debt": ("usd", "Fiscal-year debt if quarterly SEC data is unavailable"),
        "diluted_shares": ("shares", "Fiscal-year diluted average shares"),
    }
    for key, (unit, label) in labels.items():
        item = ((financials.get("highlights") or {}).get(key) or {})
        metrics[key] = {
            "latest_fiscal_year": _metric_snapshot(
                item.get("latest"),
                unit,
                source,
                key,
                "annual",
                "latest fiscal year",
                None,
                None if unit == "shares" else "USD",
                "medium",
            ),
            "previous_fiscal_year": _metric_snapshot(
                item.get("previous"),
                unit,
                source,
                key,
                "annual",
                "previous fiscal year",
                None,
                None if unit == "shares" else "USD",
                "medium",
            ),
            "change_pct": _metric_snapshot(
                item.get("change_pct"),
                "percent",
                "calculated",
                f"{key}.latest_vs_previous",
                "annual_comparison",
                "latest fiscal year vs previous fiscal year",
                None,
                None,
                "medium",
            ),
            "label": label,
        }
    return metrics


def _data_quality_checks(analysis: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    price = _as_float(((analysis.get("price") or {}).get("current")))
    market_cap = _as_float(((analysis.get("company") or {}).get("market_cap")))
    shares = _as_float((((analysis.get("balance_sheet") or {}).get("metrics") or {}).get("share_count")))
    if price is not None and market_cap is not None and shares is not None and shares > 0:
        implied = price * shares
        if implied > 0 and abs(implied - market_cap) / implied > 0.35:
            warnings.append("Market cap differs materially from price multiplied by reported share count.")

    financials = analysis.get("financials") or {}
    highlights = financials.get("highlights") or {}
    eps = _as_float((highlights.get("eps") or {}).get("latest"))
    net_income = _as_float((highlights.get("net_income") or {}).get("latest"))
    diluted = _as_float((highlights.get("diluted_shares") or {}).get("latest"))
    if eps is not None and net_income is not None and diluted not in (None, 0):
        implied_eps = net_income / diluted
        if abs(implied_eps - eps) > max(0.5, abs(eps) * 0.25):
            warnings.append("Net income divided by diluted shares does not closely match reported EPS; EPS valuation confidence is lower.")

    revenue = _as_float((highlights.get("revenue") or {}).get("latest"))
    gross_profit = _as_float((highlights.get("gross_profit") or {}).get("latest"))
    margins = financials.get("margins") or {}
    gross_margin = _as_float(margins.get("gross_margin_pct"))
    if revenue not in (None, 0) and gross_profit is not None and gross_margin is not None:
        calculated = gross_profit / revenue * 100
        if abs(calculated - gross_margin) > 0.5:
            warnings.append("Gross margin does not reconcile with gross profit divided by revenue.")

    bs = analysis.get("balance_sheet") or {}
    if bs.get("source") == "yahoo_fallback_mixed_periods":
        warnings.append("Balance-sheet values use Yahoo fallback and may not share one reporting period.")
    return warnings


def _normalized_research_snapshot(analysis: dict[str, Any]) -> dict[str, Any]:
    price = analysis.get("price") or {}
    balance_sheet = analysis.get("balance_sheet") or {}
    earnings = analysis.get("earnings") or {}
    return {
        "symbol": analysis.get("ticker"),
        "generated_at": analysis.get("generated_at"),
        "market": {
            "current_price": _metric_snapshot(
                price.get("current"),
                "usd",
                price.get("source") or "yfinance",
                "price.current",
                "current_market",
                None,
                None,
                price.get("currency") or "USD",
                "low" if price.get("delay_note") else "medium",
                [price.get("delay_note")] if price.get("delay_note") else [],
            ),
            "quote_as_of": price.get("as_of"),
            "history_last_trading_date": ((analysis.get("price_history") or {}).get("history_last_trading_date")),
        },
        "periods": {
            "balance_sheet": balance_sheet.get("period_end"),
            "earnings_next": earnings.get("next_earnings_date"),
            "price_quote": price.get("as_of"),
            "price_history": ((analysis.get("price_history") or {}).get("history_last_trading_date")),
            "financial_performance": "annual unless a metric states otherwise",
        },
        "financial_metrics": _financial_metric_snapshots(analysis.get("financials")),
        "balance_sheet": {
            key: _metric_snapshot(
                value,
                "ratio" if "ratio" in key or key.startswith("debt_to") else "usd" if isinstance(value, (int, float)) else "text",
                balance_sheet.get("source") or "balance_sheet",
                ((balance_sheet.get("source_fields") or {}).get(key) or key),
                "quarterly" if balance_sheet.get("period_end") else "fallback",
                None,
                balance_sheet.get("period_end"),
                "USD" if isinstance(value, (int, float)) and "ratio" not in key and not key.startswith("debt_to") else None,
                "high" if balance_sheet.get("source") == "sec_companyfacts" else "low",
                balance_sheet.get("warnings") or [],
            )
            for key, value in ((balance_sheet.get("metrics") or {}).items())
        },
        "validation_warnings": _data_quality_checks(analysis),
    }

def _weighted_score(scores: dict[str, int]) -> int:
    return _clamp_score(sum(scores.get(name, 50) * weight for name, weight in SCORE_WEIGHTS.items()))


def build_stock_analysis(ticker: str) -> dict[str, Any]:
    ticker = ticker.upper().strip()
    warnings: list[str] = []
    sources: list[str] = []

    market = _run_section(warnings, sources, "price_trend", lambda: _price_trend(ticker)) or {}
    prediction = None
    info = _safe_info(ticker)
    if info:
        sources.append("yahoo_profile")
    news = _run_section(warnings, sources, "news_headlines", lambda: _news(ticker, info))
    financials = _run_section(warnings, sources, "financials", lambda: _financials(ticker))

    current_price = _as_float((market.get("price") or {}).get("current"))
    company = _company_profile(ticker, info, market.get("price"))
    earnings = _run_section(warnings, sources, "earnings", lambda: _earnings(info, financials))
    balance_sheet = _run_section(warnings, sources, "balance_sheet", lambda: _balance_sheet(ticker, info, financials))
    valuation = _run_section(warnings, sources, "valuation", lambda: _valuation(ticker, current_price, financials, balance_sheet))
    dividend = _run_section(warnings, sources, "dividend", lambda: _dividend(info, current_price))
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
        "risk": int(risk.get("risk_safety_score") or risk.get("score") or 50),
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
            "method": "Weighted 0-100 Phase 1 research snapshot from valuation, fundamentals, trend, balance sheet, risk safety, liquidity, analyst, and dividend signals. Old prediction/news model outputs are excluded.",
        },
        "reddit": {
            "disabled": True,
            "reason": "Live Reddit fetching is disabled to avoid token/rate-limit crashes.",
        },
        "data_quality": {"sources": sources, "warnings": warnings},
    }
    normalized_snapshot = _normalized_research_snapshot(response)
    validation_warnings = normalized_snapshot.get("validation_warnings") or []
    if validation_warnings:
        response["data_quality"]["warnings"] = [*response["data_quality"].get("warnings", []), *validation_warnings]
    response["normalized_snapshot"] = normalized_snapshot
    return json_safe(response)
