import { useState, useEffect, useCallback } from "react";
import { API_BASE, MOCK_DATA } from "./constants";
import AppHeader    from "./components/AppHeader";
import ScoreGauge   from "./components/ScoreGauge";
import StatsPanel   from "./components/StatsPanel";
import TabNav       from "./components/TabNav";
import HoldingsTable from "./components/HoldingsTable";
import WeightsPanel  from "./components/WeightsPanel";
import HoldingDetail from "./components/HoldingDetail";

export default function App() {
  const [data, setData]                       = useState(MOCK_DATA);
  const [useMock, setUseMock]                 = useState(true);
  const [loading, setLoading]                 = useState(false);
  const [selected, setSelected]               = useState(null);
  const [activeTab, setActiveTab]             = useState("overview");
  const [sortBy, setSortBy]                   = useState("score");
  const [weights, setWeights]                 = useState(MOCK_DATA.config.timeframe_weights);
  const [indWeights, setIndWeights]           = useState(MOCK_DATA.config.indicator_weights);
  const [useCache, setUseCache]               = useState(true);
  const [tickerInput, setTickerInput]         = useState("");
  const [activeTickers, setActiveTickers]     = useState("");
  const [historicalDate, setHistoricalDate]   = useState("");
  const [historicalDateInput, setHistoricalDateInput] = useState("");
  const isHistoricalMode = !!historicalDate;

  // ─── API calls ─────────────────────────────────────────────────────────────
  const fetchHistoricalData = useCallback(async (date, tickers = activeTickers) => {
    setLoading(true);
    try {
      const tickersParam = tickers ? `&tickers=${encodeURIComponent(tickers)}` : "";
      const res  = await fetch(`${API_BASE}/historical?date=${date}${tickersParam}`);
      const json = await res.json();
      if (json.error) throw new Error(json.error);
      setData(json);
      setUseMock(false);
    } catch (e) {
      console.warn("Historische data niet beschikbaar:", e);
      setUseMock(true);
    } finally {
      setLoading(false);
    }
  }, [activeTickers]);

  const fetchLiveData = useCallback(async (cachePref = useCache, tickers = activeTickers) => {
    setLoading(true);
    try {
      const tickersParam = tickers ? `&tickers=${encodeURIComponent(tickers)}` : "";
      const res  = await fetch(`${API_BASE}/etf?use_cache=${cachePref}${tickersParam}`);
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

  // ─── Live score herberekening op basis van sliders ──────────────────────────
  const liveScore = (() => {
    const valid = (data.holdings || []).filter(h => h.scores_by_timeframe);
    const tw = valid.reduce((s, h) => s + h.etf_weight, 0);
    if (tw === 0) return 0;
    return Math.round(valid.reduce((acc, h) => {
      const s = weights.daily   * h.scores_by_timeframe.daily +
                weights.weekly  * h.scores_by_timeframe.weekly +
                weights.monthly * h.scores_by_timeframe.monthly;
      return acc + s * (h.etf_weight / tw);
    }, 0) * 10) / 10;
  })();
  const liveSignal = liveScore >= 65 ? "INSTAP" : liveScore < 45 ? "UITSTAP" : "AFWACHTEN";

  // ─── Event handlers ─────────────────────────────────────────────────────────
  const handleAnalyzeTickers = () => {
    const trimmed = tickerInput.trim().toUpperCase();
    setActiveTickers(trimmed);
    fetchLiveData(useCache, trimmed);
  };

  const handleClearTickers = () => {
    setActiveTickers("");
    setTickerInput("");
    fetchLiveData(useCache, "");
  };

  const handleSubmitHistorical = () => {
    if (!historicalDateInput) return;
    setHistoricalDate(historicalDateInput);
    fetchHistoricalData(historicalDateInput);
  };

  const handleClearHistorical = () => {
    setHistoricalDate("");
    setHistoricalDateInput("");
    fetchLiveData(useCache);
  };

  const handleCacheChange = (checked) => {
    setUseCache(checked);
    fetchLiveData(checked);
  };

  const handleSelectHolding = (holding) => {
    setSelected(holding);
    setActiveTab("detail");
  };

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

      <AppHeader
        useMock={useMock}
        isHistoricalMode={isHistoricalMode}
        historicalDate={historicalDate}
        data={data}
        activeTickers={activeTickers}
        tickerInput={tickerInput}
        setTickerInput={setTickerInput}
        onAnalyzeTickers={handleAnalyzeTickers}
        onClearTickers={handleClearTickers}
        historicalDateInput={historicalDateInput}
        setHistoricalDateInput={setHistoricalDateInput}
        onSubmitHistorical={handleSubmitHistorical}
        onClearHistorical={handleClearHistorical}
        useCache={useCache}
        setUseCache={handleCacheChange}
        loading={loading}
        onRefresh={() => isHistoricalMode ? fetchHistoricalData(historicalDate) : fetchLiveData(useCache)}
      />

      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "20px" }}>

        {/* Score gauge + statistieken */}
        <div style={{ display: "grid", gridTemplateColumns: "270px 1fr", gap: 16, marginBottom: 20 }}>
          <ScoreGauge
            score={liveScore}
            signal={liveSignal}
            holdingsAnalyzed={data.summary.holdings_analyzed}
            holdingsTotal={data.summary.holdings_total}
          />
          <StatsPanel holdings={data.holdings || []} />
        </div>

        <TabNav
          activeTab={activeTab}
          onTabChange={setActiveTab}
          selectedTicker={selected?.ticker ?? null}
        />

        {activeTab === "overview" && (
          <HoldingsTable
            holdings={data.holdings || []}
            sortBy={sortBy}
            onSortChange={setSortBy}
            selectedTicker={selected?.ticker ?? null}
            onSelectHolding={handleSelectHolding}
          />
        )}

        {activeTab === "weights" && (
          <WeightsPanel
            weights={weights}
            setWeights={setWeights}
            indWeights={indWeights}
            setIndWeights={setIndWeights}
            liveScore={liveScore}
            liveSignal={liveSignal}
          />
        )}

        {activeTab === "detail" && (
          <HoldingDetail
            holding={selected}
            isHistoricalMode={isHistoricalMode}
          />
        )}

        <div style={{ marginTop: 20, textAlign: "center", fontSize: 10, color: "#1E2D45", fontFamily: "'DM Mono'" }}>
          {useMock ? "Mock data actief — start `uvicorn etf_score_engine:app --reload` in /backend voor live data" : `Live data van ${API_BASE}`}
        </div>
      </div>
    </div>
  );
}
