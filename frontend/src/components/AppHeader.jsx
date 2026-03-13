import IndicatorTooltip from "./IndicatorTooltip";

// Props:
//   useMock, isHistoricalMode, historicalDate, data, activeTickers
//   tickerInput, setTickerInput, onAnalyzeTickers, onClearTickers
//   historicalDateInput, setHistoricalDateInput, onSubmitHistorical, onClearHistorical
//   useCache, setUseCache, loading, onRefresh
export default function AppHeader({
  useMock, isHistoricalMode, historicalDate, data, activeTickers,
  tickerInput, setTickerInput, onAnalyzeTickers, onClearTickers,
  historicalDateInput, setHistoricalDateInput, onSubmitHistorical, onClearHistorical,
  useCache, setUseCache, loading, onRefresh,
}) {
  return (
    <div className="header-wrapper" style={{ background: "#0D1321", borderBottom: "1px solid #1E2D45" }}>

      {/* Logo & status */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: 8, background: "linear-gradient(135deg,#3B82F6,#8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>📡</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: "-0.01em" }}>ETF Intelligence Dashboard</div>
          <div style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono'" }}>
            {useMock
              ? "⚠ Mock data — start backend voor live data"
              : isHistoricalMode
                ? `🕐 Historische analyse · ${new Date(historicalDate).toLocaleDateString("nl-NL", { day: "2-digit", month: "long", year: "numeric" })}`
                : data.cached
                  ? `⚡ uit cache · ${data.cache_age_minutes} min geleden · ${new Date(data.generated_at).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" })}`
                  : `Live · ${new Date(data.generated_at).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" })}`
            }
            {activeTickers && <span style={{ color: "#3B82F6", marginLeft: 8 }}>· {activeTickers}</span>}
          </div>
        </div>
      </div>

      {/* Ticker invoer */}
      <form onSubmit={e => { e.preventDefault(); onAnalyzeTickers(); }} className="header-form">
        <input
          type="text"
          value={tickerInput}
          onChange={e => setTickerInput(e.target.value)}
          placeholder="Tickers (bijv. AAPL, MSFT, NVDA)"
          className="header-ticker-input"
          style={{
            padding: "7px 12px", borderRadius: 6, background: "#060C18",
            border: "1px solid #1E3A5F", color: "#E2E8F0", fontSize: 12,
            fontFamily: "'DM Mono'", outline: "none",
          }}
        />
        <button type="submit" className="hov header-btn"
          style={{ padding: "7px 12px", borderRadius: 6, background: "#1E3A5F", border: "1px solid #2D4E7A", color: "#93C5FD", fontSize: 12, fontWeight: 500 }}>
          Analyseer
        </button>
        {activeTickers && (
          <button type="button" className="hov" onClick={onClearTickers}
            style={{ padding: "7px 10px", borderRadius: 6, background: "transparent", border: "1px solid #1E2D45", color: "#475569", fontSize: 12 }}>
            ✕
          </button>
        )}
      </form>

      {/* Historische datum picker */}
      <form onSubmit={e => { e.preventDefault(); onSubmitHistorical(); }} className="header-form">
        <input
          type="date"
          value={historicalDateInput}
          onChange={e => setHistoricalDateInput(e.target.value)}
          max={new Date().toISOString().split("T")[0]}
          className="header-date-input"
          style={{
            padding: "7px 10px", borderRadius: 6, background: "#060C18",
            border: `1px solid ${isHistoricalMode ? "#F59E0B" : "#1E3A5F"}`,
            color: "#E2E8F0", fontSize: 12, fontFamily: "'DM Mono'", outline: "none",
            colorScheme: "dark",
          }}
        />
        <button type="submit" className="header-btn"
          style={{ padding: "7px 12px", borderRadius: 6, background: "#2D1F00", border: "1px solid #F59E0B", color: "#F59E0B", fontSize: 12, fontWeight: 500, cursor: "pointer" }}>
          🕐 Historisch
        </button>
        {isHistoricalMode && (
          <button type="button" onClick={onClearHistorical}
            style={{ padding: "7px 10px", borderRadius: 6, background: "transparent", border: "1px solid #1E2D45", color: "#475569", fontSize: 12, cursor: "pointer" }}>
            ✕ Live
          </button>
        )}
      </form>

      {/* Cache-toggle & vernieuwen */}
      <div className="header-cache-row">
        <IndicatorTooltip tooltip="Als cache aan staat, wordt opgeslagen data gebruikt (max 60 min oud) zodat het dashboard razendsnel laadt. Zet uit om altijd verse data op te halen — dit duurt ~30 seconden." direction="down">
          <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12, color: useCache ? "#93C5FD" : "#475569", userSelect: "none" }}>
            <input type="checkbox" checked={useCache} disabled={isHistoricalMode}
              onChange={e => setUseCache(e.target.checked)}
              style={{ accentColor: "#3B82F6", width: 14, height: 14, cursor: isHistoricalMode ? "not-allowed" : "pointer" }} />
            ⚡ Cache
          </label>
        </IndicatorTooltip>
        <button className="hov header-btn" onClick={onRefresh}
          style={{ padding: "7px 16px", borderRadius: 6, background: "#1E3A5F", border: "1px solid #2D4E7A", color: "#93C5FD", fontSize: 12, fontWeight: 500 }}>
          {loading ? "⏳ Laden..." : "🔄 Vernieuwen"}
        </button>
      </div>
    </div>
  );
}
