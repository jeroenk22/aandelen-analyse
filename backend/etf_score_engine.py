"""
ETF Intelligence Score Engine
==============================
Installeer dependencies: pip install -r requirements.txt

Gebruik:
  python etf_score_engine.py              → analyseert de holdings, print rapport
  uvicorn etf_score_engine:app --reload   → start als API op http://localhost:8000

API endpoints:
  GET /             → health check
  GET /score/{ticker}         → score voor 1 aandeel
  GET /etf                    → gewogen ETF-score voor alle holdings
  GET /config                 → huidige gewichten
  POST /config                → gewichten aanpassen
  GET /sector-performance     → actuele sectorprestaties
  GET /intraday/{ticker}      → intraday 4-uurs koersdata
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─────────────────────────────────────────────
# FMP API CONFIGURATIE
# ─────────────────────────────────────────────

FMP_API_KEY = os.getenv("FMP_API_KEY", "demo")
FMP_BASE = "https://financialmodelingprep.com/stable"

if FMP_API_KEY == "demo":
    print("⚠ Geen FMP_API_KEY gevonden — stel FMP_API_KEY in via .env of omgevingsvariabele.")

# ─────────────────────────────────────────────
# IN-MEMORY CACHE
# ─────────────────────────────────────────────

_etf_cache: Dict[str, dict] = {}
_etf_cache_time: Dict[str, datetime] = {}
CACHE_DURATION_MINUTES = 60

# Cache voor sectorprestaties (vernieuwd elke 60 minuten)
_sector_perf_cache: dict = {}
_sector_perf_cache_time: Optional[datetime] = None

# ─────────────────────────────────────────────
# CONFIGURATIE — pas gewichten hier aan
# ─────────────────────────────────────────────

TIMEFRAME_WEIGHTS = {
    "intraday": 0.15,   # 4-uurs intraday (Premium)
    "daily":    0.25,
    "weekly":   0.35,
    "monthly":  0.25,
}

INDICATOR_WEIGHTS = {
    "rsi":              0.11,
    "ma20":             0.07,
    "ma200":            0.06,
    "forward_pe":       0.12,
    "peg":              0.12,
    "price_fcf":        0.09,
    "momentum":         0.07,
    "analyst_target":   0.08,  # vervangt dcf_discount (0.02)
    "panic":            0.05,
    "rsi_divergence":   0.06,
    "apz":              0.06,
    "williams":         0.06,  # Williams %R via API
    "adx":              0.05,  # ADX trendsterkte via API
}
# som = 1.00

# Weergavenamen en tooltips per indicator (voor frontend)
INDICATOR_META = {
    "rsi": {
        "label":   "RSI",
        "tooltip": "De Relative Strength Index meet hoe snel een koers is gedaald of gestegen. "
                   "Onder 30 = waarschijnlijk te veel gedaald (koopkans), boven 70 = waarschijnlijk te veel gestegen (verkoopkans).",
    },
    "rsi_divergence": {
        "label":   "RSI Divergentie",
        "tooltip": "Detecteert echte swing-lows en swing-highs in koers én RSI over de laatste 30 perioden. "
                   "Bullish divergentie: koers maakt lagere bodem maar RSI hogere bodem → verkoopdruk neemt af, mogelijke ommekeer omhoog. "
                   "Bearish divergentie: koers maakt hogere top maar RSI lagere top → koopdruk neemt af.",
    },
    "ma20": {
        "label":   "MA20",
        "tooltip": "Het voortschrijdend gemiddelde van de afgelopen 20 perioden. "
                   "Prijs onder de MA20 betekent dat het aandeel tijdelijk onder zijn kortetermijngemiddelde noteert — mogelijke koopkans.",
    },
    "ma200": {
        "label":   "MA200",
        "tooltip": "Het 200-daags voortschrijdend gemiddelde — de langetermijntrend. "
                   "Prijs boven MA200 = positieve trend. Eronder = negatieve langetermijntrend.",
    },
    "apz": {
        "label":   "APZ",
        "tooltip": "De Adaptive Price Zone is een dynamische bandbreedte rond een EMA. "
                   "Koers onder de ondergrens = oversold (te goedkoop), boven de bovengrens = overbought (te duur). "
                   "Past zich automatisch aan de volatiliteit aan.",
    },
    "forward_pe": {
        "label":   "Forward P/E",
        "tooltip": "Hoeveel keer de verwachte jaarwinst je betaalt voor het aandeel. "
                   "Lager dan het historisch gemiddelde = relatief goedkoop. Hoger = relatief duur.",
    },
    "peg": {
        "label":   "PEG Ratio",
        "tooltip": "De koers-winstverhouding gedeeld door de verwachte winstgroei. "
                   "Onder 1 = goedkoop gezien de groei. Boven 2 = duur. Is de eerlijkste maatstaf voor groeibedrijven.",
    },
    "price_fcf": {
        "label":   "P/FCF",
        "tooltip": "Prijs gedeeld door de vrije kasstroom per aandeel. "
                   "Vrije kasstroom is het geld dat overblijft ná alle investeringen — het 'echte' geld van het bedrijf. "
                   "Lager = goedkoper.",
    },
    "momentum": {
        "label":   "Momentum",
        "tooltip": "Gewogen rendement over 1, 3 en 6 maanden (30%/40%/30%) t.o.v. de sector. "
                   "Positief momentum betekent dat beleggers meer vertrouwen tonen dan in vergelijkbare bedrijven. "
                   "Multi-timeframe gewogen voor betere signaalstabiliteit.",
    },
    "analyst_target": {
        "label":   "Analistendoelstelling",
        "tooltip": "Het mediane koersdoel van analisten t.o.v. de huidige koers. "
                   "Hoge upside = analisten zien het aandeel als ondergewaardeerd. "
                   "Alleen beschikbaar voor US-genoteerde aandelen.",
    },
    "williams": {
        "label":   "Williams %R",
        "tooltip": "Williams %R meet hoe de huidige slotkoers zich verhoudt tot de hoogste koers van de afgelopen 14 perioden. "
                   "-100 = koers staat op het laagste punt (oversold, koopkans). "
                   "0 = koers staat op het hoogste punt (overbought, verkoopkans). "
                   "Alleen beschikbaar voor US- en Canada-genoteerde aandelen.",
    },
    "adx": {
        "label":   "ADX",
        "tooltip": "De Average Directional Index meet de sterkte van een trend, ongeacht de richting. "
                   "Boven 25 = duidelijke trend aanwezig (combineer met RSI voor richting). "
                   "Onder 20 = markt beweegt zijwaarts. "
                   "Alleen beschikbaar voor US- en Canada-genoteerde aandelen.",
    },
    "panic": {
        "label":   "Paniek Indicator",
        "tooltip": "Detecteert extreme marktpaniek via de Bollinger Bands en handelsvolume. "
                   "Als de koers ver onder de onderste Bollinger Band valt met hoog volume, wijst dat op paniekverkopen — "
                   "historisch gezien een koopkans.",
    },
}

# Standaard tickers uit config.json (gelijk gewogen)
_config_path = os.path.join(os.path.dirname(__file__), "config.json")
try:
    with open(_config_path, "r") as _f:
        _cfg = json.load(_f)
    _default_tickers = _cfg.get("default_tickers", [])
except Exception:
    _default_tickers = ["NVDA", "AAPL", "MSFT", "GOOGL", "TSM", "AMZN", "META"]

_w = round(1 / len(_default_tickers), 6) if _default_tickers else 1.0
ETF_HOLDINGS = [{"ticker": t, "name": t, "etf_weight": _w} for t in _default_tickers]


# ─────────────────────────────────────────────
# FMP HULPFUNCTIES
# ─────────────────────────────────────────────

def _fmp_get(path: str, params: dict = None):
    """GET request naar FMP API. Geeft None bij fout, 'PREMIUM' bij 402."""
    url = f"{FMP_BASE}{path}"
    p = {"apikey": FMP_API_KEY, **(params or {})}
    try:
        resp = requests.get(url, params=p, timeout=30)
        if resp.status_code == 402:
            return "PREMIUM"
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"FMP API fout ({path}): {e}")
        return None


# Interval mapping: interne naam → stable API timeframe parameter
_INTERVAL_MAP = {
    "daily":   "1day",
    "weekly":  "1week",
    "monthly": "1month",
    "4hour":   "4hour",
    "1hour":   "1hour",
}


def _fetch_indicator(ticker: str, ind_type: str, period: int,
                     interval: str = "daily", limit: int = 50) -> Optional[list]:
    """Haal technische indicator op via FMP stable API. Geeft lijst (nieuwste eerst) of None terug.
    ind_type: 'rsi', 'sma', 'ema'
    interval: 'daily', 'weekly', 'monthly', '1hour', '4hour'
    """
    tf = _INTERVAL_MAP.get(interval, interval)
    # Bereken from-datum ruim genoeg voor gevraagd aantal candles
    from_date = (datetime.now() - timedelta(days=max(limit * 2, 365))).strftime("%Y-%m-%d")
    data = _fmp_get(
        f"/technical-indicators/{ind_type}",
        {"symbol": ticker, "periodLength": period, "timeframe": tf, "from": from_date}
    )
    if isinstance(data, list) and len(data) > 0:
        return data[:limit]  # Nieuwste eerst, beperkt tot gevraagd aantal
    return None


def fetch_sector_performance() -> dict:
    """Haal actuele sectorprestaties op van FMP (gecacht per 60 min).
    Geeft dict terug: {sector_naam: pct_change}
    """
    global _sector_perf_cache, _sector_perf_cache_time
    now = datetime.now()
    if (_sector_perf_cache_time and
            (now - _sector_perf_cache_time).total_seconds() < CACHE_DURATION_MINUTES * 60):
        return _sector_perf_cache

    data = _fmp_get("/sector-performance")
    if not data or isinstance(data, str) or not isinstance(data, list):
        return _sector_perf_cache  # geef vorige waarde terug bij fout

    result = {}
    for item in data:
        sector = item.get("sector", "")
        pct = item.get("changesPercentage", 0)
        if isinstance(pct, str):
            pct = pct.replace("%", "").replace("+", "").strip()
        try:
            result[sector] = float(pct)
        except (ValueError, TypeError):
            pass

    _sector_perf_cache = result
    _sector_perf_cache_time = now
    return result


def resolve_isin_to_ticker(isin: str) -> Optional[str]:
    """Zet ISIN om naar beursticker via FMP zoekfunctie."""
    data = _fmp_get("/search-symbol", {"query": isin, "limit": 5})
    if not data or not isinstance(data, list):
        return None
    for item in data:
        if item.get("isin") == isin:
            return item["symbol"]
    return data[0]["symbol"] if data else None


def fetch_etf_holdings(ticker: str, top_n: int = 10) -> list:
    """Haal de top N holdings van een ETF op via FMP, gesorteerd op gewicht."""
    data = _fmp_get("/etf-holder", {"symbol": ticker})
    if not data or not isinstance(data, list):
        return []
    sorted_holdings = sorted(
        data, key=lambda x: x.get("weightPercentage", 0) or 0, reverse=True
    )
    if len(data) > top_n:
        print(f"  ℹ ETF {ticker} heeft {len(data)} holdings — top {top_n} geselecteerd op gewicht")
    result = []
    for h in sorted_holdings[:top_n]:
        result.append({
            "ticker": h.get("asset", ""),
            "name": h.get("name", h.get("asset", "")),
            "etf_weight": round((h.get("weightPercentage", 0) or 0) / 100, 6),
        })
    return [h for h in result if h["ticker"]]


# ─────────────────────────────────────────────
# HULPFUNCTIES
# ─────────────────────────────────────────────

def _r(v, n=2):
    """Round v to n decimals; return None if v is None, NaN or infinite."""
    if v is None:
        return None
    try:
        f = float(v)
        return round(f, n) if not (np.isnan(f) or np.isinf(f)) else None
    except (TypeError, ValueError):
        return None


def calc_apz(series: pd.Series, period: int = 20):
    """Adaptive Price Zone: EMA ± 2× gemiddelde absolute afwijking (MAD).
    Retourneert (ema, upper, lower) als float of (None, None, None) bij te weinig data."""
    if len(series) < period:
        return None, None, None
    ema = series.ewm(span=period, adjust=False).mean()
    mad = (series - ema).abs().rolling(period).mean()
    return _r(ema.iloc[-1]), _r((ema + 2 * mad).iloc[-1]), _r((ema - 2 * mad).iloc[-1])


def calc_rsi_divergence(close_s: pd.Series, rsi_s: pd.Series, lookback: int = 30) -> str:
    """Detecteer divergentie via echte swing-lows/-highs (lokale extremen).
    Bullish  = koers maakt lagere bodem, RSI hogere bodem (koopkans).
    Bearish  = koers maakt hogere top,  RSI lagere top (verkoopkans)."""
    rsi_clean = rsi_s.dropna()
    if len(close_s) < lookback or len(rsi_clean) < lookback:
        return "NEUTRAAL"

    close = close_s.values[-lookback:]
    rsi   = rsi_clean.values[-lookback:]

    def swing_lows(arr, margin=2):
        return [i for i in range(margin, len(arr) - margin)
                if arr[i] == min(arr[i-margin:i+margin+1])]

    def swing_highs(arr, margin=2):
        return [i for i in range(margin, len(arr) - margin)
                if arr[i] == max(arr[i-margin:i+margin+1])]

    price_lows, rsi_lows = swing_lows(close), swing_lows(rsi)
    if len(price_lows) >= 2 and len(rsi_lows) >= 2:
        p1, p2 = price_lows[-2], price_lows[-1]
        r1, r2 = rsi_lows[-2], rsi_lows[-1]
        if close[p2] < close[p1] and rsi[r2] > rsi[r1]:
            return "BULLISH"

    price_highs, rsi_highs = swing_highs(close), swing_highs(rsi)
    if len(price_highs) >= 2 and len(rsi_highs) >= 2:
        p1, p2 = price_highs[-2], price_highs[-1]
        r1, r2 = rsi_highs[-2], rsi_highs[-1]
        if close[p2] > close[p1] and rsi[r2] < rsi[r1]:
            return "BEARISH"

    return "NEUTRAAL"


def _calc_rsi_local(series: pd.Series, period: int = 14) -> pd.Series:
    """Bereken RSI lokaal als fallback voor API."""
    d    = series.diff()
    gain = d.clip(lower=0).rolling(period).mean()
    loss = (-d.clip(upper=0)).rolling(period).mean()
    rs   = gain / loss
    return 100 - (100 / (1 + rs))


def _calc_williams_local(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Bereken Williams %R lokaal: schaal -100 (oversold) tot 0 (overbought)."""
    highest_high = high.rolling(period).max()
    lowest_low   = low.rolling(period).min()
    wr = (highest_high - close) / (highest_high - lowest_low) * -100
    return wr


def _calc_adx_local(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Bereken ADX lokaal: maat voor trendsterkte (niet richting), 0–100."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low  - close.shift(1)).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    dm_plus  = high - high.shift(1)
    dm_minus = low.shift(1) - low
    dm_plus  = dm_plus.where((dm_plus  > dm_minus) & (dm_plus  > 0), 0.0)
    dm_minus = dm_minus.where((dm_minus > dm_plus)  & (dm_minus > 0), 0.0)

    alpha = 1 / period
    atr      = tr.ewm(alpha=alpha, adjust=False).mean()
    di_plus  = 100 * dm_plus.ewm(alpha=alpha,  adjust=False).mean() / atr
    di_minus = 100 * dm_minus.ewm(alpha=alpha, adjust=False).mean() / atr

    dx  = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, float("nan"))
    adx = dx.ewm(alpha=alpha, adjust=False).mean()
    return adx


# ─────────────────────────────────────────────
# SCORE FUNCTIES
# ─────────────────────────────────────────────

def score_rsi(rsi: float) -> Optional[float]:
    if rsi is None: return None
    if rsi < 20:    return 100.0
    if rsi < 30:    return 90.0
    if rsi < 45:    return 70.0
    if rsi < 55:    return 50.0
    if rsi < 70:    return 30.0
    return 10.0

def score_ma200(price: float, ma200: float) -> Optional[float]:
    if not price or not ma200: return None
    pct = (price - ma200) / ma200 * 100
    if pct < -10:  return 100.0
    if pct < 0:    return 80.0
    if pct < 5:    return 70.0
    if pct < 15:   return 55.0
    if pct < 30:   return 35.0
    return 10.0

def score_forward_pe(fpe: float, hist_pe: float) -> Optional[float]:
    if not fpe or not hist_pe: return None
    r = fpe / hist_pe
    if r < 0.7:  return 100.0
    if r < 0.9:  return 75.0
    if r < 1.0:  return 60.0
    if r < 1.1:  return 50.0
    if r < 1.3:  return 35.0
    return 15.0

def score_peg(peg: float) -> Optional[float]:
    if not peg or peg <= 0: return None
    if peg < 0.5:  return 100.0
    if peg < 0.75: return 85.0
    if peg < 1.0:  return 75.0
    if peg < 1.5:  return 55.0
    if peg < 2.0:  return 35.0
    return 10.0

def score_price_fcf(pfcf: float, hist: float) -> Optional[float]:
    if not pfcf or not hist: return None
    r = pfcf / hist
    if r < 0.7:  return 100.0
    if r < 0.9:  return 75.0
    if r < 1.0:  return 60.0
    if r < 1.2:  return 45.0
    return 20.0

def score_momentum(ret: float, sector_ret: float) -> Optional[float]:
    if ret is None: return None
    rel = ret - (sector_ret or 0)
    if rel > 10:   return 90.0
    if rel > 5:    return 75.0
    if rel > 0:    return 60.0
    if rel > -5:   return 45.0
    if rel > -10:  return 30.0
    return 15.0

def score_ma20(price: float, ma20: float) -> Optional[float]:
    """Hoe ver staat prijs onder/boven MA20? Onder = koopkans."""
    if not price or not ma20: return None
    pct = (price - ma20) / ma20 * 100
    if pct < -10:  return 100.0
    if pct < -5:   return 85.0
    if pct < 0:    return 70.0
    if pct < 3:    return 55.0
    if pct < 10:   return 40.0
    return 25.0

def score_panic(bb_pct_b: float, vol_spike: float) -> Optional[float]:
    """Paniekdetector op basis van Bollinger Band %B + volume spike."""
    if bb_pct_b is None: return None
    if bb_pct_b < 0:     s = 95.0
    elif bb_pct_b < 0.2: s = 80.0
    elif bb_pct_b < 0.4: s = 62.0
    elif bb_pct_b < 0.6: s = 50.0
    elif bb_pct_b < 0.8: s = 38.0
    else:                s = 20.0
    if vol_spike and vol_spike > 2.0:
        s = min(100.0, s + 10.0)
    return s

def score_rsi_divergence(div: str, rsi_val=None, momentum=None) -> Optional[float]:
    if div == "BULLISH": return 85.0
    if div == "BEARISH":
        # Onderdruk bearish signaal als RSI al oversold of momentum al sterk negatief:
        # bearish divergentie is alleen zinvol bij toppen, niet bij al ingezette dalingen
        if (rsi_val is not None and rsi_val < 40) or (momentum is not None and momentum < -0.10):
            return None
        return 20.0
    return None  # Geen divergentie = geen signaal, niet meetellen

def score_williams(w) -> Optional[float]:
    """Williams %R: schaal -100 (oversold) tot 0 (overbought). None = niet beschikbaar."""
    if w is None: return None
    if w < -90:  return 95.0
    if w < -80:  return 80.0
    if w < -50:  return 60.0
    if w < -20:  return 40.0
    if w < -10:  return 25.0
    return 15.0

def score_adx(adx) -> Optional[float]:
    """ADX meet trendsterkte (niet richting). >25 = trend aanwezig. None = niet beschikbaar."""
    if adx is None: return None
    if adx > 50:  return 75.0
    if adx > 25:  return 60.0
    if adx > 15:  return 50.0
    return 40.0

def score_analyst_target(price: float, target, n_analysts: int = 0) -> Optional[float]:
    """Scoort op basis van upside naar analistenconsensus koersdoel. None = niet beschikbaar."""
    if not price or not target or target <= 0: return None
    if n_analysts < 2: return None
    upside = (target - price) / price * 100
    if upside > 25:  return 100.0
    if upside > 15:  return 85.0
    if upside > 5:   return 70.0
    if upside > 0:   return 55.0
    if upside > -10: return 35.0
    return 15.0

def score_apz(price: float, apz_lower: float, apz_upper: float) -> float:
    if not price or apz_lower is None or apz_upper is None: return 50.0
    zone = apz_upper - apz_lower
    if zone <= 0: return 50.0
    pct = (price - apz_lower) / zone
    if pct < 0:    return 100.0
    if pct < 0.2:  return 85.0
    if pct < 0.4:  return 65.0
    if pct < 0.6:  return 50.0
    if pct < 0.8:  return 35.0
    if pct <= 1.0: return 20.0
    return 10.0


# ─────────────────────────────────────────────
# INTERPRETATIE HELPERS
# ─────────────────────────────────────────────

def _interp(signal: str, label: str, value) -> dict:
    return {"signal": signal, "label": label, "value": value}

def _with_meta(d: dict, base_key: str) -> dict:
    meta = INDICATOR_META.get(base_key, {})
    return {**d, "indicator_label": meta.get("label", base_key), "tooltip": meta.get("tooltip", "")}

def _interp_rsi(rsi, tf: str) -> dict:
    if rsi is None: return _interp("NEUTRAAL",   f"RSI {tf} — geen data",                          None)
    if rsi < 20:    return _interp("OVERSOLD",   f"RSI {tf} {rsi} — extreem oversold",              rsi)
    if rsi < 30:    return _interp("OVERSOLD",   f"RSI {tf} {rsi} — oversold, mogelijke koopkans",  rsi)
    if rsi < 45:    return _interp("DICHTBIJ",   f"RSI {tf} {rsi} — licht oversold",                rsi)
    if rsi < 55:    return _interp("NEUTRAAL",   f"RSI {tf} {rsi} — neutraal",                      rsi)
    if rsi < 70:    return _interp("DICHTBIJ",   f"RSI {tf} {rsi} — licht overbought",              rsi)
    return                 _interp("OVERBOUGHT", f"RSI {tf} {rsi} — overbought, mogelijke verkoopkans", rsi)

def _interp_ma(price, ma, name: str) -> dict:
    if not price or not ma: return _interp("NEUTRAAL", f"{name} — geen data", None)
    pct = round((price - ma) / ma * 100, 1)
    if pct < -10: return _interp("OVERSOLD",   f"{name} {pct}% onder MA — sterk oversold",       pct)
    if pct < -5:  return _interp("OVERSOLD",   f"{name} {pct}% onder MA — oversold",              pct)
    if pct < 0:   return _interp("DICHTBIJ",   f"{name} {pct}% onder MA",                         pct)
    if pct < 3:   return _interp("NEUTRAAL",   f"{name} +{pct}% boven MA",                        pct)
    if pct < 10:  return _interp("DICHTBIJ",   f"{name} +{pct}% boven MA — licht overbought",     pct)
    return               _interp("OVERBOUGHT", f"{name} +{pct}% boven MA — overbought",           pct)

def _interp_forward_pe(fpe, hist_pe) -> dict:
    if not fpe or not hist_pe: return _interp("NEUTRAAL", "Fwd P/E — geen data (alleen beschikbaar voor US-aandelen)", None)
    r = fpe / hist_pe
    if r < 0.7:  return _interp("OVERSOLD",   f"Fwd P/E {fpe} — sterk onder historisch gemiddelde", fpe)
    if r < 0.9:  return _interp("DICHTBIJ",   f"Fwd P/E {fpe} — licht ondergewaardeerd",             fpe)
    if r < 1.1:  return _interp("NEUTRAAL",   f"Fwd P/E {fpe} — in lijn met historisch",             fpe)
    if r < 1.3:  return _interp("DICHTBIJ",   f"Fwd P/E {fpe} — licht overgewaardeerd",              fpe)
    return              _interp("OVERBOUGHT", f"Fwd P/E {fpe} — duur t.o.v. historisch",             fpe)

def _interp_peg(peg) -> dict:
    if not peg or peg <= 0: return _interp("NEUTRAAL", "PEG — geen data (alleen beschikbaar voor US-aandelen)", None)
    if peg < 0.5:  return _interp("OVERSOLD",   f"PEG {peg} — groei niet ingeprijsd, koopkans",  peg)
    if peg < 1.0:  return _interp("DICHTBIJ",   f"PEG {peg} — redelijk gewaardeerd",              peg)
    if peg < 1.5:  return _interp("NEUTRAAL",   f"PEG {peg} — fair value",                        peg)
    if peg < 2.0:  return _interp("DICHTBIJ",   f"PEG {peg} — licht overgewaardeerd",             peg)
    return                _interp("OVERBOUGHT", f"PEG {peg} — overgewaardeerd",                   peg)

def _interp_price_fcf(pfcf, hist) -> dict:
    if not pfcf or not hist: return _interp("NEUTRAAL", "P/FCF — geen data (alleen beschikbaar voor US-aandelen)", None)
    r = pfcf / hist
    if r < 0.7:  return _interp("OVERSOLD",   f"P/FCF {pfcf} — sterk goedkoop t.o.v. historisch", pfcf)
    if r < 0.9:  return _interp("DICHTBIJ",   f"P/FCF {pfcf} — licht goedkoop",                    pfcf)
    if r < 1.0:  return _interp("NEUTRAAL",   f"P/FCF {pfcf} — rond historisch gemiddelde",         pfcf)
    return              _interp("OVERBOUGHT", f"P/FCF {pfcf} — duurder dan historisch",             pfcf)

def _interp_momentum(mom, sector_ret) -> dict:
    if mom is None: return _interp("NEUTRAAL", "Momentum — geen data (sectorvergelijking niet beschikbaar)", None)
    rel = round(mom - (sector_ret or 0), 1)
    if rel > 10:   return _interp("BULLISH",  f"Momentum (gew. 1M/3M/6M) +{rel}% vs sector — sterk positief",  rel)
    if rel > 5:    return _interp("BULLISH",  f"Momentum (gew. 1M/3M/6M) +{rel}% vs sector — positief",         rel)
    if rel > 0:    return _interp("DICHTBIJ", f"Momentum (gew. 1M/3M/6M) +{rel}% vs sector — licht positief",   rel)
    if rel > -5:   return _interp("NEUTRAAL", f"Momentum (gew. 1M/3M/6M) {rel}% vs sector — licht negatief",    rel)
    if rel > -10:  return _interp("BEARISH",  f"Momentum (gew. 1M/3M/6M) {rel}% vs sector — negatief",          rel)
    return                _interp("BEARISH",  f"Momentum (gew. 1M/3M/6M) {rel}% vs sector — sterk negatief",    rel)

def _interp_panic(bb_pct_b, vol_spike) -> dict:
    if bb_pct_b is None: return _interp("NEUTRAAL", "Paniek — geen data", None)
    v = round(bb_pct_b, 2)
    vol_txt = f", vol ×{vol_spike:.1f}" if vol_spike and vol_spike > 1.5 else ""
    if bb_pct_b < 0:    return _interp("OVERSOLD",   f"BB %B {v}{vol_txt} — extreme paniek, koopkans", v)
    if bb_pct_b < 0.2:  return _interp("OVERSOLD",   f"BB %B {v}{vol_txt} — oversold zone",             v)
    if bb_pct_b < 0.4:  return _interp("DICHTBIJ",   f"BB %B {v} — licht oversold",                     v)
    if bb_pct_b < 0.6:  return _interp("NEUTRAAL",   f"BB %B {v} — neutraal",                            v)
    if bb_pct_b < 0.8:  return _interp("DICHTBIJ",   f"BB %B {v} — licht overbought",                    v)
    return                      _interp("OVERBOUGHT", f"BB %B {v}{vol_txt} — overbought zone",            v)

def _interp_divergence(div: str, tf: str, rsi_val=None, momentum=None) -> dict:
    if div == "BULLISH": return _interp("BULLISH", f"RSI divergentie {tf} — bullish (koers daalt, RSI stijgt)", div)
    if div == "BEARISH":
        # Toon reden van onderdrukking als de score-filter ook aanslaat
        onderdrukt = (rsi_val is not None and rsi_val < 40) or (momentum is not None and momentum < -0.10)
        if onderdrukt:
            redenen = []
            if rsi_val is not None and rsi_val < 40:
                redenen.append(f"RSI {round(rsi_val, 1)} oversold")
            if momentum is not None and momentum < -0.10:
                redenen.append(f"momentum {round(momentum * 100, 1)}%")
            reden_txt = " / ".join(redenen)
            return _interp("BEARISH", f"RSI divergentie {tf} — bearish onderdrukt ({reden_txt})", div)
        return _interp("BEARISH", f"RSI divergentie {tf} — bearish (koers stijgt, RSI daalt)", div)
    return {**_interp("NEUTRAAL", f"RSI divergentie {tf} — geen divergentie", div), "hide": True}

def _interp_williams(w, tf: str) -> dict:
    if w is None: return {**_interp("NEUTRAAL", f"Williams %R {tf} — niet beschikbaar", None), "hide": True}
    v = round(w, 1)
    if w < -90:  return _interp("OVERSOLD",   f"Williams %R {tf} {v} — extreem oversold (koopkans)", v)
    if w < -80:  return _interp("OVERSOLD",   f"Williams %R {tf} {v} — oversold",                     v)
    if w < -50:  return _interp("DICHTBIJ",   f"Williams %R {tf} {v} — licht oversold",               v)
    if w < -20:  return _interp("NEUTRAAL",   f"Williams %R {tf} {v} — neutraal",                     v)
    if w < -10:  return _interp("DICHTBIJ",   f"Williams %R {tf} {v} — licht overbought",             v)
    return               _interp("OVERBOUGHT", f"Williams %R {tf} {v} — extreem overbought",          v)

def _interp_adx(adx, tf: str) -> dict:
    if adx is None: return {**_interp("NEUTRAAL", f"ADX {tf} — niet beschikbaar", None), "hide": True}
    v = round(adx, 1)
    if adx > 50:  return _interp("BULLISH",  f"ADX {tf} {v} — zeer sterke trend aanwezig", v)
    if adx > 25:  return _interp("DICHTBIJ", f"ADX {tf} {v} — trend aanwezig",              v)
    if adx > 15:  return _interp("NEUTRAAL", f"ADX {tf} {v} — zwakke trend / zijwaarts",    v)
    return               _interp("NEUTRAAL", f"ADX {tf} {v} — geen duidelijke trend",       v)

def _interp_analyst_target(price, target, n_analysts: int) -> dict:
    if not target or not price: return {**_interp("NEUTRAAL", "Koersdoel — geen data", None), "hide": True}
    if n_analysts < 2:          return {**_interp("NEUTRAAL", f"Koersdoel — te weinig analisten ({n_analysts})", None), "hide": True}
    upside = round((target - price) / price * 100, 1)
    if upside > 25:   return _interp("OVERSOLD",   f"Koersdoel {target:.0f} — {upside}% upside (sterk ondergewaardeerd)", upside)
    if upside > 15:   return _interp("DICHTBIJ",   f"Koersdoel {target:.0f} — {upside}% upside",                          upside)
    if upside > 5:    return _interp("DICHTBIJ",   f"Koersdoel {target:.0f} — {upside}% upside (licht ondergewaardeerd)", upside)
    if upside > 0:    return _interp("NEUTRAAL",   f"Koersdoel {target:.0f} — {upside}% upside (nabij fair value)",       upside)
    if upside > -10:  return _interp("DICHTBIJ",   f"Koersdoel {target:.0f} — {upside}% (licht overgewaardeerd)",        upside)
    return                   _interp("OVERBOUGHT", f"Koersdoel {target:.0f} — {upside}% (sterk overgewaardeerd)",        upside)

def _interp_apz(price, apz_lo, apz_up, tf: str) -> dict:
    if apz_lo is None or apz_up is None or price is None:
        return _interp("NEUTRAAL", f"APZ {tf} — geen data", None)
    zone = apz_up - apz_lo
    pct  = round((price - apz_lo) / zone * 100, 0) if zone > 0 else 50
    if price < apz_lo:  return _interp("OVERSOLD",   f"APZ {tf} — koers onder ondergrens (oversold)",   pct)
    if price > apz_up:  return _interp("OVERBOUGHT", f"APZ {tf} — koers boven bovengrens (overbought)", pct)
    if pct < 30:        return _interp("DICHTBIJ",   f"APZ {tf} — onderkant zone ({pct:.0f}%)",         pct)
    if pct > 70:        return _interp("DICHTBIJ",   f"APZ {tf} — bovenkant zone ({pct:.0f}%)",         pct)
    return                      _interp("NEUTRAAL",   f"APZ {tf} — midden zone ({pct:.0f}%)",            pct)


# ─────────────────────────────────────────────
# DATA OPHALEN
# ─────────────────────────────────────────────

def fetch_stock_data(ticker: str, as_of_date: str = None) -> dict:
    try:
        # Bepaal referentiedatum (historische modus of vandaag)
        if as_of_date:
            ref_date = datetime.strptime(as_of_date, "%Y-%m-%d")
            historical_mode = True
        else:
            ref_date = datetime.now()
            historical_mode = False

        # ── 1. Profiel (naam, sector, valuta, marktkapitalisatie) ──
        profile_data = _fmp_get("/profile", {"symbol": ticker})
        if not profile_data or not isinstance(profile_data, list):
            return None
        profile = profile_data[0]

        # ── 2. Koersgeschiedenis (30 jaar dagelijks op Premium) ───
        thirty_years_ago = (ref_date - timedelta(days=30 * 365)).strftime("%Y-%m-%d")
        today = ref_date.strftime("%Y-%m-%d")
        hist_data = _fmp_get(
            "/historical-price-eod/full",
            {"symbol": ticker, "from": thirty_years_ago, "to": today},
        )
        if hist_data == "PREMIUM":
            return {"error": f"{ticker} vereist een betaald FMP-plan (niet beschikbaar op gratis tier)", "ticker": ticker}
        if isinstance(hist_data, dict):
            hist_data = hist_data.get("historical", [])
        if not hist_data or not isinstance(hist_data, list):
            return None

        # FMP geeft nieuwste-eerst terug → omkeren naar oudste-eerst
        hist_list = list(reversed(hist_data))
        hist = pd.DataFrame(hist_list)
        hist["date"] = pd.to_datetime(hist["date"])
        hist = hist.set_index("date")
        hist = hist.rename(columns={"close": "Close", "volume": "Volume"})

        if len(hist) < 20:
            return None

        price = float(hist["Close"].iloc[-1])

        # ── OHLCV voor de referentiedag ────────────────────────────
        last_raw = hist_list[-1]
        ohlc_day = {
            "date":      str(hist.index[-1].date()),
            "open":      last_raw.get("open"),
            "high":      last_raw.get("high"),
            "low":       last_raw.get("low"),
            "close":     last_raw.get("close"),
            "adj_close": last_raw.get("adjClose"),
            "volume":    last_raw.get("volume"),
        }

        # ── 3. Ratio's TTM (P/E, PEG, P/FCF) + Analyst Price Target ──
        if not historical_mode:
            ratios_data = _fmp_get("/ratios-ttm", {"symbol": ticker})
            ratios = ratios_data[0] if ratios_data and isinstance(ratios_data, list) else {}
            # Analyst consensus price target (US-aandelen only)
            target_data = _fmp_get("/price-target-summary", {"symbol": ticker})
            analyst_target = None
            n_analysts = 0
            if target_data and isinstance(target_data, list) and len(target_data) > 0:
                t = target_data[0]
                analyst_target = t.get("targetMedian") or t.get("targetConsensus")
                n_analysts = int(t.get("numberOfAnalysts") or 0)
        else:
            ratios = {}
            analyst_target = None
            n_analysts = 0

        tpe      = ratios.get("priceToEarningsRatioTTM")
        peg      = ratios.get("priceToEarningsGrowthRatioTTM")
        pfcf     = ratios.get("priceToFreeCashFlowRatioTTM")

        fpe       = tpe
        hist_pe   = tpe * 0.95 if tpe else None
        hist_pfcf = pfcf * 1.05 if pfcf else None

        # ── 4. Sector performance (live modus) ────────────────────
        sector = profile.get("sector", "")
        sector_return = 0.0
        if not historical_mode:
            sector_perf = fetch_sector_performance()
            sector_return = sector_perf.get(sector, 0.0)

        # ── 5. Resample voor wekelijkse / maandelijkse series ─────
        hist_w = hist["Close"].resample("W").last()
        hist_m = hist["Close"].resample("ME").last()

        # ── Hulpfunctie: RSI via API ophalen en als Series teruggeven ──
        def _try_rsi_api(interval: str, limit: int = 30):
            """Probeert RSI op te halen via API. Geeft (waarde, series) of (None, None)."""
            data = _fetch_indicator(ticker, "rsi", 14, interval, limit)
            if not data:
                return None, None
            data_asc = list(reversed(data))
            vals = []
            for x in data_asc:
                v = x.get("rsi")
                vals.append(float(v) if v is not None else None)
            series = pd.Series(vals, dtype=float).dropna()
            if len(series) == 0:
                return None, None
            return float(series.iloc[-1]), series

        # ── 6. RSI per timeframe (API eerst, fallback op lokale berekening) ──
        if not historical_mode:
            rsi_val_d, rsi_api_series_d = _try_rsi_api("daily",   30)
            rsi_val_w, rsi_api_series_w = _try_rsi_api("weekly",  30)
            rsi_val_m, rsi_api_series_m = _try_rsi_api("monthly", 30)
        else:
            rsi_val_d = rsi_val_w = rsi_val_m = None
            rsi_api_series_d = rsi_api_series_w = rsi_api_series_m = None

        # Dagelijkse RSI + divergentie
        if rsi_val_d is not None:
            rsi_d       = rsi_val_d
            rsi_series_d = rsi_api_series_d
        else:
            rsi_series_d = _calc_rsi_local(hist["Close"])
            rsi_d        = float(rsi_series_d.iloc[-1])
        rsi_div_d = calc_rsi_divergence(hist["Close"], rsi_series_d)

        # Wekelijkse RSI + divergentie
        if rsi_val_w is not None:
            rsi_w        = rsi_val_w
            rsi_series_w = rsi_api_series_w
        else:
            rsi_series_w = _calc_rsi_local(hist_w) if len(hist_w) > 14 else pd.Series(dtype=float)
            rsi_w        = float(rsi_series_w.iloc[-1]) if len(rsi_series_w) > 14 else None
        rsi_div_w = calc_rsi_divergence(hist_w, rsi_series_w) if len(rsi_series_w) >= 14 else "NEUTRAAL"

        # Maandelijkse RSI + divergentie
        if rsi_val_m is not None:
            rsi_m        = rsi_val_m
            rsi_series_m = rsi_api_series_m
        else:
            rsi_series_m = _calc_rsi_local(hist_m) if len(hist_m) > 14 else pd.Series(dtype=float)
            rsi_m        = float(rsi_series_m.iloc[-1]) if len(rsi_series_m) > 14 else None
        rsi_div_m = calc_rsi_divergence(hist_m, rsi_series_m) if len(rsi_series_m) >= 14 else "NEUTRAAL"

        # ── 7. MA20 en MA200 (API eerst, fallback op lokale berekening) ──
        if not historical_mode:
            sma20_api  = _fetch_indicator(ticker, "sma", 20,  "daily", 5)
            sma200_api = _fetch_indicator(ticker, "sma", 200, "daily", 5)
            ma20_d = (float(sma20_api[0]["sma"])  if sma20_api  and sma20_api[0].get("sma")
                      else float(hist["Close"].rolling(20).mean().iloc[-1]))
            ma200  = (float(sma200_api[0]["sma"]) if sma200_api and sma200_api[0].get("sma")
                      else (float(hist["Close"].rolling(200).mean().iloc[-1]) if len(hist) >= 200
                            else float(hist["Close"].mean())))
        else:
            ma20_d = float(hist["Close"].rolling(20).mean().iloc[-1])
            ma200  = (float(hist["Close"].rolling(200).mean().iloc[-1])
                      if len(hist) >= 200 else float(hist["Close"].mean()))

        # MA20 wekelijks en maandelijks (altijd berekend uit dagelijkse data)
        ma20_w = (hist_w.rolling(20).mean().iloc[-1] if len(hist_w) >= 20 else hist_w.mean())
        ma20_m = (hist_m.rolling(20).mean().iloc[-1] if len(hist_m) >= 20 else hist_m.mean())

        # ── 8. APZ per timeframe ──────────────────────────────────
        apz_ema_d, apz_up_d, apz_lo_d = calc_apz(hist["Close"])
        apz_ema_w, apz_up_w, apz_lo_w = calc_apz(hist_w) if len(hist_w) >= 20 else (None, None, None)
        apz_ema_m, apz_up_m, apz_lo_m = calc_apz(hist_m) if len(hist_m) >= 20 else (None, None, None)

        # ── 9. Volume spike ───────────────────────────────────────
        vol_avg20 = hist["Volume"].rolling(20).mean().iloc[-1]
        vol_spike = float(hist["Volume"].iloc[-1] / vol_avg20) if vol_avg20 and vol_avg20 > 0 else None

        # ── 10. Bollinger Bands (lokaal berekend) ────────────────
        bb_mid   = hist["Close"].rolling(20).mean().iloc[-1]
        bb_std   = hist["Close"].rolling(20).std().iloc[-1]
        bb_width = float((bb_mid + 2 * bb_std) - (bb_mid - 2 * bb_std))
        bb_pct_b = float((price - (bb_mid - 2 * bb_std)) / bb_width) if bb_width > 0 else None

        # ── 11. Momentum gewogen 1M/3M/6M vs sector ─────────────
        n = len(hist)
        mom_1m = ((price - float(hist["Close"].iloc[-22]))  / float(hist["Close"].iloc[-22])  * 100) if n > 22  else None
        mom_3m = ((price - float(hist["Close"].iloc[-66]))  / float(hist["Close"].iloc[-66])  * 100) if n > 66  else None
        mom_6m = ((price - float(hist["Close"].iloc[-132])) / float(hist["Close"].iloc[-132]) * 100) if n > 132 else None
        parts = [(v, w) for v, w in [(mom_1m, 0.30), (mom_3m, 0.40), (mom_6m, 0.30)] if v is not None]
        mom = sum(v * w for v, w in parts) / sum(w for _, w in parts) if parts else 0.0

        # ── 12. Williams %R en ADX per timeframe ──
        williams_intraday = williams_daily = williams_weekly = williams_monthly = None
        adx_intraday = adx_daily = adx_weekly = adx_monthly = None

        if not historical_mode:
            for tf_name, tf_key in [("daily", "daily"), ("weekly", "weekly"), ("monthly", "monthly")]:
                w_data = _fetch_indicator(ticker, "williams", 14, tf_key, 3)
                if w_data:
                    raw = w_data[0].get("Williams") or w_data[0].get("williams")
                    if tf_name == "daily":   williams_daily   = float(raw) if raw is not None else None
                    elif tf_name == "weekly":  williams_weekly  = float(raw) if raw is not None else None
                    elif tf_name == "monthly": williams_monthly = float(raw) if raw is not None else None
                adx_data = _fetch_indicator(ticker, "adx", 14, tf_key, 3)
                if adx_data:
                    raw = adx_data[0].get("adx") or adx_data[0].get("ADX")
                    if tf_name == "daily":   adx_daily   = float(raw) if raw is not None else None
                    elif tf_name == "weekly":  adx_weekly  = float(raw) if raw is not None else None
                    elif tf_name == "monthly": adx_monthly = float(raw) if raw is not None else None
            # Fallback: bereken ADX wekelijks lokaal als API geen weekly-data levert (FMP ondersteunt 1week niet)
            if adx_weekly is None:
                hi_w = hist["high"].resample("W").max()
                lo_w = hist["low"].resample("W").min()
                adx_w = _calc_adx_local(hi_w, lo_w, hist_w)
                adx_weekly = float(adx_w.dropna().iloc[-1]) if len(adx_w.dropna()) > 0 else None
        else:
            # Historische modus: lokale berekening uit EOD-data
            hi_d  = hist["high"]
            lo_d  = hist["low"]
            cl_d  = hist["Close"]
            hi_w  = hist["high"].resample("W").max()
            lo_w  = hist["low"].resample("W").min()
            cl_w  = hist_w
            hi_m  = hist["high"].resample("ME").max()
            lo_m  = hist["low"].resample("ME").min()
            cl_m  = hist_m

            wr_d = _calc_williams_local(hi_d, lo_d, cl_d)
            wr_w = _calc_williams_local(hi_w, lo_w, cl_w)
            wr_m = _calc_williams_local(hi_m, lo_m, cl_m)
            williams_daily   = float(wr_d.dropna().iloc[-1]) if len(wr_d.dropna()) > 0 else None
            williams_weekly  = float(wr_w.dropna().iloc[-1]) if len(wr_w.dropna()) > 0 else None
            williams_monthly = float(wr_m.dropna().iloc[-1]) if len(wr_m.dropna()) > 0 else None

            adx_d = _calc_adx_local(hi_d, lo_d, cl_d)
            adx_w = _calc_adx_local(hi_w, lo_w, cl_w)
            adx_m = _calc_adx_local(hi_m, lo_m, cl_m)
            adx_daily   = float(adx_d.dropna().iloc[-1]) if len(adx_d.dropna()) > 0 else None
            adx_weekly  = float(adx_w.dropna().iloc[-1]) if len(adx_w.dropna()) > 0 else None
            adx_monthly = float(adx_m.dropna().iloc[-1]) if len(adx_m.dropna()) > 0 else None

        # ── 13. Intraday 4-uurs timeframe (live modus, Premium) ──
        rsi_intraday = rsi_div_intraday = ma20_intraday = None
        apz_up_intraday = apz_lo_intraday = None
        intraday_history = []

        if not historical_mode:
            intraday_from = (ref_date - timedelta(days=90)).strftime("%Y-%m-%d")
            intraday_raw = _fmp_get(
                "/historical-chart/4hour",
                {"symbol": ticker, "from": intraday_from, "to": today}
            )
            if intraday_raw and isinstance(intraday_raw, list) and len(intraday_raw) >= 20:
                intraday_df = pd.DataFrame(list(reversed(intraday_raw)))
                intraday_df["date"] = pd.to_datetime(intraday_df["date"])
                intraday_df = intraday_df.set_index("date")
                intraday_df = intraday_df.rename(columns={"close": "Close", "volume": "Volume"})

                rsi_intraday_series = _calc_rsi_local(intraday_df["Close"])
                intraday_history = [
                    {
                        "date":  str(idx),
                        "close": round(float(val), 2),
                        "rsi":   round(float(rsi_intraday_series.loc[idx]), 1)
                                 if idx in rsi_intraday_series.index and not pd.isna(rsi_intraday_series.loc[idx])
                                 else None,
                    }
                    for idx, val in intraday_df["Close"].items()
                ]

                # RSI 4-uurs via API
                rsi_4h_data = _fetch_indicator(ticker, "rsi", 14, "4hour", 50)
                if rsi_4h_data:
                    rsi_4h_asc = list(reversed(rsi_4h_data))
                    rsi_vals_4h = [float(x["rsi"]) if x.get("rsi") is not None else None
                                   for x in rsi_4h_asc]
                    rsi_series_4h = pd.Series(rsi_vals_4h, dtype=float).dropna()
                    rsi_intraday = float(rsi_series_4h.iloc[-1]) if len(rsi_series_4h) > 0 else None
                    rsi_div_intraday = (calc_rsi_divergence(intraday_df["Close"], rsi_series_4h)
                                        if len(rsi_series_4h) >= 14 else "NEUTRAAL")
                else:
                    rsi_series_4h = _calc_rsi_local(intraday_df["Close"])
                    valid_4h = rsi_series_4h.dropna()
                    rsi_intraday = float(valid_4h.iloc[-1]) if len(valid_4h) > 0 else None
                    rsi_div_intraday = calc_rsi_divergence(intraday_df["Close"], rsi_series_4h)

                # MA20 4-uurs via API
                sma20_4h = _fetch_indicator(ticker, "sma", 20, "4hour", 3)
                if sma20_4h and sma20_4h[0].get("sma"):
                    ma20_intraday = float(sma20_4h[0]["sma"])
                elif len(intraday_df) >= 20:
                    ma20_intraday = float(intraday_df["Close"].rolling(20).mean().iloc[-1])

                # APZ intraday
                if len(intraday_df) >= 20:
                    _, apz_up_intraday, apz_lo_intraday = calc_apz(intraday_df["Close"])

                # Williams %R en ADX intraday
                w_4h = _fetch_indicator(ticker, "williams", 14, "4hour", 3)
                if w_4h:
                    raw = w_4h[0].get("Williams") or w_4h[0].get("williams")
                    williams_intraday = float(raw) if raw is not None else None
                adx_4h = _fetch_indicator(ticker, "adx", 14, "4hour", 3)
                if adx_4h:
                    raw = adx_4h[0].get("adx") or adx_4h[0].get("ADX")
                    adx_intraday = float(raw) if raw is not None else None

        # ── 14. RSI-waarden voor chart-overlay (lokale berekening op volledige history) ──
        rsi_hist_series = _calc_rsi_local(hist["Close"])
        rsi_history: dict = {
            str(idx.date()): round(float(v), 1)
            for idx, v in rsi_hist_series.items()
            if not pd.isna(v)
        }

        # ── 15. MA-waarden voor chart-overlay (limit=500 ≈ 2 jaar) ──
        ma20_history: dict = {}
        ma200_history: dict = {}
        if not historical_mode:
            ma20_full = _fetch_indicator(ticker, "sma", 20,  "daily", 500)
            if ma20_full:
                for item in ma20_full:
                    dk = (item.get("date") or "")[:10]
                    if dk and item.get("sma") is not None:
                        ma20_history[dk] = round(float(item["sma"]), 2)
            ma200_full = _fetch_indicator(ticker, "sma", 200, "daily", 500)
            if ma200_full:
                for item in ma200_full:
                    dk = (item.get("date") or "")[:10]
                    if dk and item.get("sma") is not None:
                        ma200_history[dk] = round(float(item["sma"]), 2)

        # Lokale fallback: bereken MA uit koershistorie als API leeg is (bijv. historische modus)
        if not ma20_history:
            for idx, val in hist["Close"].rolling(20).mean().items():
                if not pd.isna(val):
                    ma20_history[str(idx.date())] = round(float(val), 2)
        if not ma200_history:
            for idx, val in hist["Close"].rolling(200).mean().items():
                if not pd.isna(val):
                    ma200_history[str(idx.date())] = round(float(val), 2)

        return {
            "ticker":               ticker,
            "name":                 profile.get("companyName") or profile.get("name", ticker),
            "sector":               sector,
            "current_price":        round(price, 2),
            "currency":             profile.get("currency", "USD"),
            "sector_return":        round(sector_return, 2),
            # RSI per timeframe
            "rsi_daily":            _r(rsi_d, 1),
            "rsi_weekly":           _r(rsi_w, 1),
            "rsi_monthly":          _r(rsi_m, 1),
            "rsi_intraday":         _r(rsi_intraday, 1),
            # RSI Divergentie per timeframe
            "rsi_divergence_daily":    rsi_div_d,
            "rsi_divergence_weekly":   rsi_div_w,
            "rsi_divergence_monthly":  rsi_div_m,
            "rsi_divergence_intraday": rsi_div_intraday or "NEUTRAAL",
            # MA20 per timeframe
            "ma20_daily":           _r(ma20_d, 2),
            "ma20_weekly":          _r(ma20_w, 2),
            "ma20_monthly":         _r(ma20_m, 2),
            "ma20_intraday":        _r(ma20_intraday, 2),
            # MA200 (dagelijks, langetermijntrend)
            "ma200":                _r(ma200, 2),
            # APZ per timeframe
            "apz_upper_daily":      apz_up_d,
            "apz_lower_daily":      apz_lo_d,
            "apz_upper_weekly":     apz_up_w,
            "apz_lower_weekly":     apz_lo_w,
            "apz_upper_monthly":    apz_up_m,
            "apz_lower_monthly":    apz_lo_m,
            "apz_upper_intraday":   apz_up_intraday,
            "apz_lower_intraday":   apz_lo_intraday,
            # Volume & Bollinger
            "vol_spike":            _r(vol_spike, 2),
            "bb_pct_b":             _r(bb_pct_b, 3),
            # Overige indicatoren
            "momentum_1m":          _r(mom, 2),
            "forward_pe":           _r(fpe, 2),
            "historical_avg_pe":    _r(hist_pe, 2),
            "peg_ratio":            _r(peg, 2),
            "price_fcf":            _r(pfcf, 2),
            "historical_avg_pfcf":  _r(hist_pfcf, 2),
            "analyst_target":       _r(analyst_target, 2),
            "n_analysts":           n_analysts,
            # Williams %R per timeframe
            "williams_daily":       _r(williams_daily, 1),
            "williams_weekly":      _r(williams_weekly, 1),
            "williams_monthly":     _r(williams_monthly, 1),
            "williams_intraday":    _r(williams_intraday, 1),
            # ADX per timeframe
            "adx_daily":            _r(adx_daily, 1),
            "adx_weekly":           _r(adx_weekly, 1),
            "adx_monthly":          _r(adx_monthly, 1),
            "adx_intraday":         _r(adx_intraday, 1),
            "fundamentals_unavailable": historical_mode,
            "ohlc_day":             ohlc_day,
            # Koersgeschiedenis met MA-overlay voor grafiek
            "price_history": [
                {
                    "date":  str(idx.date()),
                    "close": round(float(val), 2),
                    "rsi":   rsi_history.get(str(idx.date())),
                    "ma20":  ma20_history.get(str(idx.date())),
                    "ma200": ma200_history.get(str(idx.date())),
                }
                for idx, val in hist["Close"].items()
            ],
            # Intraday 4-uurs data voor grafiek
            "intraday_history": intraday_history,
        }
    except Exception as e:
        print(f"  ⚠ Fout bij {ticker}: {e}")
        return None


# ─────────────────────────────────────────────
# SCORE BEREKENEN
# ─────────────────────────────────────────────

def calculate_score(data: dict, sector_momentum: float = 0.0) -> dict:
    if data is None:
        return {"total_score": 50, "signal": "NEUTRAAL", "error": "Geen data"}
    if "error" in data:
        return {"total_score": 50, "signal": "NEUTRAAL", "error": data["error"], "ticker": data.get("ticker", "")}

    p = data["current_price"]
    # Gebruik sector_return uit de data (live sectordata), val terug op parameter
    eff_sector = data.get("sector_return", sector_momentum)

    def tf_score(rsi_val, ma20_val, rsi_div, apz_lo, apz_up, williams_val, adx_val):
        scores = {
            "rsi":             score_rsi(rsi_val),
            "ma20":            score_ma20(p, ma20_val),
            "ma200":           score_ma200(p, data["ma200"]),
            "forward_pe":      score_forward_pe(data["forward_pe"], data["historical_avg_pe"]),
            "peg":             score_peg(data["peg_ratio"]),
            "price_fcf":       score_price_fcf(data["price_fcf"], data["historical_avg_pfcf"]),
            "momentum":        score_momentum(data["momentum_1m"], eff_sector),
            "analyst_target":  score_analyst_target(p, data.get("analyst_target"), data.get("n_analysts", 0)),
            "panic":           score_panic(data["bb_pct_b"], data["vol_spike"]),
            "rsi_divergence":  score_rsi_divergence(rsi_div, rsi_val, data["momentum_1m"]),
            "apz":             score_apz(p, apz_lo, apz_up),
            "williams":        score_williams(williams_val),
            "adx":             score_adx(adx_val),
        }
        # Herverdeelt gewicht over beschikbare indicatoren (None = niet beschikbaar)
        available = {k: v for k, v in scores.items() if v is not None}
        total_weight = sum(INDICATOR_WEIGHTS[k] for k in available)
        if total_weight <= 0:
            return 50.0
        return sum(available[k] * INDICATOR_WEIGHTS[k] for k in available) / total_weight

    # Scores per timeframe
    ins = tf_score(data.get("rsi_intraday"),  data.get("ma20_intraday"),
                   data.get("rsi_divergence_intraday", "NEUTRAAL"),
                   data.get("apz_lower_intraday"), data.get("apz_upper_intraday"),
                   data.get("williams_intraday"), data.get("adx_intraday"))
    ds  = tf_score(data["rsi_daily"],   data["ma20_daily"],
                   data["rsi_divergence_daily"],
                   data["apz_lower_daily"],   data["apz_upper_daily"],
                   data.get("williams_daily"), data.get("adx_daily"))
    ws  = tf_score(data["rsi_weekly"],  data["ma20_weekly"],
                   data["rsi_divergence_weekly"],
                   data["apz_lower_weekly"],  data["apz_upper_weekly"],
                   data.get("williams_weekly"), data.get("adx_weekly"))
    ms  = tf_score(data["rsi_monthly"], data["ma20_monthly"],
                   data["rsi_divergence_monthly"],
                   data["apz_lower_monthly"], data["apz_upper_monthly"],
                   data.get("williams_monthly"), data.get("adx_monthly"))

    total  = (ins * TIMEFRAME_WEIGHTS["intraday"] +
              ds  * TIMEFRAME_WEIGHTS["daily"] +
              ws  * TIMEFRAME_WEIGHTS["weekly"] +
              ms  * TIMEFRAME_WEIGHTS["monthly"])
    signal = "KOOP" if total >= 65 else "UITSTAP" if total < 45 else "NEUTRAAL"

    # Capitulatie alert: extreme kortetermijn oversold op meerdere indicatoren tegelijk
    rsi_d_val      = data.get("rsi_daily")
    williams_d_val = data.get("williams_daily")
    bb_val         = data.get("bb_pct_b")
    capitulatie_alert = (
        rsi_d_val      is not None and rsi_d_val      < 30   and
        williams_d_val is not None and williams_d_val < -90  and
        bb_val         is not None and bb_val          < 0.2
    )

    return {
        "ticker":        data["ticker"],
        "name":          data["name"],
        "current_price": p,
        "currency":      data["currency"],
        "total_score":        round(total, 1),
        "signal":             signal,
        "capitulatie_alert":  capitulatie_alert,
        "scores_by_timeframe": {
            "intraday": round(ins, 1),
            "daily":    round(ds, 1),
            "weekly":   round(ws, 1),
            "monthly":  round(ms, 1),
        },
        "indicator_scores": {
            "rsi_daily":              _r(score_rsi(data["rsi_daily"]), 1),
            "rsi_weekly":             _r(score_rsi(data["rsi_weekly"]), 1),
            "rsi_monthly":            _r(score_rsi(data["rsi_monthly"]), 1),
            "rsi_intraday":           _r(score_rsi(data.get("rsi_intraday")), 1),
            "rsi_divergence_daily":   _r(score_rsi_divergence(data["rsi_divergence_daily"],   data["rsi_daily"],          data["momentum_1m"]), 1),
            "rsi_divergence_weekly":  _r(score_rsi_divergence(data["rsi_divergence_weekly"],  data["rsi_weekly"],         data["momentum_1m"]), 1),
            "rsi_divergence_monthly": _r(score_rsi_divergence(data["rsi_divergence_monthly"], data["rsi_monthly"],        data["momentum_1m"]), 1),
            "rsi_divergence_intraday":_r(score_rsi_divergence(data.get("rsi_divergence_intraday", "NEUTRAAL"), data.get("rsi_intraday"), data["momentum_1m"]), 1),
            "ma20_daily":             _r(score_ma20(p, data["ma20_daily"]), 1),
            "ma20_weekly":            _r(score_ma20(p, data["ma20_weekly"]), 1),
            "ma20_monthly":           _r(score_ma20(p, data["ma20_monthly"]), 1),
            "ma20_intraday":          _r(score_ma20(p, data.get("ma20_intraday")), 1),
            "ma200":                  _r(score_ma200(p, data["ma200"]), 1),
            "apz_daily":              _r(score_apz(p, data["apz_lower_daily"],    data["apz_upper_daily"]), 1),
            "apz_weekly":             _r(score_apz(p, data["apz_lower_weekly"],   data["apz_upper_weekly"]), 1),
            "apz_monthly":            _r(score_apz(p, data["apz_lower_monthly"],  data["apz_upper_monthly"]), 1),
            "apz_intraday":           _r(score_apz(p, data.get("apz_lower_intraday"), data.get("apz_upper_intraday")), 1),
            "forward_pe":             _r(score_forward_pe(data["forward_pe"], data["historical_avg_pe"]), 1),
            "peg":                    _r(score_peg(data["peg_ratio"]), 1),
            "price_fcf":              _r(score_price_fcf(data["price_fcf"], data["historical_avg_pfcf"]), 1),
            "momentum":               _r(score_momentum(data["momentum_1m"], eff_sector), 1),
            "analyst_target":         score_analyst_target(p, data.get("analyst_target"), data.get("n_analysts", 0)),
            "panic":                  _r(score_panic(data["bb_pct_b"], data["vol_spike"]), 1),
            "williams_intraday":      score_williams(data.get("williams_intraday")),
            "williams_daily":         score_williams(data.get("williams_daily")),
            "williams_weekly":        score_williams(data.get("williams_weekly")),
            "williams_monthly":       score_williams(data.get("williams_monthly")),
            "adx_intraday":           score_adx(data.get("adx_intraday")),
            "adx_daily":              score_adx(data.get("adx_daily")),
            "adx_weekly":             score_adx(data.get("adx_weekly")),
            "adx_monthly":            score_adx(data.get("adx_monthly")),
        },
        "interpretations": {
            "rsi_daily":              _with_meta(_interp_rsi(data["rsi_daily"],      "dagelijks"),   "rsi"),
            "rsi_weekly":             _with_meta(_interp_rsi(data["rsi_weekly"],     "wekelijks"),   "rsi"),
            "rsi_monthly":            _with_meta(_interp_rsi(data["rsi_monthly"],    "maandelijks"), "rsi"),
            "rsi_intraday":           _with_meta(_interp_rsi(data.get("rsi_intraday"), "4-uurs"),    "rsi"),
            "rsi_divergence_daily":   _with_meta(_interp_divergence(data["rsi_divergence_daily"],    "dagelijks",   data["rsi_daily"],          data["momentum_1m"]), "rsi_divergence"),
            "rsi_divergence_weekly":  _with_meta(_interp_divergence(data["rsi_divergence_weekly"],   "wekelijks",   data["rsi_weekly"],         data["momentum_1m"]), "rsi_divergence"),
            "rsi_divergence_monthly": _with_meta(_interp_divergence(data["rsi_divergence_monthly"],  "maandelijks", data["rsi_monthly"],        data["momentum_1m"]), "rsi_divergence"),
            "rsi_divergence_intraday":_with_meta(_interp_divergence(data.get("rsi_divergence_intraday","NEUTRAAL"), "4-uurs", data.get("rsi_intraday"), data["momentum_1m"]), "rsi_divergence"),
            "ma20_daily":             _with_meta(_interp_ma(p, data["ma20_daily"],    "MA20 dagelijks"),   "ma20"),
            "ma20_weekly":            _with_meta(_interp_ma(p, data["ma20_weekly"],   "MA20 wekelijks"),   "ma20"),
            "ma20_monthly":           _with_meta(_interp_ma(p, data["ma20_monthly"],  "MA20 maandelijks"), "ma20"),
            "ma20_intraday":          _with_meta(_interp_ma(p, data.get("ma20_intraday"), "MA20 4-uurs"),  "ma20"),
            "ma200":                  _with_meta(_interp_ma(p, data["ma200"],         "MA200"),            "ma200"),
            "apz_daily":              _with_meta(_interp_apz(p, data["apz_lower_daily"],    data["apz_upper_daily"],    "dagelijks"),   "apz"),
            "apz_weekly":             _with_meta(_interp_apz(p, data["apz_lower_weekly"],   data["apz_upper_weekly"],   "wekelijks"),   "apz"),
            "apz_monthly":            _with_meta(_interp_apz(p, data["apz_lower_monthly"],  data["apz_upper_monthly"],  "maandelijks"), "apz"),
            "apz_intraday":           _with_meta(_interp_apz(p, data.get("apz_lower_intraday"), data.get("apz_upper_intraday"), "4-uurs"), "apz"),
            "forward_pe":             _with_meta(_interp_forward_pe(data["forward_pe"], data["historical_avg_pe"]),         "forward_pe"),
            "peg":                    _with_meta(_interp_peg(data["peg_ratio"]),                                             "peg"),
            "price_fcf":              _with_meta(_interp_price_fcf(data["price_fcf"], data["historical_avg_pfcf"]),         "price_fcf"),
            "momentum":               _with_meta(_interp_momentum(data["momentum_1m"], eff_sector),                                           "momentum"),
            "analyst_target":         _with_meta(_interp_analyst_target(p, data.get("analyst_target"), data.get("n_analysts", 0)),            "analyst_target"),
            "panic":                  _with_meta(_interp_panic(data["bb_pct_b"], data["vol_spike"]),                                          "panic"),
            "williams_intraday":      _with_meta(_interp_williams(data.get("williams_intraday"), "4-uurs"),    "williams"),
            "williams_daily":         _with_meta(_interp_williams(data.get("williams_daily"),    "dagelijks"),  "williams"),
            "williams_weekly":        _with_meta(_interp_williams(data.get("williams_weekly"),   "wekelijks"),  "williams"),
            "williams_monthly":       _with_meta(_interp_williams(data.get("williams_monthly"),  "maandelijks"),"williams"),
            "adx_intraday":           _with_meta(_interp_adx(data.get("adx_intraday"), "4-uurs"),    "adx"),
            "adx_daily":              _with_meta(_interp_adx(data.get("adx_daily"),    "dagelijks"),  "adx"),
            "adx_weekly":             _with_meta(_interp_adx(data.get("adx_weekly"),   "wekelijks"),  "adx"),
            "adx_monthly":            _with_meta(_interp_adx(data.get("adx_monthly"),  "maandelijks"),"adx"),
        },
        "raw_data": data,
    }


def calculate_etf_score(results: list, holdings: list) -> dict:
    total_weight = sum(h["etf_weight"] for h in holdings)
    weight_map   = {h["ticker"]: h["etf_weight"] for h in holdings}
    valid  = [r for r in results if "error" not in r]
    score  = sum(r["total_score"] * (weight_map.get(r["ticker"], 0) / total_weight) for r in valid)
    signal = "INSTAP" if score >= 65 else "UITSTAP" if score < 45 else "AFWACHTEN"
    return {
        "etf_score":          round(score, 1),
        "etf_signal":         signal,
        "holdings_analyzed":  len(valid),
        "holdings_total":     len(holdings),
    }


# ─────────────────────────────────────────────
# FASTAPI
# ─────────────────────────────────────────────

app = FastAPI(title="ETF Intelligence API", version="2.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def root():
    return {"status": "ok", "message": "ETF Intelligence API draait!", "version": "2.0.0 (Premium)"}


@app.get("/score/{ticker}")
def get_score(ticker: str):
    data = fetch_stock_data(ticker.upper())
    return calculate_score(data)


@app.get("/etf")
def get_etf(tickers: str = None, use_cache: bool = True):
    global _etf_cache, _etf_cache_time

    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        cache_key = ",".join(sorted(ticker_list))
    else:
        ticker_list = None
        cache_key = "default"

    if use_cache and cache_key in _etf_cache and cache_key in _etf_cache_time:
        age_minutes = (datetime.now() - _etf_cache_time[cache_key]).total_seconds() / 60
        if age_minutes < CACHE_DURATION_MINUTES:
            return {**_etf_cache[cache_key], "cached": True, "cache_age_minutes": round(age_minutes, 1)}

    if ticker_list:
        weight = round(1 / len(ticker_list), 6)
        holdings = [{"ticker": t, "name": t, "etf_weight": weight} for t in ticker_list]
    else:
        holdings = ETF_HOLDINGS

    results = []
    for h in holdings:
        data  = fetch_stock_data(h["ticker"])
        score = calculate_score(data)
        score["etf_weight"] = h["etf_weight"]
        results.append(score)
    summary = calculate_etf_score(results, holdings)
    response = {
        "summary":      summary,
        "holdings":     results,
        "config":       {"timeframe_weights": TIMEFRAME_WEIGHTS, "indicator_weights": INDICATOR_WEIGHTS},
        "generated_at": datetime.now().isoformat(),
        "tickers":      cache_key if ticker_list else None,
    }
    _etf_cache[cache_key] = response
    _etf_cache_time[cache_key] = datetime.now()
    return {**response, "cached": False, "cache_age_minutes": 0}


@app.get("/historical")
def get_historical(date: str, tickers: str = None):
    """Bereken scores voor alle aandelen op een historische datum."""
    try:
        target = datetime.strptime(date, "%Y-%m-%d")
        if target > datetime.now():
            return {"error": "Datum mag niet in de toekomst liggen"}
    except ValueError:
        return {"error": "Ongeldige datum — gebruik YYYY-MM-DD formaat"}

    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        weight = round(1 / len(ticker_list), 6)
        holdings = [{"ticker": t, "name": t, "etf_weight": weight} for t in ticker_list]
    else:
        holdings = ETF_HOLDINGS

    results = []
    for h in holdings:
        data  = fetch_stock_data(h["ticker"], as_of_date=date)
        score = calculate_score(data)
        score["etf_weight"] = h["etf_weight"]
        results.append(score)

    summary = calculate_etf_score(results, holdings)
    return {
        "summary":         summary,
        "holdings":        results,
        "config":          {"timeframe_weights": TIMEFRAME_WEIGHTS, "indicator_weights": INDICATOR_WEIGHTS},
        "generated_at":    datetime.now().isoformat(),
        "historical_date": date,
        "cached":          False,
        "cache_age_minutes": 0,
    }


@app.get("/sector-performance")
def get_sector_performance_endpoint():
    """Actuele sectorprestaties ophalen van FMP."""
    return {
        "sectors":      fetch_sector_performance(),
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/intraday/{ticker}")
def get_intraday(ticker: str, interval: str = "4hour", days: int = 60):
    """Intraday koersdata ophalen voor een aandeel (standaard 4-uurs, laatste 60 dagen)."""
    ticker = ticker.upper()
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date   = datetime.now().strftime("%Y-%m-%d")

    data = _fmp_get(
        f"/historical-chart/{interval}",
        {"symbol": ticker, "from": from_date, "to": to_date}
    )

    if not data or isinstance(data, str) or not isinstance(data, list):
        return {"ticker": ticker, "interval": interval, "data": [], "error": "Geen intraday data beschikbaar"}

    # FMP geeft nieuwste eerst → omkeren naar oudste eerst
    data_asc = list(reversed(data))
    return {
        "ticker":   ticker,
        "interval": interval,
        "data": [
            {
                "date":   item.get("date", ""),
                "open":   item.get("open"),
                "high":   item.get("high"),
                "low":    item.get("low"),
                "close":  item.get("close"),
                "volume": item.get("volume"),
            }
            for item in data_asc
        ],
    }


@app.get("/config")
def get_config():
    return {
        "timeframe_weights": TIMEFRAME_WEIGHTS,
        "indicator_weights": INDICATOR_WEIGHTS,
        "indicator_meta":    INDICATOR_META,
    }


class ConfigUpdate(BaseModel):
    timeframe_weights: Optional[dict] = None
    indicator_weights: Optional[dict] = None


@app.post("/config")
def update_config(config: ConfigUpdate):
    if config.timeframe_weights:
        if abs(sum(config.timeframe_weights.values()) - 1.0) > 0.01:
            return {"error": "Timeframe gewichten moeten optellen tot 1.0"}
        TIMEFRAME_WEIGHTS.update(config.timeframe_weights)
    if config.indicator_weights:
        if abs(sum(config.indicator_weights.values()) - 1.0) > 0.01:
            return {"error": "Indicator gewichten moeten optellen tot 1.0"}
        INDICATOR_WEIGHTS.update(config.indicator_weights)
    return {"status": "ok", "config": {"timeframe_weights": TIMEFRAME_WEIGHTS, "indicator_weights": INDICATOR_WEIGHTS}}


# ─────────────────────────────────────────────
# STANDALONE RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n🚀 ETF Score Engine v2.0 (Premium) — {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    print(f"   Analyseren: {len(ETF_HOLDINGS)} aandelen\n")
    results = []
    for h in ETF_HOLDINGS:
        print(f"  → {h['ticker']:12} ophalen...")
        data  = fetch_stock_data(h["ticker"])
        score = calculate_score(data)
        score["etf_weight"] = h["etf_weight"]
        results.append(score)

    summary = calculate_etf_score(results, ETF_HOLDINGS)

    print(f"\n{'═'*65}")
    print(f"  {'Ticker':<8} {'Score':>6}  {'Signaal':<10} {'RSI':>5}  {'PEG':>5}  {'Fwd P/E':>8}")
    print(f"{'─'*65}")
    for r in sorted(results, key=lambda x: x.get("total_score", 0), reverse=True):
        if "error" in r: continue
        rd   = r["raw_data"]
        icon = "🟢" if r["signal"] == "KOOP" else "🔴" if r["signal"] == "UITSTAP" else "🟡"
        print(f"  {r['ticker']:<8} {r['total_score']:>6.1f}  {icon} {r['signal']:<8} "
              f"{str(rd.get('rsi_daily') or '-'):>5}  {str(rd.get('peg_ratio') or '-'):>5}  "
              f"{str(rd.get('forward_pe') or '-'):>8}")
    print(f"{'─'*65}")
    print(f"  ETF Score: {summary['etf_score']:.1f}/100  →  {summary['etf_signal']}")
    print(f"{'═'*65}\n")

    with open("etf_scores.json", "w") as f:
        json.dump({"summary": summary, "holdings": results, "generated_at": datetime.now().isoformat()}, f, indent=2, default=str)
    print("  ✅ Opgeslagen in etf_scores.json")
    print("  💡 Start API: uvicorn etf_score_engine:app --reload\n")
