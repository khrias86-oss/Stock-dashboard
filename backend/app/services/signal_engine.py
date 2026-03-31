"""
시그널 감지 엔진 (수학적 + 경제학적 분석)
-- 각 거시지표 데이터에서 투자 시그널을 자동 감지
-- 이동평균 교차, 표준편차 이탈, 추세 전환 등
-- AI 분석의 입력 데이터로 활용
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


def analyze_signals(macro_data: dict) -> dict:
    """
    5개 거시지표 데이터를 입력받아 각 지표별 시그널을 감지
    - 반환: {exchange, volatility, liquidity, leading, sector} 각각에 시그널 리스트
    - 이 결과를 Gemini AI에 전달하여 교차검증 + 의견 생성

    왜 수학적 시그널이 필요한가:
    AI에게 원시 데이터 전체를 보내면 토큰 낭비. 대신 핵심 시그널만 추출하여
    전달하면 AI가 더 정확하고 빠르게 판단 가능 + 비용 절감.
    """
    result = {}

    # 1. 환율 다이버전스 시그널
    result["exchange"] = _analyze_exchange(macro_data.get("exchange", {}))

    # 2. VIX 변동성 시그널
    result["volatility"] = _analyze_volatility(macro_data.get("volatility", {}))

    # 3. 유동성 시그널
    result["liquidity"] = _analyze_liquidity(macro_data.get("liquidity", {}))

    # 4. 경기 선행 지표 시그널
    result["leading"] = _analyze_leading(macro_data.get("leading", {}))

    # 5. 섹터 강도 시그널
    result["sector"] = _analyze_sector(macro_data.get("sector", {}))

    return result


def _extract_values(series: list, key: str) -> list:
    """시리즈에서 특정 키의 값만 추출 (None 제거)"""
    return [item[key] for item in series if item.get(key) is not None]


def _calc_ma(values: list, period: int) -> float | None:
    """이동평균 계산"""
    if len(values) < period:
        return None
    return float(np.mean(values[-period:]))


def _calc_std(values: list, period: int) -> float | None:
    """표준편차 계산"""
    if len(values) < period:
        return None
    return float(np.std(values[-period:]))


def _calc_roc(values: list, period: int = 20) -> float | None:
    """변화율(Rate of Change) = (현재 - N일전) / N일전 * 100"""
    if len(values) < period + 1:
        return None
    current = values[-1]
    past = values[-period - 1]
    if past == 0:
        return None
    return float((current - past) / past * 100)


def _zscore(values: list, period: int = 60) -> float | None:
    """Z-Score = (현재값 - 평균) / 표준편차 — 통계적 이상치 감지"""
    if len(values) < period:
        return None
    recent = values[-period:]
    mean = np.mean(recent)
    std = np.std(recent)
    if std == 0:
        return None
    return float((values[-1] - mean) / std)


def _analyze_exchange(data: dict) -> dict:
    """환율 다이버전스 시그널 분석"""
    signals = []
    series = data.get("series", [])
    if not series:
        return {"signals": signals, "summary": "데이터 없음"}

    usd_krw = _extract_values(series, "usd_krw")
    dxy = _extract_values(series, "dxy")

    if usd_krw:
        current = usd_krw[-1]
        ma20 = _calc_ma(usd_krw, 20)
        ma60 = _calc_ma(usd_krw, 60)
        roc = _calc_roc(usd_krw, 20)
        z = _zscore(usd_krw, 60)

        if ma20 and ma60:
            if ma20 > ma60:
                signals.append({"type": "warning", "msg": f"환율 상승 추세 (20MA {ma20:.0f} > 60MA {ma60:.0f})"})
            else:
                signals.append({"type": "safe", "msg": f"환율 하락 추세 (20MA {ma20:.0f} < 60MA {ma60:.0f})"})

        if roc and abs(roc) > 3:
            direction = "급등" if roc > 0 else "급락"
            signals.append({"type": "warning" if roc > 0 else "safe", "msg": f"환율 20일 {direction} {roc:.1f}%"})

        if z and abs(z) > 2:
            signals.append({"type": "danger", "msg": f"환율 통계적 이상치 (Z={z:.2f})"})

        # 다이버전스 활성 여부
        div_zones = data.get("divergence_zones", [])
        if div_zones:
            last_zone_end = div_zones[-1].get("end", "")
            last_date = series[-1].get("date", "")
            if last_zone_end >= last_date:
                signals.append({"type": "danger", "msg": "환율↑ + 거래량↑ 다이버전스 진행 중"})

    summary = f"원/달러 {usd_krw[-1]:.0f}원" if usd_krw else "데이터 없음"
    return {"signals": signals, "summary": summary, "current_rate": usd_krw[-1] if usd_krw else None}


def _analyze_volatility(data: dict) -> dict:
    """VIX 변동성 시그널 분석"""
    signals = []
    series = data.get("series", [])
    if not series:
        return {"signals": signals, "summary": "데이터 없음"}

    vix = _extract_values(series, "vix")
    if not vix:
        return {"signals": signals, "summary": "VIX 데이터 없음"}

    current = vix[-1]
    ma20 = _calc_ma(vix, 20)
    ma60 = _calc_ma(vix, 60)
    std20 = _calc_std(vix, 20)
    z = _zscore(vix, 60)

    # VIX 구간 판정
    if current >= 40:
        signals.append({"type": "danger", "msg": f"VIX {current:.1f} — 극단 공포 구간, 역발상 매수 관심"})
    elif current >= 30:
        signals.append({"type": "danger", "msg": f"VIX {current:.1f} — 공포 구간, 시장 스트레스 높음"})
    elif current >= 20:
        signals.append({"type": "warning", "msg": f"VIX {current:.1f} — 경계 구간, 불확실성 상승"})
    elif current >= 15:
        signals.append({"type": "safe", "msg": f"VIX {current:.1f} — 정상 변동성"})
    else:
        signals.append({"type": "warning", "msg": f"VIX {current:.1f} — 안일 구간, 시장 과열 경고"})

    # 볼린저밴드 이탈 (VIX의 상단/하단 밴드)
    if ma20 and std20:
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        if current > upper:
            signals.append({"type": "danger", "msg": f"VIX 볼린저 상단 돌파 ({current:.1f} > {upper:.1f})"})
        elif current < lower:
            signals.append({"type": "safe", "msg": f"VIX 볼린저 하단 ({current:.1f} < {lower:.1f})"})

    # 추세 분석
    if ma20 and ma60:
        if ma20 > ma60 and current > ma20:
            signals.append({"type": "danger", "msg": "VIX 상승 추세 강화 중"})
        elif ma20 < ma60 and current < ma20:
            signals.append({"type": "safe", "msg": "VIX 하락 추세 (안정화)"})

    # Z-Score 이상치
    if z and abs(z) > 2:
        signals.append({"type": "danger" if z > 0 else "safe",
                        "msg": f"VIX 통계적 이상치 (Z={z:.2f}, {'극단 공포' if z > 0 else '과하게 낮음'})"})

    return {"signals": signals, "summary": f"VIX {current:.1f}", "current_vix": current, "vix_status": data.get("vix_status")}


def _analyze_liquidity(data: dict) -> dict:
    """유동성 지표 시그널 분석"""
    signals = []
    series = data.get("series", [])
    if not series:
        return {"signals": signals, "summary": "데이터 없음"}

    m2 = _extract_values(series, "m2_us_yoy")
    if not m2:
        return {"signals": signals, "summary": "M2 데이터 없음"}

    current = m2[-1]
    roc = _calc_roc(m2, 10) if len(m2) > 10 else None

    if current > 5:
        signals.append({"type": "safe", "msg": f"M2 YoY +{current:.1f}% — 유동성 풍부, 자산 가격 우호적"})
    elif current > 0:
        signals.append({"type": "warning", "msg": f"M2 YoY +{current:.1f}% — 유동성 둔화 추세"})
    else:
        signals.append({"type": "danger", "msg": f"M2 YoY {current:.1f}% — 유동성 축소, 긴축 환경"})

    # 변곡점 근접 여부
    inflections = data.get("inflection_points", [])
    if inflections:
        last = inflections[-1]
        signals.append({"type": "warning", "msg": f"최근 유동성 변곡점: {last['date']} ({last['direction']})"})

    return {"signals": signals, "summary": f"M2 YoY {current:+.1f}%", "has_m2_data": data.get("has_m2_data")}


def _analyze_leading(data: dict) -> dict:
    """경기 선행 지표 시그널 분석"""
    signals = []
    series = data.get("series", [])
    if not series:
        return {"signals": signals, "summary": "데이터 없음"}

    spread = _extract_values(series, "spread")
    if not spread:
        return {"signals": signals, "summary": "금리차 데이터 없음"}

    current = spread[-1]
    ma20 = _calc_ma(spread, 20)
    roc = _calc_roc(spread, 20)

    # 역전 상태
    if current < 0:
        signals.append({"type": "danger", "msg": f"금리 역전 중 ({current:.3f}%) — 경기 침체 선행 시그널"})
    elif current < 0.25:
        signals.append({"type": "warning", "msg": f"금리차 {current:.3f}% — 역전 근접 주의"})
    elif current < 1.0:
        signals.append({"type": "safe", "msg": f"금리차 {current:.3f}% — 약한 정상 (모니터링 필요)"})
    else:
        signals.append({"type": "safe", "msg": f"금리차 {current:.3f}% — 정상"})

    # 추세 (금리차의 방향)
    if roc is not None:
        if roc < -10:
            signals.append({"type": "warning", "msg": "금리차 급격히 축소 중"})
        elif roc > 10:
            signals.append({"type": "safe", "msg": "금리차 확대 추세 (디스인플레이션)"})

    # 역전 구간 이력
    inversions = data.get("inversion_zones", [])
    if inversions:
        signals.append({"type": "warning", "msg": f"최근 1년 내 역전 {len(inversions)}회 발생"})

    return {"signals": signals, "summary": f"10Y-2Y {current:+.3f}%"}


def _analyze_sector(data: dict) -> dict:
    """섹터 강도 시그널 분석"""
    signals = []
    sectors = data.get("sectors", {})
    if not sectors:
        return {"signals": signals, "summary": "데이터 없음"}

    # 각 섹터의 최근 상대강도 값 비교
    latest_values = {}
    for name, series in sectors.items():
        if series:
            latest_values[name] = series[-1].get("value", 0)

    if not latest_values:
        return {"signals": signals, "summary": "섹터 데이터 없음"}

    # 가장 강한/약한 섹터
    strongest = max(latest_values, key=latest_values.get)
    weakest = min(latest_values, key=latest_values.get)

    signals.append({"type": "safe", "msg": f"최강 섹터: {strongest} ({latest_values[strongest]:+.1f}%)"})
    signals.append({"type": "danger", "msg": f"최약 섹터: {weakest} ({latest_values[weakest]:+.1f}%)"})

    # KOSPI 아웃퍼폼 섹터 수
    outperform = [n for n, v in latest_values.items() if v > 0]
    if len(outperform) > len(latest_values) / 2:
        signals.append({"type": "safe", "msg": f"{len(outperform)}/{len(latest_values)} 섹터 KOSPI 아웃퍼폼"})
    else:
        signals.append({"type": "warning", "msg": f"{len(outperform)}/{len(latest_values)} 섹터만 KOSPI 아웃퍼폼"})

    return {"signals": signals, "summary": f"최강 {strongest}, 최약 {weakest}"}
