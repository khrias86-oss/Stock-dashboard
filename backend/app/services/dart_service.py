"""
DART API 연동 서비스
-- 한국 상장사 재무 데이터 수집 (PER/PBR/ROE/영업이익률)
-- 상장 종목 목록 수집
-- API Key 없으면 fallback 데이터 제공

왜 DART를 쓰는가:
yfinance의 한국 종목 재무 데이터는 불안정함.
DART는 금감원 공식 데이터이므로 정확도가 높음.
"""

import logging
import requests
import io
import zipfile
from typing import Optional

from app.config import settings
from app.cache.cache_manager import cache

logger = logging.getLogger(__name__)

DART_BASE = "https://opendart.fss.or.kr/api"


def _is_dart_available() -> bool:
    """DART API Key 유효 확인"""
    key = settings.DART_API_KEY
    return bool(key and key != "your_dart_api_key_here")


def get_corp_codes() -> dict:
    """
    DART 전체 상장사 고유번호 목록 수집
    -- 종목코드 → DART 고유번호 매핑 (API 호출에 필요)
    -- 캐시 24시간 (거의 변하지 않음)
    """
    cache_key = "dart_corp_codes"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if not _is_dart_available():
        logger.info("[DART] API Key 미설정 → 빈 목록 반환")
        return {}

    try:
        # DART corpCode.xml 다운로드 (zip 파일)
        resp = requests.get(
            f"{DART_BASE}/corpCode.xml",
            params={"crtfc_key": settings.DART_API_KEY},
            timeout=30,
        )
        resp.raise_for_status()

        # zip 해제 → XML 파싱
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            xml_data = zf.read(zf.namelist()[0])

        root = ET.fromstring(xml_data)
        corp_map = {}  # stock_code → corp_code
        for item in root.findall("list"):
            stock_code = item.findtext("stock_code", "").strip()
            corp_code = item.findtext("corp_code", "").strip()
            corp_name = item.findtext("corp_name", "").strip()
            if stock_code:  # 상장사만 (비상장사는 stock_code가 빈 문자열)
                corp_map[stock_code] = {
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                }

        logger.info(f"[DART] 상장사 {len(corp_map)}개 매핑 완료")
        cache.set(cache_key, corp_map, ttl=86400)  # 24시간 캐시
        return corp_map

    except Exception as e:
        logger.error(f"[DART] 상장사 목록 수집 실패: {e}")
        return {}


def get_financial_summary(corp_code: str, stock_code: str) -> Optional[dict]:
    """
    특정 기업의 최근 재무 요약 데이터 수집 (확장 버전)
    -- 당기/전기 재무 데이터를 모두 수집하여 성장률 계산 가능
    -- 자본총계, 재고자산 등 ROE/PBR 정확 산출에 필요한 데이터 포함
    """
    if not _is_dart_available():
        return None

    cache_key = f"dart_financial_v2_{stock_code}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 최근 사업보고서 시도: 2025 → 2024 → 2023
    for year in ["2025", "2024", "2023"]:
        financial = _fetch_financial_data(corp_code, stock_code, year)
        if financial and financial.get("revenue"):
            cache.set(cache_key, financial, ttl=43200)  # 12시간 캐시
            logger.info(f"[DART] {stock_code} {year} 재무 데이터 수집 완료")
            return financial

    logger.warning(f"[DART] {stock_code} 재무 데이터 없음")
    return None


def _fetch_financial_data(corp_code: str, stock_code: str, bsns_year: str) -> Optional[dict]:
    """DART 재무제표에서 핵심 항목 추출 (당기/전기 모두)"""
    try:
        resp = requests.get(
            f"{DART_BASE}/fnlttSinglAcntAll.json",
            params={
                "crtfc_key": settings.DART_API_KEY,
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": "11011",  # 사업보고서
                "fs_div": "CFS",        # 연결재무제표
            },
            timeout=15,
        )

        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("status") != "000" or not data.get("list"):
            return None

        financial = {"bsns_year": bsns_year}

        for item in data["list"]:
            name = item.get("account_nm", "").strip()
            sj_div = item.get("sj_div", "")  # BS=재무상태표, IS=손익계산서
            # 당기(thstrm), 전기(frmtrm) 금액
            cur_amount = _parse_amount(item.get("thstrm_amount", "0"))
            prev_amount = _parse_amount(item.get("frmtrm_amount", "0"))

            # === 손익계산서 항목 (sj_div == "IS" 또는 "CIS") ===
            # 매출액 (매출원가 제외)
            if "매출" in name and "매출원가" not in name and "매출총" not in name:
                financial.setdefault("revenue", cur_amount)
                financial.setdefault("revenue_prev", prev_amount)
            # 영업이익
            elif name in ("영업이익", "영업이익(손실)"):
                financial.setdefault("operating_income", cur_amount)
                financial.setdefault("operating_income_prev", prev_amount)
            # 당기순이익 (지배주주 기준 우선)
            elif "지배기업" in name and "순이익" in name:
                financial["net_income"] = cur_amount
                financial["net_income_prev"] = prev_amount
            elif "당기순이익" in name and "net_income" not in financial:
                financial.setdefault("net_income", cur_amount)
                financial.setdefault("net_income_prev", prev_amount)

            # === 재무상태표 항목 (sj_div == "BS") — setdefault로 첫 번째만 ===
            # 자본총계
            elif name == "자본총계" and sj_div == "BS":
                financial.setdefault("total_equity", cur_amount)
                financial.setdefault("total_equity_prev", prev_amount)
            # 재고자산
            elif name == "재고자산" and sj_div == "BS":
                financial.setdefault("inventory", cur_amount)
                financial.setdefault("inventory_prev", prev_amount)

        # === 파생 지표 계산 ===

        # 영업이익률
        if financial.get("revenue") and financial.get("operating_income"):
            financial["operating_margin"] = round(
                financial["operating_income"] / financial["revenue"] * 100, 2
            )

        # ROE = 당기순이익 / 자본총계 × 100
        if financial.get("net_income") and financial.get("total_equity") and financial["total_equity"] != 0:
            financial["roe"] = round(
                financial["net_income"] / financial["total_equity"] * 100, 2
            )

        # 매출 성장률 (YoY)
        if financial.get("revenue") and financial.get("revenue_prev") and financial["revenue_prev"] != 0:
            financial["revenue_growth"] = round(
                (financial["revenue"] - financial["revenue_prev"]) / abs(financial["revenue_prev"]) * 100, 2
            )

        # 영업이익 성장률 (YoY)
        if financial.get("operating_income") and financial.get("operating_income_prev") and financial["operating_income_prev"] != 0:
            financial["op_income_growth"] = round(
                (financial["operating_income"] - financial["operating_income_prev"]) / abs(financial["operating_income_prev"]) * 100, 2
            )

        # 재무효율성 = 재고자산증가율 < 매출성장율
        if (financial.get("inventory") and financial.get("inventory_prev")
                and financial["inventory_prev"] != 0 and financial.get("revenue_growth") is not None):
            inv_growth = (financial["inventory"] - financial["inventory_prev"]) / abs(financial["inventory_prev"]) * 100
            financial["inventory_growth"] = round(inv_growth, 2)
            financial["financial_efficiency"] = financial.get("revenue_growth", 0) > inv_growth
        else:
            financial["financial_efficiency"] = None

        return financial if financial.get("revenue") else None

    except Exception as e:
        logger.warning(f"[DART] 재무 데이터 수집 실패 ({stock_code}, {bsns_year}): {e}")
        return None


def _parse_amount(s: str) -> float:
    """DART 금액 문자열 → float 변환 (콤마, 공백 제거)"""
    try:
        return float(s.replace(",", "").replace(" ", "").strip())
    except (ValueError, AttributeError):
        return 0.0

