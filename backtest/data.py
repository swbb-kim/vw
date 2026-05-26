"""가격 데이터 로딩.

우선순위 있는 3가지 소스를 지원한다:
  1) CSV         : 증권사/HTS에서 내려받은 일봉 (date, open, high, low, close, volume)
  2) pykrx       : 한국거래소 일봉 자동 수집 (네트워크 + KRX 계정 필요)
  3) yfinance    : 야후 파이낸스 (예: '005930.KS')
  4) synthetic   : 시연/테스트용 합성 데이터 (네트워크 불필요)

클라우드 실행 환경은 외부망이 차단될 수 있으므로, 그럴 때는 CSV나 synthetic을 사용한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_REQUIRED = ["close"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: c.lower() for c in df.columns})
    rename_map = {
        "날짜": "date", "시가": "open", "고가": "high",
        "저가": "low", "종가": "close", "거래량": "volume",
        "adj close": "close",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    df = df.sort_index()
    for col in _REQUIRED:
        if col not in df.columns:
            raise ValueError(f"필수 컬럼 누락: {col}. 보유 컬럼={list(df.columns)}")
    return df


def load_csv(path: str) -> pd.DataFrame:
    return _normalize(pd.read_csv(path))


def fetch_pykrx(symbol: str, start: str, end: str) -> pd.DataFrame:
    """예: symbol='005930', start='20230101', end='20231231'."""
    from pykrx import stock

    df = stock.get_market_ohlcv(start, end, symbol)
    df = df.rename(
        columns={"시가": "open", "고가": "high", "저가": "low",
                 "종가": "close", "거래량": "volume"}
    )
    df.index.name = "date"
    return _normalize(df.reset_index())


def fetch_yfinance(symbol: str, start: str, end: str) -> pd.DataFrame:
    """예: symbol='005930.KS'."""
    import yfinance as yf

    df = yf.download(symbol, start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index().rename(columns={"Date": "date"})
    return _normalize(df)


def make_synthetic(
    days: int = 504, seed: int = 42, start: str = "2023-01-02", s0: float = 50000.0,
    mu: float = 0.08, sigma: float = 0.25,
) -> pd.DataFrame:
    """기하 브라운 운동으로 만든 가짜 일봉 (시연/단위테스트용)."""
    rng = np.random.default_rng(seed)
    dt = 1 / 252
    shocks = rng.normal((mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), days)
    close = s0 * np.exp(np.cumsum(shocks))
    dates = pd.bdate_range(start=start, periods=days)
    intraday = 1 + rng.normal(0, 0.005, days)
    df = pd.DataFrame(
        {
            "date": dates,
            "open": close / intraday,
            "high": close * (1 + np.abs(rng.normal(0, 0.006, days))),
            "low": close * (1 - np.abs(rng.normal(0, 0.006, days))),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, days),
        }
    )
    return _normalize(df)
