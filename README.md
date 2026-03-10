# 📡 ETF Intelligence Dashboard

Analyseer ETFs op in/uitstap-momenten via 7 indicatoren × 3 timeframes met een gewogen score-algoritme.

## Projectstructuur

```
aandelen-analyse/
├── backend/
│   ├── etf_score_engine.py   # Python score engine + FastAPI
│   └── requirements.txt
└── frontend/
    ├── public/index.html
    ├── src/
│   │   ├── App.jsx           # React dashboard
│   │   └── index.js
    └── package.json
```

---

## 🚀 Snel starten

### Backend (Python)

```bash
cd backend
pip install -r requirements.txt

# Eenmalig testen — print rapport in terminal
python etf_score_engine.py

# Als API starten
uvicorn etf_score_engine:app --reload
# → http://localhost:8000
# → Swagger docs: http://localhost:8000/docs
```

### Frontend (React)

```bash
cd frontend
npm install
npm start
# → http://localhost:3000
```

> Het dashboard werkt ook zonder backend (mock data). Zodra de backend draait, klik op 🔄 Vernieuwen voor live data.

---

## 📊 Score Algoritme

### 7 Indicatoren

| Indicator | Type | Gewicht |
|---|---|---|
| RSI (Relative Strength Index) | Technisch | 15% |
| 200-daags Moving Average | Technisch | 15% |
| Forward P/E vs. historisch gem. | Fundamenteel | 20% |
| PEG Ratio | Fundamenteel | 20% |
| Price-to-Free Cash Flow | Fundamenteel | 15% |
| Relatieve Momentum | Technisch | 10% |
| DCF Fair Value Korting | Fundamenteel | 5% |

### 3 Timeframes

| Timeframe | Standaard gewicht |
|---|---|
| Dagelijks | 30% |
| Wekelijks | 40% |
| Maandelijks | 30% |

### Signalen

| Score | Signaal |
|---|---|
| 65–100 | 🟢 INSTAP |
| 45–64 | 🟡 AFWACHTEN |
| 0–44 | 🔴 UITSTAP |

---

## 🔌 API Endpoints

```
GET  /                  → health check
GET  /score/{ticker}    → score voor 1 aandeel (bijv. /score/NVDA)
GET  /etf               → volledige ETF analyse
GET  /config            → huidige gewichten
POST /config            → gewichten aanpassen
```

### Gewichten aanpassen via API

```bash
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "timeframe_weights": {"daily": 0.2, "weekly": 0.5, "monthly": 0.3},
    "indicator_weights": {"rsi": 0.20, "ma200": 0.15, "forward_pe": 0.20, "peg": 0.15, "price_fcf": 0.15, "momentum": 0.10, "dcf_discount": 0.05}
  }'
```

---

## 🗓️ Roadmap

- [x] Score engine voor 10 aandelen (yfinance)
- [x] FastAPI backend met REST endpoints
- [x] React dashboard met instelbare gewichten
- [ ] ISIN → holdings resolver (Financial Modeling Prep API)
- [ ] Willekeurige ETFs via ISIN toevoegen
- [ ] Alert systeem (email/push bij drempelwaarde)
- [ ] Meerdere ETFs vergelijken
- [ ] Deploy op Railway + Vercel

---

## 💰 Productie API kosten

| Service | Plan | Kosten/mnd |
|---|---|---|
| Financial Modeling Prep | Starter | ~€20 |
| Twelve Data | Basic | ~€29 |
| Railway (hosting) | Hobby | ~€5 |
| Vercel (frontend) | Free | Gratis |
| **Totaal** | | **~€54** |
