"use client";

import { Swords } from "lucide-react";

import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

/**
 * Toggle that switches the forecast into "Shogun" mode — internally we
 * shrink the probability threshold to surface more aggressive signals.
 */
export const ShogunToggle = () => {
  const shogun = useAppStore((s) => s.shogun);
  const toggle = useAppStore((s) => s.toggleShogun);
  return (
    <button
      type="button"
      onClick={toggle}
      title={
        shogun
          ? "Режим Сёгун: агрессивная торговля (порог снижен)"
          : "Обычный режим: стандартный порог"
      }
      className={cn(
        "btn-ghost",
        shogun &&
          "border-gold/40 text-gold bg-gold/[0.06] hover:bg-gold/[0.1]",
      )}
    >
      <Swords
        size={14}
        className={cn("transition-transform", shogun && "rotate-12")}
      />
      <span className="font-jp">{shogun ? "将軍" : "庶民"}</span>
    </button>
  );
};
