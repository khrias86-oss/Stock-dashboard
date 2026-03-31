"""
Gemini AI 일괄 분석 서비스
-- 5개 거시지표의 시그널을 모아서 Gemini에 1회만 호출
-- 토큰 최적화: 원시 데이터 대신 시그널 요약만 전송
-- 결과: 차트별 1~2줄 코멘트 + 전체 종합 의견
"""

import logging
import json
from typing import Optional

import requests

from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def _is_gemini_available() -> bool:
    """Gemini API Key 유효 확인"""
    key = settings.GEMINI_API_KEY
    return bool(key and key != "your_gemini_api_key_here")


def analyze_comprehensive(macro_signals: dict, screening_data: dict, portfolio_data: Optional[dict] = None) -> Optional[dict]:
    """
    거시지표 + 스크리닝 + 포트폴리오 데이터를 통합하여 AI 분석 (1회 호출)
    -- 토큰 최적화: 시그널 및 요약 정보만 전달
    -- 결과: 섹션별 코멘트 + 섹션별 요약 + 전체 종합 요약
    """
    if not _is_gemini_available():
        logger.info("[Gemini] API Key 미설정 → AI 분석 스킵")
        return _generate_comprehensive_fallback(macro_signals, screening_data, portfolio_data)

    prompt = _build_comprehensive_prompt(macro_signals, screening_data, portfolio_data)

    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={settings.GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 1500,
                    "responseMimeType": "application/json",
                },
            },
            timeout=40,
        )
        response.raise_for_status()
        result = response.json()

        text = result["candidates"][0]["content"]["parts"][0]["text"]
        ai_result = json.loads(text)
        logger.info(f"[Gemini] 통합 AI 분석 완료")
        return ai_result

    except Exception as e:
        logger.error(f"[Gemini] 통합 분석 실패: {e}")
        return _generate_comprehensive_fallback(macro_signals, screening_data, portfolio_data)


def _build_comprehensive_prompt(macro: dict, screening: dict, portfolio: Optional[dict]) -> str:
    """통합 분석을 위한 상세 프롬프트 구성"""
    
    # 1. 거시지표 섹션 구성
    macro_md = "\n".join([
        f"- {k.capitalize()}: {v.get('summary', 'N/A')} (시그널: {', '.join([s['msg'] for s in v.get('signals', [])])})"
        for k, v in macro.items()
    ])

    # 2. 스크리닝 섹션 구성
    picks = screening.get("top_picks", [])
    screening_md = "\n".join([
        f"- {p['name']}({p['stock_code']}): PER {p['per']}, PBR {p['pbr']}, ROE {p['roe']}%, 점수 {p['score']}, 판정 {p['signal']}"
        for p in picks[:5] # 상위 5개만 전달
    ])

    # 3. 포트폴리오 섹션 구성
    portfolio_md = "데이터 없음"
    if portfolio and portfolio.get("holdings"):
        summary = portfolio["summary"]
        holdings = portfolio["holdings"]
        portfolio_md = f"총수익률: {summary['total_return']}%, 종목수: {summary['holdings_count']}\n"
        portfolio_md += "\n".join([
            f"- {h['name']}: 수익률 {h['return_pct']}%, RSI {h['rsi']}, 판정 {h['signal']['overall']}"
            for h in holdings
        ])

    return f"""당신은 대한민국 최고의 주식 투자 전략가입니다. 
거시 경제(Macro), 시장 탐색(Screening), 개인 포트폴리오(Portfolio) 데이터를 종합 분석하여 최적의 투자 전략을 제시하세요.

### 1. 거시 경제 데이터 (거시지표 시그널)
{macro_md}

### 2. 시장 유망주 데이터 (Top 5)
{screening_md}

### 3. 개인 포트폴리오 데이터
{portfolio_md}

### 분석 요청 및 응답 형식 (JSON):
반드시 아래 JSON 구조로 응답하세요.

{{
  "macro": {{
    "exchange_comment": "환율/수급 1~2줄",
    "volatility_comment": "VIX/변동성 1~2줄",
    "liquidity_comment": "유동성/M2 1~2줄",
    "leading_comment": "장단기 금리차 1~2줄",
    "sector_comment": "섹터 강도 1~2줄",
    "summary": "거시 경제 관점의 섹션 요약 (2~3줄)"
  }},
  "screening": {{
    "summary": "시장 유망주 섹션 요약 및 주도 섹터 분석 (2~3줄)",
    "top_pick_reason": "Top 1 종목 추천 사유"
  }},
  "portfolio": {{
    "summary": "내 포트폴리오 요약 및 리스크 진단 (2~3줄)",
    "rebalance_tip": "포트폴리오 조정 제안 1줄"
  }},
  "overall": {{
    "signal": "강력매수/매수/관망/주의/매도 중 택1",
    "summary": "모든 내용을 고려한 최종 투자 전략 요약 (4~5줄)",
    "key_actions": ["당장 실행해야 할 액션 1", "액션 2"]
  }}
}}

주의사항:
- 모든 설명은 한국어로 작성하세요.
- 데이터의 수치와 시그널을 근거로 논리적인 결론을 도출하세요.
- 친절하면서도 전문적인 어조를 유지하세요."""


def _generate_comprehensive_fallback(macro: dict, screening: dict, portfolio: Optional[dict]) -> dict:
    """Fallback: 규칙 기반 기본 요약 생성"""
    return {
        "macro": {
            "exchange_comment": "환율 변동성에 주의가 필요합니다.",
            "volatility_comment": "시장 변동성이 확대되고 있습니다.",
            "liquidity_comment": "유동성 공급 흐름을 주시하세요.",
            "leading_comment": "경기 선행 지표가 혼조세를 보입니다.",
            "sector_comment": "주도 섹터의 힘이 분산되고 있습니다.",
            "summary": "전반적인 거시 경제 지표가 중립적인 상태입니다."
        },
        "screening": {
            "summary": "반도체 및 자동차 섹터에서 유망 종목이 다수 포착됩니다.",
            "top_pick_reason": "펀더멘탈과 모멘텀이 균형을 이루고 있습니다."
        },
        "portfolio": {
            "summary": "포트폴리오 수익률 관리가 필요한 시점입니다.",
            "rebalance_tip": "현금 비중 확대를 검토하세요."
        },
        "overall": {
            "signal": "관망",
            "summary": "거시 지표와 개별 종목의 신호가 일치하지 않습니다. 보수적인 접근을 권장합니다.",
            "key_actions": ["변동성 지표 확인", "포트폴리오 리밸런싱 준비"]
        }
    }


def analyze_with_ai(signals: dict) -> Optional[dict]:
    """이전 버전과의 호환성을 위한 함수"""
    res = analyze_comprehensive(signals, {"top_picks": []}, None)
    if res:
        macro = res.get("macro", {})
        overall = res.get("overall", {})
        return {
            "exchange_comment": macro.get("exchange_comment"),
            "volatility_comment": macro.get("volatility_comment"),
            "liquidity_comment": macro.get("liquidity_comment"),
            "leading_comment": macro.get("leading_comment"),
            "sector_comment": macro.get("sector_comment"),
            "overall_signal": overall.get("signal"),
            "overall_comment": overall.get("summary"),
            "risk_factors": overall.get("key_actions", []),
            "opportunities": []
        }
    return None
