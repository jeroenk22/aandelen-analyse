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
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─────────────────────────────────────────────
# CONFIGURATIE — pas gewichten hier aan
# ─────────────────────────────────────────────

TIMEFRAME_WEIGHTS = {
    "daily":   0.30,
    "weekly":  0.40,
    "monthly": 0.30,
}

INDICATOR_WEIGHTS = {
    "rsi":          0.15,
    "ma200":        0.15,
    "forward_pe":   0.20,
    "peg":          0.20,
    "price_fcf":    0.15,
    "momentum":     0.10,
    "dcf_discount": 0.05,
}

# Holdings met ETF-wegingen (uit projectinstructie)
ETF_HOLDINGS = [
    {"ticker": "NVDA",      "name": "NVIDIA Corp",             "etf_weight": 0.0454},
    {"ticker": "AAPL",      "name": "Apple Inc",               "etf_weight": 0.0369},
    {"ticker": "MSFT",      "name": "Microsoft Corp",          "etf_weight": 0.0288},
    {"ticker": "GOOGL",     "name": "Alphabet Class A",        "etf_weight": 0.0222},
    {"ticker": "TSM",       "name": "Taiwan Semiconductor",    "etf_weight": 0.0209},
    {"ticker": "AMZN",      "name": "Amazon.com Inc",          "etf_weight": 0.0208},
    {"ticker": "GOOG",      "name": "Alphabet Class C",        "etf_weight": 0.0134},
    {"ticker": "AVGO",      "name": "Broadcom Inc",            "etf_weight": 0.0125},
    {"ticker": "META",      "name": "Meta Platforms",          "etf_weight": 0.0123},
    {"ticker": "005930.KS", "name": "Samsung Electronics",     "etf_weight": 0.0111},
]


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


# ─────────────────────────────────────────────
# DATA OPHALEN
# ─────────────────────────────────────────────

def fetch_stock_data(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        if hist.empty:
            return None

        price = hist["Close"].iloc[-1]

        def calc_rsi(series, period=14):
            d = series.diff()
            gain = d.clip(lower=0).rolling(period).mean()
            loss = (-d.clip(upper=0)).rolling(period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        rsi_d = calc_rsi(hist["Close"]).iloc[-1]
        hist_w = hist["Close"].resample("W").last()
        rsi_w = calc_rsi(hist_w).iloc[-1] if len(hist_w) > 14 else None
        hist_m = hist["Close"].resample("ME").last()
        rsi_m = calc_rsi(hist_m).iloc[-1] if len(hist_m) > 5 else None

        ma200 = hist["Close"].rolling(200).mean().iloc[-1] if len(hist) >= 200 else hist["Close"].mean()

        fpe = info.get("forwardPE")
        tpe = info.get("trailingPE")
        peg = info.get("pegRatio")
        mc  = info.get("marketCap", 0)
        fcf = info.get("freeCashflow", 0)
        pfcf = (mc / fcf) if fcf and fcf > 0 else None

        p1m = hist["Close"].iloc[-22] if len(hist) >= 22 else hist["Close"].iloc[0]
        mom = ((price - p1m) / p1m) * 100

        shares = info.get("sharesOutstanding", 0)
        fcf_ps = (fcf / shares) if fcf and shares else None
        dcf_fv = fcf_ps * 25 if fcf_ps else None

        hist_pe = tpe * 0.95 if tpe else (fpe * 1.1 if fpe else None)
        hist_pfcf = pfcf * 1.05 if pfcf else None

        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "Technology"),
            "current_price": round(price, 2),
            "currency": info.get("currency", "USD"),
            "rsi_daily": round(rsi_d, 1) if rsi_d else None,
            "rsi_weekly": round(rsi_w, 1) if rsi_w else None,
            "rsi_monthly": round(rsi_m, 1) if rsi_m else None,
            "ma200": round(ma200, 2),
            "momentum_1m": round(mom, 2),
            "forward_pe": round(fpe, 2) if fpe else None,
            "historical_avg_pe": round(hist_pe, 2) if hist_pe else None,
            "peg_ratio": round(peg, 2) if peg else None,
            "price_fcf": round(pfcf, 2) if pfcf else None,
            "historical_avg_pfcf": round(hist_pfcf, 2) if hist_pfcf else None,
            "dcf_fair_value": round(dcf_fv, 2) if dcf_fv else None,
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

    def tf_score(rsi_val):
        r   = score_rsi(rsi_val)
        ma  = score_ma200(data["current_price"], data["ma200"])
        fpe = score_forward_pe(data["forward_pe"], data["historical_avg_pe"])
        peg = score_peg(data["peg_ratio"])
        pf  = score_price_fcf(data["price_fcf"], data["historical_avg_pfcf"])
        mom = score_momentum(data["momentum_1m"], sector_momentum)
        dcf = score_dcf(data["current_price"], data["dcf_fair_value"])
        return (r   * INDICATOR_WEIGHTS["rsi"] +
                ma  * INDICATOR_WEIGHTS["ma200"] +
                fpe * INDICATOR_WEIGHTS["forward_pe"] +
                peg * INDICATOR_WEIGHTS["peg"] +
                pf  * INDICATOR_WEIGHTS["price_fcf"] +
                mom * INDICATOR_WEIGHTS["momentum"] +
                dcf * INDICATOR_WEIGHTS["dcf_discount"])

    ds = tf_score(data["rsi_daily"])
    ws = tf_score(data["rsi_weekly"])
    ms = tf_score(data["rsi_monthly"])

    total = (ds * TIMEFRAME_WEIGHTS["daily"] +
             ws * TIMEFRAME_WEIGHTS["weekly"] +
             ms * TIMEFRAME_WEIGHTS["monthly"])

    signal = "KOOP" if total >= 65 else "UITSTAP" if total < 45 else "NEUTRAAL"

    return {
        "ticker": data["ticker"],
        "name": data["name"],
        "current_price": data["current_price"],
        "currency": data["currency"],
        "total_score": round(total, 1),
        "signal": signal,
        "scores_by_timeframe": {
            "daily": round(ds, 1),
            "weekly": round(ws, 1),
            "monthly": round(ms, 1),
        },
        "indicator_scores": {
            "rsi_daily":    round(score_rsi(data["rsi_daily"]), 1),
            "rsi_weekly":   round(score_rsi(data["rsi_weekly"]), 1),
            "rsi_monthly":  round(score_rsi(data["rsi_monthly"]), 1),
            "ma200":        round(score_ma200(data["current_price"], data["ma200"]), 1),
            "forward_pe":   round(score_forward_pe(data["forward_pe"], data["historical_avg_pe"]), 1),
            "peg":          round(score_peg(data["peg_ratio"]), 1),
            "price_fcf":    round(score_price_fcf(data["price_fcf"], data["historical_avg_pfcf"]), 1),
            "momentum":     round(score_momentum(data["momentum_1m"], sector_momentum), 1),
            "dcf_discount": round(score_dcf(data["current_price"], data["dcf_fair_value"]), 1),
        },
        "raw_data": data,
    }


def calculate_etf_score(results: list) -> dict:
    total_weight = sum(h["etf_weight"] for h in ETF_HOLDINGS)
    weight_map = {h["ticker"]: h["etf_weight"] for h in ETF_HOLDINGS}
    valid = [r for r in results if "error" not in r]
    score = sum(r["total_score"] * (weight_map.get(r["ticker"], 0) / total_weight) for r in valid)
    signal = "INSTAP" if score >= 65 else "UITSTAP" if score < 45 else "AFWACHTEN"
    return {
        "etf_score": round(score, 1),
        "etf_signal": signal,
        "holdings_analyzed": len(valid),
        "holdings_total": len(ETF_HOLDINGS),
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
def get_etf():
    results = []
    for h in ETF_HOLDINGS:
        data = fetch_stock_data(h["ticker"])
        score = calculate_score(data)
        score["etf_weight"] = h["etf_weight"]
        results.append(score)
    summary = calculate_etf_score(results)
    return {
        "summary": summary,
        "holdings": results,
        "config": {"timeframe_weights": TIMEFRAME_WEIGHTS, "indicator_weights": INDICATOR_WEIGHTS},
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/config")
def get_config():
    return {"timeframe_weights": TIMEFRAME_WEIGHTS, "indicator_weights": INDICATOR_WEIGHTS}


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
        data = fetch_stock_data(h["ticker"])
        score = calculate_score(data)
        score["etf_weight"] = h["etf_weight"]
        results.append(score)

    summary = calculate_etf_score(results)

    print(f"\n{'═'*65}")
    print(f"  {'Ticker':<8} {'Score':>6}  {'Signaal':<10} {'RSI':>5}  {'PEG':>5}  {'Fwd P/E':>8}")
    print(f"{'─'*65}")
    for r in sorted(results, key=lambda x: x.get("total_score", 0), reverse=True):
        if "error" in r: continue
        rd = r["raw_data"]
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
