import { signalColor, scoreColor, fmt } from "../helpers";

// Holdings-overzicht tabel met sorteermogelijkheden
// Props: holdings (array), sortBy (string), onSortChange (fn), selectedTicker (string|null), onSelectHolding (fn)
export default function HoldingsTable({ holdings, sortBy, onSortChange, selectedTicker, onSelectHolding }) {
  const failed = holdings.filter(h => h.error);
  const sorted = [...holdings].filter(h => !h.error).sort((a, b) =>
    sortBy === "score"  ? b.total_score - a.total_score :
    sortBy === "weight" ? b.etf_weight - a.etf_weight :
    a.ticker.localeCompare(b.ticker)
  );

  return (
    <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, overflow: "hidden" }}>
      {/* Koptekst met sorteerknopjes */}
      <div style={{ padding: "10px 16px", borderBottom: "1px solid #1E2D45", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <span style={{ fontSize: 11, color: "#475569" }}>Klik op een rij voor detail-analyse</span>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "#475569" }}>Sorteer:</span>
          {[["score","Score"],["weight","Weging"],["ticker","Ticker"]].map(([v, l]) => (
            <button key={v} onClick={() => onSortChange(v)}
              style={{ padding: "3px 10px", borderRadius: 4, background: sortBy === v ? "#1E3A5F" : "transparent", border: `1px solid ${sortBy === v ? "#2D4E7A" : "#1E2D45"}`, color: sortBy === v ? "#93C5FD" : "#64748B", fontSize: 11, cursor: "pointer" }}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Desktop tabel */}
      <div className="desktop-table" style={{ overflowX: "auto" }}>
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
                <tr key={h.ticker ?? i} className="hov" onClick={() => onSelectHolding(h)}
                  style={{ borderTop: "1px solid #0F1C2E", background: selectedTicker === h.ticker ? "#131B2E" : "transparent" }}>
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

      {/* Mobiele kaartweergave */}
      <div className="mobile-cards">
        {sorted.map((h, i) => {
          const rd = h.raw_data || {};
          const ma200dist = rd.ma200 ? ((h.current_price - rd.ma200) / rd.ma200 * 100).toFixed(1) : null;
          return (
            <div key={h.ticker ?? i} onClick={() => onSelectHolding(h)}
              style={{ background: selectedTicker === h.ticker ? "#131B2E" : "#060C18", border: `1px solid ${selectedTicker === h.ticker ? "#1E3A5F" : "#0F1C2E"}`, borderRadius: 10, padding: 14, cursor: "pointer" }}>

              {/* Rij 1: ticker + naam + signaal */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <span style={{ fontFamily: "'DM Mono'", fontWeight: 700, fontSize: 15, color: "#93C5FD" }}>{h.ticker}</span>
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{h.name}</div>
                </div>
                <span className="badge" style={{ background: signalColor(h.signal)+"20", color: signalColor(h.signal), border: `1px solid ${signalColor(h.signal)}40`, flexShrink: 0 }}>{h.signal}</span>
              </div>

              {/* Rij 2: score balk */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <div style={{ flex: 1, height: 6, borderRadius: 3, background: "#1E2D45", overflow: "hidden" }}>
                  <div style={{ width: `${h.total_score}%`, height: "100%", background: scoreColor(h.total_score), borderRadius: 3 }} />
                </div>
                <span style={{ fontFamily: "'DM Mono'", fontSize: 14, color: scoreColor(h.total_score), fontWeight: 800, minWidth: 36, textAlign: "right" }}>{h.total_score}</span>
              </div>

              {/* Rij 3: data grid 3×2 */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "6px 10px" }}>
                {[
                  ["Koers",       fmt(h.current_price, h.currency), "#94A3B8"],
                  ["ETF %",       `${(h.etf_weight * 100).toFixed(2)}%`, "#64748B"],
                  ["RSI dag",     rd.rsi_daily?.toFixed(1) ?? "—", rd.rsi_daily < 30 ? "#22C55E" : rd.rsi_daily > 70 ? "#EF4444" : "#94A3B8"],
                  ["PEG",         rd.peg_ratio?.toFixed(2) ?? "—", rd.peg_ratio < 1 ? "#22C55E" : rd.peg_ratio > 2 ? "#EF4444" : "#94A3B8"],
                  ["Fwd P/E",     rd.forward_pe?.toFixed(1) ?? "—", "#94A3B8"],
                  ["Afst. MA200", ma200dist ? `+${ma200dist}%` : "—", ma200dist && parseFloat(ma200dist) < 5 ? "#22C55E" : ma200dist && parseFloat(ma200dist) > 30 ? "#EF4444" : "#94A3B8"],
                ].map(([label, value, color]) => (
                  <div key={label}>
                    <div style={{ fontSize: 9, color: "#475569", fontFamily: "'DM Mono'", letterSpacing: "0.05em", marginBottom: 2 }}>{label.toUpperCase()}</div>
                    <div style={{ fontSize: 12, fontFamily: "'DM Mono'", color, fontWeight: 600 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Foutmelding voor niet-beschikbare tickers */}
      {failed.length > 0 && (
        <div style={{ marginTop: 10, padding: "10px 14px", background: "#1A0A0A", border: "1px solid #3B1010", borderRadius: 8, fontSize: 11, color: "#F87171" }}>
          Niet beschikbaar: {failed.map(h => h.ticker || "?").join(", ")} — {failed[0]?.error}
        </div>
      )}
    </div>
  );
}
