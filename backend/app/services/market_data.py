"""
시장 데이터 수집 서비스 (yfinance + 네이버 교차검증 + FRED 연동)
-- 거시지표 차트 5종에 필요한 모든 원본 데이터를 수집
-- 한국 종목: yfinance 실패 시 네이버 금융으로 자동 fallback
-- M2/금리차: FRED API Key 있으면 실제 데이터, 없으면 Mock
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from app.services.naver_finance import cross_validate_price
from app.services.fred_data import get_us_m2_yoy, get_us_treasury_spread

logger = logging.getLogger(__name__)

# ============================================================
# 날짜 범위 유틸리티
# ============================================================

def _get_date_range(months: int = 12) -> tuple[str, str]:
    """최근 N개월의 시작/종료 날짜를 'YYYY-MM-DD' 문자열로 반환"""
    end = datetime.now()
    start = end - timedelta(days=months * 30)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _safe_download(ticker: str, start: str, end: str, label: str = "", use_naver_fallback: bool = True) -> Optional[pd.DataFrame]:
    """
    yfinance 다운로드 + 네이버 교차검증 래퍼
    - ticker: 야후 파이낸스 심볼 (예: "^KS11", "005380.KS")
    - use_naver_fallback: 한국 종목일 때 네이버 교차검증 사용 여부
    - 반환: DataFrame 또는 None

    왜 교차검증이 필요한가:
    yfinance가 한국 종목(*.KS, *.KQ)에서 간헐적으로 빈 데이터나
    부정확한 종가를 반환하는 경우가 있어, 네이버 금융을 보조 소스로 활용.
    """
    yf_data = None
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            # MultiIndex 컬럼 평탄화 (yfinance 단일 ticker에서도 MultiIndex 발생)
            # 구조: (Price, Ticker) 형태 → Price 레벨만 유지
            if isinstance(df.columns, pd.MultiIndex):
                # 티커가 레벨 0이나 1에 있는 경우 해당 레벨을 제거
                if ticker in df.columns.get_level_values(1):
                    df = df.droplevel(1, axis=1)
                elif ticker in df.columns.get_level_values(0):
                    df = df.droplevel(0, axis=1)
                else:
                    # 티커를 못 찾으면 첫 번째 레벨만 남김
                    df.columns = df.columns.get_level_values(0)
            
            # 중복된 컬럼이 있을 경우 제거 (가격 데이터 할당 에러 방지)
            df = df.loc[:, ~df.columns.duplicated()]
            yf_data = df
            logger.info(f"[{label or ticker}] yfinance {len(df)}행 수집")
        else:
            logger.warning(f"[{label or ticker}] yfinance 데이터 없음")
    except Exception as e:
        logger.error(f"[{label or ticker}] yfinance 다운로드 실패: {e}")

    # 한국 종목 및 지수(^KS11)면 네이버 교차검증 수행
    if use_naver_fallback and (".KS" in ticker or ".KQ" in ticker or ticker == "^KS11"):
        try:
            validated = cross_validate_price(ticker, yf_data)
            if validated is not None and not validated.empty:
                return validated
        except Exception as e:
            logger.warning(f"[{label or ticker}] 네이버 교차검증 실패: {e}")

    return yf_data


def _df_to_records(df: pd.DataFrame, value_col: str = "Close", rename: str = "") -> list[dict]:
    """DataFrame의 날짜+특정컬럼을 [{date, value}] 리스트로 변환"""
    if df is None or df.empty:
        return []
    result = df[[value_col]].dropna().reset_index()
    result.columns = ["date", rename or value_col]
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    return result.to_dict(orient="records")


# ============================================================
# 그래프 1: 환율 및 외국인 수급 다이버전스
# ============================================================

def get_exchange_divergence_data() -> dict:
    """
    원/달러 환율 + 달러인덱스 + 외국인 순매수 데이터 수집
    - 환율↑ + 외국인순매수↑ 다이버전스 구간 자동 감지
    """
    start, end = _get_date_range(12)

    # 원/달러 환율
    usd_krw = _safe_download("KRW=X", start, end, "원/달러 환율")
    # 달러 인덱스
    dxy = _safe_download("DX-Y.NYB", start, end, "달러인덱스")
    # 데이터 합치기 (날짜 기준 outer join)
    combined = pd.DataFrame()
    if usd_krw is not None:
        combined["usd_krw"] = usd_krw["Close"]
    if dxy is not None:
        combined["dxy"] = dxy["Close"]

    if combined.empty:
        return {"series": [], "divergence_zones": []}

    combined = combined.dropna(how="all").ffill()
    combined.index = pd.to_datetime(combined.index)

    # 다이버전스 감지: 환율 20일 이동평균 상승 + DXY 하락 (비정상 구간)
    if "usd_krw" in combined.columns and "dxy" in combined.columns:
        combined["fx_ma20"] = combined["usd_krw"].rolling(20).mean()
        combined["dxy_ma20"] = combined["dxy"].rolling(20).mean()
        combined["fx_rising"] = combined["fx_ma20"].diff() > 0
        combined["dxy_falling"] = combined["dxy_ma20"].diff() < 0
        combined["divergence"] = combined["fx_rising"] & combined["dxy_falling"]
    else:
        combined["divergence"] = False

    # JSON 변환
    records = combined.reset_index()
    records.columns = [c if c != "index" else "date" for c in records.columns]
    if "Date" in records.columns:
        records = records.rename(columns={"Date": "date"})
    records["date"] = pd.to_datetime(records["date"]).dt.strftime("%Y-%m-%d")

    # 다이버전스 구간 추출 (시작~종료 날짜 쌍)
    divergence_zones = []
    in_zone = False
    zone_start = None
    for _, row in records.iterrows():
        if row.get("divergence", False) and not in_zone:
            zone_start = row["date"]
            in_zone = True
        elif not row.get("divergence", False) and in_zone:
            divergence_zones.append({"start": zone_start, "end": row["date"]})
            in_zone = False
    if in_zone and zone_start:
        divergence_zones.append({"start": zone_start, "end": records.iloc[-1]["date"]})

    # 불필요한 컬럼 제거
    output_cols = ["date"]
    for col in ["usd_krw", "dxy"]:
        if col in records.columns:
            output_cols.append(col)

    series = records[output_cols].to_dict(orient="records")

    # NaN → None 변환 (JSON 호환)
    for item in series:
        for k, v in item.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                item[k] = None

    return {
        "series": series,
        "divergence_zones": divergence_zones,
    }


# ============================================================
# 그래프 2: 시장 변동성 및 지수 바닥 확인
# ============================================================

def get_volatility_data() -> dict:
    """
    VIX + S&P500 + KOSPI 데이터 수집
    - VIX는 yfinance + FRED(VIXCLS) 교차검증
    - VIX 구간별 상태 정보 포함
    - VIX ≥ 30 시점을 자동으로 표시
    """
    start, end = _get_date_range(12)

    vix = _safe_download("^VIX", start, end, "VIX")
    sp500 = _safe_download("^GSPC", start, end, "S&P500")
    kospi = _safe_download("^KS11", start, end, "KOSPI")

    # === VIX 교차검증: FRED VIXCLS 시리즈로 확인 ===
    from app.services.fred_data import get_fred_series
    fred_vix = get_fred_series("VIXCLS", months=12, frequency="d", label="FRED VIX")

    if fred_vix is not None and not fred_vix.empty:
        fred_vix = fred_vix.rename(columns={"value": "vix_fred"})
        if vix is not None and not vix.empty:
            # 두 소스 비교: 최근 5일 종가 오차 확인
            try:
                yf_recent = vix["Close"].tail(5)
                fred_recent = fred_vix["vix_fred"].tail(5)
                common = yf_recent.index.intersection(fred_recent.index)
                if len(common) > 0:
                    diff = abs(yf_recent.loc[common].values - fred_recent.loc[common].values)
                    max_diff = diff.max()
                    logger.info(f"[VIX 교차검증] yfinance vs FRED 최대 오차: {max_diff:.2f}")
                    if max_diff > 2.0:  # 2포인트 이상 차이나면 FRED 우선
                        logger.warning(f"[VIX 교차검증] 오차 {max_diff:.2f} > 2.0 → FRED 데이터 우선 사용")
                        vix_series = fred_vix["vix_fred"]
                    else:
                        vix_series = vix["Close"]
                else:
                    vix_series = vix["Close"]
            except Exception as e:
                logger.warning(f"[VIX 교차검증] 비교 실패: {e}")
                vix_series = vix["Close"]
        else:
            # yfinance 실패 → FRED만 사용
            logger.info("[VIX] yfinance 실패 → FRED 데이터 사용")
            vix_series = fred_vix["vix_fred"]
    elif vix is not None:
        vix_series = vix["Close"]
    else:
        vix_series = None

    combined = pd.DataFrame()
    if vix_series is not None:
        combined["vix"] = vix_series
    if sp500 is not None:
        combined["sp500"] = sp500["Close"]
    if kospi is not None:
        combined["kospi"] = kospi["Close"]
        combined["kospi_volume"] = kospi["Volume"]

    if combined.empty:
        return {"series": [], "alert_dates": [], "vix_status": "데이터 없음"}

    combined = combined.dropna(how="all").ffill()

    # VIX 구간 분석
    latest_vix = combined["vix"].iloc[-1] if "vix" in combined.columns else None
    vix_status = "데이터 없음"
    if latest_vix is not None:
        if latest_vix >= 40: vix_status = "극단공포"
        elif latest_vix >= 30: vix_status = "공포"
        elif latest_vix >= 20: vix_status = "경계"
        elif latest_vix >= 15: vix_status = "정상"
        else: vix_status = "안일"

    # VIX ≥ 30 공포 극단 시점
    alert_dates = []
    if "vix" in combined.columns:
        alerts = combined[combined["vix"] >= 30]
        alert_dates = alerts.index.strftime("%Y-%m-%d").tolist()

    records = combined.reset_index()
    if "Date" in records.columns:
        records = records.rename(columns={"Date": "date"})
    records["date"] = pd.to_datetime(records["date"]).dt.strftime("%Y-%m-%d")

    series = records.to_dict(orient="records")
    for item in series:
        for k, v in item.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                item[k] = None

    return {
        "series": series,
        "alert_dates": alert_dates,
        "vix_status": vix_status,
        "latest_vix": round(latest_vix, 2) if latest_vix is not None else None,
    }


# ============================================================
# 그래프 3: 유동성 지표 (M2 + 지수)
# ============================================================

def get_liquidity_data() -> dict:
    """
    유동성 지표: M2 통화량 YoY + 주요 지수
    -- FRED API Key가 있으면 실제 M2 데이터 사용
    -- 없으면 Mock 데이터로 Fallback (UI 구조 유지)
    """
    start, end = _get_date_range(12)

    sp500 = _safe_download("^GSPC", start, end, "S&P500")
    kospi = _safe_download("^KS11", start, end, "KOSPI")

    combined = pd.DataFrame()
    if sp500 is not None:
        combined["sp500"] = sp500["Close"]
    if kospi is not None:
        combined["kospi"] = kospi["Close"]

    if combined.empty:
        return {"series": [], "inflection_points": [], "has_m2_data": False}

    combined = combined.dropna(how="all").ffill()

    # === FRED에서 실제 M2 데이터 가져오기 시도 ===
    has_m2 = False
    fred_m2 = get_us_m2_yoy()
    if fred_m2 is not None and not fred_m2.empty:
        # 월간 M2 → 일간 지수 데이터에 매핑 (가장 가까운 월로 ffill)
        m2_daily = fred_m2.reindex(combined.index, method="ffill")
        combined["m2_us_yoy"] = m2_daily["m2_us_yoy"]
        has_m2 = True
        logger.info(f"[FRED M2] 실제 데이터 {len(fred_m2)}건 연동 완료")
    else:
        # Fallback: Mock M2 데이터
        logger.info("[FRED M2] API Key 미설정 또는 데이터 없음 → Mock 데이터 사용")
        np.random.seed(42)
        combined["m2_us_yoy"] = np.linspace(2.5, -1.5, len(combined)) + np.random.normal(0, 0.3, len(combined))

    # 한국 M2는 ECOS 연동 전까지 Mock
    np.random.seed(43)
    combined["m2_kr_yoy"] = np.linspace(4.0, 1.0, len(combined)) + np.random.normal(0, 0.4, len(combined))

    # 변곡점 감지: M2 YoY가 부호가 바뀌는 시점
    inflection_points = []
    m2_vals = combined["m2_us_yoy"].dropna().values
    m2_dates = combined["m2_us_yoy"].dropna().index
    for i in range(1, len(m2_vals)):
        if (m2_vals[i-1] > 0 and m2_vals[i] <= 0) or (m2_vals[i-1] <= 0 and m2_vals[i] > 0):
            date_str = m2_dates[i].strftime("%Y-%m-%d")
            direction = "축소" if m2_vals[i] <= 0 else "확대"
            inflection_points.append({"date": date_str, "direction": direction})

    records = combined.reset_index()
    if "Date" in records.columns:
        records = records.rename(columns={"Date": "date"})
    records["date"] = pd.to_datetime(records["date"]).dt.strftime("%Y-%m-%d")

    series = records.to_dict(orient="records")
    for item in series:
        for k, v in item.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                item[k] = None

    return {
        "series": series,
        "inflection_points": inflection_points,
        "has_m2_data": has_m2,
    }


# ============================================================
# 그래프 4: 경기 선행 지표 (장단기 금리차)
# ============================================================

def get_leading_indicator_data() -> dict:
    """
    미국 10년물 - 2년물 금리차
    -- FRED API Key가 있으면 T10Y2Y 시리즈 직접 사용 (가장 정확)
    -- 없으면 yfinance에서 개별 금리 데이터 수집 후 계산
    """
    start, end = _get_date_range(12)

    # === 방법 1: FRED에서 직접 금리차 가져오기 (권장) ===
    fred_spread = get_us_treasury_spread()
    if fred_spread is not None and not fred_spread.empty:
        logger.info(f"[FRED T10Y2Y] 실제 금리차 {len(fred_spread)}건 사용")
        combined = fred_spread.copy()
        # FRED 데이터에는 개별 금리가 없으므로 spread만 사용
        combined = combined.dropna(how="all")
    else:
        # === 방법 2: yfinance에서 개별 금리 수집 후 계산 (Fallback) ===
        tnx = _safe_download("^TNX", start, end, "10Y 국채")
        twoy = _safe_download("2YY=F", start, end, "2Y 국채")

        combined = pd.DataFrame()
        if tnx is not None:
            combined["yield_10y"] = tnx["Close"]
        if twoy is not None:
            combined["yield_2y"] = twoy["Close"]

        if combined.empty:
            return {"series": [], "inversion_zones": [], "normalization_points": []}

        combined = combined.dropna(how="all").ffill()

    # 장단기 금리차 (FRED에서 이미 spread가 있으면 재계산 불필요)
    if "spread" not in combined.columns:
        if "yield_10y" in combined.columns and "yield_2y" in combined.columns:
            combined["spread"] = combined["yield_10y"] - combined["yield_2y"]
        elif "yield_10y" in combined.columns:
            combined["spread"] = combined["yield_10y"]
        else:
            return {"series": [], "inversion_zones": [], "normalization_points": []}

    # 역전 구간 감지 (spread < 0)
    inversion_zones = []
    normalization_points = []
    in_inversion = False
    inv_start = None

    spread_vals = combined["spread"].dropna()
    for date, val in spread_vals.items():
        date_str = date.strftime("%Y-%m-%d")
        if val < 0 and not in_inversion:
            inv_start = date_str
            in_inversion = True
        elif val >= 0 and in_inversion:
            inversion_zones.append({"start": inv_start, "end": date_str})
            normalization_points.append({
                "date": date_str,
                "label": "경기 침체 진입 주의"
            })
            in_inversion = False

    if in_inversion and inv_start:
        inversion_zones.append({"start": inv_start, "end": spread_vals.index[-1].strftime("%Y-%m-%d")})

    records = combined.reset_index()
    if "Date" in records.columns:
        records = records.rename(columns={"Date": "date"})
    records["date"] = pd.to_datetime(records["date"]).dt.strftime("%Y-%m-%d")

    series = records.to_dict(orient="records")
    for item in series:
        for k, v in item.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                item[k] = None

    return {
        "series": series,
        "inversion_zones": inversion_zones,
        "normalization_points": normalization_points,
    }


# ============================================================
# 그래프 5: 섹터 ETF 상대강도
# ============================================================

def get_sector_strength_data() -> dict:
    """
    섹터 ETF 상대강도 = (섹터 수익률 - KOSPI 수익률)
    - 8개 섹터: 반도체/2차전지/자동차/금융/바이오/방산/에너지/IT
    - 자동차 벤치마킹: 개별 종목 토글 데이터 포함
    - 산출 근거(ETF 명칭, 티커, 운용사) 포함
    """
    start, end = _get_date_range(12)

    # KOSPI 기준 지수
    kospi = _safe_download("^KS11", start, end, "KOSPI 기준")

    # 섹터 ETF 정의 + 산출 근거
    # 한국 ETF는 yfinance에서 불안정 → 글로벌 대표 ETF로 대체하여 상대강도 비교
    # 선정 기준: KOSPI 업종별 시가총액 비중 + 한국 산업 경쟁력 고려
    sector_config = {
        "반도체": {
            "ticker": "SOXX",
            "source": "iShares Semiconductor ETF (SOXX, BlackRock)",
            "reason": "삼성전자·SK하이닉스가 KOSPI 시총 30%+ 차지, 국내 대표 산업",
        },
        "2차전지": {
            "ticker": "LIT",
            "source": "Global X Lithium & Battery Tech ETF (LIT)",
            "reason": "LG에너지솔루션·삼성SDI 등 K-배터리 글로벌 점유율 상위",
        },
        "자동차": {
            "ticker": "CARZ",
            "source": "First Trust S-Network Future Vehicles ETF (CARZ)",
            "reason": "현대차그룹 글로벌 판매량 3위, 전기차 전환 핵심 섹터",
        },
        "금융": {
            "ticker": "XLF",
            "source": "Financial Select Sector SPDR Fund (XLF, State Street)",
            "reason": "KB·신한·하나 등 금융지주 KOSPI 시총 상위, 금리 민감 섹터",
        },
        "바이오": {
            "ticker": "XBI",
            "source": "SPDR S&P Biotech ETF (XBI, State Street)",
            "reason": "셀트리온·삼성바이오로직스 KOSPI 시총 상위, 성장주 대표",
        },
        "방산": {
            "ticker": "ITA",
            "source": "iShares U.S. Aerospace & Defense ETF (ITA, BlackRock)",
            "reason": "한화에어로스페이스·LIG넥스원, 방산 수출 급증으로 주목 섹터",
        },
        "에너지/화학": {
            "ticker": "XLE",
            "source": "Energy Select Sector SPDR Fund (XLE, State Street)",
            "reason": "SK이노베이션·LG화학 등 정유/화학 대형주, 유가 연동",
        },
        "IT/소프트웨어": {
            "ticker": "XLK",
            "source": "Technology Select Sector SPDR Fund (XLK, State Street)",
            "reason": "네이버·카카오·NCSoft 등 국내 IT 플랫폼 대표주",
        },
    }

    sector_tickers = {name: cfg["ticker"] for name, cfg in sector_config.items()}

    # 산출 근거 정보 (프론트엔드에서 표시용)
    sector_sources = {name: {
        "etf": cfg["source"],
        "reason": cfg["reason"],
        "ticker": cfg["ticker"],
    } for name, cfg in sector_config.items()}

    # 자동차 벤치마킹 개별 종목
    auto_benchmarks = {
        "현대차": "005380.KS",
        "기아": "000270.KS",
        "토요타": "TM",
        "테슬라": "TSLA",
    }

    if kospi is None or kospi.empty:
        return {"sectors": {}, "auto_benchmarks": {}, "sector_sources": sector_sources}

    kospi_returns = (kospi["Close"] / kospi["Close"].iloc[0] - 1) * 100

    # 섹터별 상대강도 계산
    sectors = {}
    for name, ticker in sector_tickers.items():
        df = _safe_download(ticker, start, end, f"섹터-{name}")
        if df is not None and not df.empty:
            # 동일 날짜 범위로 맞추기
            sector_returns = (df["Close"] / df["Close"].iloc[0] - 1) * 100
            merged = pd.DataFrame({
                "sector": sector_returns,
                "kospi": kospi_returns,
            }).dropna()

            if not merged.empty:
                merged["relative"] = merged["sector"] - merged["kospi"]
                records = merged[["relative"]].reset_index()
                if "Date" in records.columns:
                    records = records.rename(columns={"Date": "date"})
                records["date"] = pd.to_datetime(records["date"]).dt.strftime("%Y-%m-%d")
                records = records.rename(columns={"relative": "value"})

                data_list = records.to_dict(orient="records")
                for item in data_list:
                    for k, v in item.items():
                        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                            item[k] = None
                sectors[name] = data_list

    # 자동차 벤치마킹 개별 종목
    auto_data = {}
    for name, ticker in auto_benchmarks.items():
        df = _safe_download(ticker, start, end, f"자동차-{name}")
        if df is not None and not df.empty:
            stock_returns = (df["Close"] / df["Close"].iloc[0] - 1) * 100
            merged = pd.DataFrame({
                "stock": stock_returns,
                "kospi": kospi_returns,
            }).dropna()

            if not merged.empty:
                merged["relative"] = merged["stock"] - merged["kospi"]
                records = merged[["relative"]].reset_index()
                if "Date" in records.columns:
                    records = records.rename(columns={"Date": "date"})
                records["date"] = pd.to_datetime(records["date"]).dt.strftime("%Y-%m-%d")
                records = records.rename(columns={"relative": "value"})

                data_list = records.to_dict(orient="records")
                for item in data_list:
                    for k, v in item.items():
                        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                            item[k] = None
                auto_data[name] = data_list

    return {
        "sectors": sectors,
        "auto_benchmarks": auto_data,
        "sector_sources": sector_sources,
    }
