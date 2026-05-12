"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

/**
 * Asset selector dropdown with type-to-search and "free input" support.
 *
 * The supported set comes from `/tickers` on the backend, but the user can
 * type any ticker — yfinance will resolve it on the server.
 */
export const TickerSelector = () => {
  const ticker = useAppStore((s) => s.ticker);
  const setTicker = useAppStore((s) => s.setTicker);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const { data } = useQuery({
    queryKey: ["tickers"],
    queryFn: api.tickers,
  });

  const options = useMemo(() => data?.tickers ?? [], [data?.tickers]);
  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase();
    if (!q) return options;
    return options.filter((t) => t.toUpperCase().includes(q));
  }, [options, query]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    if (open) window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  const commit = (value: string) => {
    const trimmed = value.trim().toUpperCase();
    if (!trimmed) return;
    setTicker(trimmed);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-flex items-center gap-3 rounded-lg px-3 py-2 min-w-[180px]",
          "border border-ivory/[0.08] bg-ivory/[0.025] hover:bg-ivory/[0.05]",
          "transition",
          open && "bg-ivory/[0.05] border-gold/30",
        )}
      >
        <span className="text-[10px] uppercase tracking-[0.18em] text-ivory/40">
          актив
        </span>
        <span className="mono-num text-gold text-base">{ticker}</span>
        <ChevronDown
          size={14}
          className={cn(
            "text-ivory/50 ml-auto transition-transform",
            open && "rotate-180 text-gold/80",
          )}
        />
      </button>
      {open && (
        <div className="absolute z-30 mt-2 left-0 w-[280px] panel p-2 ink-wash">
          <label className="flex items-center gap-2 px-2 py-1.5 border-b border-ivory/[0.06] mb-1">
            <Search size={14} className="text-ivory/40" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commit(query || ticker);
                if (e.key === "Escape") setOpen(false);
              }}
              placeholder="AAPL, ^GSPC, MSFT…"
              className="bg-transparent outline-none text-sm flex-1 placeholder:text-ivory/30"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="text-ivory/40 hover:text-carmine"
              >
                <X size={12} />
              </button>
            )}
          </label>
          <ul className="max-h-64 overflow-auto py-1">
            {filtered.map((t) => (
              <li key={t}>
                <button
                  type="button"
                  onClick={() => commit(t)}
                  className={cn(
                    "w-full text-left px-3 py-1.5 text-sm rounded-md flex items-center justify-between",
                    "hover:bg-ivory/[0.05] transition",
                    t === ticker && "text-gold bg-ivory/[0.05]",
                  )}
                >
                  <span className="mono-num">{t}</span>
                  {t === ticker && (
                    <span className="text-[8px] text-gold">●</span>
                  )}
                </button>
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="px-3 py-2 text-xs text-ivory/40 italic">
                Нажмите Enter чтобы выбрать «{query.toUpperCase()}»
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};
