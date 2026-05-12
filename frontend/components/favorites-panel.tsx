"use client";

import { useQueries } from "@tanstack/react-query";
import { Plus, Star, Trash2 } from "lucide-react";
import { useState } from "react";

import { Panel } from "@/components/ui/panel";
import { api } from "@/lib/api";
import { dayChange } from "@/lib/indicators";
import { useAppStore } from "@/lib/store";
import {
  cn,
  formatPrice,
  formatSignedPercent,
  minusDays,
  today,
} from "@/lib/utils";

/**
 * Left rail: list of favorite tickers with live last-close + daily change.
 *
 * Backed by `/ohlcv` queries (one short request per ticker, cached by RQ).
 */
export const FavoritesPanel = () => {
  const favorites = useAppStore((s) => s.favorites);
  const ticker = useAppStore((s) => s.ticker);
  const setTicker = useAppStore((s) => s.setTicker);
  const addFavorite = useAppStore((s) => s.addFavorite);
  const removeFavorite = useAppStore((s) => s.removeFavorite);
  const [input, setInput] = useState("");

  const start = minusDays(14);
  const end = today();

  const queries = useQueries({
    queries: favorites.map((t) => ({
      queryKey: ["ohlcv", t, start, end, "fav"],
      queryFn: () => api.ohlcv({ ticker: t, start, end }),
      staleTime: 5 * 60_000,
      retry: 0,
    })),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim().toUpperCase();
    if (!value) return;
    addFavorite(value);
    setInput("");
  };

  return (
    <Panel
      title="Избранное · 選"
      kanji="選"
      right={
        <span className="chip mono-num">{favorites.length}</span>
      }
      className="h-full flex flex-col"
    >
      <ul className="flex-1 overflow-auto p-2 space-y-1">
        {favorites.map((t, idx) => {
          const q = queries[idx];
          const bars = q?.data?.bars ?? [];
          const change = dayChange(bars);
          const active = t === ticker;
          return (
            <li key={t}>
              <div
                className={cn(
                  "group flex w-full items-center gap-2 rounded-lg border transition",
                  active
                    ? "bg-ivory/[0.06] border-gold/30"
                    : "border-transparent hover:bg-ivory/[0.04] hover:border-ivory/[0.06]",
                )}
              >
                <button
                  type="button"
                  onClick={() => setTicker(t)}
                  className="flex min-w-0 flex-1 items-center gap-3 px-3 py-2 text-left"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={cn(
                          "mono-num truncate text-sm",
                          active ? "text-gold" : "text-ivory",
                        )}
                      >
                        {t}
                      </span>
                      {active && (
                        <Star size={10} className="fill-gold/80 text-gold" />
                      )}
                    </div>
                    <div className="mono-num text-[10px] text-ivory/40">
                      {q?.isLoading
                        ? "···"
                        : change
                          ? formatPrice(change.last)
                          : q?.isError
                            ? "—"
                            : "—"}
                    </div>
                  </div>
                  <div
                    className={cn(
                      "mono-num shrink-0 rounded-md px-1.5 py-0.5 text-xs",
                      !change && "text-ivory/40",
                      change &&
                        change.relative >= 0 &&
                        "bg-emerald/10 text-emerald",
                      change &&
                        change.relative < 0 &&
                        "bg-flame/10 text-flame",
                    )}
                  >
                    {change ? formatSignedPercent(change.relative, 2) : "—"}
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => removeFavorite(t)}
                  className="mr-1 shrink-0 rounded-md p-2 text-ivory/30 opacity-0 transition hover:bg-ivory/[0.06] hover:text-carmine group-hover:opacity-100"
                  aria-label={`Удалить ${t}`}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </li>
          );
        })}
        {favorites.length === 0 && (
          <li className="px-3 py-6 text-xs text-ivory/40 italic text-center">
            Список пуст — добавьте тикер ниже
          </li>
        )}
      </ul>
      <form
        onSubmit={submit}
        className="p-2 border-t border-ivory/[0.06] flex items-center gap-1.5"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="+ Добавить тикер"
          className="input-soft flex-1 mono-num placeholder:font-sans"
        />
        <button
          type="submit"
          className="btn-ghost px-2.5 py-1.5"
          aria-label="Добавить"
        >
          <Plus size={14} />
        </button>
      </form>
    </Panel>
  );
};
