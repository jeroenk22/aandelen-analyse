import { useState, useRef, useEffect } from "react";
import IndicatorTooltip from "./IndicatorTooltip";

// ─── Custom datepicker in dashboard-stijl ────────────────────────────────────
function DatePicker({ value, onChange, min, max, onClear }) {
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(() => (value ? new Date(value + "T00:00:00") : new Date()).getFullYear());
  const [viewMonth, setViewMonth] = useState(() => (value ? new Date(value + "T00:00:00") : new Date()).getMonth());
  const ref = useRef();

  const selected  = value ? new Date(value + "T00:00:00") : null;
  const minDate   = min   ? new Date(min   + "T00:00:00") : null;
  const maxDate   = max   ? new Date(max   + "T00:00:00") : null;

  // Sluit bij klik buiten component
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Navigatie helpers
  const prevMonth = () => viewMonth === 0  ? (setViewMonth(11), setViewYear(y => y - 1)) : setViewMonth(m => m - 1);
  const nextMonth = () => viewMonth === 11 ? (setViewMonth(0),  setViewYear(y => y + 1)) : setViewMonth(m => m + 1);
  const prevYear  = () => setViewYear(y => y - 1);
  const nextYear  = () => setViewYear(y => y + 1);

  const isDisabled = (day) => {
    const d = new Date(viewYear, viewMonth, day);
    return (minDate && d < minDate) || (maxDate && d > maxDate);
  };
  const isSelected = (day) => selected &&
    selected.getFullYear() === viewYear && selected.getMonth() === viewMonth && selected.getDate() === day;
  const isToday = (day) => {
    const t = new Date();
    return t.getFullYear() === viewYear && t.getMonth() === viewMonth && t.getDate() === day;
  };

  const selectDay = (day) => {
    if (isDisabled(day)) return;
    // Gebruik lokale datumopmaak om timezone-verschuiving te voorkomen (toISOString geeft UTC terug)
    const str = `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    onChange(str);
    setOpen(false);
  };

  const goToday = () => {
    const t = new Date();
    // Gebruik lokale datumopmaak om timezone-verschuiving te voorkomen
    const str = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    onChange(str);
    setOpen(false);
  };

  const clearDate = () => { onChange(""); setOpen(false); };

  // Celgrid bouwen (ma=0 … zo=6)
  const firstDow = (new Date(viewYear, viewMonth, 1).getDay() + 6) % 7;
  const totalDays = new Date(viewYear, viewMonth + 1, 0).getDate();
  const cells = [...Array(firstDow).fill(null), ...Array.from({ length: totalDays }, (_, i) => i + 1)];

  const MONTHS = ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"];
  const DAYS   = ["MA","DI","WO","DO","VR","ZA","ZO"];

  const displayVal = selected
    ? `${String(selected.getDate()).padStart(2,"0")}-${String(selected.getMonth()+1).padStart(2,"0")}-${selected.getFullYear()}`
    : "dd-mm-jjjj";

  const btnNav = { background: "none", border: "none", cursor: "pointer", color: "#475569",
    fontSize: 13, padding: "0 5px", lineHeight: 1 };

  return (
    <div ref={ref} style={{ position: "relative", display: "flex", alignItems: "stretch", flex: 1 }}>
      {/* Tekstveld */}
      <div
        data-testid="date-picker-trigger"
        onClick={() => setOpen(o => !o)}
        style={{
          padding: selected && onClear ? "7px 24px 7px 10px" : "7px 10px",
          flex: 1, cursor: "pointer", userSelect: "none",
          color: selected ? "#FCD34D" : "#475569",
          fontSize: 12, fontFamily: "'DM Mono'", display: "flex", alignItems: "center",
        }}
      >
        {displayVal}
      </div>
      {selected && onClear && (
        <button type="button" onClick={e => { e.stopPropagation(); onClear(); }}
          style={{ position: "absolute", right: 6, top: "50%", transform: "translateY(-50%)",
            background: "none", border: "none", color: "#475569", cursor: "pointer",
            fontSize: 13, lineHeight: 1, padding: "2px 3px", display: "flex", alignItems: "center" }}>✕</button>
      )}

      {/* Kalender dropdown */}
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 6px)", left: 0, zIndex: 1000,
          background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 10,
          padding: "12px 10px", width: 216,
          boxShadow: "0 8px 32px #000C",
        }}>
          {/* Navigatiebalk */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ display: "flex", gap: 0 }}>
              <button type="button" style={btnNav} onClick={prevYear}  title="Vorig jaar">«</button>
              <button type="button" style={btnNav} onClick={prevMonth} title="Vorige maand">‹</button>
            </div>
            <span style={{ fontSize: 12, fontFamily: "'DM Mono'", color: "#93C5FD", fontWeight: 600, letterSpacing: "0.04em" }}>
              {MONTHS[viewMonth].toUpperCase()} {viewYear}
            </span>
            <div style={{ display: "flex", gap: 0 }}>
              <button type="button" style={btnNav} onClick={nextMonth} title="Volgende maand">›</button>
              <button type="button" style={btnNav} onClick={nextYear}  title="Volgend jaar">»</button>
            </div>
          </div>

          {/* Dag-header */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", marginBottom: 3 }}>
            {DAYS.map(d => (
              <div key={d} style={{ textAlign: "center", fontSize: 9, color: "#334155",
                fontFamily: "'DM Mono'", fontWeight: 700, padding: "2px 0" }}>{d}</div>
            ))}
          </div>

          {/* Dagcellen */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2 }}>
            {cells.map((day, i) => {
              if (!day) return <div key={i} />;
              const disabled = isDisabled(day);
              const sel      = isSelected(day);
              const today    = isToday(day);
              return (
                <div key={i} onClick={() => selectDay(day)} style={{
                  textAlign: "center", fontSize: 11, fontFamily: "'DM Mono'",
                  padding: "4px 1px", borderRadius: 5,
                  cursor: disabled ? "default" : "pointer",
                  color:      disabled ? "#1E3A5F" : sel ? "#0D1321" : today ? "#F59E0B" : "#94A3B8",
                  background: sel ? "#F59E0B" : today && !sel ? "#F59E0B14" : "transparent",
                  border:     today && !sel ? "1px solid #F59E0B44" : "1px solid transparent",
                  fontWeight: sel ? 700 : 400,
                  transition: "background 0.1s",
                }}
                  onMouseEnter={e => { if (!disabled && !sel) e.currentTarget.style.background = "#1E2D45"; }}
                  onMouseLeave={e => { if (!disabled && !sel) e.currentTarget.style.background = today ? "#F59E0B14" : "transparent"; }}
                >{day}</div>
              );
            })}
          </div>

          {/* Footer */}
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10,
            paddingTop: 8, borderTop: "1px solid #1E2D45" }}>
            <button type="button" onClick={clearDate}
              style={{ background: "none", border: "none", color: "#475569", cursor: "pointer",
                fontSize: 11, fontFamily: "'DM Mono'" }}>Wissen</button>
            <button type="button" onClick={goToday}
              style={{ background: "none", border: "none", color: "#F59E0B", cursor: "pointer",
                fontSize: 11, fontFamily: "'DM Mono'", fontWeight: 600 }}>Vandaag</button>
          </div>
        </div>
      )}
    </div>
  );
}

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
      <div className="header-logo" style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: 8, background: "linear-gradient(135deg,#3B82F6,#8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>📡</div>
        <div style={{ minWidth: 0 }}>
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
            {activeTickers && <span className="header-tickers" style={{ color: "#3B82F6" }}>{activeTickers}</span>}
          </div>
        </div>
      </div>

      {/* Ticker invoer */}
      <form onSubmit={e => { e.preventDefault(); onAnalyzeTickers(); }} className="header-form">
        {/* Input met inline ✕ */}
        <div style={{ position: "relative", display: "flex", alignItems: "center", flex: 1, minWidth: 0 }}>
          <input
            type="text"
            value={tickerInput}
            onChange={e => setTickerInput(e.target.value)}
            placeholder="Tickers (bijv. AAPL, MSFT, NVDA)"
            className="header-ticker-input"
            style={{
              padding: activeTickers ? "0 28px 0 12px" : "0 12px",
              borderRadius: 6, background: "#060C18", width: "100%",
              border: "1px solid #1E3A5F", color: "#E2E8F0", fontSize: 12,
              fontFamily: "'DM Mono'", outline: "none", minWidth: 0, boxSizing: "border-box",
            }}
          />
          {activeTickers && (
            <button type="button" onClick={onClearTickers} style={{
              position: "absolute", right: 6, background: "none", border: "none",
              color: "#475569", cursor: "pointer", fontSize: 13, lineHeight: 1,
              padding: "2px 3px", display: "flex", alignItems: "center",
            }}>✕</button>
          )}
        </div>
        <button type="submit" className="hov header-btn"
          style={{ padding: "0 14px", borderRadius: 6, background: "#1E3A5F", border: "1px solid #2D4E7A", color: "#93C5FD", fontSize: 12, fontWeight: 500, cursor: "pointer", flexShrink: 0 }}>
          Analyseer
        </button>
      </form>

      {/* Historische datum picker */}
      {(() => {
        // Pending = datum gewijzigd maar nog niet opgehaald
        const isPending = historicalDateInput && historicalDateInput !== historicalDate;
        const borderColor = isPending ? "#3B82F688" : isHistoricalMode ? "#F59E0B88" : "#1E3A5F";
        const glowColor   = isPending ? "0 0 0 2px #3B82F61A" : isHistoricalMode ? "0 0 0 2px #F59E0B1A" : "none";
        const iconColor   = isPending ? "#3B82F6" : isHistoricalMode ? "#F59E0B" : "#475569";
        return (
          <form onSubmit={e => { e.preventDefault(); onSubmitHistorical(); }} className="header-form">
            <div style={{
              display: "flex", alignItems: "stretch", height: 34, boxSizing: "border-box", flex: 1,
              border: `1px solid ${borderColor}`,
              borderRadius: 6, background: "#060C18",
              boxShadow: glowColor,
              transition: "box-shadow 0.2s, border-color 0.2s",
            }}>
              <span style={{
                padding: "0 9px", display: "flex", alignItems: "center",
                fontSize: 11, color: iconColor,
                fontFamily: "'DM Mono'", fontWeight: 600,
                borderRight: `1px solid ${isPending ? "#3B82F644" : isHistoricalMode ? "#F59E0B44" : "#1E2D45"}`,
                background: isPending ? "#3B82F60D" : isHistoricalMode ? "#F59E0B0D" : "transparent",
                borderRadius: "5px 0 0 5px",
                userSelect: "none", letterSpacing: "0.04em", flexShrink: 0,
              }}>🕐</span>
              <DatePicker
                value={historicalDateInput}
                onChange={v => { setHistoricalDateInput(v); if (!v) onClearHistorical(); }}
                onClear={onClearHistorical}
                min={new Date(Date.now() - 30 * 365.25 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]}
                max={new Date().toISOString().split("T")[0]}
              />
            </div>
            <button type="submit" className="hov header-btn"
              style={{
                padding: "0 14px", borderRadius: 6, cursor: isPending || historicalDateInput ? "pointer" : "default", flexShrink: 0,
                background: isPending ? "#1E3A5F" : isHistoricalMode ? "#F59E0B1A" : "#2D1F00",
                border: `1px solid ${isPending ? "#3B82F688" : isHistoricalMode ? "#F59E0B88" : "#92400E88"}`,
                color: isPending ? "#93C5FD" : "#F59E0B",
                fontSize: 12, fontWeight: 600, justifyContent: "center",
              }}>
              {loading && isHistoricalMode ? "⏳ Laden..." : isPending ? "Ophalen" : isHistoricalMode ? "Actief" : "Historisch"}
            </button>
          </form>
        );
      })()}

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
        <button className="hov header-btn" onClick={isHistoricalMode ? onClearHistorical : onRefresh}
          style={{
            padding: "0 16px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
            background: isHistoricalMode ? "#0D2A1A" : "#1E3A5F",
            border: `1px solid ${isHistoricalMode ? "#16A34A88" : "#2D4E7A"}`,
            color: isHistoricalMode ? "#4ADE80" : "#93C5FD",
          }}>
          {loading && !isHistoricalMode ? "⏳ Laden..." : isHistoricalMode ? "▶ Terug naar Live" : "🔄 Vernieuwen"}
        </button>
      </div>
    </div>
  );
}
