import type { OhlcvBar } from "@/lib/types";

/**
 * Estimate support / resistance from a rolling window of recent prices.
 *
 * Uses simple low/high percentiles over the last `windowSize` bars — robust
 * enough for a UI hint and avoids dragging in a pivot-detection library.
 */
export const estimateLevels = (
  bars: OhlcvBar[],
  windowSize = 30,
): { support: number; resistance: number; stopLoss: number } | null => {
  if (bars.length === 0) return null;
  const recent = bars.slice(-Math.min(windowSize, bars.length));
  const lows = recent.map((b) => b.low).sort((a, b) => a - b);
  const highs = recent.map((b) => b.high).sort((a, b) => a - b);
  const pct = (arr: number[], p: number): number => {
    const idx = Math.min(arr.length - 1, Math.max(0, Math.floor(arr.length * p)));
    return arr[idx];
  };
  const support = pct(lows, 0.15);
  const resistance = pct(highs, 0.85);
  const lastClose = recent[recent.length - 1].close;
  const stopLoss = Math.min(support, lastClose * 0.97);
  return { support, resistance, stopLoss };
};

/** Read the latest non-null indicator value from a bar series. */
export const lastIndicator = (
  bars: OhlcvBar[],
  field: "rsi_14" | "macd_hist" | "bollinger_pctb",
): number | null => {
  for (let i = bars.length - 1; i >= 0; i--) {
    const v = bars[i][field];
    if (v != null && Number.isFinite(v)) return v;
  }
  return null;
};

/**
 * Simple linear forecast band from probability and recent volatility.
 *
 * This is a UI heuristic only — the actual signal comes from the model;
 * we just translate `(probability, threshold)` into a visual price band.
 */
export const projectForecastBand = (
  bars: OhlcvBar[],
  probability: number,
  threshold: number,
  horizon = 5,
): { upper: number[]; mid: number[]; lower: number[]; dates: string[] } => {
  if (bars.length < 20) return { upper: [], mid: [], lower: [], dates: [] };
  const recent = bars.slice(-30);
  const returns = recent.slice(1).map((b, i) => (b.close - recent[i].close) / recent[i].close);
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const variance =
    returns.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(1, returns.length - 1);
  const stdev = Math.sqrt(variance);
  const lastClose = recent[recent.length - 1].close;
  const lastDate = new Date(recent[recent.length - 1].date);

  // Confidence-scaled drift: above threshold -> bullish bias, below -> bearish.
  const scaled = (probability - threshold) / Math.max(0.001, 1 - threshold);
  const direction = scaled >= 0 ? 1 : -1;
  const magnitude = Math.min(1, Math.abs(scaled));

  const mid: number[] = [];
  const upper: number[] = [];
  const lower: number[] = [];
  const dates: string[] = [];

  for (let i = 1; i <= horizon; i++) {
    const drift = direction * magnitude * Math.max(stdev, 0.002) * i;
    const midPrice = lastClose * (1 + drift);
    const widening = stdev * Math.sqrt(i) * 1.5;
    mid.push(midPrice);
    upper.push(midPrice * (1 + widening));
    lower.push(midPrice * (1 - widening));
    const nextDate = new Date(lastDate);
    nextDate.setDate(lastDate.getDate() + i);
    dates.push(nextDate.toISOString().slice(0, 10));
  }
  return { upper, mid, lower, dates };
};

export const dayChange = (
  bars: OhlcvBar[],
): { absolute: number; relative: number; last: number } | null => {
  if (bars.length < 2) return null;
  const last = bars[bars.length - 1].close;
  const prev = bars[bars.length - 2].close;
  return {
    absolute: last - prev,
    relative: (last - prev) / prev,
    last,
  };
};
