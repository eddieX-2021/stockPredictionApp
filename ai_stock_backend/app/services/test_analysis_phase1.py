import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.routes import normalize_ticker_symbol
from app.services.analysis import _analyst, _balance_sheet, _company_profile, _dividend, _earnings, _pct_change, _risk_score, _run_section, _valuation


class PhaseOneAnalysisHelpersTest(unittest.TestCase):
    def test_pct_change_handles_missing_and_zero_previous(self):
        self.assertIsNone(_pct_change(None, 10))
        self.assertIsNone(_pct_change(10, 0))
        self.assertAlmostEqual(_pct_change(110, 100), 10.0)
        self.assertAlmostEqual(_pct_change(90, 100), -10.0)

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
        self.assertIn("High recent volatility", risk["factors"])
        self.assertIn("Large one-year drawdown", risk["factors"])

    def test_optional_sections_return_none_without_provider_data(self):
        self.assertIsNone(_earnings({}, None))
        with patch("app.services.analysis._safe_info", return_value={}):
            self.assertIsNone(_valuation("ZZZZ", None, None))
        self.assertIsNone(_balance_sheet({}, None))
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
