"use client";

import { Check, Trash2, X } from "lucide-react";

import { Panel } from "@/components/ui/panel";
import { useAppStore } from "@/lib/store";
import { cn, formatPercent } from "@/lib/utils";

/**
 * Compact log of recent AI forecasts, persisted in localStorage.
 *
 * Each row shows when the call was made, the model, probability and
 * direction. A calligraphy "✓"/"✗" appears in the corner when realized
 * outcome becomes available.
 */
export const ForecastHistory = () => {
  const history = useAppStore((s) => s.history);
  const clear = useAppStore((s) => s.clearHistory);

  return (
    <Panel
      title="История · 史"
      kanji="史"
      right={
        history.length > 0 && (
          <button
            type="button"
            onClick={clear}
            className="btn-ghost"
            title="Очистить историю"
          >
            <Trash2 size={11} />
          </button>
        )
      }
    >
      <div className="max-h-44 overflow-auto p-2 space-y-1">
        {history.length === 0 ? (
          <div className="px-3 py-4 text-[11px] text-ivory/40 italic">
            История пуста — сделайте первый прогноз.
          </div>
        ) : (
          history.map((h) => (
            <div
              key={h.id}
              className="px-3 py-1.5 flex items-center gap-2 text-xs rounded-md border border-ivory/[0.06] bg-ivory/[0.02]"
            >
              <span className="mono-num text-ivory/85 w-14 truncate">
                {h.ticker}
              </span>
              <span className="mono-num text-[10px] text-ivory/40 w-20">
                {h.date}
              </span>
              <span
                className={cn(
                  "mono-num px-1.5 py-0.5 rounded-md",
                  h.signal === 1
                    ? "text-emerald bg-emerald/10"
                    : "text-flame bg-flame/10",
                )}
              >
                {h.signal === 1 ? "↑" : "↓"} {formatPercent(h.probability, 0)}
              </span>
              {h.shogun && (
                <span className="font-jp text-[10px] text-gold">将</span>
              )}
              <span className="ml-auto">
                {h.realized == null ? (
                  <span className="text-ivory/25 text-[10px]">···</span>
                ) : h.realized === h.signal ? (
                  <Check className="text-emerald" size={14} />
                ) : (
                  <X className="text-flame" size={14} />
                )}
              </span>
            </div>
          ))
        )}
      </div>
    </Panel>
  );
};
