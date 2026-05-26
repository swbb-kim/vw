"""핵심 로직 검증용 경량 테스트. 실행: python -m backtest.tests"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data, indicators as ta
from .engine import CostModel, run
from .strategy import BuyAndHold, SmaCross


def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = ta.sma(s, 2)
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == 1.5
    assert out.iloc[-1] == 4.5


def test_rsi_bounds():
    df = data.make_synthetic(days=200)
    r = ta.rsi(df["close"]).dropna()
    assert (r >= 0).all() and (r <= 100).all()


def test_buyhold_matches_benchmark_minus_entry_cost():
    df = data.make_synthetic(days=120)
    zero = CostModel(commission=0, sell_tax=0, slippage=0)
    res = run(df, BuyAndHold(), zero)
    # 비용이 0이면 매수후보유 = 벤치마크 (부동소수 오차 허용)
    assert abs(res.equity.iloc[-1] - res.benchmark.iloc[-1]) < 1e-9


def test_no_lookahead():
    # 신호가 다음 봉에 반영되는지: 1일차 포지션은 항상 0(전일 신호 없음)
    df = data.make_synthetic(days=60)
    res = run(df, SmaCross(3, 10), CostModel())
    assert res.positions.iloc[0] == 0.0


def test_costs_reduce_return():
    df = data.make_synthetic(days=200)
    cheap = run(df, SmaCross(5, 20), CostModel(0, 0, 0))
    pricey = run(df, SmaCross(5, 20), CostModel(0.001, 0.003, 0.002))
    assert pricey.equity.iloc[-1] < cheap.equity.iloc[-1]


def main() -> int:
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print("-" * 30)
    print(f"{len(tests) - failed}/{len(tests)} 통과")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
