"""매매 전략. 전략은 가격 데이터를 받아 목표 보유비중(0=현금, 1=풀매수)을 돌려준다.

룩어헤드(미래참조) 편향을 막기 위해, 여기서 만든 신호는 엔진에서 한 칸 미뤄
다음 봉에 체결된다고 가정한다. (당일 종가 신호 -> 다음날 반영)
"""
from __future__ import annotations

import pandas as pd

from . import indicators as ta


class Strategy:
    name = "base"

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """df['close'] 등을 보고 0/1 목표 비중 시리즈를 반환."""
        raise NotImplementedError


class BuyAndHold(Strategy):
    name = "buyhold"

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(1.0, index=df.index)


class SmaCross(Strategy):
    """골든/데드 크로스: 단기 이평 > 장기 이평이면 매수."""

    name = "sma_cross"

    def __init__(self, fast: int = 5, slow: int = 20):
        if fast >= slow:
            raise ValueError("fast 기간은 slow 기간보다 작아야 합니다.")
        self.fast = fast
        self.slow = slow

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        fast = ta.sma(df["close"], self.fast)
        slow = ta.sma(df["close"], self.slow)
        pos = (fast > slow).astype(float)
        pos[slow.isna()] = 0.0
        return pos


class RsiReversion(Strategy):
    """RSI 평균회귀: 과매도(<low)에서 매수, 과매수(>high)에서 청산."""

    name = "rsi"

    def __init__(self, window: int = 14, low: float = 30.0, high: float = 70.0):
        self.window = window
        self.low = low
        self.high = high

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        r = ta.rsi(df["close"], self.window)
        pos = pd.Series(pd.NA, index=df.index, dtype="Float64")
        pos[r < self.low] = 1.0
        pos[r > self.high] = 0.0
        # 신호가 없는 구간은 직전 상태 유지, 시작은 현금
        pos = pos.ffill().fillna(0.0)
        return pos.astype(float)


STRATEGIES = {
    BuyAndHold.name: BuyAndHold,
    SmaCross.name: SmaCross,
    RsiReversion.name: RsiReversion,
}
