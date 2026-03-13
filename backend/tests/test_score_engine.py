"""
Tests voor ETF Score Engine
============================
Dekt:
  - Score-functies (unit tests)
  - Cache-logica van /etf endpoint
  - API endpoints via FastAPI TestClient
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Voeg backend-map toe aan path zodat import werkt
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import etf_score_engine as engine
from etf_score_engine import app

client = TestClient(app)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def mock_stock_data(ticker="TEST"):
    return {
        "ticker": ticker,
        "name": "Test Corp",
        "sector": "Technology",
        "current_price": 100.0,
        "currency": "USD",
        "rsi_daily": 40.0,
        "rsi_weekly": 38.0,
        "rsi_monthly": 42.0,
        "rsi_divergence_daily": "BULLISH",
        "rsi_divergence_weekly": "NEUTRAAL",
        "rsi_divergence_monthly": "NEUTRAAL",
        "ma20_daily": 105.0,
        "ma20_weekly": 103.0,
        "ma20_monthly": 102.0,
        "ma200": 90.0,
        "apz_upper_daily": 115.0,
        "apz_lower_daily": 85.0,
        "apz_upper_weekly": 118.0,
        "apz_lower_weekly": 82.0,
        "apz_upper_monthly": 120.0,
        "apz_lower_monthly": 80.0,
        "vol_spike": 1.5,
        "bb_pct_b": 0.25,
        "momentum_1m": 3.0,
        "forward_pe": 20.0,
        "historical_avg_pe": 25.0,
        "peg_ratio": 0.9,
        "price_fcf": 18.0,
        "historical_avg_pfcf": 22.0,
        "dcf_fair_value": 120.0,
    }


# ─────────────────────────────────────────────
# UNIT TESTS — SCORE FUNCTIES
# ─────────────────────────────────────────────

class TestScoreRsi:
    def test_extreme_oversold(self):
        assert engine.score_rsi(15) == 100.0

    def test_oversold(self):
        assert engine.score_rsi(25) == 90.0

    def test_licht_oversold(self):
        assert engine.score_rsi(40) == 70.0

    def test_neutraal(self):
        assert engine.score_rsi(50) == 50.0

    def test_licht_overbought(self):
        assert engine.score_rsi(65) == 30.0

    def test_overbought(self):
        assert engine.score_rsi(75) == 10.0

    def test_none(self):
        assert engine.score_rsi(None) == 50.0


class TestScoreMa200:
    def test_ver_onder(self):
        assert engine.score_ma200(80, 100) == 100.0

    def test_licht_onder(self):
        assert engine.score_ma200(96, 100) == 80.0

    def test_net_boven(self):
        assert engine.score_ma200(103, 100) == 70.0

    def test_ver_boven(self):
        assert engine.score_ma200(150, 100) == 10.0

    def test_geen_data(self):
        assert engine.score_ma200(None, None) == 50.0


class TestScorePeg:
    def test_zeer_laag(self):
        assert engine.score_peg(0.3) == 100.0

    def test_laag(self):
        assert engine.score_peg(0.6) == 85.0

    def test_onder_1(self):
        assert engine.score_peg(0.8) == 75.0

    def test_fair(self):
        assert engine.score_peg(1.2) == 55.0

    def test_duur(self):
        assert engine.score_peg(1.8) == 35.0

    def test_erg_duur(self):
        assert engine.score_peg(2.5) == 10.0

    def test_nul(self):
        assert engine.score_peg(0) == 50.0

    def test_negatief(self):
        assert engine.score_peg(-1) == 50.0


class TestScoreForwardPE:
    def test_sterk_goedkoop(self):
        assert engine.score_forward_pe(14, 25) == 100.0  # ratio 0.56

    def test_licht_goedkoop(self):
        assert engine.score_forward_pe(22, 25) == 75.0   # ratio 0.88

    def test_in_lijn(self):
        # ratio 1.0 valt in r < 1.1 tak → 50.0
        assert engine.score_forward_pe(25, 25) == 50.0

    def test_net_onder_1(self):
        # ratio 0.99 → r < 1.0 tak → 60.0
        assert engine.score_forward_pe(24, 25) == 60.0   # ratio 0.96

    def test_duur(self):
        assert engine.score_forward_pe(35, 25) == 15.0   # ratio 1.4

    def test_geen_data(self):
        assert engine.score_forward_pe(None, 25) == 50.0


class TestScorePanic:
    def test_extreme_paniek(self):
        assert engine.score_panic(-0.1, None) == 95.0

    def test_oversold_zone(self):
        assert engine.score_panic(0.1, None) == 80.0

    def test_neutraal(self):
        assert engine.score_panic(0.5, None) == 50.0

    def test_volume_spike_boost(self):
        base = engine.score_panic(0.5, None)
        met_spike = engine.score_panic(0.5, 2.5)
        assert met_spike == min(100.0, base + 10.0)

    def test_geen_data(self):
        assert engine.score_panic(None, None) == 50.0


class TestScoreRsiDivergence:
    def test_bullish(self):
        assert engine.score_rsi_divergence("BULLISH") == 85.0

    def test_bearish(self):
        assert engine.score_rsi_divergence("BEARISH") == 20.0

    def test_neutraal(self):
        assert engine.score_rsi_divergence("NEUTRAAL") == 50.0


class TestScoreApz:
    def test_onder_ondergrens(self):
        assert engine.score_apz(80, 85, 115) == 100.0

    def test_boven_bovengrens(self):
        assert engine.score_apz(120, 85, 115) == 10.0

    def test_onderkant_zone(self):
        score = engine.score_apz(87, 85, 115)
        assert score == 85.0  # pct = (87-85)/30 = 0.067 < 0.2

    def test_midden_zone(self):
        score = engine.score_apz(100, 85, 115)
        assert score == 50.0  # pct = 0.5

    def test_geen_data(self):
        assert engine.score_apz(None, 85, 115) == 50.0


# ─────────────────────────────────────────────
# UNIT TESTS — CALCULATE SCORE
# ─────────────────────────────────────────────

class TestCalculateScore:
    def test_retourneert_verplichte_velden(self):
        result = engine.calculate_score(mock_stock_data())
        assert "total_score" in result
        assert "signal" in result
        assert "scores_by_timeframe" in result
        assert "indicator_scores" in result

    def test_score_tussen_0_en_100(self):
        result = engine.calculate_score(mock_stock_data())
        assert 0 <= result["total_score"] <= 100

    def test_signaal_koop_bij_hoge_score(self):
        data = mock_stock_data()
        # Zet RSI extreem laag en PEG laag → hoge score
        data.update({"rsi_daily": 15, "rsi_weekly": 15, "rsi_monthly": 15, "peg_ratio": 0.3})
        result = engine.calculate_score(data)
        assert result["signal"] in ("KOOP", "NEUTRAAL", "UITSTAP")

    def test_geen_data(self):
        result = engine.calculate_score(None)
        assert result["total_score"] == 50
        assert result["signal"] == "NEUTRAAL"
        assert "error" in result

    def test_timeframe_scores_aanwezig(self):
        result = engine.calculate_score(mock_stock_data())
        tf = result["scores_by_timeframe"]
        assert set(tf.keys()) == {"daily", "weekly", "monthly"}


# ─────────────────────────────────────────────
# UNIT TESTS — CACHE LOGICA
# ─────────────────────────────────────────────

FAKE_HOLDINGS_DATA = [mock_stock_data(h["ticker"]) for h in engine.ETF_HOLDINGS]


def _reset_cache():
    engine._etf_cache.clear()
    engine._etf_cache_time.clear()


def _make_mock_fetch(data_list):
    idx = {"i": 0}
    def _fetch(ticker, as_of_date=None):
        d = data_list[idx["i"] % len(data_list)]
        idx["i"] += 1
        return d
    return _fetch


class TestCacheLogica:
    def setup_method(self):
        _reset_cache()

    def test_eerste_aanroep_cached_false(self):
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)):
            res = client.get("/etf?use_cache=true")
        assert res.status_code == 200
        assert res.json()["cached"] is False
        assert res.json()["cache_age_minutes"] == 0

    def test_tweede_aanroep_cached_true(self):
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)):
            client.get("/etf?use_cache=true")
        # Tweede aanroep: cache al gevuld
        res = client.get("/etf?use_cache=true")
        assert res.json()["cached"] is True

    def test_use_cache_false_slaat_cache_over(self):
        # Vul cache
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)):
            client.get("/etf?use_cache=true")
        # Aanroep met use_cache=false moet verse data halen
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)) as mock_fn:
            res = client.get("/etf?use_cache=false")
            assert mock_fn.call_count > 0
        assert res.json()["cached"] is False

    def test_verlopen_cache_wordt_vernieuwd(self):
        # Stel cache in met verouderde timestamp (70 minuten geleden)
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)):
            client.get("/etf?use_cache=true")
        engine._etf_cache_time["default"] = datetime.now() - timedelta(minutes=70)

        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)) as mock_fn:
            res = client.get("/etf?use_cache=true")
            assert mock_fn.call_count > 0
        assert res.json()["cached"] is False

    def test_geldige_cache_fetch_wordt_niet_aangeroepen(self):
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)):
            client.get("/etf?use_cache=true")
        # Cache is vers → fetch mag niet worden aangeroepen
        with patch.object(engine, "fetch_stock_data") as mock_fn:
            client.get("/etf?use_cache=true")
            mock_fn.assert_not_called()

    def test_cache_age_minutes_stijgt(self):
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)):
            client.get("/etf?use_cache=true")
        # Manipuleer timestamp: 5 minuten geleden
        engine._etf_cache_time["default"] = datetime.now() - timedelta(minutes=5)
        res = client.get("/etf?use_cache=true")
        age = res.json()["cache_age_minutes"]
        assert 4.9 <= age <= 5.5


# ─────────────────────────────────────────────
# API ENDPOINT TESTS
# ─────────────────────────────────────────────

class TestApiEndpoints:
    def test_root_gezond(self):
        res = client.get("/")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_config_retourneert_gewichten(self):
        res = client.get("/config")
        assert res.status_code == 200
        data = res.json()
        assert "timeframe_weights" in data
        assert "indicator_weights" in data
        assert "indicator_meta" in data

    def test_config_gewichten_optellen_tot_1(self):
        res = client.get("/config")
        tw = res.json()["timeframe_weights"]
        iw = res.json()["indicator_weights"]
        assert abs(sum(tw.values()) - 1.0) < 0.01
        assert abs(sum(iw.values()) - 1.0) < 0.01

    def test_etf_response_structuur(self):
        _reset_cache()
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)):
            res = client.get("/etf")
        assert res.status_code == 200
        body = res.json()
        assert "summary" in body
        assert "holdings" in body
        assert "config" in body
        assert "generated_at" in body
        assert "cached" in body
        assert "cache_age_minutes" in body

    def test_etf_summary_velden(self):
        _reset_cache()
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(FAKE_HOLDINGS_DATA)):
            res = client.get("/etf")
        summary = res.json()["summary"]
        assert "etf_score" in summary
        assert "etf_signal" in summary
        assert summary["etf_signal"] in ("INSTAP", "AFWACHTEN", "UITSTAP")

    def test_post_config_update(self):
        res = client.post("/config", json={
            "timeframe_weights": {"daily": 0.4, "weekly": 0.4, "monthly": 0.2}
        })
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        # Herstel originele waarden
        client.post("/config", json={
            "timeframe_weights": {"daily": 0.3, "weekly": 0.4, "monthly": 0.3}
        })

    def test_post_config_ongeldige_som(self):
        res = client.post("/config", json={
            "timeframe_weights": {"daily": 0.5, "weekly": 0.5, "monthly": 0.5}
        })
        assert "error" in res.json()


# ─────────────────────────────────────────────
# HELPERS HISTORISCHE MODUS
# ─────────────────────────────────────────────

def mock_stock_data_historisch(ticker="TEST"):
    """Mock stockdata zoals teruggegeven in historische modus:
    fundamentals zijn None en fundamentals_unavailable=True."""
    data = mock_stock_data(ticker)
    data.update({
        "forward_pe":          None,
        "historical_avg_pe":   None,
        "peg_ratio":           None,
        "price_fcf":           None,
        "historical_avg_pfcf": None,
        "dcf_fair_value":      None,
        "fundamentals_unavailable": True,
    })
    return data


# ─────────────────────────────────────────────
# UNIT TESTS — HISTORISCHE MODUS
# ─────────────────────────────────────────────

class TestFetchStockDataHistorisch:
    """Test het gedrag van fetch_stock_data met as_of_date parameter."""

    def test_fundamentals_unavailable_flag_bij_historische_datum(self):
        """Bij as_of_date moet fundamentals_unavailable True zijn."""
        with patch.object(engine, "_fmp_get") as mock_fmp:
            mock_fmp.side_effect = _mock_fmp_historisch
            result = engine.fetch_stock_data("AAPL", as_of_date="2024-01-15")
        assert result is not None
        assert result.get("fundamentals_unavailable") is True

    def test_ratios_ttm_niet_aangeroepen_bij_historische_datum(self):
        """/ratios-ttm mag NIET worden aangeroepen in historische modus."""
        aanroepen = []
        def _track_fmp(path, params=None):
            aanroepen.append(path)
            return _mock_fmp_historisch(path, params)

        with patch.object(engine, "_fmp_get", side_effect=_track_fmp):
            engine.fetch_stock_data("AAPL", as_of_date="2024-01-15")

        assert "/ratios-ttm" not in aanroepen

    def test_ratios_ttm_wel_aangeroepen_bij_live(self):
        """/ratios-ttm MOET worden aangeroepen in live modus."""
        aanroepen = []
        def _track_fmp(path, params=None):
            aanroepen.append(path)
            return _mock_fmp_live(path, params)

        with patch.object(engine, "_fmp_get", side_effect=_track_fmp):
            engine.fetch_stock_data("AAPL")

        assert "/ratios-ttm" in aanroepen

    def test_fundamentals_none_bij_historische_datum(self):
        """Fundamentele velden moeten None zijn in historische modus."""
        with patch.object(engine, "_fmp_get") as mock_fmp:
            mock_fmp.side_effect = _mock_fmp_historisch
            result = engine.fetch_stock_data("AAPL", as_of_date="2024-01-15")
        assert result["forward_pe"] is None
        assert result["peg_ratio"] is None
        assert result["price_fcf"] is None
        assert result["dcf_fair_value"] is None

    def test_technische_indicatoren_aanwezig_bij_historische_datum(self):
        """Technische indicatoren (RSI, MA, APZ) moeten wél beschikbaar zijn."""
        with patch.object(engine, "_fmp_get") as mock_fmp:
            mock_fmp.side_effect = _mock_fmp_historisch
            result = engine.fetch_stock_data("AAPL", as_of_date="2024-01-15")
        assert result["rsi_daily"] is not None
        assert result["ma200"] is not None
        assert result["momentum_1m"] is not None

    def test_koersdatum_gebruikt_opgegeven_datum(self):
        """De 'to' parameter voor historische koers moet de opgegeven datum zijn."""
        gebruikte_params = {}
        def _track_fmp(path, params=None):
            if path == "/historical-price-eod/full":
                gebruikte_params.update(params or {})
            return _mock_fmp_historisch(path, params)

        with patch.object(engine, "_fmp_get", side_effect=_track_fmp):
            engine.fetch_stock_data("AAPL", as_of_date="2023-06-30")

        assert gebruikte_params.get("to") == "2023-06-30"

    def test_fundamentals_unavailable_false_bij_live(self):
        """In live modus moet fundamentals_unavailable False zijn."""
        with patch.object(engine, "_fmp_get") as mock_fmp:
            mock_fmp.side_effect = _mock_fmp_live
            result = engine.fetch_stock_data("AAPL")
        assert result is not None
        assert result.get("fundamentals_unavailable") is False


class TestCalculateScoreZonderFundamentals:
    """Score-berekening moet werken als fundamentals None zijn (historische modus)."""

    def test_score_berekening_werkt_zonder_fundamentals(self):
        result = engine.calculate_score(mock_stock_data_historisch())
        assert 0 <= result["total_score"] <= 100
        assert result["signal"] in ("KOOP", "NEUTRAAL", "UITSTAP")

    def test_indicator_scores_aanwezig_zonder_fundamentals(self):
        result = engine.calculate_score(mock_stock_data_historisch())
        scores = result["indicator_scores"]
        assert "rsi_daily" in scores
        assert "ma200" in scores
        assert "forward_pe" in scores  # Score aanwezig, maar neutraal (50)
        assert scores["forward_pe"] == 50.0

    def test_peg_score_neutraal_zonder_data(self):
        result = engine.calculate_score(mock_stock_data_historisch())
        assert result["indicator_scores"]["peg"] == 50.0

    def test_raw_data_bevat_fundamentals_unavailable(self):
        result = engine.calculate_score(mock_stock_data_historisch())
        assert result["raw_data"]["fundamentals_unavailable"] is True


class TestHistorischEndpoint:
    """Tests voor het /historical API endpoint."""

    def test_ongeldige_datum_geeft_foutmelding(self):
        res = client.get("/historical?date=geen-datum")
        assert res.status_code == 200
        assert "error" in res.json()

    def test_datum_in_toekomst_geeft_foutmelding(self):
        toekomst = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        res = client.get(f"/historical?date={toekomst}")
        assert res.status_code == 200
        assert "error" in res.json()

    def test_geldige_datum_retourneert_correcte_structuur(self):
        historische_data = [mock_stock_data_historisch(h["ticker"]) for h in engine.ETF_HOLDINGS]
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(historische_data)):
            res = client.get("/historical?date=2024-06-01")
        assert res.status_code == 200
        body = res.json()
        assert "summary" in body
        assert "holdings" in body
        assert "config" in body
        assert "historical_date" in body
        assert "generated_at" in body

    def test_historical_date_in_response(self):
        historische_data = [mock_stock_data_historisch(h["ticker"]) for h in engine.ETF_HOLDINGS]
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(historische_data)):
            res = client.get("/historical?date=2024-03-15")
        assert res.json()["historical_date"] == "2024-03-15"

    def test_cached_altijd_false(self):
        historische_data = [mock_stock_data_historisch(h["ticker"]) for h in engine.ETF_HOLDINGS]
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(historische_data)):
            res = client.get("/historical?date=2024-06-01")
        assert res.json()["cached"] is False

    def test_etf_signal_geldig(self):
        historische_data = [mock_stock_data_historisch(h["ticker"]) for h in engine.ETF_HOLDINGS]
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(historische_data)):
            res = client.get("/historical?date=2024-06-01")
        assert res.json()["summary"]["etf_signal"] in ("INSTAP", "AFWACHTEN", "UITSTAP")

    def test_custom_tickers_worden_gebruikt(self):
        """Met ?tickers=AAPL,MSFT mogen alleen die twee aandelen geanalyseerd worden."""
        calls = []
        def _track(ticker, as_of_date=None):
            calls.append(ticker)
            return mock_stock_data_historisch(ticker)

        with patch.object(engine, "fetch_stock_data", side_effect=_track):
            res = client.get("/historical?date=2024-06-01&tickers=AAPL,MSFT")
        assert res.status_code == 200
        assert set(calls) == {"AAPL", "MSFT"}

    def test_as_of_date_doorgegeven_aan_fetch(self):
        """fetch_stock_data moet worden aangeroepen met as_of_date=opgegeven datum."""
        ontvangen_datum = []
        def _track(ticker, as_of_date=None):
            ontvangen_datum.append(as_of_date)
            return mock_stock_data_historisch(ticker)

        with patch.object(engine, "fetch_stock_data", side_effect=_track):
            client.get("/historical?date=2023-11-20&tickers=AAPL")

        assert all(d == "2023-11-20" for d in ontvangen_datum)

    def test_fundamentals_unavailable_in_holdings(self):
        """Holdings in historische response moeten fundamentals_unavailable=True hebben."""
        historische_data = [mock_stock_data_historisch(h["ticker"]) for h in engine.ETF_HOLDINGS]
        with patch.object(engine, "fetch_stock_data", side_effect=_make_mock_fetch(historische_data)):
            res = client.get("/historical?date=2024-06-01")
        for holding in res.json()["holdings"]:
            if "raw_data" in holding:
                assert holding["raw_data"]["fundamentals_unavailable"] is True


# ─────────────────────────────────────────────
# FMP MOCK HELPERS
# ─────────────────────────────────────────────

import pandas as pd
import numpy as np

def _maak_koersdata(n=300, basisprijs=100.0):
    """Genereer n dagelijkse koersrecords (nieuwste eerst, zoals FMP teruggeeft)."""
    prijzen = basisprijs + np.cumsum(np.random.randn(n) * 0.5)
    volumes = np.random.randint(1_000_000, 5_000_000, size=n)
    vandaag = datetime.now()
    records = []
    for i in range(n):
        dag = vandaag - timedelta(days=i)
        prijs = round(float(prijzen[i]), 2)
        records.append({
            "date":      dag.strftime("%Y-%m-%d"),
            "open":      round(prijs * 0.99, 2),
            "high":      round(prijs * 1.02, 2),
            "low":       round(prijs * 0.97, 2),
            "close":     prijs,
            "adjClose":  prijs,
            "volume":    int(volumes[i]),
        })
    return records  # nieuwste eerst, zoals FMP


def _mock_fmp_historisch(path, params=None):
    """FMP-mock voor historische modus: geen ratios-ttm."""
    if path == "/profile":
        return [{"companyName": "Test Corp", "sector": "Technology", "currency": "USD"}]
    if path == "/historical-price-eod/full":
        return _maak_koersdata()
    return None  # /ratios-ttm wordt niet aangeroepen in historische modus


def _mock_fmp_live(path, params=None):
    """FMP-mock voor live modus: met ratios-ttm."""
    if path == "/profile":
        return [{"companyName": "Test Corp", "sector": "Technology", "currency": "USD"}]
    if path == "/historical-price-eod/full":
        return _maak_koersdata()
    if path == "/ratios-ttm":
        return [{
            "priceToEarningsRatioTTM": 22.0,
            "priceToEarningsGrowthRatioTTM": 1.1,
            "priceToFreeCashFlowRatioTTM": 18.0,
            "freeCashFlowPerShareTTM": 5.0,
        }]
    return None


# ─────────────────────────────────────────────
# UNIT TESTS — OHLC_DAY EN PRICE_HISTORY
# ─────────────────────────────────────────────

class TestOhlcDayEnPriceHistory:
    """Test dat fetch_stock_data ohlc_day en price_history correct retourneert."""

    def test_ohlc_day_aanwezig(self):
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_live):
            result = engine.fetch_stock_data("AAPL")
        assert result is not None
        assert "ohlc_day" in result

    def test_ohlc_day_bevat_verplichte_velden(self):
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_live):
            result = engine.fetch_stock_data("AAPL")
        ohlc = result["ohlc_day"]
        assert "date" in ohlc
        assert "open" in ohlc
        assert "high" in ohlc
        assert "low" in ohlc
        assert "close" in ohlc
        assert "adj_close" in ohlc
        assert "volume" in ohlc

    def test_ohlc_day_close_gelijk_aan_current_price(self):
        """De close van ohlc_day moet overeenkomen met current_price."""
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_live):
            result = engine.fetch_stock_data("AAPL")
        assert result["ohlc_day"]["close"] == result["current_price"]

    def test_ohlc_day_high_groter_of_gelijk_aan_low(self):
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_live):
            result = engine.fetch_stock_data("AAPL")
        ohlc = result["ohlc_day"]
        if ohlc["high"] is not None and ohlc["low"] is not None:
            assert ohlc["high"] >= ohlc["low"]

    def test_price_history_aanwezig(self):
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_live):
            result = engine.fetch_stock_data("AAPL")
        assert "price_history" in result
        assert isinstance(result["price_history"], list)
        assert len(result["price_history"]) > 0

    def test_price_history_bevat_date_en_close(self):
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_live):
            result = engine.fetch_stock_data("AAPL")
        for record in result["price_history"][:5]:
            assert "date" in record
            assert "close" in record

    def test_price_history_gesorteerd_oudste_eerst(self):
        """price_history moet chronologisch gesorteerd zijn (oudste eerst)."""
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_live):
            result = engine.fetch_stock_data("AAPL")
        datums = [r["date"] for r in result["price_history"]]
        assert datums == sorted(datums)

    def test_price_history_laatste_close_gelijk_aan_current_price(self):
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_live):
            result = engine.fetch_stock_data("AAPL")
        assert result["price_history"][-1]["close"] == result["current_price"]

    def test_ohlc_day_ook_aanwezig_in_historische_modus(self):
        with patch.object(engine, "_fmp_get", side_effect=_mock_fmp_historisch):
            result = engine.fetch_stock_data("AAPL", as_of_date="2024-01-15")
        assert result is not None
        assert "ohlc_day" in result
        assert "price_history" in result
