"""
시장 유망주 스크리닝 엔진 v2
-- KOSPI/KOSDAQ 시가총액 상위 종목 대상
-- PER, PBR, ROE, PEG를 DART 자본총계 기반으로 정확 산출
-- yfinance와 교차검증하여 정확성 확보
-- 재무효율성(재고자산증가율 < 매출성장률) 추가
-- SQLite 기반 분기 데이터 캐시 + 교차검증 체계

왜 DART 직접 계산을 우선하는가:
yfinance가 한국 종목의 PER/PBR/ROE를 잘못 반환하는 사례가 다수 있음.
DART 공시 데이터(순이익, 자본총계)로 직접 계산한 값이 가장 정확함.
yfinance 값은 보조 교차검증 용도로만 사용.
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from app.cache.cache_manager import cache
from app.services.dart_service import get_corp_codes, get_financial_summary
from app.services.financial_db import cross_validate_and_save

logger = logging.getLogger(__name__)

from app.services.naver_finance import get_top_200_stocks
def get_top_picks(limit: int = 10) -> dict:
    """
    스크리닝 Top N 유망 종목 반환
    - DART 기반 정확 재무지표 + yfinance 교차검증
    - 캐시 6시간
    """
    cache_key = f"screening_top_v2_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Top 200 종목 가져오기
    top_stocks = get_top_200_stocks()
    if not top_stocks:
        logger.warning("[스크리닝] Top 200 수집 실패, 기본 목록 사용")
        top_stocks = [("005930", "삼성전자"), ("000660", "SK하이닉스"), ("005380", "현대차"), ("000270", "기아"), ("035420", "NAVER")]

    logger.info(f"[스크리닝 v2] {len(top_stocks)}개 종목 분석 시작...")
    corp_codes = get_corp_codes()

    results = []
    for stock_code, name in top_stocks:
        try:
            stock_data = _analyze_single_stock(stock_code, name, corp_codes)
            if stock_data and stock_data.get("score") is not None:
                results.append(stock_data)
        except Exception as e:
            logger.warning(f"[스크리닝] {name}({stock_code}) 분석 실패: {e}")

    if not results:
        logger.warning("[스크리닝] 분석 결과 없음 → 샘플 데이터 반환")
        return _get_fallback_data()

    results.sort(key=lambda x: x.get("score", 0), reverse=True)

    output = {
        "top_picks": results[:limit],
        "total_analyzed": len(results),
        "methodology": {
            "description": "PER/PBR(가치 30%) + ROE/PEG(수익성·성장 30%) + 모멘텀(20%) + 재무효율성(20%)",
        },
    }

    cache.set(cache_key, output, ttl=21600)  # 6시간 캐시
    logger.info(f"[스크리닝 v2] {len(results)}개 종목 분석 완료, Top {limit} 선정")
    return output


def _analyze_single_stock(stock_code: str, name: str, corp_codes: dict) -> Optional[dict]:
    """
    단일 종목 분석:
    1) yfinance → 시가총액, 현재가 (+ PER/PBR yfinance값 = 교차검증용)
    2) DART → 순이익, 자본총계 → PER/PBR/ROE 직접 계산
    3) EPS 성장률 → PEG 산출
    4) 재무효율성 판별
    5) SQLite DB 교차검증
    """
    ticker = f"{stock_code}.KS"

    # === 1. yfinance에서 시가총액, 현재가, 종가일 수집 ===
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception:
        info = {}

    current_price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
    market_cap = info.get("marketCap", 0)  # 원 단위

    # 종가일 확인
    price_date = None
    try:
        hist = t.history(period="5d")
        if hist is not None and not hist.empty:
            price_date = hist.index[-1].strftime("%Y-%m-%d")
            if not current_price:
                current_price = float(hist["Close"].iloc[-1])
    except Exception:
        pass

    if not current_price:
        return None

    # yfinance 참고값 (교차검증용)
    yf_per = info.get("trailingPE") or info.get("forwardPE")
    yf_pbr = info.get("priceToBook")
    yf_roe = info.get("returnOnEquity")
    if yf_roe:
        yf_roe = round(yf_roe * 100, 2)  # 소수 → 퍼센트

    # 모멘텀 (3개월/6개월 수익률)
    momentum_3m, momentum_6m = _calc_momentum(ticker)

    # === 2. DART 재무 데이터에서 정확한 지표 산출 ===
    per_calc = None
    pbr_calc = None
    roe = None
    peg = None
    revenue_growth = None
    op_income_growth = None
    financial_efficiency = None
    inventory_growth = None
    bsns_year = None

    corp_info = corp_codes.get(stock_code)
    if corp_info:
        financial = get_financial_summary(corp_info["corp_code"], stock_code)
        if financial:
            bsns_year = financial.get("bsns_year")
            net_income = financial.get("net_income", 0)
            total_equity = financial.get("total_equity", 0)

            # PER = 시가총액 / 당기순이익  (시가총액은 원 단위, 순이익은 백만원 단위일 수 있음)
            # DART 금액 → 백만원 단위가 기본 (확인 필요)
            if market_cap and net_income and net_income > 0:
                # DART 금액은 원 단위임 (콤마 제거 후 float)
                per_calc = round(market_cap / net_income, 2)

            # PBR = 시가총액 / 자본총계
            if market_cap and total_equity and total_equity > 0:
                pbr_calc = round(market_cap / total_equity, 2)

            # ROE = 당기순이익 / 자본총계 × 100 (DART에서 이미 계산됨)
            roe = financial.get("roe")

            # 성장률
            revenue_growth = financial.get("revenue_growth")
            op_income_growth = financial.get("op_income_growth")
            financial_efficiency = financial.get("financial_efficiency")
            inventory_growth = financial.get("inventory_growth")

            # PEG = PER / EPS 성장률
            # EPS 성장률 ≈ 순이익 성장률 (주식 수 변동이 적으므로 근사에 사용 가능)
            net_income_prev = financial.get("net_income_prev", 0)
            if per_calc and net_income_prev and net_income_prev > 0 and net_income:
                eps_growth = ((net_income - net_income_prev) / abs(net_income_prev)) * 100
                if eps_growth > 0:
                    peg = round(per_calc / eps_growth, 2)

            # === 교차검증: DART 직접계산 vs yfinance 비교 ===
            _cross_validate(name, stock_code,
                            per_calc, yf_per, "PER",
                            pbr_calc, yf_pbr, "PBR",
                            roe, yf_roe, "ROE")

            # === SQLite DB 교차검증 및 저장 ===
            quarter = f"{bsns_year}Q4"
            db_metrics = {
                "roe": roe,
                "per_calc": per_calc,
                "pbr_calc": pbr_calc,
                "revenue_growth": revenue_growth,
                "op_income_growth": op_income_growth,
            }
            cross_validate_and_save(stock_code, name, quarter, db_metrics)

    # PER/PBR fallback: DART 계산 불가 시 yfinance 사용
    per = per_calc or yf_per
    pbr = pbr_calc or yf_pbr
    if roe is None:
        roe = yf_roe

    # 종합 스코어 산출
    score = _calc_score(per, pbr, roe, peg, revenue_growth, op_income_growth,
                        momentum_3m, momentum_6m, financial_efficiency)

    # 시그널 판정
    signal = _judge_signal(score, per, pbr, roe, peg)

    return {
        "stock_code": stock_code,
        "name": name,
        "price": round(current_price),
        "price_date": price_date,
        "market_cap_billion": round(market_cap / 1e8) if market_cap else None,  # 억원
        "per": round(per, 2) if per else None,
        "pbr": round(pbr, 2) if pbr else None,
        "roe": round(roe, 2) if roe else None,
        "peg": peg,
        "revenue_growth": round(revenue_growth, 1) if revenue_growth is not None else None,
        "op_income_growth": round(op_income_growth, 1) if op_income_growth is not None else None,
        "revenue": round(financial.get("revenue", 0) / 1e8) if financial and financial.get("revenue") else None,  # 억원
        "operating_income": round(financial.get("operating_income", 0) / 1e8) if financial and financial.get("operating_income") else None, # 억원
        "revenue_prev": round(financial.get("revenue_prev", 0) / 1e8) if financial and financial.get("revenue_prev") else None,
        "operating_income_prev": round(financial.get("operating_income_prev", 0) / 1e8) if financial and financial.get("operating_income_prev") else None,
        "operating_margin": financial.get("operating_margin") if financial else None,
        "financial_efficiency": financial_efficiency,
        "inventory_growth": round(inventory_growth, 1) if inventory_growth is not None else None,
        "momentum_3m": round(momentum_3m, 2) if momentum_3m is not None else None,
        "score": round(score, 1) if score is not None else None,
        "signal": signal,
        "bsns_year": bsns_year,
    }


def _cross_validate(name, code, dart_per, yf_per, per_label,
                    dart_pbr, yf_pbr, pbr_label,
                    dart_roe, yf_roe, roe_label):
    """DART 직접계산 vs yfinance 교차검증 (10% 이상 차이 시 WARNING)"""
    pairs = [
        (dart_per, yf_per, per_label),
        (dart_pbr, yf_pbr, pbr_label),
        (dart_roe, yf_roe, roe_label),
    ]
    for dart_val, yf_val, label in pairs:
        if dart_val is not None and yf_val is not None and yf_val != 0:
            pct_diff = abs((dart_val - yf_val) / yf_val) * 100
            if pct_diff > 10:
                logger.warning(
                    f"[교차검증] {name}({code}) {label}: "
                    f"DART={dart_val:.2f}, yfinance={yf_val:.2f} (차이 {pct_diff:.1f}%) → DART 값 우선 사용"
                )


def _calc_momentum(ticker: str) -> tuple:
    """3개월/6개월 수익률 계산"""
    try:
        df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None, None

        if isinstance(df.columns, pd.MultiIndex):
            if ticker in df.columns.get_level_values(1):
                df = df.droplevel(1, axis=1)
            else:
                df.columns = df.columns.get_level_values(0)
        df = df.loc[:, ~df.columns.duplicated()]

        closes = df["Close"].dropna()
        if len(closes) < 20:
            return None, None

        current = closes.iloc[-1]
        m3_idx = max(0, len(closes) - 63)
        momentum_3m = ((current - closes.iloc[m3_idx]) / closes.iloc[m3_idx]) * 100
        momentum_6m = ((current - closes.iloc[0]) / closes.iloc[0]) * 100
        return float(momentum_3m), float(momentum_6m)
    except Exception:
        return None, None


def _calc_score(per, pbr, roe, peg, rev_growth, op_growth,
                mom_3m, mom_6m, fin_efficiency) -> Optional[float]:
    """
    종합 스코어 산출 (0~100) — 4축 가중 평균
    - 가치 (30%): PER, PBR
    - 수익성·성장 (30%): ROE, PEG, 매출/영업이익 성장률
    - 모멘텀 (20%): 3M/6M 수익률
    - 재무효율성 (20%): 재고자산증가율 < 매출성장률
    """
    scores = []
    weights = []

    # === 가치 (30%) ===
    if per is not None and per > 0:
        val_per = max(0, min(100, (25 - per) / 20 * 100))
        scores.append(val_per)
        weights.append(0.15)

    if pbr is not None and pbr > 0:
        val_pbr = max(0, min(100, (3.0 - pbr) / 2.5 * 100))
        scores.append(val_pbr)
        weights.append(0.15)

    # === 수익성·성장 (30%) ===
    if roe is not None:
        val_roe = max(0, min(100, roe / 20 * 100))
        scores.append(val_roe)
        weights.append(0.10)

    if peg is not None and peg > 0:
        # PEG ≤ 1 = 만점, PEG > 3 = 0점
        val_peg = max(0, min(100, (3.0 - peg) / 2.0 * 100))
        scores.append(val_peg)
        weights.append(0.10)

    if rev_growth is not None:
        val_rev = max(0, min(100, (rev_growth + 20) / 60 * 100))
        scores.append(val_rev)
        weights.append(0.05)

    if op_growth is not None:
        val_op = max(0, min(100, (op_growth + 20) / 60 * 100))
        scores.append(val_op)
        weights.append(0.05)

    # === 모멘텀 (20%) ===
    if mom_3m is not None:
        val_m3 = max(0, min(100, (mom_3m + 30) / 60 * 100))
        scores.append(val_m3)
        weights.append(0.10)

    if mom_6m is not None:
        val_m6 = max(0, min(100, (mom_6m + 30) / 60 * 100))
        scores.append(val_m6)
        weights.append(0.10)

    # === 재무효율성 (20%) ===
    if fin_efficiency is not None:
        scores.append(100 if fin_efficiency else 30)
        weights.append(0.20)

    if not scores:
        return None

    total_weight = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


def _judge_signal(score, per, pbr, roe, peg) -> str:
    """투자 시그널 판정"""
    if score is None:
        return "관망"

    # PEG ≤ 1 보너스
    if score >= 65 and peg is not None and peg <= 1.0:
        return "강력매수"
    if score >= 70:
        return "강력매수"
    elif score >= 55:
        return "매수"
    elif score >= 40:
        return "관망"
    elif score >= 25:
        return "주의"
    else:
        return "매도"


def _get_fallback_data() -> dict:
    """DART API 없거나 모든 종목 분석 실패 시 샘플 데이터"""
    sample = [
        {"stock_code": "005930", "name": "삼성전자",
         "price": 62000, "price_date": "2026-03-28",
         "market_cap_billion": 370000, "per": 12.5,
         "pbr": 1.2, "roe": 9.8, "peg": 1.5,
         "revenue_growth": 5.0, "op_income_growth": 12.3,
         "financial_efficiency": True, "inventory_growth": 2.1,
         "momentum_3m": -5.2, "score": 62.5,
         "signal": "매수", "bsns_year": "2024"},
    ]
    return {
        "top_picks": sample,
        "total_analyzed": 1,
        "methodology": {
            "description": "⚠️ 샘플 데이터입니다. DART API Key 설정 후 실제 데이터로 전환됩니다.",
        },
        "is_sample": True,
    }
