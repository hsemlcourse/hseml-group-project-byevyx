import clsx, { type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { IsoDate, Timeframe } from "@/lib/types";

/** Tailwind-aware className combiner. */
export const cn = (...inputs: ClassValue[]): string =>
  twMerge(clsx(inputs));

/** Today as ISO YYYY-MM-DD. */
export const today = (): IsoDate => new Date().toISOString().slice(0, 10);

/** Subtract `days` from `from` (defaults to today) and return ISO date. */
export const minusDays = (days: number, from: Date = new Date()): IsoDate => {
  const d = new Date(from);
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
};

/** How many days of history a timeframe should pull. */
export const timeframeDays: Record<Timeframe, number> = {
  "1m": 35,
  "3m": 100,
  "6m": 200,
  "1y": 380,
  "2y": 760,
  "5y": 1900,
};

export const formatPercent = (value: number, digits = 2): string =>
  `${(value * 100).toFixed(digits)}%`;

export const formatSignedPercent = (value: number, digits = 2): string => {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(digits)}%`;
};

export const formatNumber = (value: number, digits = 2): string =>
  Number.isFinite(value) ? value.toFixed(digits) : "—";

export const formatPrice = (value: number): string => {
  if (!Number.isFinite(value)) return "—";
  if (value >= 1000) return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return value.toFixed(2);
};

/** Cheap, deterministic id used for client-side records. */
export const cuid = (): string =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

/** Clamp a value into [min, max]. */
export const clamp = (value: number, min: number, max: number): number =>
  Math.min(Math.max(value, min), max);
