import type {
  BacktestRequest,
  BacktestResponse,
  HealthResponse,
  ModelsResponse,
  OhlcvResponse,
  PredictRequest,
  PredictResponse,
  TickersResponse,
} from "@/lib/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

/**
 * Lightweight typed wrapper around `fetch` that throws a readable error for
 * non-2xx responses. Used by all API helpers below.
 */
const request = async <T>(
  path: string,
  init?: RequestInit,
): Promise<T> => {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      accept: "application/json",
      ...(init?.body ? { "content-type": "application/json" } : {}),
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      // ignore body parse errors — fall back to statusText
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return (await res.json()) as T;
};

export const api = {
  health: () => request<HealthResponse>("/health"),
  models: () => request<ModelsResponse>("/models"),
  tickers: () => request<TickersResponse>("/tickers"),
  ohlcv: (params: { ticker: string; start: string; end: string }) => {
    const qs = new URLSearchParams({
      ticker: params.ticker,
      start: params.start,
      end: params.end,
    }).toString();
    return request<OhlcvResponse>(`/ohlcv?${qs}`);
  },
  predict: (body: PredictRequest) =>
    request<PredictResponse>("/predict", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  backtest: (body: BacktestRequest) =>
    request<BacktestResponse>("/backtest", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export { API_URL };
