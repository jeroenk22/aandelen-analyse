# CLAUDE.md — Instructies voor dit project

## Projectoverzicht

ETF Intelligence Dashboard: analyseert aandelen op in/uitstap-momenten via een gewogen score-algoritme (11 indicatoren × 4 timeframes: intraday/dag/week/maand).

```
aandelen-analyse/
├── backend/
│   ├── etf_score_engine.py   # Python score engine + FastAPI (ENIGE backend bestand)
│   ├── config.json           # Standaard tickers (handmatig instellen)
│   ├── requirements.txt
│   └── tests/
└── frontend/
    └── src/
        ├── App.jsx           # React dashboard (ENIGE frontend bestand)
        └── main.jsx
```

## Starten

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn etf_score_engine:app --reload   # → http://localhost:8000

# Frontend
cd frontend && npm install && npm run dev  # → http://localhost:5173
```

## FMP API — Huidig plan: Premium ($69/mo)

De app gebruikt **Financial Modeling Prep (FMP)** via `https://financialmodelingprep.com/stable`.

| Plan | Prijs | Historisch | Calls |
|---|---|---|---|
| Basic | Gratis | 5 jaar | 250/dag |
| Starter | $29/mo | 5 jaar | 300/min |
| **Premium** | **$69/mo** | **30+ jaar** | **750/min** |

### Endpoints die dit project gebruikt (Premium)

| Endpoint | Beschikbaar | Opmerking |
|---|---|---|
| `/profile` | ✅ Worldwide | Bedrijfsnaam, sector |
| `/historical-price-eod/full` | ✅ 30 jaar | Koersgeschiedenis dagelijks |
| `/ratios-ttm` | ✅ US-only | P/E, PEG, P/FCF TTM |
| `/technical_indicator/{interval}/{symbol}` | ✅ Premium | RSI, SMA, EMA via API |
| `/historical-chart/{interval}/{symbol}` | ✅ Premium | Intraday (1h, 4h) koersdata |
| `/sector-performance` | ✅ Premium | Actuele sectorprestaties |
| `/etf-holder` | ❌ Niet beschikbaar | Alleen op Ultimate ($139/mo) |
| `/search-symbol` | ✅ Worldwide | ISIN → ticker |

### Belangrijke noten op Premium

- **`/ratios-ttm`** werkt alleen voor **US-genoteerde aandelen** (NVDA, AAPL etc.)
- **Niet-US aandelen** (TSM, ASML): fundamentals zijn leeg — technische analyse werkt wél
- **`/etf-holder`** is NIET beschikbaar op Premium — holdings handmatig instellen in `config.json`
- **Historische data** tot 30 jaar beschikbaar
- **Technische indicatoren** worden opgehaald via API (RSI, SMA20, SMA200) met fallback op lokale berekening
- **Intraday** 4-uurs data beschikbaar via `/historical-chart/4hour/{symbol}`

### API-foutcodes

- `402` = endpoint niet beschikbaar op huidig plan → geeft `"PREMIUM"` terug in `_fmp_get()`
- `None` = netwerk/timeout fout

## Score Algoritme

### Indicatoren & gewichten (in `INDICATOR_WEIGHTS`)

```
rsi:            13%   # Relative Strength Index
ma20:            8%   # Moving Average 20 perioden
ma200:           7%   # Moving Average 200 dagen (langetermijntrend)
forward_pe:     15%   # Forward P/E vs historisch gemiddelde
peg:            15%   # PEG Ratio (P/E / groei)
price_fcf:      11%   # Price-to-Free Cash Flow
momentum:        8%   # 1-maands relatief momentum vs sector
dcf_discount:    2%   # DCF fair value korting
panic:           5%   # Paniekdetectie (Bollinger Bands + volume)
rsi_divergence:  8%   # Bullish/bearish RSI divergentie
apz:             8%   # Adaptive Price Zone
```

### Timeframe gewichten (in `TIMEFRAME_WEIGHTS`)

```
intraday: 15%   # 4-uurs intraday (nieuw, Premium)
daily:    25%
weekly:   35%
monthly:  25%
```

### Signalen

| Score | Signaal |
|---|---|
| 65–100 | INSTAP |
| 45–64 | AFWACHTEN |
| 0–44 | UITSTAP |

## Ontwikkelrichtlijnen

### Taal & stijl
- **Backend**: Python, type hints, bestaande functies niet hernoemen
- **Frontend**: React JSX (geen TypeScript), geen extra bibliotheken tenzij gevraagd
- **Taal in UI**: Nederlands
- **Commentaar in code**: Nederlands

### Regels
- Voeg geen extra bestanden toe — alle backend-logica staat in `etf_score_engine.py`
- Wijzig gewichten ALLEEN als de gebruiker dat expliciet vraagt
- De `_fmp_get()` functie is de enige plek voor FMP API-aanroepen
- Cache-duur is 60 minuten (`CACHE_DURATION_MINUTES`) — niet aanpassen zonder vraag
- `config.json` bevat de standaard tickers — nooit hardcoden in Python

### Omgevingsvariabelen
- `FMP_API_KEY` instellen via `.env` (zie `.env.example`)
- Nooit een echte API-key in code of git committen

### Testen
```bash
cd backend && python -m pytest tests/
cd frontend && npm test
```

## Bekende issues / TODO

- [ ] Niet-US aandelen (TSM, ASML) krijgen geen fundamentals — score is dan puur technisch
- [ ] ETF-holdings ophalen via API (`/etf-holder`) vereist Ultimate-plan ($139/mo) → gebruik `config.json`
- [ ] Intraday data niet beschikbaar in historische modus (API geeft geen historische intraday terug)
- [ ] Sector performance mapping: FMP-sectornamen moeten overeenkomen met `/profile` sector-veld

## Git workflow

- Huidige feature-tak: `feature/premium-api-upgrade`
- Push altijd naar de juiste branch: `git push -u origin <branch-naam>`
- Nooit pushen naar `master` zonder expliciete toestemming
