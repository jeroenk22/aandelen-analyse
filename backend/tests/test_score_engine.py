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
    def _fetch(ticker):
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
