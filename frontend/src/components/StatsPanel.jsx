import { useMemo } from "react";
import IndicatorTooltip from "./IndicatorTooltip";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from "recharts";

const LIJN_KLEUREN = ["#3B82F6", "#22C55E", "#F59E0B", "#A855F7", "#06B6D4", "#EF4444"];

// Vier statistiek-kaarten en 60-daagse genormaliseerde koersprestatie per holding
// Props: holdings (array)
export default function StatsPanel({ holdings }) {
  const stats = [
    { label: "Koop signalen",  value: holdings.filter(h => h.signal === "KOOP").length,     color: "#22C55E" },
    { label: "Neutraal",       value: holdings.filter(h => h.signal === "NEUTRAAL").length, color: "#F59E0B" },
    { label: "Uitstap",        value: holdings.filter(h => h.signal === "UITSTAP").length,  color: "#EF4444" },
    { label: "Hoogste score",  value: Math.max(...holdings.map(h => h.total_score)).toFixed(1), color: "#60A5FA", icon: "🏆" },
  ];

  // Bouw gecombineerde koersprestatie op uit price_history per holding
  const { chartData, geldigeHoldings } = useMemo(() => {
    const geldig = holdings.filter(h => h.raw_data?.price_history?.length >= 2);
    if (geldig.length === 0) return { chartData: [], geldigeHoldings: [] };

    // Neem laatste 60 datapunten per holding, normaliseer op 100 bij eerste punt
    const normsPerTicker = {};
    geldig.forEach(h => {
      const slice = h.raw_data.price_history.slice(-60);
      const startKoers = slice[0]?.close;
      if (!startKoers) return;
      normsPerTicker[h.ticker] = {};
      slice.forEach(p => {
        normsPerTicker[h.ticker][p.date] = Math.round((p.close / startKoers) * 1000) / 10;
      });
    });

    // Alle unieke datums gesorteerd
    const alleDatums = [...new Set(
      geldig.flatMap(h => h.raw_data.price_history.slice(-60).map(p => p.date))
    )].sort();

    const data = alleDatums.map(datum => {
      const entry = { datum: datum.slice(5) }; // MM-DD
      geldig.forEach(h => {
        const waarde = normsPerTicker[h.ticker]?.[datum];
        if (waarde !== undefined) entry[h.ticker] = waarde;
      });
      return entry;
    });

    return { chartData: data, geldigeHoldings: geldig };
  }, [holdings]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Statistiek kaarten */}
      <div className="stats-grid">
        {stats.map((s, i) => (
          <div key={i} style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 10, padding: "12px 14px" }}>
            <div style={{ fontSize: 10, color: "#475569", marginBottom: 4, fontFamily: "'DM Mono'" }}>{s.label.toUpperCase()}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {s.icon
                ? <span style={{ fontSize: 20 }}>{s.icon}</span>
                : <span style={{ display: "inline-block", width: 16, height: 16, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
              }
              <span style={{ fontSize: 26, fontWeight: 800, color: s.color, fontFamily: "'DM Mono'" }}>{s.value}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 60-daagse koersprestatie (genormaliseerd op 100) */}
      <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 10, padding: "14px 16px", flex: 1 }}>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px 12px", marginBottom: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
            <span style={{ fontSize: 10, color: "#475569", fontFamily: "'DM Mono'", letterSpacing: "0.08em" }}>
              60-DAAGSE KOERSPRESTATIE (GENORMALISEERD = 100)
            </span>
            <IndicatorTooltip
              tooltip="Elke lijn start op 100 op dag 1. Een waarde van 110 betekent +10% ten opzichte van het startpunt 60 handelsdagen geleden. Dit maakt aandelen met verschillende koersen onderling vergelijkbaar."
              direction="down"
            >
              <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 14, height: 14, borderRadius: "50%", border: "1px solid #334155", color: "#475569", fontSize: 9, fontFamily: "'DM Mono'", cursor: "pointer", flexShrink: 0 }}>?</span>
            </IndicatorTooltip>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 10px" }}>
            {geldigeHoldings.map((h, i) => (
              <div key={h.ticker} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 16, height: 2, background: LIJN_KLEUREN[i % LIJN_KLEUREN.length], display: "inline-block", borderRadius: 1 }} />
                <span style={{ fontSize: 9, color: "#94A3B8", fontFamily: "'DM Mono'" }}>{h.ticker}</span>
              </div>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={110}>
          <LineChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E2D45" vertical={false} />
            <XAxis dataKey="datum" tick={{ fontSize: 9, fill: "#475569", fontFamily: "'DM Mono'" }} tickLine={false} axisLine={false} interval={9} />
            <YAxis domain={["auto", "auto"]} tickFormatter={v => Math.round(v)} tick={{ fontSize: 9, fill: "#475569" }} tickLine={false} axisLine={false} width={28} />
            <ReferenceLine y={100} stroke="#64748B" strokeDasharray="4 4" strokeOpacity={0.6} />
            <Tooltip
              contentStyle={{ background: "#131B2E", border: "1px solid #1E2D45", borderRadius: 6, fontSize: 11, fontFamily: "'DM Mono'" }}
              formatter={(v, name) => [`${v.toFixed(1)}`, name]}
              labelFormatter={(l) => l}
            />
            {geldigeHoldings.map((h, i) => (
              <Line
                key={h.ticker}
                type="monotone"
                dataKey={h.ticker}
                stroke={LIJN_KLEUREN[i % LIJN_KLEUREN.length]}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
