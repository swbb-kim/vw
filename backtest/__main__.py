"""CLI 진입점.

예시:
  # 합성데이터로 SMA 크로스 전략 백테스트 (네트워크 불필요)
  python -m backtest --source synthetic --strategy sma_cross --fast 5 --slow 20

  # CSV 파일로
  python -m backtest --source csv --csv data/005930.csv --strategy rsi

  # pykrx 자동수집 (네트워크 + KRX 계정 필요)
  python -m backtest --source pykrx --symbol 005930 --start 20230101 --end 20231231
"""
from __future__ import annotations

import argparse
import sys

from . import data as data_mod
from .engine import CostModel, run
from .metrics import format_summary, summarize
from .strategy import STRATEGIES


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="backtest", description="한국 주식 백테스트")
    p.add_argument(
        "--source",
        choices=["synthetic", "csv", "pykrx", "yfinance"],
        default="synthetic",
    )
    p.add_argument("--csv", help="CSV 경로 (--source csv)")
    p.add_argument("--symbol", help="종목코드 (예: 005930 또는 005930.KS)")
    p.add_argument("--start", help="시작일 (YYYYMMDD 또는 YYYY-MM-DD)")
    p.add_argument("--end", help="종료일")
    p.add_argument("--strategy", choices=list(STRATEGIES), default="sma_cross")
    p.add_argument("--fast", type=int, default=5)
    p.add_argument("--slow", type=int, default=20)
    p.add_argument("--rsi-window", type=int, default=14)
    p.add_argument("--rsi-low", type=float, default=30.0)
    p.add_argument("--rsi-high", type=float, default=70.0)
    p.add_argument("--commission", type=float, default=0.00015)
    p.add_argument("--sell-tax", type=float, default=0.0018)
    p.add_argument("--slippage", type=float, default=0.001)
    return p


def load_data(args):
    if args.source == "csv":
        if not args.csv:
            raise SystemExit("--source csv 에는 --csv 경로가 필요합니다.")
        return data_mod.load_csv(args.csv)
    if args.source == "pykrx":
        return data_mod.fetch_pykrx(args.symbol, args.start, args.end)
    if args.source == "yfinance":
        return data_mod.fetch_yfinance(args.symbol, args.start, args.end)
    return data_mod.make_synthetic()


def build_strategy(args):
    cls = STRATEGIES[args.strategy]
    if args.strategy == "sma_cross":
        return cls(fast=args.fast, slow=args.slow)
    if args.strategy == "rsi":
        return cls(window=args.rsi_window, low=args.rsi_low, high=args.rsi_high)
    return cls()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    df = load_data(args)
    strategy = build_strategy(args)
    costs = CostModel(
        commission=args.commission, sell_tax=args.sell_tax, slippage=args.slippage
    )
    result = run(df, strategy, costs)

    print(f"데이터 기간 : {df.index[0].date()} ~ {df.index[-1].date()}  ({len(df)} 거래일)")
    print(f"전략        : {args.strategy}")
    print("-" * 40)
    print(format_summary(summarize(result)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
