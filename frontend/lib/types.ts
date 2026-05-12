/**
 * TypeScript mirrors of FastAPI pydantic schemas in `src/api/schemas.py`.
 *
 * Keep field names in sync with the backend — these are wire types.
 */

export type IsoDate = string; // "YYYY-MM-DD"

export interface HealthResponse {
  status: "ok";
  model_loaded: boolean;
  models_count: number;
}

export interface ModelInfo {
  name: string;
  threshold: number;
  features_used: string[];
  val_metrics: Record<string, number>;
  test_metrics: Record<string, number>;
}

export interface ModelsResponse {
  models: ModelInfo[];
  default_model: string | null;
}

export interface PredictRequest {
  ticker: string;
  date: IsoDate;
  model_name?: string | null;
}

export interface PredictResponse {
  ticker: string;
  date: IsoDate;
  model: string;
  probability: number;
  signal: 0 | 1;
  threshold: number;
  warnings: string[];
}

export interface BacktestRequest {
  ticker: string;
  start: IsoDate;
  end: IsoDate;
  model_name?: string | null;
  fee?: number;
  horizon?: number;
}

export interface EquityPoint {
  date: IsoDate;
  value: number;
}

export interface BacktestResponse {
  model: string;
  ticker: string;
  cum_return: number;
  sharpe: number;
  max_drawdown: number;
  trade_freq: number;
  n_trades: number;
  equity_curve: EquityPoint[];
  drawdown_curve: EquityPoint[];
}

export interface OhlcvBar {
  date: IsoDate;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  rsi_14: number | null;
  macd_hist: number | null;
  bollinger_pctb: number | null;
  sma_20: number | null;
}

export interface OhlcvResponse {
  ticker: string;
  start: IsoDate;
  end: IsoDate;
  bars: OhlcvBar[];
}

export interface TickersResponse {
  tickers: string[];
}

/** UI-only types — not part of the API. */
export type Timeframe = "1m" | "3m" | "6m" | "1y" | "2y" | "5y";
export type ThemeName = "kabu" | "washi";

export interface ForecastHistoryEntry {
  id: string;
  ticker: string;
  date: IsoDate;
  model: string;
  probability: number;
  threshold: number;
  signal: 0 | 1;
  shogun: boolean;
  createdAt: number;
  /** Realized direction once we know the future close (filled later). */
  realized?: 0 | 1 | null;
}
