// Tabnavigatie balk
// Props: activeTab (string), onTabChange (fn), selectedTicker (string|null)
export default function TabNav({ activeTab, onTabChange, selectedTicker }) {
  const tabs = [
    ["overview", "📋 Holdings"],
    ["weights",  "🎚️ Gewichten"],
    ["detail",   selectedTicker ? `🔍 ${selectedTicker}` : "🔍 Detail"],
  ];

  return (
    <div style={{ display: "flex", borderBottom: "1px solid #1E2D45", marginBottom: 16 }}>
      {tabs.map(([id, label]) => (
        <button key={id} className={`tab ${activeTab === id ? "on" : ""}`} onClick={() => onTabChange(id)}
          style={{ padding: "10px 18px", color: activeTab === id ? "#93C5FD" : "#64748B", fontSize: 13, fontWeight: 500, fontFamily: "'DM Sans'" }}>
          {label}
        </button>
      ))}
    </div>
  );
}
