import { RadialBarChart, RadialBar, ResponsiveContainer } from "recharts";
import { signalColor } from "../helpers";

// Radiale gauge die de ETF totaalscore toont
// Props: score (number), signal (string), holdingsAnalyzed, holdingsTotal
export default function ScoreGauge({ score, signal, holdingsAnalyzed, holdingsTotal }) {
  const color = signalColor(signal);
  return (
    <div style={{ background: "#0D1321", border: `1px solid ${color}33`, borderRadius: 14, padding: 24, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", boxSizing: "border-box" }}>
      <div style={{ fontSize: 10, color: "#475569", fontFamily: "'DM Mono'", marginBottom: 12, letterSpacing: "0.1em" }}>ETF TOTAAL SCORE</div>
      <div style={{ position: "relative", width: 155, height: 155 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart cx="50%" cy="50%" innerRadius="78%" outerRadius="92%" startAngle={225} endAngle={-45}
            data={[{ value: score, fill: color }]}>
            <RadialBar dataKey="value" cornerRadius={8} background={{ fill: "#1E2D45" }} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", textAlign: "center" }}>
          <div style={{ fontSize: 38, fontWeight: 800, color, lineHeight: 1, fontFamily: "'DM Mono'" }}>{score}</div>
          <div style={{ fontSize: 10, color: "#64748B", marginTop: 2 }}>/ 100</div>
        </div>
      </div>
      <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 6 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
        <span style={{ fontWeight: 700, fontSize: 15, color }}>{signal}</span>
      </div>
      <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>{holdingsAnalyzed} van {holdingsTotal} aandelen</div>
    </div>
  );
}
