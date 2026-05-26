"""백테스트 엔진. 거래비용(수수료, 슬리피지, 한국 증권거래세)을 반영한다."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .strategy import Strategy


@dataclass
class CostModel:
    """한국 주식 기본값. 수치는 비율(0.001 = 0.1%)."""

    commission: float = 0.00015  # 편도 위탁수수료 (증권사별 상이)
    sell_tax: float = 0.0018     # 증권거래세 (매도 시에만, 2024년 기준 ~0.18%)
    slippage: float = 0.001      # 체결 미끄러짐 (편도)


@dataclass
class BacktestResult:
    equity: pd.Series          # 전략 누적 자산곡선 (시작=1.0)
    benchmark: pd.Series       # 매수후보유 자산곡선
    positions: pd.Series       # 실제 적용된 보유비중
    trades: pd.DataFrame       # 라운드트립 매매 기록
    returns: pd.Series         # 전략 일간 수익률


def run(
    df: pd.DataFrame,
    strategy: Strategy,
    costs: CostModel | None = None,
) -> BacktestResult:
    """df: 'close' 컬럼 필수, DatetimeIndex 권장."""
    if "close" not in df.columns:
        raise ValueError("입력 데이터에 'close' 컬럼이 필요합니다.")
    costs = costs or CostModel()

    price = df["close"].astype(float)
    price_ret = price.pct_change().fillna(0.0)

    target = strategy.generate_positions(df).astype(float)
    # 당일 신호는 다음날 체결 (룩어헤드 방지)
    position = target.shift(1).fillna(0.0)

    # 비중 변화량 = 매매 회전율
    turnover = position.diff().fillna(position)
    buy = turnover.clip(lower=0.0)
    sell = (-turnover).clip(lower=0.0)

    buy_cost = buy * (costs.commission + costs.slippage)
    sell_cost = sell * (costs.commission + costs.slippage + costs.sell_tax)
    cost = buy_cost + sell_cost

    strat_ret = position * price_ret - cost
    equity = (1.0 + strat_ret).cumprod()
    benchmark = (1.0 + price_ret).cumprod()

    trades = _extract_trades(price, position)

    return BacktestResult(
        equity=equity,
        benchmark=benchmark,
        positions=position,
        trades=trades,
        returns=strat_ret,
    )


def _extract_trades(price: pd.Series, position: pd.Series) -> pd.DataFrame:
    """0->1 진입, 1->0 청산을 라운드트립으로 묶는다 (롱 온리 가정)."""
    rows = []
    entry_date = None
    entry_price = None
    prev = 0.0
    for date, pos in position.items():
        if prev <= 0.0 and pos > 0.0:
            entry_date, entry_price = date, price.loc[date]
        elif prev > 0.0 and pos <= 0.0 and entry_price is not None:
            ret = price.loc[date] / entry_price - 1.0
            rows.append(
                {
                    "entry_date": entry_date,
                    "exit_date": date,
                    "entry_price": entry_price,
                    "exit_price": price.loc[date],
                    "return": ret,
                }
            )
            entry_date = entry_price = None
        prev = pos
    # 미청산 포지션
    if entry_price is not None:
        last = price.index[-1]
        rows.append(
            {
                "entry_date": entry_date,
                "exit_date": last,
                "entry_price": entry_price,
                "exit_price": price.iloc[-1],
                "return": price.iloc[-1] / entry_price - 1.0,
            }
        )
    return pd.DataFrame(rows)
