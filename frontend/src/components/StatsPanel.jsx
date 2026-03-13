import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from "recharts";
import { MOCK_HISTORY } from "../constants";

// Vier statistiek-kaarten en een gesimuleerde scoregrafiek van 60 dagen
// Props: holdings (array)
export default function StatsPanel({ holdings }) {
  const stats = [
    { label: "Koop signalen",  value: holdings.filter(h => h.signal === "KOOP").length,     color: "#22C55E" },
    { label: "Neutraal",       value: holdings.filter(h => h.signal === "NEUTRAAL").length, color: "#F59E0B" },
    { label: "Uitstap",        value: holdings.filter(h => h.signal === "UITSTAP").length,  color: "#EF4444" },
    { label: "Hoogste score",  value: Math.max(...holdings.map(h => h.total_score)).toFixed(1), color: "#60A5FA", icon: "🏆" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Statistiek kaarten */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
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

      {/* 60-daagse score history */}
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
  );
}
