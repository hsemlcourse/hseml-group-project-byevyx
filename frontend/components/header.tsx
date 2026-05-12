"use client";

import { Sparkles, Wand2 } from "lucide-react";

import { Seal } from "@/components/ui/seal";
import { ShogunToggle } from "@/components/shogun-toggle";
import { ThemeToggle } from "@/components/theme-toggle";
import { TickerSelector } from "@/components/ticker-selector";
import { cn } from "@/lib/utils";

interface HeaderProps {
  onRunForecast: () => void;
  isRunning: boolean;
  modelLoaded: boolean;
}

/**
 * Top dashboard bar: seal logo + brand, asset selector, "Run forecast"
 * action with a soft ripple, plus Shogun and theme toggles on the right.
 */
export const Header = ({ onRunForecast, isRunning, modelLoaded }: HeaderProps) => (
  <header className="sticky top-0 z-20 flex items-center gap-4 px-6 py-3.5 bg-ink/70 backdrop-blur-xl border-b border-ivory/[0.06]">
    <div className="flex items-center gap-3">
      <Seal />
      <div className="leading-tight">
        <h1 className="font-jp text-lg tracking-wide text-ivory flex items-center gap-2">
          KABU
          <span className="text-gold/70 text-sm">株</span>
        </h1>
        <p className="text-[10px] uppercase tracking-[0.24em] text-ivory/40">
          東京 · Trading Console
        </p>
      </div>
    </div>

    <div className="h-7 w-px bg-ivory/[0.08] mx-1" />

    <TickerSelector />

    <div className="ml-auto flex items-center gap-2">
      <button
        type="button"
        onClick={onRunForecast}
        disabled={isRunning || !modelLoaded}
        className={cn("btn-carmine group", isRunning && "cursor-progress")}
        title={
          modelLoaded
            ? "Запустить прогноз"
            : "Модели не обучены — выполните make api-train"
        }
      >
        {isRunning ? (
          <Sparkles size={16} className="animate-spin" />
        ) : (
          <Wand2 size={16} />
        )}
        <span>{isRunning ? "Считаем…" : "Запустить прогноз"}</span>
        {!isRunning && modelLoaded && (
          <span
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-lg ring-1 ring-carmine/40 animate-ripple"
          />
        )}
      </button>
      <ShogunToggle />
      <ThemeToggle />
    </div>
  </header>
);
