"use client";

import { useMutation } from "@tanstack/react-query";
import { History, PlayCircle } from "lucide-react";
import { useMemo, useState } from "react";

import { Panel } from "@/components/ui/panel";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { BacktestResponse } from "@/lib/types";
import {
  cn,
  formatNumber,
  formatPercent,
  formatSignedPercent,
  minusDays,
  today,
} from "@/lib/utils";

/**
 * On-demand backtest block: posts to /backtest and renders an equity curve
 * sparkline together with key risk metrics (Sharpe, max DD, trade count).
 */
export const BacktestPanel = () => {
  const ticker = useAppStore((s) => s.ticker);
  const modelName = useAppStore((s) => s.modelName);
  const [start, setStart] = useState(minusDays(365));
  const [end, setEnd] = useState(today());

  const mutation = useMutation({
    mutationFn: () =>
      api.backtest({
        ticker,
        start,
        end,
        model_name: modelName,
      }),
  });

  const data = mutation.data;

  return (
    <Panel
      title="Бэктест · 検"
      kanji="検"
      right={
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="btn-ghost"
        >
          <PlayCircle size={11} />
          {mutation.isPending ? "идёт…" : "запустить"}
        </button>
      }
    >
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2 text-[11px]">
          <History size={12} className="text-ivory/40" />
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="input-soft mono-num py-1 text-xs"
          />
          <span className="text-ivory/30">→</span>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="input-soft mono-num py-1 text-xs"
          />
        </div>

        {mutation.isError && (
          <div className="text-[11px] text-flame px-2 py-1 rounded-md bg-flame/10 border border-flame/20">
            {(mutation.error as Error).message}
          </div>
        )}

        {data && <BacktestResult data={data} />}
        {!data && !mutation.isPending && (
          <div className="text-[11px] text-ivory/40 italic">
            Запустите чтобы увидеть equity curve и Sharpe.
          </div>
        )}
      </div>
    </Panel>
  );
};

const BacktestResult = ({ data }: { data: BacktestResponse }) => {
  const sparkline = useMemo(() => {
    const points = data.equity_curve;
    if (points.length < 2) return null;
    const values = points.map((p) => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const w = 240;
    const h = 56;
    const step = w / (points.length - 1);
    const d = points
      .map((p, i) => {
        const x = i * step;
        const y = h - ((p.value - min) / range) * h;
        return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
    return { d, w, h };
  }, [data.equity_curve]);

  const positive = data.cum_return >= 0;

  return (
    <div className="space-y-2 ink-wash">
      <div className="flex items-baseline gap-3">
        <span
          className={cn(
            "mono-num text-2xl",
            positive ? "text-emerald" : "text-flame",
          )}
        >
          {formatSignedPercent(data.cum_return, 2)}
        </span>
        <span className="text-[10px] uppercase tracking-widest text-ivory/40">
          {data.model}
        </span>
      </div>

      {sparkline && (
        <svg
          width={sparkline.w}
          height={sparkline.h}
          className="w-full h-14 overflow-visible"
          viewBox={`0 0 ${sparkline.w} ${sparkline.h}`}
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient
              id="eq-grad"
              x1="0"
              y1="0"
              x2="0"
              y2={sparkline.h}
              gradientUnits="userSpaceOnUse"
            >
              <stop
                offset="0%"
                stopColor={positive ? "#7DD3A8" : "#F18B7A"}
                stopOpacity={0.3}
              />
              <stop
                offset="100%"
                stopColor={positive ? "#7DD3A8" : "#F18B7A"}
                stopOpacity={0}
              />
            </linearGradient>
          </defs>
          <path
            d={`${sparkline.d} L ${sparkline.w},${sparkline.h} L 0,${sparkline.h} Z`}
            fill="url(#eq-grad)"
          />
          <path
            d={sparkline.d}
            fill="none"
            stroke={positive ? "#7DD3A8" : "#F18B7A"}
            strokeWidth={1.6}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}

      <dl className="grid grid-cols-3 gap-2 text-[11px] mono-num">
        <Metric label="Sharpe" value={formatNumber(data.sharpe, 2)} />
        <Metric label="Max DD" value={formatPercent(data.max_drawdown, 1)} />
        <Metric label="Trades" value={String(data.n_trades)} />
        <Metric label="Trade freq" value={formatPercent(data.trade_freq, 1)} />
        <Metric label="Тикер" value={data.ticker} />
      </dl>
    </div>
  );
};

const Metric = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-lg border border-ivory/[0.06] bg-ivory/[0.025] px-2 py-1.5">
    <div className="text-[9px] uppercase tracking-[0.18em] text-ivory/40 font-sans">
      {label}
    </div>
    <div className="text-gold mt-0.5">{value}</div>
  </div>
);
