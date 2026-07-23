import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.api.routes import normalize_ticker_symbol, research_snapshot_payload
from app.main import app
from app.services.analysis import _analyst, _balance_sheet, _company_profile, _dividend, _earnings, _earnings_date_selection, _headline_relevance, _normalized_dividend_yield, _normalized_research_snapshot, _pct_change, _price_payload_from_history_and_quote, _risk_score, _run_section, _valuation, _weighted_score


class PhaseOneAnalysisHelpersTest(unittest.TestCase):
    def test_pct_change_handles_missing_and_zero_previous(self):
        self.assertIsNone(_pct_change(None, 10))
        self.assertIsNone(_pct_change(10, 0))
        self.assertAlmostEqual(_pct_change(110, 100), 10.0)
        self.assertAlmostEqual(_pct_change(90, 100), -10.0)

    def test_price_payload_prefers_latest_quote_and_keeps_metadata(self):
        payload = _price_payload_from_history_and_quote(
            100.0,
            98.0,
            {
                "current": 103.0,
                "previous_close": 101.0,
                "currency": "USD",
                "source": "yfinance_info_regular_market",
                "session": "regular",
                "as_of": "2026-07-21T20:00:00+00:00",
            },
        )

        self.assertEqual(payload["current"], 103.0)
        self.assertEqual(payload["previous_close"], 101.0)
        self.assertAlmostEqual(payload["day_change_pct"], 1.9801980198)
        self.assertEqual(payload["source"], "yfinance_info_regular_market")
        self.assertEqual(payload["as_of"], "2026-07-21T20:00:00+00:00")
        self.assertFalse(payload["is_realtime"])
        self.assertIn("not guaranteed real-time", payload["delay_note"])
    def test_dividend_yield_uses_decimal_internal_convention(self):
        normalized = _normalized_dividend_yield(0.25, dividend_rate=0.88, current_price=348.85)

        self.assertIsNotNone(normalized)
        self.assertAlmostEqual(normalized or 0, 0.00252257417)
        dividend = _dividend({"dividendYield": 0.25, "dividendRate": 0.88, "payoutRatio": 0.1}, 348.85)
        self.assertAlmostEqual(dividend["metrics"]["dividend_yield_pct"], 0.252257417, places=5)

    def test_earnings_dates_do_not_use_today_placeholder_as_recent(self):
        now = datetime(2026, 7, 21, 16, 0, tzinfo=timezone.utc)
        today_placeholder = int(datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc).timestamp())
        next_earnings = int(datetime(2026, 7, 22, 20, 0, tzinfo=timezone.utc).timestamp())

        dates = _earnings_date_selection(
            {
                "earningsTimestamp": today_placeholder,
                "earningsTimestampStart": next_earnings,
                "earningsTimestampEnd": next_earnings,
            },
            now=now,
        )

        self.assertIsNone(dates["recent"])
        self.assertEqual(dates["next"]["date"].date().isoformat(), "2026-07-22")

    def test_higher_risk_level_lowers_weighted_score(self):
        base = {
            "valuation": 60,
            "fundamentals": 60,
            "trend": 60,
            "balance_sheet": 60,
            "liquidity": 60,
            "analyst": 60,
            "dividend": 60,
        }

        safer = _weighted_score({**base, "risk": 80})
        riskier = _weighted_score({**base, "risk": 20})

        self.assertGreater(safer, riskier)
    def test_news_relevance_excludes_unrelated_entertainment(self):
        relevant = _headline_relevance("MU", "Micron shares rise after memory demand improves", {"longName": "Micron Technology Inc"})
        unrelated = _headline_relevance("MU", "Barcelona signs star as Brad Pitt movie opens", {"longName": "Micron Technology Inc"})

        self.assertEqual(relevant["status"], "relevant")
        self.assertEqual(unrelated["status"], "excluded_unrelated")

    def test_normalized_snapshot_labels_annual_and_quarterly_periods(self):
        analysis = {
            "ticker": "MU",
            "generated_at": "2026-07-23T00:00:00+00:00",
            "price": {"current": 100, "source": "yfinance", "currency": "USD"},
            "price_history": {"history_last_trading_date": "2026-07-22"},
            "company": {"market_cap": 1000},
            "financials": {"source": "sec", "highlights": {"revenue": {"latest": 10, "previous": 8, "change_pct": 25}}},
            "balance_sheet": {"period_end": "2026-05-28", "source": "sec_companyfacts", "metrics": {"cash_and_equivalents": 5, "total_interest_bearing_debt": 2}},
            "earnings": {"next_earnings_date": "2026-09-01T00:00:00+00:00"},
        }

        snapshot = _normalized_research_snapshot(analysis)

        self.assertEqual(snapshot["financial_metrics"]["revenue"]["latest_fiscal_year"]["period_type"], "annual")
        self.assertEqual(snapshot["balance_sheet"]["cash_and_equivalents"]["period_type"], "quarterly")
        self.assertEqual(snapshot["periods"]["balance_sheet"], "2026-05-28")
    def test_phase2_and_mcp_routes_are_not_registered(self):
        paths = {getattr(route, "path", "") for route in app.routes}

        self.assertNotIn("/phase2/explain", paths)
        self.assertNotIn("/api/phase2/explain", paths)
        self.assertNotIn("/mcp", paths)
        self.assertIn("/api/stocks/{symbol}/research-snapshot", paths)

    def test_research_snapshot_payload_schema_is_phase1_structured_data(self):
        payload = research_snapshot_payload(
            {
                "ticker": "AAPL",
                "generated_at": "2026-07-23T00:00:00+00:00",
                "company": {"ticker": "AAPL", "market_cap": 1000},
                "price": {"current": 100, "as_of": "2026-07-23T13:00:00+00:00"},
                "summary": {"overall_score": 60, "key_points": ["Rule-based driver"]},
                "scores": {"overall": 60},
                "score_model": {"version": "phase-1"},
                "price_history": {"available_ranges": ["1y"], "history_last_trading_date": "2026-07-22"},
                "financials": {"model": {"direction": "UP"}},
                "normalized_snapshot": {"periods": {"balance_sheet": "2026-03-31"}},
                "news": {"items": []},
                "prediction": {"direction": "UP"},
                "data_quality": {"warnings": []},
            }
        )

        self.assertEqual(payload["endpoint_version"], "phase1-research-snapshot-v1")
        self.assertEqual(payload["symbol"], "AAPL")
        self.assertEqual(payload["financial_periods"]["balance_sheet"], "2026-03-31")
        self.assertIn("stock_price_model", payload["experimental_prediction_signals"])
        self.assertNotIn("promptVersion", payload)
        self.assertNotIn("dataSnapshotHash", payload)

    def test_frontend_removes_phase2_buttons_and_keeps_future_app_notice(self):
        root = Path(__file__).resolve().parents[3]
        page = (root / "next-app" / "app" / "[stock]" / "page.tsx").read_text(encoding="utf-8")

        for phrase in ("Generate scenarios", "Explain score", "Explain price", "Identify risks", "Explain metrics", "Analyze earnings", "Phase2"):
            self.assertNotIn(phrase, page)
        self.assertIn("AI Research Assistant", page)
        self.assertIn("/chatgpt-app", page)
        self.assertIn("predictionModelNames", page)
        self.assertIn("No sufficiently relevant recent headlines found.", page)

    def test_chatgpt_app_page_is_under_development(self):
        root = Path(__file__).resolve().parents[3]
        page = (root / "next-app" / "app" / "chatgpt-app" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("ChatGPT App", page)
        self.assertIn("Under development", page)
        self.assertIn("Return to dashboard", page)
        self.assertNotIn("signup", page.lower())
        self.assertNotIn("api key", page.lower())

    def test_company_profile_uses_free_profile_and_links(self):
        profile = _company_profile(
            "MSFT",
            {
                "longName": "Microsoft Corporation",
                "sector": "Technology",
                "industry": "Software - Infrastructure",
                "marketCap": 123456789,
                "exchange": "NMS",
            },
            {"current": 400.0, "day_change_pct": 1.25, "currency": "USD"},
        )

        self.assertEqual(profile["name"], "Microsoft Corporation")
        self.assertEqual(profile["ticker"], "MSFT")
        self.assertEqual(profile["current_price"], 400.0)
        self.assertIn("MSFT", profile["links"]["yahoo_finance"])
        self.assertIn("MSFT", profile["links"]["sec_search"])

    def test_earnings_marks_surprise_unavailable_without_estimate_actual_pair(self):
        earnings = _earnings(
            {"trailingEps": 5.0, "forwardEps": 5.5, "totalRevenue": 1000.0},
            {
                "highlights": {
                    "eps": {"latest": 5.0, "previous": 4.0},
                    "revenue": {"latest": 1000.0, "previous": 800.0},
                }
            },
        )

        self.assertEqual(earnings["reported_eps"], 5.0)
        self.assertEqual(earnings["estimated_eps"], 5.5)
        self.assertAlmostEqual(earnings["eps_change_pct"], 25.0)
        self.assertEqual(earnings["surprise"]["status"], "unavailable")

    def test_risk_score_combines_available_observations(self):
        risk = _risk_score(
            {"volatility_20d_pct": 70, "max_drawdown_1y_pct": -50},
            {"metrics": {"beta": 1.8}},
            {"score": 35},
        )

        self.assertLess(risk["score"], 50)
        self.assertIn("Elevated recent volatility", risk["factors"])
        self.assertIn("Large one-year drawdown", risk["factors"])

    def test_optional_sections_return_none_without_provider_data(self):
        self.assertIsNone(_earnings({}, None))
        with patch("app.services.analysis._safe_info", return_value={}):
            self.assertIsNone(_valuation("ZZZZ", None, None))
        self.assertIsNone(_balance_sheet("ZZZZ", {}, None))
        self.assertIsNone(_dividend({}))
        self.assertIsNone(_analyst({}, None))

    def test_risk_score_marks_limited_data_neutral(self):
        risk = _risk_score(None, None, None)

        self.assertEqual(risk["score"], 50)
        self.assertIn("Risk data is limited", risk["factors"][0])

    def test_ticker_normalization_accepts_common_symbols(self):
        self.assertEqual(normalize_ticker_symbol(" msft "), "MSFT")
        self.assertEqual(normalize_ticker_symbol("brk.b"), "BRK.B")
        self.assertEqual(normalize_ticker_symbol("bf-b"), "BF-B")

    def test_ticker_normalization_rejects_invalid_symbols(self):
        for value in ("", "BAD SYMBOL", "../../AAPL", "THISISTOOLONG"):
            with self.subTest(value=value):
                with self.assertRaises(HTTPException):
                    normalize_ticker_symbol(value)

    def test_run_section_records_warning_without_raising(self):
        warnings = []
        sources = []

        result = _run_section(warnings, sources, "optional_news", lambda: (_ for _ in ()).throw(ValueError("provider down")))

        self.assertIsNone(result)
        self.assertEqual(sources, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("optional_news unavailable", warnings[0])


if __name__ == "__main__":
    unittest.main()
