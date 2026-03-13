// ─── HELPERS ──────────────────────────────────────────────────────────────────

// Kleur op basis van signaal (KOOP/INSTAP = groen, UITSTAP = rood, anders geel)
export const signalColor = (s) =>
  s === "KOOP" || s === "INSTAP" ? "#22C55E" : s === "UITSTAP" ? "#EF4444" : "#F59E0B";

// Kleur op basis van score (>=65 groen, >=45 geel, anders rood)
export const scoreColor = (s) =>
  s >= 65 ? "#22C55E" : s >= 45 ? "#F59E0B" : "#EF4444";

// Prijs formatteren met valuta-symbool
export const fmt = (price, currency) =>
  price == null ? "—" : currency === "KRW" ? `₩${price.toLocaleString()}` : `$${price.toFixed(2)}`;

// Kleur voor indicator-signaal dots
export const signalDotColor = (s) =>
  s === "OVERSOLD" || s === "BULLISH"   ? "#22C55E" :
  s === "OVERBOUGHT" || s === "BEARISH" ? "#EF4444" :
  s === "DICHTBIJ"                      ? "#F59E0B" : "#475569";
