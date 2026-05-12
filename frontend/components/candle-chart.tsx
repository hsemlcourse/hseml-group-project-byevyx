"use client";

import {
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  createChart,
} from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";

import type { OhlcvBar, PredictResponse, Timeframe } from "@/lib/types";
import { projectForecastBand } from "@/lib/indicators";
import { cn } from "@/lib/utils";

interface CandleChartProps {
  bars: OhlcvBar[];
  prediction: PredictResponse | null;
  isLoading: boolean;
  timeframe: Timeframe;
  onTimeframeChange: (t: Timeframe) => void;
}

const TIMEFRAMES: { id: Timeframe; label: string; jp: string }[] = [
  { id: "1m", label: "1М", jp: "月" },
  { id: "3m", label: "3М", jp: "季" },
  { id: "6m", label: "6М", jp: "半" },
  { id: "1y", label: "1Г", jp: "年" },
  { id: "2y", label: "2Г", jp: "弐" },
  { id: "5y", label: "5Г", jp: "伍" },
];

const toUtcTs = (iso: string): UTCTimestamp =>
  Math.floor(new Date(iso + "T00:00:00Z").getTime() / 1000) as UTCTimestamp;

/**
 * The dashboard centerpiece: japanese candlesticks + volume + AI forecast line.
 *
 * Built on TradingView's `lightweight-charts`. The forecast is rendered as a
 * dashed gold projection forward from the last close, framed by a confidence
 * band drawn as two thin lines.
 */
export const CandleChart = ({
  bars,
  prediction,
  isLoading,
  timeframe,
  onTimeframeChange,
}: CandleChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const smaRef = useRef<ISeriesApi<"Line"> | null>(null);
  const forecastMidRef = useRef<ISeriesApi<"Line"> | null>(null);
  const forecastUpperRef = useRef<ISeriesApi<"Line"> | null>(null);
  const forecastLowerRef = useRef<ISeriesApi<"Line"> | null>(null);

  // Build chart once on mount; resize handled below.
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "rgba(0,0,0,0)" },
        textColor: "rgba(242,234,211,0.55)",
        fontFamily: "var(--font-plex-mono), monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(242,234,211,0.045)" },
        horzLines: { color: "rgba(242,234,211,0.045)" },
      },
      rightPriceScale: {
        borderColor: "rgba(242,234,211,0.08)",
      },
      timeScale: {
        borderColor: "rgba(242,234,211,0.08)",
        timeVisible: false,
        secondsVisible: false,
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: "rgba(232,197,71,0.35)",
          width: 1,
          style: LineStyle.Dashed,
        },
        horzLine: {
          color: "rgba(232,197,71,0.35)",
          width: 1,
          style: LineStyle.Dashed,
        },
      },
      autoSize: true,
    });

    const candle = chart.addCandlestickSeries({
      upColor: "#7DD3A8", // matcha
      downColor: "#F18B7A", // terracotta
      borderUpColor: "#7DD3A8",
      borderDownColor: "#F18B7A",
      wickUpColor: "rgba(125,211,168,0.7)",
      wickDownColor: "rgba(241,139,122,0.7)",
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });

    const volume = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
      color: "rgba(232,197,71,0.25)",
    });
    chart.priceScale("vol").applyOptions({
      scaleMargins: { top: 0.84, bottom: 0 },
      borderVisible: false,
    });

    const sma = chart.addLineSeries({
      color: "rgba(232,197,71,0.45)",
      lineWidth: 1,
      lineStyle: LineStyle.Solid,
      crosshairMarkerVisible: false,
      lastValueVisible: false,
      priceLineVisible: false,
    });

    const forecastMid = chart.addLineSeries({
      color: "#E8C547",
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      crosshairMarkerVisible: false,
      lastValueVisible: false,
      priceLineVisible: false,
    });
    const forecastUpper = chart.addLineSeries({
      color: "rgba(232,197,71,0.4)",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      crosshairMarkerVisible: false,
      lastValueVisible: false,
      priceLineVisible: false,
    });
    const forecastLower = chart.addLineSeries({
      color: "rgba(232,197,71,0.4)",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      crosshairMarkerVisible: false,
      lastValueVisible: false,
      priceLineVisible: false,
    });

    chartRef.current = chart;
    candleRef.current = candle;
    volumeRef.current = volume;
    smaRef.current = sma;
    forecastMidRef.current = forecastMid;
    forecastUpperRef.current = forecastUpper;
    forecastLowerRef.current = forecastLower;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // Push OHLCV updates into the chart whenever the data changes.
  useEffect(() => {
    if (!candleRef.current || !volumeRef.current || !smaRef.current) return;
    const candleData = bars.map((b) => ({
      time: toUtcTs(b.date),
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));
    candleRef.current.setData(candleData);

    const volumeData = bars.map((b) => ({
      time: toUtcTs(b.date),
      value: b.volume,
      color:
        b.close >= b.open
          ? "rgba(125,211,168,0.28)"
          : "rgba(241,139,122,0.32)",
    }));
    volumeRef.current.setData(volumeData);

    const smaData = bars
      .filter((b) => b.sma_20 != null && Number.isFinite(b.sma_20))
      .map((b) => ({ time: toUtcTs(b.date), value: b.sma_20 as number }));
    smaRef.current.setData(smaData);

    if (bars.length > 0) chartRef.current?.timeScale().fitContent();
  }, [bars]);

  // Draw / clear the AI forecast band from the latest prediction.
  useEffect(() => {
    if (!forecastMidRef.current || !forecastUpperRef.current || !forecastLowerRef.current)
      return;
    if (!prediction || bars.length < 20) {
      forecastMidRef.current.setData([]);
      forecastUpperRef.current.setData([]);
      forecastLowerRef.current.setData([]);
      return;
    }
    const band = projectForecastBand(
      bars,
      prediction.probability,
      prediction.threshold,
      5,
    );
    const lastClose = bars[bars.length - 1].close;
    const anchorDate = bars[bars.length - 1].date;
    const mid = [
      { time: toUtcTs(anchorDate), value: lastClose },
      ...band.dates.map((d, i) => ({ time: toUtcTs(d), value: band.mid[i] })),
    ];
    const upper = [
      { time: toUtcTs(anchorDate), value: lastClose },
      ...band.dates.map((d, i) => ({ time: toUtcTs(d), value: band.upper[i] })),
    ];
    const lower = [
      { time: toUtcTs(anchorDate), value: lastClose },
      ...band.dates.map((d, i) => ({ time: toUtcTs(d), value: band.lower[i] })),
    ];
    forecastMidRef.current.setData(mid);
    forecastUpperRef.current.setData(upper);
    forecastLowerRef.current.setData(lower);
  }, [prediction, bars]);

  const summary = useMemo(() => {
    if (bars.length === 0) return null;
    const last = bars[bars.length - 1];
    const first = bars[0];
    const totalChange = (last.close - first.close) / first.close;
    return { last, totalChange };
  }, [bars]);

  return (
    <div className="panel relative flex h-full min-h-0 flex-col">
      <div className="panel-header relative z-30 shrink-0 bg-ink-50/95 backdrop-blur-sm">
        <span className="panel-title">График · 日本式</span>
        <div className="flex items-center gap-1 rounded-lg border border-ivory/[0.06] bg-ivory/[0.025] p-0.5">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.id}
              type="button"
              onClick={() => onTimeframeChange(tf.id)}
              className={cn(
                "mono-num rounded-md px-2.5 py-1 text-[10px] tracking-widest transition",
                tf.id === timeframe
                  ? "bg-ivory/10 text-gold shadow-sm"
                  : "text-ivory/55 hover:bg-ivory/[0.04] hover:text-ivory",
              )}
              title={tf.jp}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart area only — loading / empty overlays must not cover the header (timeframe buttons). */}
      <div className="relative z-0 flex min-h-0 flex-1 flex-col px-1 pb-1">
        {summary && (
          <div className="pointer-events-none absolute left-4 top-3 z-10 ink-wash">
            <div className="flex items-baseline gap-3">
              <span className="mono-num text-3xl tracking-tight text-ivory">
                {summary.last.close.toFixed(2)}
              </span>
              <span
                className={cn(
                  "mono-num rounded-md px-1.5 py-0.5 text-sm",
                  summary.totalChange >= 0
                    ? "bg-emerald/10 text-emerald"
                    : "bg-flame/10 text-flame",
                )}
              >
                {summary.totalChange >= 0 ? "+" : ""}
                {(summary.totalChange * 100).toFixed(2)}%
              </span>
            </div>
            <div className="mt-0.5 text-[10px] uppercase tracking-[0.18em] text-ivory/35">
              период · {bars.length} баров
            </div>
          </div>
        )}
        <span
          aria-hidden
          className="kanji-watermark right-4 top-2 text-[11rem]"
        >
          相場
        </span>
        <div ref={containerRef} className="relative z-0 min-h-0 w-full flex-1" />
        {isLoading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center rounded-lg bg-ink/35 backdrop-blur-sm">
            <span className="animate-pulse font-jp text-gold/80">
              読み込み中…
            </span>
          </div>
        )}
        {!isLoading && bars.length === 0 && (
          <div className="absolute inset-0 z-20 flex items-center justify-center rounded-lg text-sm text-ivory/40">
            Нет данных по выбранному тикеру
          </div>
        )}
      </div>
    </div>
  );
};
