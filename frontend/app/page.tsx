"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import { BacktestPanel } from "@/components/backtest-panel";
import { CandleChart } from "@/components/candle-chart";
import { FavoritesPanel } from "@/components/favorites-panel";
import { ForecastHistory } from "@/components/forecast-history";
import { ForecastPanel } from "@/components/forecast-panel";
import { Header } from "@/components/header";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { PredictResponse } from "@/lib/types";
import { cuid, minusDays, timeframeDays, today } from "@/lib/utils";

const Home = () => {
  const ticker = useAppStore((s) => s.ticker);
  const timeframe = useAppStore((s) => s.timeframe);
  const setTimeframe = useAppStore((s) => s.setTimeframe);
  const modelName = useAppStore((s) => s.modelName);
  const setModelName = useAppStore((s) => s.setModelName);
  const shogun = useAppStore((s) => s.shogun);
  const sound = useAppStore((s) => s.sound);
  const pushHistory = useAppStore((s) => s.pushHistory);

  const [prediction, setPrediction] = useState<PredictResponse | null>(null);

  // Reset prediction when ticker changes — it no longer applies.
  useEffect(() => {
    setPrediction(null);
  }, [ticker]);

  const range = useMemo(() => {
    const end = today();
    const start = minusDays(timeframeDays[timeframe]);
    return { start, end };
  }, [timeframe]);

  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 60_000,
  });

  const models = useQuery({
    queryKey: ["models"],
    queryFn: api.models,
    enabled: health.data?.model_loaded === true,
  });

  // Sync the default model from the API on first successful load.
  useEffect(() => {
    if (!models.data) return;
    if (modelName && models.data.models.some((m) => m.name === modelName)) return;
    if (models.data.default_model) setModelName(models.data.default_model);
    else if (models.data.models[0]) setModelName(models.data.models[0].name);
  }, [models.data, modelName, setModelName]);

  const ohlcv = useQuery({
    queryKey: ["ohlcv", ticker, range.start, range.end],
    queryFn: () =>
      api.ohlcv({ ticker, start: range.start, end: range.end }),
    enabled: !!ticker,
  });

  const predictMutation = useMutation({
    mutationFn: async () => {
      const res = await api.predict({
        ticker,
        date: today(),
        model_name: modelName,
      });
      // Apply Shogun bias on the client: lower the effective threshold to
      // surface a more aggressive signal without retraining the model.
      if (shogun) {
        const aggressiveThreshold = Math.max(0.4, res.threshold - 0.08);
        return {
          ...res,
          threshold: aggressiveThreshold,
          signal: (res.probability >= aggressiveThreshold ? 1 : 0) as 0 | 1,
        } satisfies PredictResponse;
      }
      return res;
    },
    onSuccess: (data) => {
      setPrediction(data);
      pushHistory({
        id: cuid(),
        ticker: data.ticker,
        date: data.date,
        model: data.model,
        probability: data.probability,
        threshold: data.threshold,
        signal: data.signal,
        shogun,
        createdAt: Date.now(),
      });
      // Temple bell on bullish signal, taiko thud on bearish — only if user opted in.
      if (sound && typeof window !== "undefined") {
        try {
          playBell(data.signal === 1);
        } catch {
          // ignore audio failures (Safari autoplay etc.)
        }
      }
    },
  });

  const runForecast = useCallback(() => {
    predictMutation.mutate();
  }, [predictMutation]);

  const modelLoaded = !!health.data?.model_loaded;

  return (
    <div className="relative min-h-screen flex flex-col z-10">
      <Header
        onRunForecast={runForecast}
        isRunning={predictMutation.isPending}
        modelLoaded={modelLoaded}
      />

      {!modelLoaded && (
        <div className="mx-4 mt-4 rounded-xl border border-gold/25 bg-gold/[0.06] text-[11px] px-4 py-2.5 text-ivory/85 flex items-center gap-2">
          <span className="font-jp text-gold">⚠</span>
          API не нашёл обученных моделей. Запустите{" "}
          <code className="mono-num text-gold mx-1 px-1.5 py-0.5 rounded bg-ivory/[0.05]">
            make api-train
          </code>{" "}
          и перезапустите сервер на :8000.
        </div>
      )}
      {predictMutation.isError && (
        <div className="mx-4 mt-4 rounded-xl border border-flame/25 bg-flame/[0.08] text-[11px] px-4 py-2.5 text-flame">
          Ошибка прогноза: {(predictMutation.error as Error).message}
        </div>
      )}

      <main className="flex-1 grid grid-cols-12 gap-4 p-4 min-h-0">
        <aside className="col-span-12 md:col-span-3 lg:col-span-2 min-h-[420px]">
          <FavoritesPanel />
        </aside>
        <section className="col-span-12 md:col-span-6 lg:col-span-7 min-h-[560px]">
          <CandleChart
            bars={ohlcv.data?.bars ?? []}
            prediction={prediction}
            isLoading={ohlcv.isLoading}
            timeframe={timeframe}
            onTimeframeChange={setTimeframe}
          />
        </section>
        <aside className="col-span-12 md:col-span-3 lg:col-span-3 flex flex-col gap-4 min-h-[560px]">
          <ForecastPanel
            bars={ohlcv.data?.bars ?? []}
            prediction={prediction}
            ticker={ticker}
            shogun={shogun}
          />
        </aside>
      </main>

      <section className="grid grid-cols-12 gap-4 px-4 pb-4">
        <div className="col-span-12 md:col-span-6">
          <BacktestPanel />
        </div>
        <div className="col-span-12 md:col-span-6">
          <ForecastHistory />
        </div>
      </section>

      <footer className="px-6 py-3.5 border-t border-ivory/[0.06] text-[10px] text-ivory/45 flex items-center justify-between">
        <span className="flex items-center gap-2">
          <span className="w-1 h-1 rounded-full bg-emerald inline-block" />
          KABU · {models.data?.models.length ?? 0} моделей загружено
        </span>
        <span className="font-jp text-ivory/55">明日は明日の風が吹く</span>
      </footer>
    </div>
  );
};

/**
 * Very short procedural chime synthesised through the Web Audio API.
 * Frequency differs for bullish (high bell) vs bearish (low taiko-ish thud).
 */
const playBell = (bullish: boolean) => {
  const ctx = new (window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext })
      .webkitAudioContext)();
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.connect(g);
  g.connect(ctx.destination);
  o.frequency.value = bullish ? 880 : 110;
  o.type = bullish ? "sine" : "triangle";
  g.gain.setValueAtTime(0.0001, ctx.currentTime);
  g.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.4);
  o.start();
  o.stop(ctx.currentTime + 1.4);
};

export default Home;
