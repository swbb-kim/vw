"""성과 지표 계산."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def total_return(equity: pd.Series) -> float:
    return float(equity.iloc[-1] - 1.0)


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    years = len(equity) / TRADING_DAYS
    if years <= 0:
        return 0.0
    return float(equity.iloc[-1] ** (1 / years) - 1.0)


def max_drawdown(equity: pd.Series) -> float:
    """최대 낙폭 (음수)."""
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def sharpe(returns: pd.Series, risk_free: float = 0.0) -> float:
    """연율화 샤프지수 (일간 수익률 기준)."""
    excess = returns - risk_free / TRADING_DAYS
    std = excess.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(np.sqrt(TRADING_DAYS) * excess.mean() / std)


def win_rate(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    return float((trades["return"] > 0).mean())


def summarize(result) -> dict:
    eq = result.equity
    return {
        "총수익률": total_return(eq),
        "CAGR": cagr(eq),
        "최대낙폭(MDD)": max_drawdown(eq),
        "샤프지수": sharpe(result.returns),
        "매매횟수": int(len(result.trades)),
        "승률": win_rate(result.trades),
        "벤치마크_총수익률": total_return(result.benchmark),
    }


def format_summary(summary: dict) -> str:
    lines = []
    for k, v in summary.items():
        if k in ("매매횟수",):
            lines.append(f"{k:<16}: {v}")
        elif "수익률" in k or k in ("CAGR", "최대낙폭(MDD)", "승률"):
            lines.append(f"{k:<16}: {v * 100:+.2f}%")
        else:
            lines.append(f"{k:<16}: {v:.3f}")
    return "\n".join(lines)
