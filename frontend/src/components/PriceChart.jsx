import { useState } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const RANGES = { "1M": 21, "3M": 63, "6M": 126, "1J": 252, "3J": 756, "5J": 1260 };

// Koersgrafiek (AreaChart) voor een geselecteerd aandeel
// Props: ticker (string), name (string), currency (string), priceHistory (array)
export default function PriceChart({ ticker, name, currency, priceHistory }) {
  const [chartRange, setChartRange] = useState("1J");

  const days = RANGES[chartRange] ?? 252;
  const sliced = priceHistory.slice(-days);
  const firstClose = sliced[0]?.close;
  const lastClose = sliced[sliced.length - 1]?.close;
  const change = firstClose ? ((lastClose - firstClose) / firstClose * 100) : null;
  const isPositive = change == null || change >= 0;
  const lineColor = isPositive ? "#22C55E" : "#EF4444";

  const labelInterval = Math.max(1, Math.floor(sliced.length / 6));
  const chartData = sliced.map((p, i) => ({
    ...p,
    label: i % labelInterval === 0
      ? new Date(p.date).toLocaleDateString("nl-NL", { day: "2-digit", month: "short" })
      : undefined,
  }));

  return (
    <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div>
          <span style={{ fontFamily: "'DM Mono'", fontSize: 15, fontWeight: 700, color: "#E2E8F0" }}>{ticker}</span>
          <span style={{ fontSize: 12, color: "#64748B", marginLeft: 10 }}>{name}</span>
          {change != null && (
            <span style={{ marginLeft: 12, fontSize: 12, fontFamily: "'DM Mono'", color: lineColor, fontWeight: 600 }}>
              {isPositive ? "+" : ""}{change.toFixed(2)}%
            </span>
          )}
        </div>
        {/* Bereiksknoppen */}
        <div style={{ display: "flex", gap: 4 }}>
          {Object.keys(RANGES).map(r => (
            <button key={r} onClick={() => setChartRange(r)}
              style={{ padding: "4px 10px", borderRadius: 6, fontSize: 11, fontFamily: "'DM Mono'", cursor: "pointer",
                background: chartRange === r ? lineColor + "22" : "transparent",
                border: `1px solid ${chartRange === r ? lineColor + "88" : "#1E2D45"}`,
                color: chartRange === r ? lineColor : "#475569", fontWeight: chartRange === r ? 700 : 400 }}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={lineColor} stopOpacity={0.18} />
              <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E2D45" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 9, fill: "#475569", fontFamily: "'DM Mono'" }} tickLine={false} axisLine={false} interval={0} />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 9, fill: "#475569", fontFamily: "'DM Mono'" }}
            tickLine={false} axisLine={false} width={52}
            tickFormatter={v => currency === "KRW" ? `₩${(v/1000).toFixed(0)}k` : `$${v.toFixed(0)}`}
          />
          <Tooltip
            contentStyle={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 8, fontSize: 11, fontFamily: "'DM Mono'" }}
            labelFormatter={(_l, payload) => payload?.[0]?.payload?.date ?? ""}
            formatter={v => [currency === "KRW" ? `₩${Number(v).toLocaleString()}` : `$${Number(v).toFixed(2)}`, "Slotkoers"]}
          />
          <Area type="monotone" dataKey="close" stroke={lineColor} strokeWidth={2} fill="url(#chartGrad)" dot={false} activeDot={{ r: 4 }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
