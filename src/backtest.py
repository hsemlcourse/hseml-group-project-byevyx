from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def backtest_signals(
    df: pd.DataFrame,
    signals: np.ndarray,
    *,
    fee: float = 0.002,
    horizon: int = 1,
) -> dict[str, object]:
    """упрощённый бэктест: торгуем return за `horizon` дней когда signal==1.

    horizon=1 — классический next-day (старая семантика).
    horizon=5 — недельный таргет: на сигнал покупаем и держим 5 дней (равные доли,
    т.е. в каждый день одновременно может быть несколько перекрывающихся позиций;
    PnL дня = средний signal[t-h:t] * daily_return[t]).

    реализм:
    - комиссия `fee` на каждую сделку (вход+выход = 2*fee за сделку, амортизируется по дням).
    - сделки исполняются по close.
    """
    if len(df) != len(signals):
        raise ValueError(f"len(df)={len(df)} != len(signals)={len(signals)}")
    close = df["Close"].to_numpy(dtype=float)
    sig = np.asarray(signals).astype(float).copy()
    n = len(close)

    daily_ret = np.zeros(n)
    daily_ret[1:] = (close[1:] - close[:-1]) / close[:-1]

    # позиция t = средняя доля подписей на длительность последних `horizon` дней
    if horizon > 1:
        position = np.zeros(n)
        for t in range(n):
            start = max(0, t - horizon + 1)
            position[t] = sig[start : t + 1].mean()
        # комиссия амортизируется: вход+выход на полное горизонт-окно
        cost_per_day = 2.0 * fee / horizon
    else:
        position = sig.copy()
        cost_per_day = 2.0 * fee

    # позиция действует на следующий день, поэтому shift(1)
    position_lag = np.zeros(n)
    position_lag[1:] = position[:-1]
    daily_pnl = position_lag * daily_ret - (position_lag > 0).astype(float) * cost_per_day

    equity = np.cumprod(1.0 + daily_pnl)
    rolling_max = np.maximum.accumulate(equity)
    drawdown = equity / rolling_max - 1.0

    trade_days = int((sig > 0).sum())
    nonzero = daily_pnl[position_lag > 0]
    if nonzero.size == 0:
        sharpe = 0.0
    else:
        std = float(daily_pnl.std(ddof=1))
        sharpe = float(daily_pnl.mean() / std * np.sqrt(TRADING_DAYS)) if std > 0 else 0.0

    return {
        "cum_return": float(equity[-1] - 1.0),
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "n_trades": trade_days,
        "trade_freq": float((sig > 0).mean()),
        "equity_curve": pd.Series(equity, index=df.index, name="equity"),
        "drawdown_curve": pd.Series(drawdown, index=df.index, name="drawdown"),
    }


def backtest_with_sizing(
    df: pd.DataFrame,
    proba: np.ndarray,
    *,
    threshold: float = 0.5,
    fee: float = 0.002,
    horizon: int = 1,
    stop_loss: float | None = -0.03,
    max_position: float = 1.0,
    confidence_scaling: bool = True,
) -> dict[str, object]:
    """продвинутый бэктест: размер позиции = функция уверенности модели + stop-loss.

    Args:
        proba: P(up) для каждого дня.
        threshold: открываем позицию только если proba >= threshold.
        horizon: сколько дней держим позицию.
        stop_loss: если cumulative return позиции опускается ниже stop_loss — закрываем досрочно.
                   None отключает stop-loss.
        max_position: максимальная доля капитала в одной сделке (для рисковых сценариев < 1.0).
        confidence_scaling: если True, размер = (proba - threshold) / (1 - threshold) * max_position
                            (масштабируем уверенность от 0 до max_position).
                            если False — fixed-size = max_position.

    Логика:
    - сигнал на день t открывается по close дня t,
    - позиция держится до min(t+horizon, t_stop) где t_stop — день срабатывания stop-loss,
    - на закрытии берётся комиссия 2*fee.
    """
    if len(df) != len(proba):
        raise ValueError(f"len(df)={len(df)} != len(proba)={len(proba)}")
    close = df["Close"].to_numpy(dtype=float)
    p = np.asarray(proba, dtype=float)
    n = len(close)

    open_signal = p >= threshold
    if confidence_scaling:
        denom = max(1.0 - threshold, 1e-6)
        sizes = np.clip((p - threshold) / denom, 0.0, 1.0) * max_position
    else:
        sizes = np.where(open_signal, max_position, 0.0)
    sizes = sizes * open_signal.astype(float)

    daily_pnl = np.zeros(n)
    held_until = -1  # индекс, до которого занята позиция (включительно)
    n_trades = 0
    sum_size = 0.0

    t = 0
    while t < n - 1:
        if t > held_until and sizes[t] > 0:
            entry_price = close[t]
            size = sizes[t]
            sum_size += size
            n_trades += 1
            # держим максимум horizon дней или до stop-loss
            exit_t = min(t + horizon, n - 1)
            for d in range(t + 1, exit_t + 1):
                ret = (close[d] - entry_price) / entry_price
                if stop_loss is not None and ret <= stop_loss:
                    # закрываемся в этот день по stop-loss
                    exit_t = d
                    break
            # распределим pnl по дням удержания (geometric daily P&L, без аппроксимации)
            for d in range(t + 1, exit_t + 1):
                day_ret = (close[d] - close[d - 1]) / close[d - 1]
                daily_pnl[d] += size * day_ret
            # комиссия на вход в день t (и на выход в exit_t)
            daily_pnl[t] -= size * fee
            daily_pnl[exit_t] -= size * fee
            held_until = exit_t
        t += 1

    equity = np.cumprod(1.0 + daily_pnl)
    rolling_max = np.maximum.accumulate(equity)
    drawdown = equity / rolling_max - 1.0
    std = float(daily_pnl.std(ddof=1))
    sharpe = float(daily_pnl.mean() / std * np.sqrt(TRADING_DAYS)) if std > 0 else 0.0

    return {
        "cum_return": float(equity[-1] - 1.0),
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "n_trades": int(n_trades),
        "avg_size": float(sum_size / n_trades) if n_trades > 0 else 0.0,
        "trade_freq": float(open_signal.mean()),
        "equity_curve": pd.Series(equity, index=df.index, name="equity"),
        "drawdown_curve": pd.Series(drawdown, index=df.index, name="drawdown"),
    }


def buy_and_hold(df: pd.DataFrame, *, fee: float = 0.002) -> dict[str, object]:
    """реперная стратегия: покупаем в начале периода, держим до конца."""
    n = len(df)
    signals = np.ones(n, dtype=int)
    close = df["Close"].to_numpy(dtype=float)
    gross = close[-1] / close[0] - 1.0
    return {
        "cum_return": float(gross - 2.0 * fee),
        "sharpe": float("nan"),
        "max_drawdown": float("nan"),
        "n_trades": 1,
        "trade_freq": 1.0,
        "equity_curve": pd.Series(close / close[0], index=df.index, name="equity"),
        "drawdown_curve": pd.Series(close / np.maximum.accumulate(close) - 1.0, index=df.index, name="drawdown"),
        "signals": signals,
    }
