import { useState, useEffect, useCallback } from "react";
import {
  RadialBarChart, RadialBar, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine
} from "recharts";

// ─── CONFIG ───────────────────────────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8001";

const INDICATOR_LABELS = {
  rsi: "RSI",
  rsi_daily: "RSI Dag", rsi_weekly: "RSI Week", rsi_monthly: "RSI Maand",
  rsi_divergence: "RSI Divergentie",
  rsi_divergence_daily: "RSI Div. Dag", rsi_divergence_weekly: "RSI Div. Week", rsi_divergence_monthly: "RSI Div. Maand",
  ma20: "MA20",
  ma20_daily: "MA20 Dag", ma20_weekly: "MA20 Week", ma20_monthly: "MA20 Maand",
  ma200: "MA200",
  apz: "APZ",
  apz_daily: "APZ Dag", apz_weekly: "APZ Week", apz_monthly: "APZ Maand",
  forward_pe: "Fwd P/E", peg: "PEG", price_fcf: "P/FCF",
  momentum: "Momentum", dcf_discount: "DCF Korting", panic: "Paniek",
};

const MOCK_DATA = {
  summary: { etf_score: 61.4, etf_signal: "AFWACHTEN", holdings_analyzed: 10, holdings_total: 10 },
  generated_at: new Date().toISOString(),
  config: {
    timeframe_weights: { daily: 0.30, weekly: 0.40, monthly: 0.30 },
    indicator_weights: { rsi: 0.15, ma200: 0.15, forward_pe: 0.20, peg: 0.20, price_fcf: 0.15, momentum: 0.10, dcf_discount: 0.05 },
  },
  holdings: [
    { ticker: "NVDA",  name: "NVIDIA Corp",          current_price: 875.40,  currency: "USD", total_score: 72.3, signal: "KOOP",     etf_weight: 0.0454, scores_by_timeframe: { daily: 74.1, weekly: 71.8, monthly: 70.9 }, indicator_scores: { rsi_daily: 42, rsi_weekly: 38, rsi_monthly: 45, ma200: 82, forward_pe: 68, peg: 71, price_fcf: 65, momentum: 75, dcf_discount: 55 }, raw_data: { rsi_daily: 42.1, peg_ratio: 0.89, forward_pe: 28.4, ma200: 721.30, momentum_1m: 3.2 } },
    { ticker: "AAPL",  name: "Apple Inc",             current_price: 189.30,  currency: "USD", total_score: 58.1, signal: "NEUTRAAL", etf_weight: 0.0369, scores_by_timeframe: { daily: 57.2, weekly: 58.9, monthly: 58.1 }, indicator_scores: { rsi_daily: 55, rsi_weekly: 52, rsi_monthly: 50, ma200: 60, forward_pe: 52, peg: 58, price_fcf: 60, momentum: 55, dcf_discount: 50 }, raw_data: { rsi_daily: 54.8, peg_ratio: 1.42, forward_pe: 29.1, ma200: 181.20, momentum_1m: 0.8 } },
    { ticker: "MSFT",  name: "Microsoft Corp",        current_price: 378.90,  currency: "USD", total_score: 63.7, signal: "KOOP",     etf_weight: 0.0288, scores_by_timeframe: { daily: 62.1, weekly: 64.5, monthly: 64.4 }, indicator_scores: { rsi_daily: 48, rsi_weekly: 46, rsi_monthly: 47, ma200: 70, forward_pe: 65, peg: 62, price_fcf: 68, momentum: 60, dcf_discount: 58 }, raw_data: { rsi_daily: 47.6, peg_ratio: 1.18, forward_pe: 30.2, ma200: 355.40, momentum_1m: 1.9 } },
    { ticker: "GOOGL", name: "Alphabet Class A",      current_price: 165.20,  currency: "USD", total_score: 68.9, signal: "KOOP",     etf_weight: 0.0222, scores_by_timeframe: { daily: 67.3, weekly: 70.1, monthly: 69.2 }, indicator_scores: { rsi_daily: 44, rsi_weekly: 41, rsi_monthly: 43, ma200: 78, forward_pe: 72, peg: 69, price_fcf: 70, momentum: 62, dcf_discount: 65 }, raw_data: { rsi_daily: 43.9, peg_ratio: 0.98, forward_pe: 21.3, ma200: 148.90, momentum_1m: 2.4 } },
    { ticker: "TSM",   name: "Taiwan Semiconductor",  current_price: 142.80,  currency: "USD", total_score: 74.2, signal: "KOOP",     etf_weight: 0.0209, scores_by_timeframe: { daily: 75.8, weekly: 73.4, monthly: 73.6 }, indicator_scores: { rsi_daily: 38, rsi_weekly: 35, rsi_monthly: 40, ma200: 88, forward_pe: 74, peg: 76, price_fcf: 72, momentum: 68, dcf_discount: 70 }, raw_data: { rsi_daily: 37.4, peg_ratio: 0.76, forward_pe: 18.9, ma200: 118.60, momentum_1m: 4.1 } },
    { ticker: "AMZN",  name: "Amazon.com Inc",        current_price: 183.50,  currency: "USD", total_score: 65.4, signal: "KOOP",     etf_weight: 0.0208, scores_by_timeframe: { daily: 64.1, weekly: 66.2, monthly: 65.8 }, indicator_scores: { rsi_daily: 46, rsi_weekly: 44, rsi_monthly: 45, ma200: 72, forward_pe: 67, peg: 64, price_fcf: 66, momentum: 63, dcf_discount: 60 }, raw_data: { rsi_daily: 45.8, peg_ratio: 1.05, forward_pe: 34.8, ma200: 166.20, momentum_1m: 2.1 } },
    { ticker: "GOOG",  name: "Alphabet Class C",      current_price: 166.80,  currency: "USD", total_score: 68.2, signal: "KOOP",     etf_weight: 0.0134, scores_by_timeframe: { daily: 66.9, weekly: 69.4, monthly: 68.1 }, indicator_scores: { rsi_daily: 44, rsi_weekly: 42, rsi_monthly: 44, ma200: 77, forward_pe: 71, peg: 68, price_fcf: 69, momentum: 61, dcf_discount: 64 }, raw_data: { rsi_daily: 44.2, peg_ratio: 0.99, forward_pe: 21.5, ma200: 149.70, momentum_1m: 2.3 } },
    { ticker: "AVGO",  name: "Broadcom Inc",          current_price: 1380.20, currency: "USD", total_score: 55.8, signal: "NEUTRAAL", etf_weight: 0.0125, scores_by_timeframe: { daily: 54.2, weekly: 56.4, monthly: 56.7 }, indicator_scores: { rsi_daily: 58, rsi_weekly: 55, rsi_monthly: 54, ma200: 55, forward_pe: 50, peg: 53, price_fcf: 58, momentum: 52, dcf_discount: 48 }, raw_data: { rsi_daily: 57.9, peg_ratio: 1.68, forward_pe: 25.4, ma200: 1290.50, momentum_1m: -0.4 } },
    { ticker: "META",  name: "Meta Platforms",        current_price: 496.30,  currency: "USD", total_score: 70.1, signal: "KOOP",     etf_weight: 0.0123, scores_by_timeframe: { daily: 69.5, weekly: 71.0, monthly: 69.8 }, indicator_scores: { rsi_daily: 41, rsi_weekly: 39, rsi_monthly: 42, ma200: 80, forward_pe: 70, peg: 72, price_fcf: 71, momentum: 66, dcf_discount: 63 }, raw_data: { rsi_daily: 40.6, peg_ratio: 0.91, forward_pe: 22.8, ma200: 438.70, momentum_1m: 3.6 } },
    { ticker: "005930.KS", name: "Samsung Electronics", current_price: 71200, currency: "KRW", total_score: 42.6, signal: "UITSTAP", etf_weight: 0.0111, scores_by_timeframe: { daily: 40.8, weekly: 43.5, monthly: 43.3 }, indicator_scores: { rsi_daily: 68, rsi_weekly: 65, rsi_monthly: 62, ma200: 38, forward_pe: 40, peg: 42, price_fcf: 45, momentum: 40, dcf_discount: 38 }, raw_data: { rsi_daily: 67.8, peg_ratio: 2.14, forward_pe: 14.2, ma200: 78400, momentum_1m: -3.8 } },
  ],
};

const MOCK_HISTORY = Array.from({ length: 60 }, (_, i) => {
  const d = new Date(); d.setDate(d.getDate() - (59 - i));
  return { date: d.toLocaleDateString("nl-NL", { day: "2-digit", month: "2-digit" }), score: 45 + Math.sin(i * 0.2) * 12 + i * 0.15 + (Math.random() - 0.5) * 4 };
});

// ─── HELPERS ──────────────────────────────────────────────────────────────────
const signalColor = (s) => s === "KOOP" || s === "INSTAP" ? "#22C55E" : s === "UITSTAP" ? "#EF4444" : "#F59E0B";
const scoreColor  = (s) => s >= 65 ? "#22C55E" : s >= 45 ? "#F59E0B" : "#EF4444";
const fmt = (price, currency) => price == null ? "—" : currency === "KRW" ? `₩${price.toLocaleString()}` : `$${price.toFixed(2)}`;

const signalDotColor = (s) =>
  s === "OVERSOLD" || s === "BULLISH"   ? "#22C55E" :
  s === "OVERBOUGHT" || s === "BEARISH" ? "#EF4444" :
  s === "DICHTBIJ"                      ? "#F59E0B" : "#475569";

function IndicatorTooltip({ tooltip, children, direction = "up" }) {
  const [show, setShow] = useState(false);
  const pos = direction === "down"
    ? { top: "calc(100% + 8px)", right: 0 }
    : { bottom: "calc(100% + 8px)", left: 0 };
  return (
    <span style={{ position: "relative" }}
      onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      {show && tooltip && (
        <div style={{
          position: "absolute", ...pos,
          background: "#0D1A2D", border: "1px solid #1E3A5F", borderRadius: 8,
          padding: "10px 14px", fontSize: 11, color: "#94A3B8",
          width: 280, lineHeight: 1.65, zIndex: 200,
          pointerEvents: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          whiteSpace: "normal",
        }}>
          {tooltip}
        </div>
      )}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
export default function App() {
  const [data, setData]         = useState(MOCK_DATA);
  const [useMock, setUseMock]   = useState(true);
  const [loading, setLoading]   = useState(false);
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [sortBy, setSortBy]     = useState("score");
  const [weights, setWeights]   = useState(MOCK_DATA.config.timeframe_weights);
  const [indWeights, setIndWeights] = useState(MOCK_DATA.config.indicator_weights);
  const [useCache, setUseCache] = useState(true);
  const [tickerInput, setTickerInput] = useState("");
  const [activeTickers, setActiveTickers] = useState("");

  const fetchLiveData = useCallback(async (cachePref = useCache, tickers = activeTickers) => {
    setLoading(true);
    try {
      const tickersParam = tickers ? `&tickers=${encodeURIComponent(tickers)}` : "";
      const res = await fetch(`${API_BASE}/etf?use_cache=${cachePref}${tickersParam}`);
      const json = await res.json();
      if (json.error) throw new Error(json.error);
      setData(json);
      setWeights(json.config.timeframe_weights);
      setIndWeights(json.config.indicator_weights);
      setUseMock(false);
      const failed = json.holdings.filter(h => h.error);
      if (failed.length > 0) {
        console.warn(`[FMP] ${failed.length}/${json.holdings.length} holdings niet beschikbaar:`, failed.map(h => h.error).filter((v, i, a) => a.indexOf(v) === i));
      } else {
        console.info(`[FMP] Alle ${json.holdings.length} holdings succesvol geladen.`);
      }
    } catch (e) {
      console.warn("API niet bereikbaar, mock data gebruikt:", e);
      setUseMock(true);
    } finally {
      setLoading(false);
    }
  }, [useCache]);

  // Probeer live data bij laden
  useEffect(() => { fetchLiveData(); }, [fetchLiveData]);

  // Live ETF score herberekening op basis van slider
  const liveScore = (() => {
    const validHoldings = (data.holdings || []).filter(h => h.scores_by_timeframe);
    const tw = validHoldings.reduce((s, h) => s + h.etf_weight, 0);
    if (tw === 0) return 0;
    return Math.round(validHoldings.reduce((acc, h) => {
      const s = weights.daily * h.scores_by_timeframe.daily +
                weights.weekly * h.scores_by_timeframe.weekly +
                weights.monthly * h.scores_by_timeframe.monthly;
      return acc + s * (h.etf_weight / tw);
    }, 0) * 10) / 10;
  })();
  const liveSignal = liveScore >= 65 ? "INSTAP" : liveScore < 45 ? "UITSTAP" : "AFWACHTEN";

  const sorted = [...(data.holdings || [])].filter(h => !h.error).sort((a, b) =>
    sortBy === "score"  ? b.total_score - a.total_score :
    sortBy === "weight" ? b.etf_weight - a.etf_weight :
    a.ticker.localeCompare(b.ticker)
  );

  return (
    <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", background: "#0A0F1A", minHeight: "100vh", color: "#E2E8F0" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #0A0F1A; }
        ::-webkit-scrollbar-thumb { background: #1E3A5F; border-radius: 2px; }
        .hov:hover { background: #131B2E !important; cursor: pointer; }
        .tab { transition: all 0.15s; cursor: pointer; border-bottom: 2px solid transparent; background: none; border-top: none; border-left: none; border-right: none; }
        .tab.on { border-bottom-color: #3B82F6; color: #93C5FD !important; }
        .slider { -webkit-appearance: none; height: 4px; border-radius: 2px; outline: none; cursor: pointer; width: 100%; }
        .slider::-webkit-slider-thumb { -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%; background: #3B82F6; cursor: pointer; }
        .badge { display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; font-family: 'DM Mono', monospace; }
        tr.hov { transition: background 0.1s; }
      `}</style>

      {/* HEADER */}
      <div style={{ background: "#0D1321", borderBottom: "1px solid #1E2D45", padding: "14px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 34, height: 34, borderRadius: 8, background: "linear-gradient(135deg,#3B82F6,#8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>📡</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: "-0.01em" }}>ETF Intelligence Dashboard</div>
            <div style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono'" }}>
              {useMock
                ? "⚠ Mock data — start backend voor live data"
                : data.cached
                  ? `⚡ uit cache · ${data.cache_age_minutes} min geleden · ${new Date(data.generated_at).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" })}`
                  : `Live · ${new Date(data.generated_at).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" })}`
              }
              {activeTickers && <span style={{ color: "#3B82F6", marginLeft: 8 }}>· {activeTickers}</span>}
            </div>
          </div>
        </div>
        {/* TICKER INVOER */}
        <form onSubmit={e => {
          e.preventDefault();
          const trimmed = tickerInput.trim().toUpperCase();
          setActiveTickers(trimmed);
          fetchLiveData(useCache, trimmed);
        }} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="text"
            value={tickerInput}
            onChange={e => setTickerInput(e.target.value)}
            placeholder="Tickers (bijv. AAPL, MSFT, NVDA)"
            style={{
              padding: "7px 12px", borderRadius: 6, background: "#060C18",
              border: "1px solid #1E3A5F", color: "#E2E8F0", fontSize: 12,
              fontFamily: "'DM Mono'", width: 260, outline: "none",
            }}
          />
          <button type="submit" className="hov"
            style={{ padding: "7px 12px", borderRadius: 6, background: "#1E3A5F", border: "1px solid #2D4E7A", color: "#93C5FD", fontSize: 12, fontWeight: 500 }}>
            Analyseer
          </button>
          {activeTickers && (
            <button type="button" className="hov" onClick={() => {
              setActiveTickers(""); setTickerInput(""); fetchLiveData(useCache, "");
            }} style={{ padding: "7px 10px", borderRadius: 6, background: "transparent", border: "1px solid #1E2D45", color: "#475569", fontSize: 12 }}>
              ✕
            </button>
          )}
        </form>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <IndicatorTooltip tooltip="Als cache aan staat, wordt opgeslagen data gebruikt (max 60 min oud) zodat het dashboard razendsnel laadt. Zet uit om altijd verse data op te halen — dit duurt ~30 seconden." direction="down">
            <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12, color: useCache ? "#93C5FD" : "#475569", userSelect: "none" }}>
              <input type="checkbox" checked={useCache}
                onChange={e => {
                  setUseCache(e.target.checked);
                  fetchLiveData(e.target.checked);
                }}
                style={{ accentColor: "#3B82F6", width: 14, height: 14, cursor: "pointer" }} />
              ⚡ Cache
            </label>
          </IndicatorTooltip>
          <button className="hov" onClick={() => fetchLiveData(useCache)}
            style={{ padding: "7px 16px", borderRadius: 6, background: "#1E3A5F", border: "1px solid #2D4E7A", color: "#93C5FD", fontSize: 12, fontWeight: 500 }}>
            {loading ? "⏳ Laden..." : "🔄 Vernieuwen"}
          </button>
        </div>
      </div>

      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "20px" }}>

        {/* SCORE + STATS */}
        <div style={{ display: "grid", gridTemplateColumns: "270px 1fr", gap: 16, marginBottom: 20 }}>

          {/* Gauge */}
          <div style={{ background: "#0D1321", border: `1px solid ${signalColor(liveSignal)}33`, borderRadius: 14, padding: 24, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <div style={{ fontSize: 10, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 12, letterSpacing: "0.1em" }}>ETF TOTAAL SCORE</div>
            <div style={{ position: "relative", width: 155, height: 155 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart cx="50%" cy="50%" innerRadius="65%" outerRadius="85%" startAngle={225} endAngle={-45}
                  data={[{ value: liveScore, fill: signalColor(liveSignal) }]}>
                  <RadialBar dataKey="value" cornerRadius={8} background={{ fill: "#1E2D45" }} />
                </RadialBarChart>
              </ResponsiveContainer>
              <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", textAlign: "center" }}>
                <div style={{ fontSize: 38, fontWeight: 800, color: signalColor(liveSignal), lineHeight: 1, fontFamily: "'DM Mono'" }}>{liveScore}</div>
                <div style={{ fontSize: 10, color: "#64748B", marginTop: 2 }}>/ 100</div>
              </div>
            </div>
            <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: signalColor(liveSignal) }} />
              <span style={{ fontWeight: 700, fontSize: 15, color: signalColor(liveSignal) }}>{liveSignal}</span>
            </div>
            <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>{data.summary.holdings_analyzed} van {data.summary.holdings_total} aandelen</div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
              {[
                { label: "Koop signalen",  value: data.holdings.filter(h => h.signal === "KOOP").length,     color: "#22C55E", icon: "🟢" },
                { label: "Neutraal",       value: data.holdings.filter(h => h.signal === "NEUTRAAL").length, color: "#F59E0B", icon: "🟡" },
                { label: "Uitstap",        value: data.holdings.filter(h => h.signal === "UITSTAP").length,  color: "#EF4444", icon: "🔴" },
                { label: "Hoogste score",  value: Math.max(...data.holdings.map(h => h.total_score)).toFixed(1), color: "#60A5FA", icon: "🏆" },
              ].map((s, i) => (
                <div key={i} style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 10, padding: "12px 14px" }}>
                  <div style={{ fontSize: 10, color: "#475569", marginBottom: 4, fontFamily: "'DM Mono'" }}>{s.label.toUpperCase()}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {s.color !== "#60A5FA" && <span style={{ display: "inline-block", width: 16, height: 16, borderRadius: "50%", background: s.color, flexShrink: 0 }} />}
                    {s.color === "#60A5FA" && <span style={{ fontSize: 20 }}>{s.icon}</span>}
                    <span style={{ fontSize: 26, fontWeight: 800, color: s.color, fontFamily: "'DM Mono'" }}>{s.value}</span>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 10, padding: "14px 16px", flex: 1 }}>
              <div style={{ fontSize: 10, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 10, letterSpacing: "0.08em" }}>60-DAAGSE ETF SCORE HISTORY (GESIMULEERD)</div>
              <ResponsiveContainer width="100%" height={80}>
                <LineChart data={MOCK_HISTORY}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E2D45" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#475569", fontFamily: "'DM Mono'" }} tickLine={false} axisLine={false} interval={9} />
                  <YAxis domain={[30, 90]} tick={{ fontSize: 9, fill: "#475569" }} tickLine={false} axisLine={false} width={28} />
                  <ReferenceLine y={65} stroke="#22C55E" strokeDasharray="4 4" strokeOpacity={0.4} />
                  <ReferenceLine y={45} stroke="#EF4444" strokeDasharray="4 4" strokeOpacity={0.4} />
                  <Tooltip contentStyle={{ background: "#131B2E", border: "1px solid #1E2D45", borderRadius: 6, fontSize: 11, fontFamily: "'DM Mono'" }} formatter={(v) => [v.toFixed(1), "Score"]} />
                  <Line type="monotone" dataKey="score" stroke="#3B82F6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* TABS */}
        <div style={{ display: "flex", borderBottom: "1px solid #1E2D45", marginBottom: 16 }}>
          {[["overview","📋 Holdings"], ["weights","🎚️ Gewichten"], ["detail", selected ? `🔍 ${selected.ticker ?? "Detail"}` : "🔍 Detail"]].map(([id, label]) => (
            <button key={id} className={`tab ${activeTab === id ? "on" : ""}`} onClick={() => setActiveTab(id)}
              style={{ padding: "10px 18px", color: activeTab === id ? "#93C5FD" : "#64748B", fontSize: 13, fontWeight: 500, fontFamily: "'DM Sans'" }}>
              {label}
            </button>
          ))}
        </div>

        {/* TAB: HOLDINGS */}
        {activeTab === "overview" && (
          <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, overflow: "hidden" }}>
            <div style={{ padding: "10px 16px", borderBottom: "1px solid #1E2D45", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
              <span style={{ fontSize: 11, color: "#475569" }}>Klik op een rij voor detail-analyse</span>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "#475569" }}>Sorteer:</span>
                {[["score","Score"],["weight","Weging"],["ticker","Ticker"]].map(([v, l]) => (
                  <button key={v} onClick={() => setSortBy(v)}
                    style={{ padding: "3px 10px", borderRadius: 4, background: sortBy === v ? "#1E3A5F" : "transparent", border: `1px solid ${sortBy === v ? "#2D4E7A" : "#1E2D45"}`, color: sortBy === v ? "#93C5FD" : "#64748B", fontSize: 11, cursor: "pointer" }}>
                    {l}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#060C18" }}>
                    {["Ticker","Naam","Koers","ETF %","Score","Signaal","RSI dag","PEG","Fwd P/E","Afstand MA200"].map(h => (
                      <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 10, color: "#475569", fontWeight: 600, fontFamily: "'DM Mono'", letterSpacing: "0.06em", whiteSpace: "nowrap" }}>{h.toUpperCase()}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((h, i) => {
                    const rd = h.raw_data || {};
                    const ma200dist = rd.ma200 ? ((h.current_price - rd.ma200) / rd.ma200 * 100).toFixed(1) : null;
                    return (
                      <tr key={h.ticker ?? i} className="hov" onClick={() => { setSelected(h); setActiveTab("detail"); }}
                        style={{ borderTop: "1px solid #0F1C2E", background: selected?.ticker === h.ticker ? "#131B2E" : "transparent" }}>
                        <td style={{ padding: "11px 14px", fontFamily: "'DM Mono'", fontWeight: 600, fontSize: 13, color: "#93C5FD" }}>{h.ticker}</td>
                        <td style={{ padding: "11px 14px", fontSize: 12, color: "#94A3B8", whiteSpace: "nowrap" }}>{h.name}</td>
                        <td style={{ padding: "11px 14px", fontFamily: "'DM Mono'", fontSize: 12 }}>{fmt(h.current_price, h.currency)}</td>
                        <td style={{ padding: "11px 14px", fontFamily: "'DM Mono'", fontSize: 12, color: "#64748B" }}>{(h.etf_weight * 100).toFixed(2)}%</td>
                        <td style={{ padding: "11px 14px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <div style={{ width: 44, height: 5, borderRadius: 3, background: "#1E2D45", overflow: "hidden" }}>
                              <div style={{ width: `${h.total_score}%`, height: "100%", background: scoreColor(h.total_score), borderRadius: 3 }} />
                            </div>
                            <span style={{ fontFamily: "'DM Mono'", fontSize: 12, color: scoreColor(h.total_score), fontWeight: 700 }}>{h.total_score}</span>
                          </div>
                        </td>
                        <td style={{ padding: "11px 14px" }}>
                          <span className="badge" style={{ background: signalColor(h.signal)+"20", color: signalColor(h.signal), border: `1px solid ${signalColor(h.signal)}40` }}>{h.signal}</span>
                        </td>
                        <td style={{ padding: "11px 14px", fontFamily: "'DM Mono'", fontSize: 12, color: rd.rsi_daily < 30 ? "#22C55E" : rd.rsi_daily > 70 ? "#EF4444" : "#94A3B8" }}>
                          {rd.rsi_daily?.toFixed(1)}
                        </td>
                        <td style={{ padding: "11px 14px", fontFamily: "'DM Mono'", fontSize: 12, color: rd.peg_ratio < 1 ? "#22C55E" : rd.peg_ratio > 2 ? "#EF4444" : "#94A3B8" }}>
                          {rd.peg_ratio?.toFixed(2)}
                        </td>
                        <td style={{ padding: "11px 14px", fontFamily: "'DM Mono'", fontSize: 12, color: "#94A3B8" }}>{rd.forward_pe?.toFixed(1)}</td>
                        <td style={{ padding: "11px 14px", fontFamily: "'DM Mono'", fontSize: 12, color: ma200dist && parseFloat(ma200dist) < 5 ? "#22C55E" : ma200dist && parseFloat(ma200dist) > 30 ? "#EF4444" : "#94A3B8" }}>
                          {ma200dist ? `+${ma200dist}%` : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {(data.holdings || []).filter(h => h.error).length > 0 && (
              <div style={{ marginTop: 10, padding: "10px 14px", background: "#1A0A0A", border: "1px solid #3B1010", borderRadius: 8, fontSize: 11, color: "#F87171" }}>
                Niet beschikbaar: {(data.holdings || []).filter(h => h.error).map(h => h.ticker || "?").join(", ")} — {(data.holdings || []).find(h => h.error)?.error}
              </div>
            )}
          </div>
        )}

        {/* TAB: GEWICHTEN */}
        {activeTab === "weights" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#93C5FD" }}>⏱ Timeframe Gewichten</div>
              {Object.entries(weights).map(([key, val]) => (
                <div key={key} style={{ marginBottom: 18 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ fontSize: 12, color: "#94A3B8" }}>{key === "daily" ? "Dagelijks" : key === "weekly" ? "Wekelijks" : "Maandelijks"}</span>
                    <span style={{ fontFamily: "'DM Mono'", fontSize: 12, color: "#60A5FA", fontWeight: 600 }}>{(val * 100).toFixed(0)}%</span>
                  </div>
                  <input type="range" className="slider" min={0} max={100} value={Math.round(val * 100)}
                    style={{ background: `linear-gradient(to right, #3B82F6 ${val*100}%, #1E2D45 ${val*100}%)` }}
                    onChange={e => setWeights(prev => ({ ...prev, [key]: parseInt(e.target.value) / 100 }))} />
                </div>
              ))}
              <div style={{ padding: "8px 10px", background: "#060C18", borderRadius: 6, fontSize: 11, color: "#475569", fontFamily: "'DM Mono'" }}>
                Totaal: {(Object.values(weights).reduce((a,b)=>a+b,0)*100).toFixed(0)}%
                {Math.abs(Object.values(weights).reduce((a,b)=>a+b,0)-1) > 0.05 && <span style={{ color: "#EF4444" }}> ⚠ moet 100% zijn</span>}
              </div>
            </div>

            <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#93C5FD" }}>📊 Indicator Gewichten</div>
              {Object.entries(indWeights).map(([key, val]) => (
                <div key={key} style={{ marginBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: "#94A3B8" }}>{INDICATOR_LABELS[key] || key}</span>
                    <span style={{ fontFamily: "'DM Mono'", fontSize: 11, color: "#A78BFA" }}>{(val * 100).toFixed(0)}%</span>
                  </div>
                  <input type="range" className="slider" min={0} max={40} value={Math.round(val * 100)}
                    style={{ background: `linear-gradient(to right, #8B5CF6 ${val*100/0.4}%, #1E2D45 ${val*100/0.4}%)` }}
                    onChange={e => setIndWeights(prev => ({ ...prev, [key]: parseInt(e.target.value) / 100 }))} />
                </div>
              ))}
            </div>

            <div style={{ gridColumn: "1 / -1", background: "#0D1321", border: `2px solid ${signalColor(liveSignal)}44`, borderRadius: 12, padding: 16, display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ fontSize: 36, fontWeight: 800, color: signalColor(liveSignal), fontFamily: "'DM Mono'" }}>{liveScore}</div>
              <div>
                <div style={{ fontWeight: 600, color: signalColor(liveSignal) }}>Live ETF Score preview</div>
                <div style={{ fontSize: 12, color: "#475569" }}>Past mee terwijl je de sliders versleept</div>
              </div>
              <div style={{ marginLeft: "auto" }}>
                <span className="badge" style={{ background: signalColor(liveSignal)+"20", color: signalColor(liveSignal), border: `1px solid ${signalColor(liveSignal)}44`, fontSize: 13, padding: "6px 18px" }}>{liveSignal}</span>
              </div>
            </div>
          </div>
        )}

        {/* TAB: DETAIL */}
        {activeTab === "detail" && selected && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
                  <div>
                    <div style={{ fontFamily: "'DM Mono'", fontSize: 24, fontWeight: 700, color: "#93C5FD" }}>{selected.ticker}</div>
                    <div style={{ fontSize: 12, color: "#64748B" }}>{selected.name}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "'DM Mono'" }}>{fmt(selected.current_price, selected.currency)}</div>
                    <span className="badge" style={{ background: signalColor(selected.signal)+"20", color: signalColor(selected.signal), border: `1px solid ${signalColor(selected.signal)}44`, marginTop: 4 }}>{selected.signal}</span>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                  {[["Dagelijks","daily"],["Wekelijks","weekly"],["Maandelijks","monthly"]].map(([label, key]) => (
                    <div key={key} style={{ background: "#060C18", borderRadius: 8, padding: "10px 12px", textAlign: "center" }}>
                      <div style={{ fontSize: 10, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 4 }}>{label.toUpperCase()}</div>
                      <div style={{ fontSize: 24, fontWeight: 700, color: scoreColor(selected.scores_by_timeframe?.[key]), fontFamily: "'DM Mono'" }}>{selected.scores_by_timeframe?.[key] ?? "—"}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 12 }}>RAW DATA</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {[
                    ["RSI (dag)", selected.raw_data?.rsi_daily?.toFixed(1), selected.raw_data?.rsi_daily < 30 ? "#22C55E" : selected.raw_data?.rsi_daily > 70 ? "#EF4444" : "#94A3B8"],
                    ["PEG Ratio", selected.raw_data?.peg_ratio?.toFixed(2), selected.raw_data?.peg_ratio < 1 ? "#22C55E" : selected.raw_data?.peg_ratio > 2 ? "#EF4444" : "#94A3B8"],
                    ["Forward P/E", selected.raw_data?.forward_pe?.toFixed(1), "#94A3B8"],
                    ["Momentum 1m", selected.raw_data?.momentum_1m != null ? `${selected.raw_data.momentum_1m > 0 ? "+" : ""}${selected.raw_data.momentum_1m.toFixed(1)}%` : "—", selected.raw_data?.momentum_1m > 0 ? "#22C55E" : "#EF4444"],
                    ["MA200", fmt(selected.raw_data?.ma200, selected.currency), "#94A3B8"],
                    ["ETF Weging", `${(selected.etf_weight * 100).toFixed(2)}%`, "#60A5FA"],
                  ].map(([label, val, color]) => (
                    <div key={label} style={{ background: "#060C18", borderRadius: 6, padding: "8px 12px" }}>
                      <div style={{ fontSize: 10, color: "#475569", marginBottom: 2, fontFamily: "'DM Mono'" }}>{label}</div>
                      <div style={{ fontSize: 14, fontWeight: 600, color, fontFamily: "'DM Mono'" }}>{val ?? "—"}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
              <div style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 16 }}>INDICATOR SCORES (0 – 100)</div>
              {Object.entries(selected.indicator_scores ?? {}).map(([key, val]) => {
                const interp   = selected.interpretations?.[key];
                const indLabel = interp?.indicator_label || INDICATOR_LABELS[key] || key;
                const desc     = interp?.label;
                const tooltip  = interp?.tooltip;
                const dotColor = signalDotColor(interp?.signal);
                return (
                  <div key={key} style={{ marginBottom: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, alignItems: "flex-start", gap: 8 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <IndicatorTooltip tooltip={tooltip}>
                          <span style={{ fontSize: 11, color: "#94A3B8", display: "inline-flex", alignItems: "center", gap: 5, cursor: tooltip ? "help" : "default", flexWrap: "wrap" }}>
                            <span style={{ width: 6, height: 6, borderRadius: "50%", background: dotColor, flexShrink: 0, display: "inline-block" }} />
                            {indLabel}
                            {interp?.signal && interp.signal !== "NEUTRAAL" && (
                              <span style={{
                                fontSize: 9, fontWeight: 700, fontFamily: "'DM Mono'",
                                padding: "1px 6px", borderRadius: 4,
                                background: dotColor + "22", color: dotColor,
                                border: `1px solid ${dotColor}44`, letterSpacing: "0.04em",
                              }}>
                                {interp.signal}
                              </span>
                            )}
                            {tooltip && <span style={{ fontSize: 9, color: "#475569" }}>ⓘ</span>}
                          </span>
                        </IndicatorTooltip>
                        {desc && (
                          <div style={{ fontSize: 9.5, color: "#475569", marginTop: 2, marginLeft: 11, fontStyle: "italic", lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {desc}
                          </div>
                        )}
                      </div>
                      <span style={{ fontSize: 11, fontFamily: "'DM Mono'", color: scoreColor(val), fontWeight: 700, flexShrink: 0 }}>{val}</span>
                    </div>
                    <div style={{ height: 5, borderRadius: 3, background: "#1E2D45", overflow: "hidden" }}>
                      <div style={{ width: `${val}%`, height: "100%", background: `linear-gradient(90deg, ${scoreColor(val)}88, ${scoreColor(val)})`, borderRadius: 3, transition: "width 0.4s ease" }} />
                    </div>
                  </div>
                );
              })}
              <div style={{ marginTop: 20, padding: 12, background: "#060C18", borderRadius: 8 }}>
                <span style={{ fontSize: 11, color: "#94A3B8" }}>Totaal score: </span>
                <span style={{ color: scoreColor(selected.total_score), fontWeight: 800, fontSize: 18, fontFamily: "'DM Mono'" }}>{selected.total_score}</span>
                <span style={{ color: "#475569", fontSize: 11 }}> / 100</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === "detail" && !selected && (
          <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 40, textAlign: "center", color: "#475569" }}>
            ← Klik op een aandeel in de Holdings tab voor detail-analyse
          </div>
        )}

        <div style={{ marginTop: 20, textAlign: "center", fontSize: 10, color: "#1E2D45", fontFamily: "'DM Mono'" }}>
          {useMock ? "Mock data actief — start `uvicorn etf_score_engine:app --reload` in /backend voor live data" : `Live data van ${API_BASE}`}
        </div>
      </div>
    </div>
  );
}
