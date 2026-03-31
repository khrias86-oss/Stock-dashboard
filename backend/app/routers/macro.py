"""
거시지표(Macro) API 라우터
-- 5개 거시지표 차트 데이터를 제공하는 REST 엔드포인트
-- 캐싱을 적용하여 불필요한 외부 API 호출을 방지
"""

from fastapi import APIRouter, HTTPException
import logging

from app.services.market_data import (
    get_exchange_divergence_data,
    get_volatility_data,
    get_liquidity_data,
    get_leading_indicator_data,
    get_sector_strength_data,
)
from app.cache.cache_manager import cache
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/macro", tags=["거시지표"])


def _get_cached_or_fetch(cache_key: str, fetch_fn, ttl: int = None):
    """
    캐시된 데이터가 있으면 반환, 없으면 fetch_fn 실행 후 캐싱
    -- 모든 엔드포인트에서 공통으로 사용하는 패턴
    """
    if ttl is None:
        ttl = settings.CACHE_TTL_MARKET_HOURS

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = fetch_fn()
        cache.set(cache_key, data, ttl=ttl)
        return data
    except Exception as e:
        logger.error(f"[{cache_key}] 데이터 수집 실패: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"데이터 수집 중 오류 발생: {str(e)}"
        )


@router.get("/exchange-divergence")
def exchange_divergence():
    """
    그래프 1: 환율 및 외국인 수급 다이버전스
    - 원/달러 환율, 달러인덱스, KOSPI, 거래량
    - 다이버전스 구간 자동 감지
    """
    return _get_cached_or_fetch(
        "macro_exchange_divergence",
        get_exchange_divergence_data
    )


@router.get("/volatility")
def volatility():
    """
    그래프 2: 시장 변동성 및 지수 바닥 확인
    - VIX, S&P500, KOSPI
    - VIX ≥ 30 알림 시점
    """
    return _get_cached_or_fetch(
        "macro_volatility",
        get_volatility_data
    )


@router.get("/liquidity")
def liquidity():
    """
    그래프 3: 유동성 지표
    - M2 YoY 증감률, KOSPI, S&P500
    - 유동성 변곡점
    """
    return _get_cached_or_fetch(
        "macro_liquidity",
        get_liquidity_data
    )


@router.get("/leading-indicator")
def leading_indicator():
    """
    그래프 4: 경기 선행 지표
    - 미국 10Y-2Y 장단기 금리차
    - 역전 구간 및 정상화 시점
    """
    return _get_cached_or_fetch(
        "macro_leading_indicator",
        get_leading_indicator_data
    )


@router.get("/sector-strength")
def sector_strength():
    """
    그래프 5: 주요 섹터 ETF 상대강도
    - 반도체, 2차전지, 자동차, 금융
    - 자동차 벤치마킹 개별 종목
    """
    return _get_cached_or_fetch(
        "macro_sector_strength",
        get_sector_strength_data
    )


@router.delete("/cache")
def clear_cache():
    """관리용: 거시지표 캐시 전체 삭제"""
    for key in [
        "macro_exchange_divergence",
        "macro_volatility",
        "macro_liquidity",
        "macro_leading_indicator",
        "macro_sector_strength",
    ]:
        cache.invalidate(key)
    return {"message": "거시지표 캐시가 클리어되었습니다."}
