import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ForecastHistoryEntry, ThemeName, Timeframe } from "@/lib/types";

interface AppState {
  ticker: string;
  setTicker: (t: string) => void;

  timeframe: Timeframe;
  setTimeframe: (t: Timeframe) => void;

  favorites: string[];
  addFavorite: (ticker: string) => void;
  removeFavorite: (ticker: string) => void;

  modelName: string | null;
  setModelName: (name: string | null) => void;

  shogun: boolean;
  toggleShogun: () => void;

  theme: ThemeName;
  setTheme: (t: ThemeName) => void;

  sound: boolean;
  toggleSound: () => void;

  history: ForecastHistoryEntry[];
  pushHistory: (entry: ForecastHistoryEntry) => void;
  clearHistory: () => void;
}

const DEFAULT_FAVORITES = ["^GSPC", "AAPL", "MSFT", "JPM", "XOM"];

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ticker: "AAPL",
      setTicker: (t) => set({ ticker: t }),

      timeframe: "6m",
      setTimeframe: (t) => set({ timeframe: t }),

      favorites: DEFAULT_FAVORITES,
      addFavorite: (ticker) => {
        const t = ticker.trim().toUpperCase();
        if (!t) return;
        const list = get().favorites;
        if (list.includes(t)) return;
        set({ favorites: [...list, t] });
      },
      removeFavorite: (ticker) =>
        set({ favorites: get().favorites.filter((x) => x !== ticker) }),

      modelName: null,
      setModelName: (name) => set({ modelName: name }),

      shogun: false,
      toggleShogun: () => set({ shogun: !get().shogun }),

      theme: "kabu",
      setTheme: (t) => set({ theme: t }),

      sound: false,
      toggleSound: () => set({ sound: !get().sound }),

      history: [],
      pushHistory: (entry) =>
        set({ history: [entry, ...get().history].slice(0, 50) }),
      clearHistory: () => set({ history: [] }),
    }),
    {
      name: "kabu-app-store",
      version: 1,
    },
  ),
);
