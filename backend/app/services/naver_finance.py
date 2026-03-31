"""
네이버 금융 데이터 수집 서비스 (교차검증용)
-- yfinance가 한국 종목(*.KS, *.KQ)에서 불안정할 때 fallback으로 사용
-- 네이버 금융 API는 별도 Key 없이 사용 가능
-- 이전 DART 프로젝트에서 검증된 패턴 재활용
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# 네이버 금융 차트 API 기본 URL
NAVER_CHART_URL = "https://fchart.stock.naver.com/sise.nhn"
NAVER_API_URL = "https://m.stock.naver.com/api/stock"


def _clean_ticker_for_naver(ticker: str) -> Optional[str]:
    """
    yfinance 티커를 네이버 금융 종목코드로 변환
    예: '005380.KS' → '005380', '000270.KQ' → '000270'
    미국 종목이면 None 반환 (네이버에서 한국 종목만 지원)
    """
    if ".KS" in ticker or ".KQ" in ticker:
        return ticker.split(".")[0]
    if ticker == "^KS11":
        return "KOSPI"
    if ticker == "^GSPC":
        return "SPI@SPX"  # 네이버 S&P 500 심볼
    return None


def get_naver_stock_price(ticker: str, days: int = 365) -> Optional[pd.DataFrame]:
    """
    네이버 금융에서 일봉 데이터 수집
    - ticker: yfinance 형식 (예: '005380.KS') 또는 네이버 형식 (예: '005380')
    - days: 수집할 일수
    - 반환: DataFrame (columns: Date, Open, High, Low, Close, Volume) 또는 None

    왜 이 방법을 쓰나:
    네이버 금융의 fchart API는 XML 형태로 일봉 데이터를 제공하며,
    별도 인증 없이 접근 가능. yfinance 대비 한국 종목 안정성이 높음.
    """
    code = _clean_ticker_for_naver(ticker) or ticker

    try:
        params = {
            "symbol": code,
            "timeframe": "day",
            "count": days,
            "requestType": 0,
        }

        response = requests.get(NAVER_CHART_URL, params=params, timeout=10)
        response.raise_for_status()

        # XML 파싱 (간단한 패턴 매칭 — lxml 의존성 제거)
        import re
        items = re.findall(r'<item data="([^"]+)"', response.text)

        if not items:
            logger.warning(f"[네이버-{code}] 데이터 없음")
            return None

        records = []
        for item in items:
            parts = item.split("|")
            if len(parts) >= 6:
                records.append({
                    "Date": pd.to_datetime(parts[0]),
                    "Open": float(parts[1]),
                    "High": float(parts[2]),
                    "Low": float(parts[3]),
                    "Close": float(parts[4]),
                    "Volume": int(parts[5]),
                })

        if not records:
            return None

        df = pd.DataFrame(records)
        df = df.set_index("Date").sort_index()
        logger.info(f"[네이버-{code}] {len(df)}행 수집 완료")
        return df

    except Exception as e:
        logger.error(f"[네이버-{code}] 수집 실패: {e}")
        return None


def get_naver_stock_info(code: str) -> Optional[dict]:
    """
    네이버 금융 모바일 API에서 종목 기본 정보 수집
    - 현재가, 전일대비, 시가총액, PER, PBR 등
    """
    try:
        url = f"{NAVER_API_URL}/{code}/basic"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        return {
            "name": data.get("stockName", ""),
            "price": data.get("closePrice", ""),
            "change_rate": data.get("compareToPreviousClosePrice", ""),
            "market_cap": data.get("marketValue", ""),
            "per": data.get("per", ""),
            "pbr": data.get("pbr", ""),
            "eps": data.get("eps", ""),
        }

    except Exception as e:
        logger.error(f"[네이버 기본정보-{code}] 수집 실패: {e}")
        return None


def cross_validate_price(
    ticker: str,
    yf_data: Optional[pd.DataFrame],
    tolerance: float = 0.02
) -> pd.DataFrame:
    """
    yfinance와 네이버 금융 데이터를 교차검증
    -- 두 소스의 종가 차이가 tolerance(기본 2%) 이상이면 경고 로그
    -- yfinance가 None이면 네이버 데이터로 완전 대체
    -- 네이버가 None이면 yfinance 그대로 사용

    왜 이 로직이 필요한가:
    yfinance는 한국 종목에서 간헐적으로 빈 데이터를 반환하거나
    종가가 부정확한 경우가 있음. 네이버를 보조 소스로 두면 안정성 향상.
    """
    naver_code = _clean_ticker_for_naver(ticker)

    # 미국 종목 및 지수 대응
    if naver_code is None:
        # 야후 지수 티커(^GSPC 등)는 네이버에서 별도 처리 가능할 경우 추가
        if yf_data is not None:
            return yf_data
        return pd.DataFrame()

    # 네이버 데이터 수집
    naver_data = get_naver_stock_price(ticker)

    # Case 1: yfinance 실패 → 네이버로 완전 대체
    if yf_data is None or yf_data.empty:
        if naver_data is not None and not naver_data.empty:
            logger.info(f"[{ticker}] yfinance 실패 → 네이버 데이터로 대체")
            return naver_data
        logger.error(f"[{ticker}] yfinance, 네이버 모두 실패")
        return pd.DataFrame()

    # Case 2: 네이버 실패 → yfinance 그대로
    if naver_data is None or naver_data.empty:
        logger.info(f"[{ticker}] 네이버 실패 → yfinance 데이터 사용")
        return yf_data

    # Case 3: 둘 다 있음 → 종가 비교 검증
    try:
        # 최근 5일 종가 비교
        yf_recent = yf_data["Close"].tail(5)
        naver_recent = naver_data["Close"].tail(5)

        # 날짜가 겹치는 부분만 비교
        common_dates = yf_recent.index.intersection(naver_recent.index)
        if len(common_dates) > 0:
            yf_prices = yf_recent.loc[common_dates]
            naver_prices = naver_recent.loc[common_dates]

            # 오차율 계산
            diff_rate = abs(yf_prices - naver_prices) / naver_prices
            max_diff = diff_rate.max()

            if max_diff > tolerance:
                logger.warning(
                    f"[{ticker}] yfinance-네이버 종가 차이 {max_diff:.1%} > {tolerance:.0%} "
                    f"→ 네이버 데이터 우선 사용"
                )
                return naver_data
            else:
                logger.info(f"[{ticker}] 교차검증 통과 (최대 오차: {max_diff:.2%})")
    except Exception as e:
        logger.warning(f"[{ticker}] 교차검증 중 오류: {e}")

    return yf_data

def get_top_200_stocks() -> list:
    """
    네이버 금융 API를 통해 KOSPI 상위 100개, KOSDAQ 상위 100개 종목을 가져옵니다.
    반환 형태: [(종목코드, 종목명), ...]
    """
    import requests
    headers = {"User-Agent": "Mozilla/5.0"}
    tickers = []
    
    try:
        kospi = requests.get("https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=100", headers=headers, timeout=10).json()
        for s in kospi.get("stocks", []):
            tickers.append((s["itemCode"], s["stockName"]))
    except Exception as e:
        logger.error(f"[네이버] KOSPI Top 100 수집 실패: {e}")
        
    try:
        kosdaq = requests.get("https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ?page=1&pageSize=100", headers=headers, timeout=10).json()
        for s in kosdaq.get("stocks", []):
            tickers.append((s["itemCode"], s["stockName"]))
    except Exception as e:
        logger.error(f"[네이버] KOSDAQ Top 100 수집 실패: {e}")

    return tickers
