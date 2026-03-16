import { useState, useEffect } from "react";
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { API_BASE } from "../constants";

// EOD bereiken: label → aantal handelsdagen
const EOD_RANGES = {
  "1M":  21,
  "3M":  63,
  "6M":  126,
  "1J":  252,
  "3J":  756,
  "5J":  1260,
  "10J": 2520,
  "30J": 7560,
};

// Koersgrafiek (ComposedChart) voor een geselecteerd aandeel
// Props: ticker (string), name (string), currency (string), priceHistory (array), isHistoricalMode (boolean)
export default function PriceChart({ ticker, name, currency, priceHistory, isHistoricalMode = false }) {
  const [chartRange, setChartRange]           = useState("1J");
  const [showIntraday, setShowIntraday]       = useState(false);
  const [intradayData, setIntradayData]       = useState([]);
  const [intradayLoading, setIntradayLoading] = useState(false);
  const [showMA, setShowMA]                   = useState(true);
  const [showRSI, setShowRSI]                 = useState(true);

  // Reset intraday bij wisselen van aandeel
  useEffect(() => {
    setIntradayData([]);
    setShowIntraday(false);
  }, [ticker]);

  const handleIntradayToggle = () => {
    const next = !showIntraday;
    setShowIntraday(next);
    if (next && intradayData.length === 0) {
      setIntradayLoading(true);
      fetch(`${API_BASE}/intraday/${ticker}?interval=4hour&days=60`)
        .then(r => r.json())
        .then(d => setIntradayData(d.data || []))
        .catch(() => setIntradayData([]))
        .finally(() => setIntradayLoading(false));
    }
  };

  // Selecteer databron en pas bereik toe
  const sliced = showIntraday
    ? intradayData
    : priceHistory.slice(-(EOD_RANGES[chartRange] ?? 252));

  const firstClose = sliced[0]?.close;
  const lastClose  = sliced[sliced.length - 1]?.close;
  const change     = firstClose ? ((lastClose - firstClose) / firstClose * 100) : null;
  const isPositive = change == null || change >= 0;
  const lineColor  = isPositive ? "#22C55E" : "#EF4444";

  // MA-data beschikbaar (onafhankelijk van showMA, voor knopzichtbaarheid)
  const ma20Exists  = !showIntraday && sliced.some(p => p.ma20  != null);
  const ma200Exists = !showIntraday && sliced.some(p => p.ma200 != null);
  // MA-lijnen alleen tekenen als data beschikbaar én MA aan staat
  const hasMA20  = showMA && ma20Exists;
  const hasMA200 = showMA && ma200Exists;

  // RSI-data beschikbaar
  const rsiExists = sliced.some(p => p.rsi != null);

  const labelInterval = Math.max(1, Math.floor(sliced.length / 6));
  const chartData = sliced.map((p, i) => ({
    ...p,
    label: i % labelInterval === 0
      ? new Date(p.date).toLocaleDateString("nl-NL", { day: "2-digit", month: "short" })
      : undefined,
  }));

  const tickFormatter = v =>
    currency === "KRW" ? `₩${(v / 1000).toFixed(0)}k` : `$${v.toFixed(0)}`;

  const btnStyle = (active, color = lineColor) => ({
    padding: "4px 10px",
    borderRadius: 6,
    fontSize: 11,
    fontFamily: "'DM Mono'",
    cursor: "pointer",
    background:   active ? color + "22"  : "transparent",
    border:       `1px solid ${active ? color + "88" : "#1E2D45"}`,
    color:        active ? color         : "#475569",
    fontWeight:   active ? 700           : 400,
  });

  // RSI-kleur op basis van waarde (overbought/oversold)
  const rsiColor = (v) => v >= 70 ? "#EF4444" : v <= 30 ? "#22C55E" : "#38BDF8";
  const lastRsi  = [...chartData].reverse().find(p => p.rsi != null)?.rsi;

  return (
    <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
      {/* Header: ticker info + knoppen */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div>
          <span style={{ fontFamily: "'DM Mono'", fontSize: 15, fontWeight: 700, color: "#E2E8F0" }}>{ticker}</span>
          <span style={{ fontSize: 12, color: "#64748B", marginLeft: 10 }}>{name}</span>
          {change != null && (
            <span style={{ marginLeft: 12, fontSize: 12, fontFamily: "'DM Mono'", color: lineColor, fontWeight: 600 }}>
              {isPositive ? "+" : ""}{change.toFixed(2)}%
              {showIntraday && <span style={{ fontSize: 10, color: "#475569", marginLeft: 4 }}>4u</span>}
            </span>
          )}
        </div>

        {/* Knoppen-rij */}
        <div className="chart-btns" style={{ display: "flex", gap: 4, flexWrap: "wrap", alignItems: "center" }}>
          {/* Intraday toggle (alleen in live modus) */}
          {!isHistoricalMode && (
            <>
              <button onClick={handleIntradayToggle} style={btnStyle(showIntraday, "#8B5CF6")}>
                {intradayLoading ? "⏳" : "4U"}
              </button>
              <div style={{ width: 1, height: 16, background: "#1E2D45", margin: "0 2px" }} />
            </>
          )}

          {/* EOD bereiksknoppen */}
          {Object.keys(EOD_RANGES).map(r => (
            <button key={r}
              onClick={() => { setShowIntraday(false); setChartRange(r); }}
              style={btnStyle(!showIntraday && chartRange === r)}>
              {r}
            </button>
          ))}

          {/* MA toggle (alleen bij EOD, zichtbaar als data beschikbaar) */}
          {(ma20Exists || ma200Exists) && (
            <>
              <div style={{ width: 1, height: 16, background: "#1E2D45", margin: "0 2px" }} />
              <button onClick={() => setShowMA(p => !p)} style={btnStyle(showMA, "#F59E0B")}>
                MA
              </button>
            </>
          )}

          {/* RSI toggle */}
          {rsiExists && (
            <button onClick={() => setShowRSI(p => !p)} style={btnStyle(showRSI, "#38BDF8")}>
              RSI
            </button>
          )}
        </div>
      </div>

      {/* Koersgrafiek */}
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={lineColor} stopOpacity={0.18} />
              <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E2D45" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 9, fill: "#475569", fontFamily: "'DM Mono'" }}
            tickLine={false} axisLine={false} interval={0}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 9, fill: "#475569", fontFamily: "'DM Mono'" }}
            tickLine={false} axisLine={false} width={56}
            tickFormatter={tickFormatter}
          />
          <Tooltip
            contentStyle={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 8, fontSize: 11, fontFamily: "'DM Mono'" }}
            labelFormatter={(_l, payload) => payload?.[0]?.payload?.date ?? ""}
            formatter={(v, key) => {
              const labels = { close: "Koers", ma20: "MA20", ma200: "MA200" };
              const fmtV = currency === "KRW" ? `₩${Number(v).toLocaleString()}` : `$${Number(v).toFixed(2)}`;
              return [fmtV, labels[key] ?? key];
            }}
          />
          <Area
            type="monotone" dataKey="close"
            stroke={lineColor} strokeWidth={2}
            fill="url(#chartGrad)" dot={false} activeDot={{ r: 4 }}
          />
          {hasMA20 && (
            <Line
              type="monotone" dataKey="ma20"
              stroke="#F59E0B" strokeWidth={1.5}
              dot={false} strokeDasharray="5 3"
              activeDot={false} connectNulls
            />
          )}
          {hasMA200 && (
            <Line
              type="monotone" dataKey="ma200"
              stroke="#8B5CF6" strokeWidth={1.5}
              dot={false} strokeDasharray="3 2"
              activeDot={false} connectNulls
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* MA legenda */}
      {!showIntraday && (hasMA20 || hasMA200) && showMA && (
        <div style={{ display: "flex", gap: 14, marginTop: 6, fontSize: 10, color: "#475569", fontFamily: "'DM Mono'" }}>
          {hasMA20  && <span><span style={{ color: "#F59E0B", marginRight: 4 }}>━━</span>MA20</span>}
          {hasMA200 && <span><span style={{ color: "#8B5CF6", marginRight: 4 }}>━━</span>MA200</span>}
        </div>
      )}

      {/* RSI paneel */}
      {showRSI && rsiExists && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: "#475569", fontFamily: "'DM Mono'" }}>RSI (14)</span>
            {lastRsi != null && (
              <span style={{ fontSize: 11, fontFamily: "'DM Mono'", fontWeight: 700, color: rsiColor(lastRsi) }}>
                {lastRsi.toFixed(1)}
                {lastRsi >= 70 && <span style={{ marginLeft: 4, fontSize: 10 }}>overbought</span>}
                {lastRsi <= 30 && <span style={{ marginLeft: 4, fontSize: 10 }}>oversold</span>}
              </span>
            )}
          </div>
          <ResponsiveContainer width="100%" height={80}>
            <ComposedChart data={chartData} margin={{ top: 2, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2D45" vertical={false} />
              <XAxis dataKey="label" hide />
              <YAxis
                domain={[0, 100]} ticks={[30, 50, 70]}
                tick={{ fontSize: 9, fill: "#475569", fontFamily: "'DM Mono'" }}
                tickLine={false} axisLine={false} width={56}
              />
              <Tooltip
                contentStyle={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 8, fontSize: 11, fontFamily: "'DM Mono'" }}
                labelFormatter={(_l, payload) => payload?.[0]?.payload?.date ?? ""}
                formatter={(v) => [Number(v).toFixed(1), "RSI"]}
              />
              <ReferenceLine y={70} stroke="#EF444444" strokeDasharray="3 2" />
              <ReferenceLine y={30} stroke="#22C55E44" strokeDasharray="3 2" />
              <ReferenceLine y={50} stroke="#1E2D45" strokeDasharray="2 2" />
              <Line
                type="monotone" dataKey="rsi"
                stroke="#38BDF8" strokeWidth={1.5}
                dot={false} activeDot={{ r: 3 }} connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Intraday melding bij lege data */}
      {showIntraday && !intradayLoading && intradayData.length === 0 && (
        <div style={{ textAlign: "center", fontSize: 11, color: "#475569", marginTop: 8, fontFamily: "'DM Mono'" }}>
          Geen intraday data beschikbaar (vereist Premium + actieve markt)
        </div>
      )}
    </div>
  );
}
