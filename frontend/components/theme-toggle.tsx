"use client";

import { Moon, ScrollText } from "lucide-react";

import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

/** Switches between the default night Edo theme and the Washi paper light theme. */
export const ThemeToggle = () => {
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const isWashi = theme === "washi";
  return (
    <button
      type="button"
      onClick={() => setTheme(isWashi ? "kabu" : "washi")}
      className={cn("btn-ghost")}
      title={
        isWashi
          ? "Переключить на ночную тему"
          : "Переключить на бумажный свиток"
      }
    >
      {isWashi ? <Moon size={14} /> : <ScrollText size={14} />}
      <span className="font-jp">{isWashi ? "夜" : "和紙"}</span>
    </button>
  );
};
