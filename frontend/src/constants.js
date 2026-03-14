// ─── CONFIG ───────────────────────────────────────────────────────────────────
export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8001";

export const INDICATOR_LABELS = {
  rsi: "RSI",
  rsi_daily: "RSI Dag", rsi_weekly: "RSI Week", rsi_monthly: "RSI Maand", rsi_intraday: "RSI 4u",
  rsi_divergence: "RSI Divergentie",
  rsi_divergence_daily: "RSI Div. Dag", rsi_divergence_weekly: "RSI Div. Week",
  rsi_divergence_monthly: "RSI Div. Maand", rsi_divergence_intraday: "RSI Div. 4u",
  ma20: "MA20",
  ma20_daily: "MA20 Dag", ma20_weekly: "MA20 Week", ma20_monthly: "MA20 Maand", ma20_intraday: "MA20 4u",
  ma200: "MA200",
  apz: "APZ",
  apz_daily: "APZ Dag", apz_weekly: "APZ Week", apz_monthly: "APZ Maand", apz_intraday: "APZ 4u",
  forward_pe: "Fwd P/E", peg: "PEG", price_fcf: "P/FCF",
  momentum: "Momentum", panic: "Paniek",
  analyst_target: "Analistendoelstelling",
  williams: "Williams %R",
  williams_daily: "Williams %R Dag", williams_weekly: "Williams %R Week", williams_monthly: "Williams %R Maand", williams_intraday: "Williams %R 4u",
  adx: "ADX",
  adx_daily: "ADX Dag", adx_weekly: "ADX Week", adx_monthly: "ADX Maand", adx_intraday: "ADX 4u",
};

export const MOCK_DATA = {
  summary: { etf_score: 61.4, etf_signal: "AFWACHTEN", holdings_analyzed: 10, holdings_total: 10 },
  generated_at: new Date().toISOString(),
  config: {
    timeframe_weights: { intraday: 0.15, daily: 0.25, weekly: 0.35, monthly: 0.25 },
    indicator_weights: { rsi: 0.11, ma20: 0.07, ma200: 0.06, forward_pe: 0.12, peg: 0.12, price_fcf: 0.09, momentum: 0.07, analyst_target: 0.08, panic: 0.05, rsi_divergence: 0.06, apz: 0.06, williams: 0.06, adx: 0.05 },
  },
  holdings: [
    { ticker: "NVDA",  name: "NVIDIA Corp",          current_price: 875.40,  currency: "USD", total_score: 72.3, signal: "KOOP",     etf_weight: 0.0454, scores_by_timeframe: { intraday: 73.2, daily: 74.1, weekly: 71.8, monthly: 70.9 }, indicator_scores: { rsi_daily: 42, rsi_weekly: 38, rsi_monthly: 45, rsi_intraday: 40, ma200: 82, forward_pe: 68, peg: 71, price_fcf: 65, momentum: 75, analyst_target: 80, williams_daily: 85, adx_daily: 62 }, raw_data: { rsi_daily: 42.1, rsi_intraday: 40.3, peg_ratio: 0.89, forward_pe: 28.4, ma200: 721.30, momentum_1m: 3.2, sector_return: 1.4 } },
    { ticker: "AAPL",  name: "Apple Inc",             current_price: 189.30,  currency: "USD", total_score: 58.1, signal: "NEUTRAAL", etf_weight: 0.0369, scores_by_timeframe: { intraday: 56.0, daily: 57.2, weekly: 58.9, monthly: 58.1 }, indicator_scores: { rsi_daily: 55, rsi_weekly: 52, rsi_monthly: 50, rsi_intraday: 54, ma200: 60, forward_pe: 52, peg: 58, price_fcf: 60, momentum: 55, analyst_target: 50, williams_daily: 45, adx_daily: 50 }, raw_data: { rsi_daily: 54.8, rsi_intraday: 53.5, peg_ratio: 1.42, forward_pe: 29.1, ma200: 181.20, momentum_1m: 0.8, sector_return: 1.4 } },
    { ticker: "MSFT",  name: "Microsoft Corp",        current_price: 378.90,  currency: "USD", total_score: 63.7, signal: "KOOP",     etf_weight: 0.0288, scores_by_timeframe: { intraday: 63.0, daily: 62.1, weekly: 64.5, monthly: 64.4 }, indicator_scores: { rsi_daily: 48, rsi_weekly: 46, rsi_monthly: 47, rsi_intraday: 47, ma200: 70, forward_pe: 65, peg: 62, price_fcf: 68, momentum: 60, analyst_target: 65, williams_daily: 70, adx_daily: 58 }, raw_data: { rsi_daily: 47.6, rsi_intraday: 46.8, peg_ratio: 1.18, forward_pe: 30.2, ma200: 355.40, momentum_1m: 1.9, sector_return: 1.4 } },
    { ticker: "GOOGL", name: "Alphabet Class A",      current_price: 165.20,  currency: "USD", total_score: 68.9, signal: "KOOP",     etf_weight: 0.0222, scores_by_timeframe: { intraday: 68.5, daily: 67.3, weekly: 70.1, monthly: 69.2 }, indicator_scores: { rsi_daily: 44, rsi_weekly: 41, rsi_monthly: 43, rsi_intraday: 43, ma200: 78, forward_pe: 72, peg: 69, price_fcf: 70, momentum: 62, analyst_target: 72, williams_daily: 78, adx_daily: 65 }, raw_data: { rsi_daily: 43.9, rsi_intraday: 42.5, peg_ratio: 0.98, forward_pe: 21.3, ma200: 148.90, momentum_1m: 2.4, sector_return: 1.4 } },
    { ticker: "TSM",   name: "Taiwan Semiconductor",  current_price: 142.80,  currency: "USD", total_score: 74.2, signal: "KOOP",     etf_weight: 0.0209, scores_by_timeframe: { intraday: 75.0, daily: 75.8, weekly: 73.4, monthly: 73.6 }, indicator_scores: { rsi_daily: 38, rsi_weekly: 35, rsi_monthly: 40, rsi_intraday: 37, ma200: 88, forward_pe: 74, peg: 76, price_fcf: 72, momentum: 68, analyst_target: null, williams_daily: 82, adx_daily: 70 }, raw_data: { rsi_daily: 37.4, rsi_intraday: 36.8, peg_ratio: 0.76, forward_pe: 18.9, ma200: 118.60, momentum_1m: 4.1, sector_return: 0.8 } },
    { ticker: "AMZN",  name: "Amazon.com Inc",        current_price: 183.50,  currency: "USD", total_score: 65.4, signal: "KOOP",     etf_weight: 0.0208, scores_by_timeframe: { intraday: 65.0, daily: 64.1, weekly: 66.2, monthly: 65.8 }, indicator_scores: { rsi_daily: 46, rsi_weekly: 44, rsi_monthly: 45, rsi_intraday: 45, ma200: 72, forward_pe: 67, peg: 64, price_fcf: 66, momentum: 63, analyst_target: 68, williams_daily: 72, adx_daily: 60 }, raw_data: { rsi_daily: 45.8, rsi_intraday: 44.9, peg_ratio: 1.05, forward_pe: 34.8, ma200: 166.20, momentum_1m: 2.1, sector_return: 1.4 } },
    { ticker: "GOOG",  name: "Alphabet Class C",      current_price: 166.80,  currency: "USD", total_score: 68.2, signal: "KOOP",     etf_weight: 0.0134, scores_by_timeframe: { intraday: 67.8, daily: 66.9, weekly: 69.4, monthly: 68.1 }, indicator_scores: { rsi_daily: 44, rsi_weekly: 42, rsi_monthly: 44, rsi_intraday: 43, ma200: 77, forward_pe: 71, peg: 68, price_fcf: 69, momentum: 61, analyst_target: 71, williams_daily: 77, adx_daily: 64 }, raw_data: { rsi_daily: 44.2, rsi_intraday: 43.1, peg_ratio: 0.99, forward_pe: 21.5, ma200: 149.70, momentum_1m: 2.3, sector_return: 1.4 } },
    { ticker: "AVGO",  name: "Broadcom Inc",          current_price: 1380.20, currency: "USD", total_score: 55.8, signal: "NEUTRAAL", etf_weight: 0.0125, scores_by_timeframe: { intraday: 54.5, daily: 54.2, weekly: 56.4, monthly: 56.7 }, indicator_scores: { rsi_daily: 58, rsi_weekly: 55, rsi_monthly: 54, rsi_intraday: 57, ma200: 55, forward_pe: 50, peg: 53, price_fcf: 58, momentum: 52, analyst_target: 45, williams_daily: 35, adx_daily: 48 }, raw_data: { rsi_daily: 57.9, rsi_intraday: 56.5, peg_ratio: 1.68, forward_pe: 25.4, ma200: 1290.50, momentum_1m: -0.4, sector_return: 1.4 } },
    { ticker: "META",  name: "Meta Platforms",        current_price: 496.30,  currency: "USD", total_score: 70.1, signal: "KOOP",     etf_weight: 0.0123, scores_by_timeframe: { intraday: 70.5, daily: 69.5, weekly: 71.0, monthly: 69.8 }, indicator_scores: { rsi_daily: 41, rsi_weekly: 39, rsi_monthly: 42, rsi_intraday: 40, ma200: 80, forward_pe: 70, peg: 72, price_fcf: 71, momentum: 66, analyst_target: 73, williams_daily: 80, adx_daily: 63 }, raw_data: { rsi_daily: 40.6, rsi_intraday: 39.8, peg_ratio: 0.91, forward_pe: 22.8, ma200: 438.70, momentum_1m: 3.6, sector_return: 1.4 } },
    { ticker: "005930.KS", name: "Samsung Electronics", current_price: 71200, currency: "KRW", total_score: 42.6, signal: "UITSTAP", etf_weight: 0.0111, scores_by_timeframe: { intraday: 41.0, daily: 40.8, weekly: 43.5, monthly: 43.3 }, indicator_scores: { rsi_daily: 68, rsi_weekly: 65, rsi_monthly: 62, rsi_intraday: 67, ma200: 38, forward_pe: 40, peg: 42, price_fcf: 45, momentum: 40, analyst_target: null, williams_daily: 30, adx_daily: 55 }, raw_data: { rsi_daily: 67.8, rsi_intraday: 66.2, peg_ratio: 2.14, forward_pe: 14.2, ma200: 78400, momentum_1m: -3.8, sector_return: -0.5 } },
  ],
};

export const MOCK_HISTORY = Array.from({ length: 60 }, (_, i) => {
  const d = new Date(); d.setDate(d.getDate() - (59 - i));
  return { date: d.toLocaleDateString("nl-NL", { day: "2-digit", month: "2-digit" }), score: 45 + Math.sin(i * 0.2) * 12 + i * 0.15 + (Math.random() - 0.5) * 4 };
});
