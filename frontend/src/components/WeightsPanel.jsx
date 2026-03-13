import { signalColor } from "../helpers";
import { INDICATOR_LABELS } from "../constants";

// Gewichtenpaneel met sliders voor timeframes en indicatoren + live score preview
// Props: weights, setWeights, indWeights, setIndWeights, liveScore, liveSignal
export default function WeightsPanel({ weights, setWeights, indWeights, setIndWeights, liveScore, liveSignal }) {
  const timeframeLabels = { daily: "Dagelijks", weekly: "Wekelijks", monthly: "Maandelijks" };
  const totalTimeframe = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

      {/* Timeframe gewichten */}
      <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#93C5FD" }}>⏱ Timeframe Gewichten</div>
        {Object.entries(weights).map(([key, val]) => (
          <div key={key} style={{ marginBottom: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: "#94A3B8" }}>{timeframeLabels[key] ?? key}</span>
              <span style={{ fontFamily: "'DM Mono'", fontSize: 12, color: "#60A5FA", fontWeight: 600 }}>{(val * 100).toFixed(0)}%</span>
            </div>
            <input type="range" className="slider" min={0} max={100} value={Math.round(val * 100)}
              style={{ background: `linear-gradient(to right, #3B82F6 ${val*100}%, #1E2D45 ${val*100}%)` }}
              onChange={e => setWeights(prev => ({ ...prev, [key]: parseInt(e.target.value) / 100 }))} />
          </div>
        ))}
        <div style={{ padding: "8px 10px", background: "#060C18", borderRadius: 6, fontSize: 11, color: "#475569", fontFamily: "'DM Mono'" }}>
          Totaal: {(totalTimeframe * 100).toFixed(0)}%
          {Math.abs(totalTimeframe - 1) > 0.05 && <span style={{ color: "#EF4444" }}> ⚠ moet 100% zijn</span>}
        </div>
      </div>

      {/* Indicator gewichten */}
      <div style={{ background: "#0D1321", border: "1px solid #1E2D45", borderRadius: 12, padding: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#93C5FD" }}>📊 Indicator Gewichten</div>
        {Object.entries(indWeights).map(([key, val]) => (
          <div key={key} style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: "#94A3B8" }}>{INDICATOR_LABELS[key] || key}</span>
              <span style={{ fontFamily: "'DM Mono'", fontSize: 11, color: "#A78BFA" }}>{(val * 100).toFixed(0)}%</span>
            </div>
            <input type="range" className="slider" min={0} max={40} value={Math.round(val * 100)}
              style={{ background: `linear-gradient(to right, #8B5CF6 ${val*100/0.4}%, #1E2D45 ${val*100/0.4}%)` }}
              onChange={e => setIndWeights(prev => ({ ...prev, [key]: parseInt(e.target.value) / 100 }))} />
          </div>
        ))}
      </div>

      {/* Live score preview */}
      <div style={{ gridColumn: "1 / -1", background: "#0D1321", border: `2px solid ${signalColor(liveSignal)}44`, borderRadius: 12, padding: 16, display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ fontSize: 36, fontWeight: 800, color: signalColor(liveSignal), fontFamily: "'DM Mono'" }}>{liveScore}</div>
        <div>
          <div style={{ fontWeight: 600, color: signalColor(liveSignal) }}>Live ETF Score preview</div>
          <div style={{ fontSize: 12, color: "#475569" }}>Past mee terwijl je de sliders versleept</div>
        </div>
        <div style={{ marginLeft: "auto" }}>
          <span className="badge" style={{ background: signalColor(liveSignal)+"20", color: signalColor(liveSignal), border: `1px solid ${signalColor(liveSignal)}44`, fontSize: 13, padding: "6px 18px" }}>{liveSignal}</span>
        </div>
      </div>
    </div>
  );
}
