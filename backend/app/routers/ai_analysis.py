"""
AI 분석 API 라우터
-- 5개 거시지표의 시그널 + AI 의견을 통합 반환
-- 캐시 TTL이 긴 편 (10분) — AI 호출 비용 절감
"""

import logging
from fastapi import APIRouter

from app.services.market_data import (
    get_exchange_divergence_data,
    get_volatility_data,
    get_liquidity_data,
    get_leading_indicator_data,
    get_sector_strength_data,
)
from app.services.signal_engine import analyze_signals
from app.services.screening_engine import get_top_picks
from app.services.gemini_ai import analyze_with_ai, analyze_comprehensive
from app.cache.cache_manager import cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI 분석"])


@router.get("/macro-analysis")
async def get_macro_analysis():
    # ... (기존 코드와 동일)
    cache_key = "ai_macro_analysis"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        macro_data = {
            "exchange": get_exchange_divergence_data(),
            "volatility": get_volatility_data(),
            "liquidity": get_liquidity_data(),
            "leading": get_leading_indicator_data(),
            "sector": get_sector_strength_data(),
        }
        signals = analyze_signals(macro_data)
        ai_result = analyze_with_ai(signals)
        result = {
            "signals": signals,
            "ai_comments": ai_result,
            "status": "success",
        }
        cache.set(cache_key, result, ttl=600)
        return result
    except Exception as e:
        logger.error(f"[AI 분석] 오류: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/comprehensive-analysis")
async def get_comprehensive_analysis(body: dict = {}):
    """
    거시+스크리닝+포트폴리오 통합 AI 분석
    -- POST body: {"portfolio": {...분석된 포트폴리오 결과...}}
    -- 캐시 사용 시 주의 (포트폴리오가 사용자마다 다를 수 있음)
    """
    try:
        # 1. 거시지표 데이터 및 시그널
        macro_data = {
            "exchange": get_exchange_divergence_data(),
            "volatility": get_volatility_data(),
            "liquidity": get_liquidity_data(),
            "leading": get_leading_indicator_data(),
            "sector": get_sector_strength_data(),
        }
        macro_signals = analyze_signals(macro_data)

        # 2. 스크리닝 데이터 (상위 10개)
        screening_data = get_top_picks(limit=10)

        # 3. 포트폴리오 데이터 (요청 바디에서 받음)
        portfolio_data = body.get("portfolio")

        # 4. 통합 AI 분석 (1회 호출)
        ai_result = analyze_comprehensive(macro_signals, screening_data, portfolio_data)

        return {
            "status": "success",
            "macro_signals": macro_signals,
            "ai_analysis": ai_result
        }

    except Exception as e:
        logger.error(f"[통합 AI 분석] 오류: {e}")
        return {"status": "error", "error": str(e)}

