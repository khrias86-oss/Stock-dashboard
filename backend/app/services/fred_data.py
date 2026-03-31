"""
FRED API 데이터 수집 서비스
-- 미국 M2 통화량 등 FRED에서만 가져올 수 있는 데이터 수집
-- API Key가 없으면 None 반환 (Fallback 처리는 호출 측에서)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests

from app.config import settings

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def _is_fred_available() -> bool:
    """FRED API Key가 유효하게 설정되어 있는지 확인"""
    key = settings.FRED_API_KEY
    return bool(key and key != "your_fred_api_key_here")


def get_fred_series(
    series_id: str,
    months: int = 12,
    frequency: str = "m",  # m=월간, d=일간, w=주간
    label: str = "",
) -> Optional[pd.DataFrame]:
    """
    FRED API에서 시계열 데이터를 가져옴
    - series_id: FRED 시리즈 ID (예: 'M2SL' = 미국 M2 통화량)
    - months: 최근 N개월
    - frequency: 데이터 빈도 (m: 월간, d: 일간)
    - 반환: DataFrame (index=Date, columns=[value]) 또는 None
    """
    if not _is_fred_available():
        logger.warning(f"[FRED-{series_id}] API Key 미설정 → 스킵")
        return None

    try:
        end = datetime.now()
        start = end - timedelta(days=months * 30)

        params = {
            "series_id": series_id,
            "api_key": settings.FRED_API_KEY,
            "file_type": "json",
            "observation_start": start.strftime("%Y-%m-%d"),
            "observation_end": end.strftime("%Y-%m-%d"),
            "frequency": frequency,
        }

        response = requests.get(FRED_BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        observations = data.get("observations", [])
        if not observations:
            logger.warning(f"[FRED-{label or series_id}] 데이터 없음")
            return None

        records = []
        for obs in observations:
            val = obs.get("value", ".")
            if val == ".":  # FRED에서 결측값을 "."으로 표시
                continue
            records.append({
                "date": pd.to_datetime(obs["date"]),
                "value": float(val),
            })

        if not records:
            return None

        df = pd.DataFrame(records).set_index("date")
        logger.info(f"[FRED-{label or series_id}] {len(df)}행 수집 완료")
        return df

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            logger.error(f"[FRED-{series_id}] 잘못된 시리즈 ID 또는 파라미터: {e}")
        elif e.response.status_code == 429:
            logger.error(f"[FRED-{series_id}] Rate Limit 초과")
        else:
            logger.error(f"[FRED-{series_id}] HTTP 에러: {e}")
        return None
    except Exception as e:
        logger.error(f"[FRED-{series_id}] 수집 실패: {e}")
        return None


def get_us_m2_yoy() -> Optional[pd.DataFrame]:
    """
    미국 M2 통화량 YoY 증감률 계산
    - FRED 시리즈: M2SL (M2 Money Stock, 월간, 계절조정)
    - 24개월치를 가져와서 12개월 전 대비 증감률 계산
    - 반환: DataFrame (columns=[m2_us_yoy]) 또는 None
    """
    # 24개월치 데이터로 YoY 계산 가능하게
    df = get_fred_series("M2SL", months=24, frequency="m", label="미국 M2")
    if df is None or len(df) < 13:
        logger.warning("[FRED] M2 데이터 부족 (최소 13개월 필요)")
        return None

    # YoY 증감률 (%) = (현재값 - 12개월전값) / 12개월전값 * 100
    df["m2_us_yoy"] = df["value"].pct_change(periods=12) * 100
    df = df.dropna(subset=["m2_us_yoy"])

    return df[["m2_us_yoy"]]


def get_us_treasury_spread() -> Optional[pd.DataFrame]:
    """
    미국 장단기 금리차 (10Y - 2Y)
    - FRED 시리즈: T10Y2Y (10-Year Treasury Minus 2-Year Treasury)
    - 이 데이터는 yfinance보다 FRED가 더 정확함
    """
    df = get_fred_series("T10Y2Y", months=12, frequency="d", label="10Y-2Y 금리차")
    if df is None:
        return None

    df = df.rename(columns={"value": "spread"})
    return df
