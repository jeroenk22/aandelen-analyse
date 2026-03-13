import { signalColor, scoreColor, fmt, signalDotColor } from "../helpers";
import { INDICATOR_LABELS } from "../constants";
import IndicatorTooltip from "./IndicatorTooltip";
import PriceChart from "./PriceChart";

// OHLCV-tabel voor dagkoersen
function OhlcTable({ ohlc, currency, isHistoricalMode }) {
  const fmtVal = (v) => v == null ? "—" : currency === "KRW" ? `₩${Number(v).toLocaleString("nl-NL")}` : `$${Number(v).toFixed(2)}`;
  const fmtVol = (v) => v == null ? "—" : Number(v).toLocaleString("nl-NL");
  const dateStr = new Date(ohlc.date).toLocaleDateString("nl-NL", { day: "numeric", month: "long", year: "numeric" });

  const ohlcItems = [
    { label: "Open",     value: fmtVal(ohlc.open),      color: "#E2E8F0" },
    { label: "High",     value: fmtVal(ohlc.high),      color: "#22C55E" },
    { label: "Low",      value: fmtVal(ohlc.low),       color: "#EF4444" },
    { label: "Close",    value: fmtVal(ohlc.close),     color: "#93C5FD" },
    ...(ohlc.adj_close != null ? [{ label: "Adj Close", value: fmtVal(ohlc.adj_close), color: "#94A3B8" }] : []),
    { label: "Volume",   value: fmtVol(ohlc.volume),    color: "#64748B" },
  ];

  return (
    <div style={{ marginBottom: 16, background: "#060C18", borderRadius: 10, border: isHistoricalMode ? "1px solid #F59E0B44" : "1px solid #1E2D45", overflow: "hidden" }}>
      <div style={{ padding: "8px 14px", borderBottom: "1px solid #1E2D45", display: "flex", alignItems: "center", gap: 8 }}>
        {isHistoricalMode
          ? <span style={{ fontSize: 11, color: "#F59E0B", fontFamily: "'DM Mono'", fontWeight: 600 }}>🕐 HISTORISCHE DATA</span>
          : <span style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono'", fontWeight: 600 }}>DAGKOERSEN</span>
        }
        <span style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono'" }}>· {dateStr}</span>
      </div>

      {/* Desktop: tabelweergave */}
      <div className="ohlc-desktop">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#060C18" }}>
              {ohlcItems.map(item => (
                <th key={item.label} style={{ padding: "7px 14px", textAlign: "right", fontSize: 10, color: "#475569", fontWeight: 600, fontFamily: "'DM Mono'", letterSpacing: "0.06em" }}>{item.label.toUpperCase()}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {ohlcItems.map(item => (
                <td key={item.label} style={{ padding: "9px 14px", textAlign: "right", fontFamily: "'DM Mono'", fontSize: 13, color: item.color, fontWeight: item.label === "Close" ? 700 : 400 }}>{item.value}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {/* Mobiel: kaart-raster */}
      <div className="ohlc-mobile">
        {ohlcItems.map(item => (
          <div key={item.label}>
            <div style={{ fontSize: 9, color: "#475569", fontFamily: "'DM Mono'", letterSpacing: "0.05em", marginBottom: 3 }}>{item.label.toUpperCase()}</div>
            <div style={{ fontSize: 13, fontFamily: "'DM Mono'", color: item.color, fontWeight: item.label === "Close" ? 700 : 500 }}>{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Timeframe score kaartjes (dag/week/maand)
function TimeframeScores({ scores }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
      {[["Dagelijks","daily"],["Wekelijks","weekly"],["Maandelijks","monthly"]].map(([label, key]) => (
        <div key={key} style={{ background: "#060C18", borderRadius: 8, padding: "10px 12px", textAlign: "center" }}>
          <div style={{ fontSize: 10, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 4 }}>{label.toUpperCase()}</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: scoreColor(scores?.[key]), fontFamily: "'DM Mono'" }}>{scores?.[key] ?? "—"}</div>
        </div>
      ))}
    </div>
  );
}

// Raw data kaart met 6 metrics
function RawDataCard({ holding }) {
  const rd = holding.raw_data || {};
  const metrics = [
    ["RSI (dag)",    rd.rsi_daily?.toFixed(1),    rd.rsi_daily < 30 ? "#22C55E" : rd.rsi_daily > 70 ? "#EF4444" : "#94A3B8"],
    ["PEG Ratio",    rd.peg_ratio?.toFixed(2),    rd.peg_ratio < 1 ? "#22C55E" : rd.peg_ratio > 2 ? "#EF4444" : "#94A3B8"],
    ["Forward P/E",  rd.forward_pe?.toFixed(1),   "#94A3B8"],
    ["Momentum 1m",  rd.momentum_1m != null ? `${rd.momentum_1m > 0 ? "+" : ""}${rd.momentum_1m.toFixed(1)}%` : "—", rd.momentum_1m > 0 ? "#22C55E" : "#EF4444"],
    ["MA200",        fmt(rd.ma200, holding.currency), "#94A3B8"],
    ["ETF Weging",   `${(holding.etf_weight * 100).toFixed(2)}%`, "#60A5FA"],
  ];

  return (
    <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
      <div style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 12 }}>RAW DATA</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {metrics.map(([label, val, color]) => (
          <div key={label} style={{ background: "#060C18", borderRadius: 6, padding: "8px 12px" }}>
            <div style={{ fontSize: 10, color: "#475569", marginBottom: 2, fontFamily: "'DM Mono'" }}>{label}</div>
            <div style={{ fontSize: 14, fontWeight: 600, color, fontFamily: "'DM Mono'" }}>{val ?? "—"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Indicator scores lijst met voortgangsbalkjes en tooltips
function IndicatorScores({ holding }) {
  const FUNDAMENTALS = new Set(["forward_pe", "peg", "price_fcf", "dcf_discount"]);

  return (
    <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
      <div style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 16 }}>INDICATOR SCORES (0 – 100)</div>
      {Object.entries(holding.indicator_scores ?? {}).map(([key, val]) => {
        const interp     = holding.interpretations?.[key];
        const indLabel   = interp?.indicator_label || INDICATOR_LABELS[key] || key;
        const desc       = interp?.label;
        const tooltip    = interp?.tooltip;
        const dotColor   = signalDotColor(interp?.signal);
        const unavailable = holding.raw_data?.fundamentals_unavailable && FUNDAMENTALS.has(key);

        if (unavailable) {
          return (
            <div key={key} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4, gap: 8 }}>
                <span style={{ fontSize: 11, color: "#64748B", display: "inline-flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#334155", flexShrink: 0, display: "inline-block" }} />
                  {indLabel}
                </span>
                <span style={{ fontSize: 10, color: "#92400E", fontStyle: "italic", flexShrink: 0, background: "#451A0320", padding: "2px 8px", borderRadius: 4, border: "1px solid #92400E44" }}>
                  Niet beschikbaar in Starter pakket
                </span>
              </div>
              <div style={{ height: 5, borderRadius: 3, background: "#1E2D45" }} />
            </div>
          );
        }

        return (
          <div key={key} style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, alignItems: "flex-start", gap: 8 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <IndicatorTooltip tooltip={tooltip}>
                  <span style={{ fontSize: 11, color: "#94A3B8", display: "inline-flex", alignItems: "center", gap: 5, cursor: tooltip ? "help" : "default", flexWrap: "wrap" }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: dotColor, flexShrink: 0, display: "inline-block" }} />
                    {indLabel}
                    {interp?.signal && interp.signal !== "NEUTRAAL" && (
                      <span style={{ fontSize: 9, fontWeight: 700, fontFamily: "'DM Mono'", padding: "1px 6px", borderRadius: 4, background: dotColor + "22", color: dotColor, border: `1px solid ${dotColor}44`, letterSpacing: "0.04em" }}>
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

      {/* Totaalscore */}
      <div style={{ marginTop: 20, padding: 12, background: "#060C18", borderRadius: 8 }}>
        <span style={{ fontSize: 11, color: "#94A3B8" }}>Totaal score: </span>
        <span style={{ color: scoreColor(holding.total_score), fontWeight: 800, fontSize: 18, fontFamily: "'DM Mono'" }}>{holding.total_score}</span>
        <span style={{ color: "#475569", fontSize: 11 }}> / 100</span>
      </div>
    </div>
  );
}

// Volledige detail-tab voor een geselecteerd aandeel
// Props: holding (object), isHistoricalMode (boolean)
export default function HoldingDetail({ holding, isHistoricalMode }) {
  if (!holding) {
    return (
      <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 40, textAlign: "center", color: "#475569" }}>
        ← Klik op een aandeel in de Holdings tab voor detail-analyse
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Koersgrafiek */}
      {holding.raw_data?.price_history?.length > 0 && (
        <PriceChart
          ticker={holding.ticker}
          name={holding.name}
          currency={holding.currency}
          priceHistory={holding.raw_data.price_history}
        />
      )}

      <div className="detail-grid">
        {/* Linker kolom: holding-info, OHLCV, timeframe scores, raw data */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Holding header */}
          <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
              <div>
                <div style={{ fontFamily: "'DM Mono'", fontSize: 24, fontWeight: 700, color: "#93C5FD" }}>{holding.ticker}</div>
                <div style={{ fontSize: 12, color: "#64748B" }}>{holding.name}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "'DM Mono'" }}>{fmt(holding.current_price, holding.currency)}</div>
                <span className="badge" style={{ background: signalColor(holding.signal)+"20", color: signalColor(holding.signal), border: `1px solid ${signalColor(holding.signal)}44`, marginTop: 4 }}>{holding.signal}</span>
              </div>
            </div>
            {holding.raw_data?.ohlc_day && (
              <OhlcTable ohlc={holding.raw_data.ohlc_day} currency={holding.currency} isHistoricalMode={isHistoricalMode} />
            )}
            <TimeframeScores scores={holding.scores_by_timeframe} />
          </div>

          <RawDataCard holding={holding} />
        </div>

        {/* Rechter kolom: indicator scores */}
        <IndicatorScores holding={holding} />
      </div>
    </div>
  );
}
