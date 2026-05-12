"use client";

import { toPng } from "html-to-image";
import {
  Activity,
  AlertTriangle,
  Download,
  ScrollText,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useRef } from "react";

import { Gauge } from "@/components/ui/gauge";
import { Panel } from "@/components/ui/panel";
import type { OhlcvBar, PredictResponse } from "@/lib/types";
import { estimateLevels, lastIndicator } from "@/lib/indicators";
import {
  cn,
  formatNumber,
  formatPercent,
  formatPrice,
} from "@/lib/utils";

interface ForecastPanelProps {
  bars: OhlcvBar[];
  prediction: PredictResponse | null;
  ticker: string;
  shogun: boolean;
}

/**
 * Right rail: AI synthesis, key levels, RSI / MACD / Bollinger gauges and
 * an "Export report as PNG" action that snapshots the panel itself.
 */
export const ForecastPanel = ({
  bars,
  prediction,
  ticker,
  shogun,
}: ForecastPanelProps) => {
  const exportRef = useRef<HTMLDivElement>(null);

  const levels = estimateLevels(bars);
  const rsi = lastIndicator(bars, "rsi_14");
  const macd = lastIndicator(bars, "macd_hist");
  const pctB = lastIndicator(bars, "bollinger_pctb");

  const bullish = prediction != null && prediction.signal === 1;
  const confidence =
    prediction != null
      ? Math.abs(prediction.probability - prediction.threshold) /
        Math.max(0.001, 1 - prediction.threshold)
      : 0;

  const downloadPng = async () => {
    if (!exportRef.current) return;
    const dataUrl = await toPng(exportRef.current, {
      backgroundColor: "#0A0A0A",
      pixelRatio: 2,
      filter: (node) =>
        !(node instanceof HTMLElement && node.dataset.exportIgnore === "true"),
    });
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = `kabu-${ticker}-${new Date().toISOString().slice(0, 10)}.png`;
    a.click();
  };

  return (
    <Panel
      title="Прогноз · 占"
      kanji="占"
      right={
        <button
          type="button"
          data-export-ignore="true"
          onClick={downloadPng}
          className="btn-ghost"
          title="Экспорт отчёта в PNG"
        >
          <Download size={12} />
          PNG
        </button>
      }
      className="h-full flex flex-col"
    >
      <div ref={exportRef} className="flex-1 overflow-auto p-4 space-y-5 ink-wash">
        <section className="space-y-2.5">
          <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.18em] text-ivory/45">
            <span>Синтез</span>
            <span className="font-jp text-gold/80">
              {shogun ? "将軍モード" : "通常"}
            </span>
          </div>
          {prediction ? (
            <div
              className={cn(
                "rounded-xl border p-4 transition",
                bullish
                  ? "border-emerald/25 bg-emerald/[0.06]"
                  : "border-flame/25 bg-flame/[0.06]",
              )}
            >
              <div className="flex items-baseline gap-2">
                <span
                  className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full",
                    bullish
                      ? "bg-emerald/15 text-emerald"
                      : "bg-flame/15 text-flame",
                  )}
                >
                  {bullish ? (
                    <TrendingUp size={16} />
                  ) : (
                    <TrendingDown size={16} />
                  )}
                </span>
                <span className="mono-num text-3xl text-ivory tracking-tight">
                  {formatPercent(prediction.probability, 1)}
                </span>
                <span className="text-[10px] uppercase tracking-[0.18em] text-ivory/40 ml-auto">
                  P(↑ 5д)
                </span>
              </div>
              <p className="mt-3 text-[12px] text-ivory/75 leading-relaxed">
                Модель{" "}
                <span className="mono-num text-gold">{prediction.model}</span>{" "}
                видит{" "}
                <span
                  className={cn(
                    "font-medium",
                    bullish ? "text-emerald" : "text-flame",
                  )}
                >
                  {bullish ? "восходящий" : "нисходящий"}
                </span>{" "}
                тренд на 5 сессий с уверенностью{" "}
                <span className="mono-num text-gold">
                  {formatPercent(confidence, 0)}
                </span>
                . Порог{" "}
                <span className="mono-num text-ivory/85">
                  {formatNumber(prediction.threshold, 3)}
                </span>
                {shogun && (
                  <>
                    {" "}
                    в режиме <span className="text-gold">Сёгун</span>
                  </>
                )}
                .
              </p>
              {prediction.warnings.length > 0 && (
                <div className="mt-3 flex items-start gap-1.5 text-[10px] text-gold/70 border-t border-ivory/[0.06] pt-2">
                  <AlertTriangle size={11} className="mt-px shrink-0" />
                  <span>{prediction.warnings.join("; ")}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-ivory/[0.06] bg-ivory/[0.02] p-4 flex items-center gap-2 text-xs text-ivory/45">
              <Sparkles size={14} className="text-gold/60" />
              Нажмите «Запустить прогноз» чтобы получить сигнал ИИ.
            </div>
          )}
        </section>

        <section className="space-y-2">
          <div className="text-[10px] uppercase tracking-[0.18em] text-ivory/45">
            Ключевые уровни
          </div>
          <div className="grid grid-cols-3 gap-2">
            <LevelCard
              label="Поддержка"
              value={levels ? formatPrice(levels.support) : "—"}
              tone="bull"
            />
            <LevelCard
              label="Сопротивление"
              value={levels ? formatPrice(levels.resistance) : "—"}
              tone="bear"
            />
            <LevelCard
              label="Стоп-лосс"
              value={levels ? formatPrice(levels.stopLoss) : "—"}
              tone="warn"
            />
          </div>
        </section>

        <section className="space-y-2">
          <div className="text-[10px] uppercase tracking-[0.18em] text-ivory/45 flex items-center gap-1">
            <Activity size={11} /> Индикаторы
          </div>
          <div className="rounded-xl border border-ivory/[0.06] bg-ivory/[0.02] p-2 flex items-start justify-around gap-1">
            <Gauge
              label="RSI 14"
              value={rsi}
              min={0}
              max={100}
              zones={[
                { from: 0, to: 30, color: "#7DD3A8" },
                { from: 70, to: 100, color: "#F18B7A" },
              ]}
              size={96}
            />
            <Gauge
              label="MACD"
              value={macd}
              min={-3}
              max={3}
              zones={[
                { from: -3, to: 0, color: "#F18B7A" },
                { from: 0, to: 3, color: "#7DD3A8" },
              ]}
              size={96}
            />
            <Gauge
              label="%B"
              value={pctB}
              min={-0.2}
              max={1.2}
              zones={[
                { from: -0.2, to: 0, color: "#7DD3A8" },
                { from: 1, to: 1.2, color: "#F18B7A" },
              ]}
              size={96}
            />
          </div>
        </section>

        <section className="space-y-2 border-t border-ivory/[0.06] pt-3">
          <div className="text-[10px] uppercase tracking-[0.18em] text-ivory/45 flex items-center gap-1">
            <ScrollText size={11} /> Свиток
          </div>
          <p className="text-[11px] text-ivory/45 italic leading-relaxed">
            «風林火山» — быстро как ветер, тихо как лес, яростно как огонь,
            недвижимо как гора. ИИ-сигнал — лишь шепот рынка, не приказ.
          </p>
        </section>
      </div>
    </Panel>
  );
};

const LevelCard = ({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "bull" | "bear" | "warn";
}) => {
  const toneClass =
    tone === "bull"
      ? "text-emerald border-emerald/20 bg-emerald/[0.05]"
      : tone === "bear"
        ? "text-flame border-flame/20 bg-flame/[0.05]"
        : "text-carmine border-carmine/20 bg-carmine/[0.06]";
  return (
    <div className={cn("rounded-lg border px-2.5 py-2", toneClass)}>
      <div className="text-[9px] uppercase tracking-[0.18em] text-ivory/40 font-sans">
        {label}
      </div>
      <div className="mono-num text-sm mt-0.5">{value}</div>
    </div>
  );
};
