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
# IN-MEMORY CACHE (per ISIN of 'default')
# ─────────────────────────────────────────────

_etf_cache: Dict[str, dict] = {}
_etf_cache_time: Dict[str, datetime] = {}
CACHE_DURATION_MINUTES = 60

# ─────────────────────────────────────────────
# CONFIGURATIE — pas gewichten hier aan
# ─────────────────────────────────────────────

TIMEFRAME_WEIGHTS = {
    "daily":   0.30,
    "weekly":  0.40,
    "monthly": 0.30,
}

INDICATOR_WEIGHTS = {
    "rsi":             0.13,
    "ma20":            0.08,
    "ma200":           0.07,
    "forward_pe":      0.15,
    "peg":             0.15,
    "price_fcf":       0.11,
    "momentum":        0.08,
    "dcf_discount":    0.02,
    "panic":           0.05,
    "rsi_divergence":  0.08,
    "apz":             0.08,
}

# Weergavenamen en tooltips per indicator (voor frontend)
INDICATOR_META = {
    "rsi": {
        "label":   "RSI",
        "tooltip": "De Relative Strength Index meet hoe snel een koers is gedaald of gestegen. "
                   "Onder 30 = waarschijnlijk te veel gedaald (koopkans), boven 70 = waarschijnlijk te veel gestegen (verkoopkans).",
    },
    "rsi_divergence": {
        "label":   "RSI Divergentie",
        "tooltip": "Vergelijkt koersbodems met RSI-bodems. Als de koers een nieuwe bodem maakt maar de RSI niet "
                   "(bullish divergentie), is dat een signaal dat de verkoopdruk afneemt — mogelijke ommekeer omhoog.",
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
        "tooltip": "Hoe sterk het aandeel de afgelopen maand presteerde ten opzichte van de sector. "
                   "Positief momentum betekent dat beleggers meer vertrouwen tonen dan in vergelijkbare bedrijven.",
    },
    "dcf_discount": {
        "label":   "DCF Korting",
        "tooltip": "Schatting van de 'echte waarde' op basis van toekomstige kasstromen (Discounted Cash Flow). "
                   "Een grote korting (koers ver onder berekende waarde) suggereert dat het aandeel ondergewaardeerd is.",
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


def resolve_isin_to_ticker(isin: str) -> Optional[str]:
    """Zet ISIN om naar beursticker via FMP zoekfunctie."""
    data = _fmp_get("/search-symbol", {"query": isin, "limit": 5})
    if not data or not isinstance(data, list):
        return None
    # Prefereer exacte ISIN match, anders eerste resultaat
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
            # FMP geeft gewicht als percentage (bijv. 5.4), omzetten naar decimaal (0.054)
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


def calc_rsi_divergence(close_s: pd.Series, rsi_s: pd.Series, lookback: int = 14) -> str:
    """Detecteer bullish/bearish RSI-divergentie over de laatste `lookback` perioden.
    Bullish  = koers maakt lagere bodem, RSI hogere bodem.
    Bearish  = koers maakt hogere top,  RSI lagere top."""
    rsi_clean = rsi_s.dropna()
    if len(close_s) < lookback or len(rsi_clean) < lookback:
        return "NEUTRAAL"
    close = close_s.values[-lookback:]
    rsi   = rsi_clean.values[-lookback:]
    half  = lookback // 2

    lo1 = int(np.argmin(close[:half]))
    lo2 = int(np.argmin(close[half:]))
    if close[half + lo2] < close[lo1] and rsi[half + lo2] > rsi[lo1]:
        return "BULLISH"

    hi1 = int(np.argmax(close[:half]))
    hi2 = int(np.argmax(close[half:]))
    if close[half + hi2] > close[hi1] and rsi[half + hi2] < rsi[hi1]:
        return "BEARISH"

    return "NEUTRAAL"


# ─────────────────────────────────────────────
# SCORE FUNCTIES
# ─────────────────────────────────────────────

def score_rsi(rsi: float) -> float:
    if rsi is None: return 50.0
    if rsi < 20:    return 100.0
    if rsi < 30:    return 90.0
    if rsi < 45:    return 70.0
    if rsi < 55:    return 50.0
    if rsi < 70:    return 30.0
    return 10.0

def score_ma200(price: float, ma200: float) -> float:
    if not price or not ma200: return 50.0
    pct = (price - ma200) / ma200 * 100
    if pct < -10:  return 100.0
    if pct < 0:    return 80.0
    if pct < 5:    return 70.0
    if pct < 15:   return 55.0
    if pct < 30:   return 35.0
    return 10.0

def score_forward_pe(fpe: float, hist_pe: float) -> float:
    if not fpe or not hist_pe: return 50.0
    r = fpe / hist_pe
    if r < 0.7:  return 100.0
    if r < 0.9:  return 75.0
    if r < 1.0:  return 60.0
    if r < 1.1:  return 50.0
    if r < 1.3:  return 35.0
    return 15.0

def score_peg(peg: float) -> float:
    if not peg or peg <= 0: return 50.0
    if peg < 0.5:  return 100.0
    if peg < 0.75: return 85.0
    if peg < 1.0:  return 75.0
    if peg < 1.5:  return 55.0
    if peg < 2.0:  return 35.0
    return 10.0

def score_price_fcf(pfcf: float, hist: float) -> float:
    if not pfcf or not hist: return 50.0
    r = pfcf / hist
    if r < 0.7:  return 100.0
    if r < 0.9:  return 75.0
    if r < 1.0:  return 60.0
    if r < 1.2:  return 45.0
    return 20.0

def score_momentum(ret: float, sector_ret: float) -> float:
    if ret is None: return 50.0
    rel = ret - (sector_ret or 0)
    if rel > 10:   return 90.0
    if rel > 5:    return 75.0
    if rel > 0:    return 60.0
    if rel > -5:   return 45.0
    if rel > -10:  return 30.0
    return 15.0

def score_dcf(price: float, fv: float) -> float:
    if not price or not fv: return 50.0
    disc = (fv - price) / fv * 100
    if disc > 30:  return 100.0
    if disc > 20:  return 85.0
    if disc > 10:  return 65.0
    if disc > 0:   return 55.0
    if disc > -10: return 40.0
    return 15.0

def score_ma20(price: float, ma20: float) -> float:
    """Hoe ver staat prijs onder/boven MA20? Onder = koopkans."""
    if not price or not ma20: return 50.0
    pct = (price - ma20) / ma20 * 100
    if pct < -10:  return 100.0
    if pct < -5:   return 85.0
    if pct < 0:    return 70.0
    if pct < 3:    return 55.0
    if pct < 10:   return 40.0
    return 25.0

def score_panic(bb_pct_b: float, vol_spike: float) -> float:
    """Paniekdetector op basis van Bollinger Band %B + volume spike.
    Hoge score = prijspaniek (= koopkans). Lage score = euforie (= uitstapkans)."""
    if bb_pct_b is None: return 50.0
    if bb_pct_b < 0:     s = 95.0
    elif bb_pct_b < 0.2: s = 80.0
    elif bb_pct_b < 0.4: s = 62.0
    elif bb_pct_b < 0.6: s = 50.0
    elif bb_pct_b < 0.8: s = 38.0
    else:                s = 20.0
    if vol_spike and vol_spike > 2.0:
        s = min(100.0, s + 10.0)
    return s

def score_rsi_divergence(div: str) -> float:
    """Bullish divergentie = koopkans (hoog), bearish = verkoopkans (laag)."""
    if div == "BULLISH": return 85.0
    if div == "BEARISH": return 20.0
    return 50.0

def score_apz(price: float, apz_lower: float, apz_upper: float) -> float:
    """APZ positie: onder ondergrens = oversold (hoog), boven bovengrens = overbought (laag)."""
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
    """Voeg indicator_label en tooltip toe vanuit INDICATOR_META."""
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
    if not fpe or not hist_pe: return _interp("NEUTRAAL", "Fwd P/E — geen data", None)
    r = fpe / hist_pe
    if r < 0.7:  return _interp("OVERSOLD",   f"Fwd P/E {fpe} — sterk onder historisch gemiddelde", fpe)
    if r < 0.9:  return _interp("DICHTBIJ",   f"Fwd P/E {fpe} — licht ondergewaardeerd",             fpe)
    if r < 1.1:  return _interp("NEUTRAAL",   f"Fwd P/E {fpe} — in lijn met historisch",             fpe)
    if r < 1.3:  return _interp("DICHTBIJ",   f"Fwd P/E {fpe} — licht overgewaardeerd",              fpe)
    return              _interp("OVERBOUGHT", f"Fwd P/E {fpe} — duur t.o.v. historisch",             fpe)

def _interp_peg(peg) -> dict:
    if not peg or peg <= 0: return _interp("NEUTRAAL", "PEG — geen data", None)
    if peg < 0.5:  return _interp("OVERSOLD",   f"PEG {peg} — groei niet ingeprijsd, koopkans",  peg)
    if peg < 1.0:  return _interp("DICHTBIJ",   f"PEG {peg} — redelijk gewaardeerd",              peg)
    if peg < 1.5:  return _interp("NEUTRAAL",   f"PEG {peg} — fair value",                        peg)
    if peg < 2.0:  return _interp("DICHTBIJ",   f"PEG {peg} — licht overgewaardeerd",             peg)
    return                _interp("OVERBOUGHT", f"PEG {peg} — overgewaardeerd",                   peg)

def _interp_price_fcf(pfcf, hist) -> dict:
    if not pfcf or not hist: return _interp("NEUTRAAL", "P/FCF — geen data", None)
    r = pfcf / hist
    if r < 0.7:  return _interp("OVERSOLD",   f"P/FCF {pfcf} — sterk goedkoop t.o.v. historisch", pfcf)
    if r < 0.9:  return _interp("DICHTBIJ",   f"P/FCF {pfcf} — licht goedkoop",                    pfcf)
    if r < 1.0:  return _interp("NEUTRAAL",   f"P/FCF {pfcf} — rond historisch gemiddelde",         pfcf)
    return              _interp("OVERBOUGHT", f"P/FCF {pfcf} — duurder dan historisch",             pfcf)

def _interp_momentum(mom, sector_ret) -> dict:
    if mom is None: return _interp("NEUTRAAL", "Momentum — geen data", None)
    rel = round(mom - (sector_ret or 0), 1)
    if rel > 10:   return _interp("BULLISH",  f"Momentum +{rel}% vs sector — sterk positief",  rel)
    if rel > 5:    return _interp("BULLISH",  f"Momentum +{rel}% vs sector — positief",         rel)
    if rel > 0:    return _interp("DICHTBIJ", f"Momentum +{rel}% vs sector — licht positief",   rel)
    if rel > -5:   return _interp("NEUTRAAL", f"Momentum {rel}% vs sector — licht negatief",    rel)
    if rel > -10:  return _interp("BEARISH",  f"Momentum {rel}% vs sector — negatief",          rel)
    return                _interp("BEARISH",  f"Momentum {rel}% vs sector — sterk negatief",    rel)

def _interp_dcf(price, fv) -> dict:
    if not price or not fv: return _interp("NEUTRAAL", "DCF — geen data", None)
    disc = round((fv - price) / fv * 100, 1)
    if disc > 30:  return _interp("OVERSOLD",   f"DCF korting {disc}% — sterk ondergewaardeerd", disc)
    if disc > 10:  return _interp("DICHTBIJ",   f"DCF korting {disc}% — licht ondergewaardeerd",  disc)
    if disc > 0:   return _interp("NEUTRAAL",   f"DCF korting {disc}% — nabij fair value",         disc)
    return                _interp("OVERBOUGHT", f"DCF {abs(disc)}% boven fair value",              disc)

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

def _interp_divergence(div: str, tf: str) -> dict:
    if div == "BULLISH": return _interp("BULLISH",  f"RSI divergentie {tf} — bullish (koers daalt, RSI stijgt)", div)
    if div == "BEARISH": return _interp("BEARISH",  f"RSI divergentie {tf} — bearish (koers stijgt, RSI daalt)", div)
    return                       _interp("NEUTRAAL", f"RSI divergentie {tf} — geen divergentie",                  div)

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

        # ── 2. Koersgeschiedenis (3 jaar dagelijks) ────────────────
        three_years_ago = (ref_date - timedelta(days=3 * 365)).strftime("%Y-%m-%d")
        today = ref_date.strftime("%Y-%m-%d")
        hist_data = _fmp_get(
            "/historical-price-eod/full",
            {"symbol": ticker, "from": three_years_ago, "to": today},
        )
        if hist_data == "PREMIUM":
            return {"error": f"{ticker} vereist een betaald FMP-plan (niet beschikbaar op gratis tier)", "ticker": ticker}
        # Stable API geeft een lijst terug; v3 API gaf {"historical": [...]}
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

        # ── 3. Ratio's TTM (P/E, PEG, P/FCF) ─────────────────────
        # Fundamentals zijn niet beschikbaar voor historische datums op Starter-plan
        if not historical_mode:
            ratios_data = _fmp_get("/ratios-ttm", {"symbol": ticker})
            ratios = ratios_data[0] if ratios_data and isinstance(ratios_data, list) else {}
        else:
            ratios = {}

        tpe      = ratios.get("priceToEarningsRatioTTM")
        peg      = ratios.get("priceToEarningsGrowthRatioTTM")
        pfcf     = ratios.get("priceToFreeCashFlowRatioTTM")
        fcf_ps_r = ratios.get("freeCashFlowPerShareTTM")  # FCF per aandeel uit ratios

        # ── Fundamentals berekenen ─────────────────────────────────
        fpe    = tpe  # gebruik TTM P/E als forward P/E-benadering
        dcf_fv = float(fcf_ps_r) * 25 if fcf_ps_r else None

        hist_pe   = tpe * 0.95 if tpe else None
        hist_pfcf = pfcf * 1.05 if pfcf else None

        # ── Technische indicatoren ─────────────────────────────────
        def calc_rsi(series, period=14):
            d    = series.diff()
            gain = d.clip(lower=0).rolling(period).mean()
            loss = (-d.clip(upper=0)).rolling(period).mean()
            rs   = gain / loss
            return 100 - (100 / (1 + rs))

        hist_w = hist["Close"].resample("W").last()
        hist_m = hist["Close"].resample("ME").last()

        # RSI + divergentie per timeframe
        rsi_series_d = calc_rsi(hist["Close"])
        rsi_d        = rsi_series_d.iloc[-1]
        rsi_div_d    = calc_rsi_divergence(hist["Close"], rsi_series_d)

        rsi_series_w = calc_rsi(hist_w)
        rsi_w        = rsi_series_w.iloc[-1] if len(hist_w) > 14 else None
        rsi_div_w    = calc_rsi_divergence(hist_w, rsi_series_w) if len(hist_w) > 14 else "NEUTRAAL"

        rsi_series_m = calc_rsi(hist_m)
        rsi_m        = rsi_series_m.iloc[-1] if len(hist_m) > 14 else None
        rsi_div_m    = calc_rsi_divergence(hist_m, rsi_series_m) if len(hist_m) > 14 else "NEUTRAAL"

        # MA20 per timeframe
        ma20_d = hist["Close"].rolling(20).mean().iloc[-1]
        ma20_w = hist_w.rolling(20).mean().iloc[-1] if len(hist_w) >= 20 else hist_w.mean()
        ma20_m = hist_m.rolling(20).mean().iloc[-1] if len(hist_m) >= 20 else hist_m.mean()

        # MA200
        ma200 = hist["Close"].rolling(200).mean().iloc[-1] if len(hist) >= 200 else hist["Close"].mean()

        # APZ per timeframe
        apz_ema_d, apz_up_d, apz_lo_d = calc_apz(hist["Close"])
        apz_ema_w, apz_up_w, apz_lo_w = calc_apz(hist_w) if len(hist_w) >= 20 else (None, None, None)
        apz_ema_m, apz_up_m, apz_lo_m = calc_apz(hist_m) if len(hist_m) >= 20 else (None, None, None)

        # Volume spike
        vol_avg20 = hist["Volume"].rolling(20).mean().iloc[-1]
        vol_spike = float(hist["Volume"].iloc[-1] / vol_avg20) if vol_avg20 and vol_avg20 > 0 else None

        # Bollinger Bands (paniekdetectie)
        bb_mid   = hist["Close"].rolling(20).mean().iloc[-1]
        bb_std   = hist["Close"].rolling(20).std().iloc[-1]
        bb_width = float((bb_mid + 2 * bb_std) - (bb_mid - 2 * bb_std))
        bb_pct_b = float((price - (bb_mid - 2 * bb_std)) / bb_width) if bb_width > 0 else None

        # Momentum (1 maand)
        p1m = hist["Close"].iloc[-22] if len(hist) >= 22 else hist["Close"].iloc[0]
        mom = ((price - float(p1m)) / float(p1m)) * 100

        return {
            "ticker":               ticker,
            "name":                 profile.get("companyName") or profile.get("name", ticker),
            "sector":               profile.get("sector", "Technology"),
            "current_price":        round(price, 2),
            "currency":             profile.get("currency", "USD"),
            # RSI
            "rsi_daily":            _r(rsi_d, 1),
            "rsi_weekly":           _r(rsi_w, 1),
            "rsi_monthly":          _r(rsi_m, 1),
            # RSI Divergentie
            "rsi_divergence_daily":   rsi_div_d,
            "rsi_divergence_weekly":  rsi_div_w,
            "rsi_divergence_monthly": rsi_div_m,
            # MA20
            "ma20_daily":           _r(ma20_d, 2),
            "ma20_weekly":          _r(ma20_w, 2),
            "ma20_monthly":         _r(ma20_m, 2),
            # MA200
            "ma200":                _r(ma200, 2),
            # APZ
            "apz_upper_daily":      apz_up_d,
            "apz_lower_daily":      apz_lo_d,
            "apz_upper_weekly":     apz_up_w,
            "apz_lower_weekly":     apz_lo_w,
            "apz_upper_monthly":    apz_up_m,
            "apz_lower_monthly":    apz_lo_m,
            # Volume & Bollinger
            "vol_spike":            _r(vol_spike, 2),
            "bb_pct_b":             _r(bb_pct_b, 3),
            # Overige
            "momentum_1m":          _r(mom, 2),
            "forward_pe":           _r(fpe, 2),
            "historical_avg_pe":    _r(hist_pe, 2),
            "peg_ratio":            _r(peg, 2),
            "price_fcf":            _r(pfcf, 2),
            "historical_avg_pfcf":  _r(hist_pfcf, 2),
            "dcf_fair_value":       _r(dcf_fv, 2),
            "fundamentals_unavailable": historical_mode,
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

    def tf_score(rsi_val, ma20_val, rsi_div, apz_lo, apz_up):
        r    = score_rsi(rsi_val)
        m20  = score_ma20(p, ma20_val)
        ma   = score_ma200(p, data["ma200"])
        fpe  = score_forward_pe(data["forward_pe"], data["historical_avg_pe"])
        peg  = score_peg(data["peg_ratio"])
        pf   = score_price_fcf(data["price_fcf"], data["historical_avg_pfcf"])
        mom  = score_momentum(data["momentum_1m"], sector_momentum)
        dcf  = score_dcf(p, data["dcf_fair_value"])
        pan  = score_panic(data["bb_pct_b"], data["vol_spike"])
        div  = score_rsi_divergence(rsi_div)
        apz  = score_apz(p, apz_lo, apz_up)
        return (r   * INDICATOR_WEIGHTS["rsi"] +
                m20 * INDICATOR_WEIGHTS["ma20"] +
                ma  * INDICATOR_WEIGHTS["ma200"] +
                fpe * INDICATOR_WEIGHTS["forward_pe"] +
                peg * INDICATOR_WEIGHTS["peg"] +
                pf  * INDICATOR_WEIGHTS["price_fcf"] +
                mom * INDICATOR_WEIGHTS["momentum"] +
                dcf * INDICATOR_WEIGHTS["dcf_discount"] +
                pan * INDICATOR_WEIGHTS["panic"] +
                div * INDICATOR_WEIGHTS["rsi_divergence"] +
                apz * INDICATOR_WEIGHTS["apz"])

    ds = tf_score(data["rsi_daily"],   data["ma20_daily"],
                  data["rsi_divergence_daily"],
                  data["apz_lower_daily"],   data["apz_upper_daily"])
    ws = tf_score(data["rsi_weekly"],  data["ma20_weekly"],
                  data["rsi_divergence_weekly"],
                  data["apz_lower_weekly"],  data["apz_upper_weekly"])
    ms = tf_score(data["rsi_monthly"], data["ma20_monthly"],
                  data["rsi_divergence_monthly"],
                  data["apz_lower_monthly"], data["apz_upper_monthly"])

    total  = (ds * TIMEFRAME_WEIGHTS["daily"] +
              ws * TIMEFRAME_WEIGHTS["weekly"] +
              ms * TIMEFRAME_WEIGHTS["monthly"])
    signal = "KOOP" if total >= 65 else "UITSTAP" if total < 45 else "NEUTRAAL"

    return {
        "ticker":        data["ticker"],
        "name":          data["name"],
        "current_price": p,
        "currency":      data["currency"],
        "total_score":   round(total, 1),
        "signal":        signal,
        "scores_by_timeframe": {
            "daily":   round(ds, 1),
            "weekly":  round(ws, 1),
            "monthly": round(ms, 1),
        },
        "indicator_scores": {
            "rsi_daily":              round(score_rsi(data["rsi_daily"]), 1),
            "rsi_weekly":             round(score_rsi(data["rsi_weekly"]), 1),
            "rsi_monthly":            round(score_rsi(data["rsi_monthly"]), 1),
            "rsi_divergence_daily":   round(score_rsi_divergence(data["rsi_divergence_daily"]), 1),
            "rsi_divergence_weekly":  round(score_rsi_divergence(data["rsi_divergence_weekly"]), 1),
            "rsi_divergence_monthly": round(score_rsi_divergence(data["rsi_divergence_monthly"]), 1),
            "ma20_daily":             round(score_ma20(p, data["ma20_daily"]), 1),
            "ma20_weekly":            round(score_ma20(p, data["ma20_weekly"]), 1),
            "ma20_monthly":           round(score_ma20(p, data["ma20_monthly"]), 1),
            "ma200":                  round(score_ma200(p, data["ma200"]), 1),
            "apz_daily":              round(score_apz(p, data["apz_lower_daily"],   data["apz_upper_daily"]), 1),
            "apz_weekly":             round(score_apz(p, data["apz_lower_weekly"],  data["apz_upper_weekly"]), 1),
            "apz_monthly":            round(score_apz(p, data["apz_lower_monthly"], data["apz_upper_monthly"]), 1),
            "forward_pe":             round(score_forward_pe(data["forward_pe"], data["historical_avg_pe"]), 1),
            "peg":                    round(score_peg(data["peg_ratio"]), 1),
            "price_fcf":              round(score_price_fcf(data["price_fcf"], data["historical_avg_pfcf"]), 1),
            "momentum":               round(score_momentum(data["momentum_1m"], sector_momentum), 1),
            "dcf_discount":           round(score_dcf(p, data["dcf_fair_value"]), 1),
            "panic":                  round(score_panic(data["bb_pct_b"], data["vol_spike"]), 1),
        },
        "interpretations": {
            "rsi_daily":              _with_meta(_interp_rsi(data["rsi_daily"],   "dagelijks"),   "rsi"),
            "rsi_weekly":             _with_meta(_interp_rsi(data["rsi_weekly"],  "wekelijks"),   "rsi"),
            "rsi_monthly":            _with_meta(_interp_rsi(data["rsi_monthly"], "maandelijks"), "rsi"),
            "rsi_divergence_daily":   _with_meta(_interp_divergence(data["rsi_divergence_daily"],   "dagelijks"),   "rsi_divergence"),
            "rsi_divergence_weekly":  _with_meta(_interp_divergence(data["rsi_divergence_weekly"],  "wekelijks"),   "rsi_divergence"),
            "rsi_divergence_monthly": _with_meta(_interp_divergence(data["rsi_divergence_monthly"], "maandelijks"), "rsi_divergence"),
            "ma20_daily":             _with_meta(_interp_ma(p, data["ma20_daily"],   "MA20 dagelijks"),   "ma20"),
            "ma20_weekly":            _with_meta(_interp_ma(p, data["ma20_weekly"],  "MA20 wekelijks"),   "ma20"),
            "ma20_monthly":           _with_meta(_interp_ma(p, data["ma20_monthly"], "MA20 maandelijks"), "ma20"),
            "ma200":                  _with_meta(_interp_ma(p, data["ma200"],        "MA200"),            "ma200"),
            "apz_daily":              _with_meta(_interp_apz(p, data["apz_lower_daily"],   data["apz_upper_daily"],   "dagelijks"),   "apz"),
            "apz_weekly":             _with_meta(_interp_apz(p, data["apz_lower_weekly"],  data["apz_upper_weekly"],  "wekelijks"),   "apz"),
            "apz_monthly":            _with_meta(_interp_apz(p, data["apz_lower_monthly"], data["apz_upper_monthly"], "maandelijks"), "apz"),
            "forward_pe":             _with_meta(_interp_forward_pe(data["forward_pe"], data["historical_avg_pe"]),         "forward_pe"),
            "peg":                    _with_meta(_interp_peg(data["peg_ratio"]),                                             "peg"),
            "price_fcf":              _with_meta(_interp_price_fcf(data["price_fcf"], data["historical_avg_pfcf"]),         "price_fcf"),
            "momentum":               _with_meta(_interp_momentum(data["momentum_1m"], sector_momentum),                    "momentum"),
            "dcf_discount":           _with_meta(_interp_dcf(p, data["dcf_fair_value"]),                                    "dcf_discount"),
            "panic":                  _with_meta(_interp_panic(data["bb_pct_b"], data["vol_spike"]),                        "panic"),
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

app = FastAPI(title="ETF Intelligence API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def root():
    return {"status": "ok", "message": "ETF Intelligence API draait!"}


@app.get("/score/{ticker}")
def get_score(ticker: str):
    data = fetch_stock_data(ticker.upper())
    return calculate_score(data)


@app.get("/etf")
def get_etf(tickers: str = None, use_cache: bool = True):
    global _etf_cache, _etf_cache_time

    # Normaliseer tickers-param naar gesorteerde sleutel voor cache
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

    # Bepaal holdings: custom tickers of standaard ETF_HOLDINGS
    if ticker_list:
        # Gelijke verdeling over alle opgegeven tickers
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
        "summary":        summary,
        "holdings":       results,
        "config":         {"timeframe_weights": TIMEFRAME_WEIGHTS, "indicator_weights": INDICATOR_WEIGHTS},
        "generated_at":   datetime.now().isoformat(),
        "historical_date": date,
        "cached":         False,
        "cache_age_minutes": 0,
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
    print(f"\n🚀 ETF Score Engine — {datetime.now().strftime('%d-%m-%Y %H:%M')}")
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
