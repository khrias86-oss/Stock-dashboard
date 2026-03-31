"""
포트폴리오 분석 엔진
-- CSV/JSON 형식 보유 종목 입력 → 종목별 분석
-- 기술적 지표: RSI(14), 볼린저밴드(20,2σ), MACD(12/26/9)
-- 재무 지표: PER/PBR/ROE (yfinance + DART)
-- 수익률/평가손익 계산

왜 기술적 지표를 직접 계산하는가:
외부 라이브러리(ta-lib 등)는 설치가 복잡하고 의존성 문제가 있음.
RSI/볼린저/MACD는 pandas/numpy만으로 충분히 정확하게 계산 가능.
"""

import logging
import io
import csv
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from app.cache.cache_manager import cache

logger = logging.getLogger(__name__)


# === 기술적 지표 계산 함수 ===

def calc_rsi(closes: pd.Series, period: int = 14) -> Optional[float]:
    """
    RSI(Relative Strength Index) 계산
    - 70 이상: 과매수 (매도 검토)
    - 30 이하: 과매도 (매수 검토)
    """
    if len(closes) < period + 1:
        return None

    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))

    avg_gain = gain.rolling(window=period).mean().iloc[-1]
    avg_loss = loss.rolling(window=period).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return float(round(100 - (100 / (1 + rs)), 2))


def calc_bollinger(closes: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
    """
    볼린저 밴드 계산
    - 상단 돌파: 과매수, 하락 가능성
    - 하단 이탈: 과매도, 반등 기대
    - %B: (현재가 - 하밴드) / (상밴드 - 하밴드)
    """
    if len(closes) < period:
        return {}

    ma = closes.rolling(window=period).mean()
    std = closes.rolling(window=period).std()
    upper = ma + (std_dev * std)
    lower = ma - (std_dev * std)

    current = closes.iloc[-1]
    curr_upper = upper.iloc[-1]
    curr_lower = lower.iloc[-1]
    curr_ma = ma.iloc[-1]

    width = curr_upper - curr_lower
    pct_b = float((current - curr_lower) / width * 100) if width > 0 else 50.0

    return {
        "upper": round(float(curr_upper)),
        "middle": round(float(curr_ma)),
        "lower": round(float(curr_lower)),
        "pct_b": round(pct_b, 1),  # 0~100, 50이 중간
        "position": "과매수" if pct_b > 100 else "과매도" if pct_b < 0 else "밴드 내",
    }


def calc_macd(closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    MACD (이동평균 수렴/발산) 계산
    - MACD > Signal: 매수 시그널 (골든크로스)
    - MACD < Signal: 매도 시그널 (데드크로스)
    """
    if len(closes) < slow + signal:
        return {}

    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    curr_macd = float(macd_line.iloc[-1])
    curr_signal = float(signal_line.iloc[-1])
    curr_hist = float(histogram.iloc[-1])

    # 크로스 판단: 직전 히스토그램 부호 변화
    prev_hist = float(histogram.iloc[-2]) if len(histogram) >= 2 else 0
    cross = "없음"
    if prev_hist < 0 and curr_hist > 0:
        cross = "골든크로스"
    elif prev_hist > 0 and curr_hist < 0:
        cross = "데드크로스"

    return {
        "macd": round(curr_macd, 2),
        "signal": round(curr_signal, 2),
        "histogram": round(curr_hist, 2),
        "cross": cross,
        "trend": "상승" if curr_macd > curr_signal else "하락",
    }


# === 포트폴리오 분석 ===

def analyze_portfolio(portfolio_items: list[dict]) -> dict:
    """
    포트폴리오 전체 분석
    - portfolio_items: [{"code": "005930", "buy_price": 60000, "quantity": 100}, ...]
    - 반환: 종목별 분석 + 포트폴리오 요약
    """
    results = []
    total_cost = 0
    total_value = 0

    for item in portfolio_items:
        account = item.get("account", "기본계좌").strip()
        code = item.get("code", "").strip()
        buy_price = float(item.get("buy_price", 0))
        quantity = int(item.get("quantity", 0))

        if not code or buy_price <= 0 or quantity <= 0:
            continue

        analysis = _analyze_single_holding(code, buy_price, quantity)
        if analysis:
            analysis["account"] = account
            results.append(analysis)
            total_cost += analysis.get("total_cost", 0)
            total_value += analysis.get("total_value", 0)

    # 포트폴리오 요약
    total_pnl = total_value - total_cost
    total_return = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    # 섹터 비중
    sector_weight = {}
    for r in results:
        sector = r.get("sector", "기타")
        sector_weight[sector] = sector_weight.get(sector, 0) + r.get("total_value", 0)
    # 비중 %로 변환
    if total_value > 0:
        sector_weight = {k: round(v / total_value * 100, 1) for k, v in sector_weight.items()}

    # 계좌별 요약
    accounts_summary = {}
    for r in results:
        acc = r["account"]
        if acc not in accounts_summary:
            accounts_summary[acc] = {"total_cost": 0, "total_value": 0, "total_pnl": 0}
        accounts_summary[acc]["total_cost"] += r["total_cost"]
        accounts_summary[acc]["total_value"] += r["total_value"]
        accounts_summary[acc]["total_pnl"] += r["pnl"]
    
    for acc, data in accounts_summary.items():
        data["total_return"] = round(data["total_pnl"] / data["total_cost"] * 100, 2) if data["total_cost"] > 0 else 0
        data["total_cost"] = round(data["total_cost"])
        data["total_value"] = round(data["total_value"])
        data["total_pnl"] = round(data["total_pnl"])

    return {
        "holdings": results,
        "summary": {
            "total_cost": round(total_cost),
            "total_value": round(total_value),
            "total_pnl": round(total_pnl),
            "total_return": round(total_return, 2),
            "holdings_count": len(results),
            "sector_weight": sector_weight,
            "accounts": accounts_summary,
        },
    }


def _analyze_single_holding(code: str, buy_price: float, quantity: int) -> Optional[dict]:
    """단일 보유 종목 분석"""
    ticker = f"{code}.KS"

    try:
        # 6개월 치 데이터 (기술적 지표 계산에 필요)
        df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(level=1, axis=1)

        closes = df["Close"].dropna()
        if len(closes) < 20:
            return None

        current_price = float(closes.iloc[-1])

        # 기본 정보
        try:
            info = yf.Ticker(ticker).info
            name = info.get("shortName") or info.get("longName", code)
            sector = info.get("sector", "기타")
            per = info.get("trailingPE") or info.get("forwardPE")
            pbr = info.get("priceToBook")
        except Exception:
            name = code
            sector = "기타"
            per = None
            pbr = None

        # 기술적 지표 계산
        rsi = calc_rsi(closes)
        bollinger = calc_bollinger(closes)
        macd = calc_macd(closes)

        # 수익률 계산
        total_cost = buy_price * quantity
        total_value = current_price * quantity
        pnl = total_value - total_cost
        return_pct = (pnl / total_cost) * 100

        # 종합 시그널 판정
        signal = _judge_holding_signal(rsi, bollinger, macd, return_pct)

        return {
            "code": code,
            "name": name,
            "sector": sector,
            "buy_price": round(buy_price),
            "current_price": round(current_price),
            "quantity": quantity,
            "total_cost": round(total_cost),
            "total_value": round(total_value),
            "pnl": round(pnl),
            "return_pct": round(return_pct, 2),
            "per": round(per, 2) if per else None,
            "pbr": round(pbr, 2) if pbr else None,
            "rsi": rsi,
            "bollinger": bollinger,
            "macd": macd,
            "signal": signal,
        }

    except Exception as e:
        logger.warning(f"[포트폴리오] {code} 분석 실패: {e}")
        return None


def _judge_holding_signal(rsi, bollinger, macd, return_pct) -> dict:
    """보유 종목 종합 시그널"""
    signals = []

    # RSI 시그널
    if rsi is not None:
        if rsi >= 70:
            signals.append({"type": "danger", "msg": f"RSI {rsi} — 과매수, 매도 검토"})
        elif rsi <= 30:
            signals.append({"type": "safe", "msg": f"RSI {rsi} — 과매도, 추가매수 검토"})
        else:
            signals.append({"type": "neutral", "msg": f"RSI {rsi} — 중립"})

    # 볼린저 시그널
    if bollinger:
        pct_b = bollinger.get("pct_b", 50)
        if pct_b > 100:
            signals.append({"type": "danger", "msg": "볼린저 상단 돌파 — 과열"})
        elif pct_b < 0:
            signals.append({"type": "safe", "msg": "볼린저 하단 이탈 — 반등 기대"})

    # MACD 시그널
    if macd:
        cross = macd.get("cross", "없음")
        if cross == "골든크로스":
            signals.append({"type": "safe", "msg": "MACD 골든크로스 — 매수 시그널"})
        elif cross == "데드크로스":
            signals.append({"type": "danger", "msg": "MACD 데드크로스 — 매도 시그널"})

    # 수익률 시그널
    if return_pct >= 30:
        signals.append({"type": "warning", "msg": f"수익률 +{return_pct:.0f}% — 차익실현 검토"})
    elif return_pct <= -20:
        signals.append({"type": "danger", "msg": f"수익률 {return_pct:.0f}% — 손절 검토"})

    # 종합 판정
    danger_count = sum(1 for s in signals if s["type"] == "danger")
    safe_count = sum(1 for s in signals if s["type"] == "safe")

    if danger_count >= 2:
        overall = "매도"
    elif danger_count >= 1:
        overall = "주의"
    elif safe_count >= 2:
        overall = "매수"
    elif safe_count >= 1:
        overall = "관망"
    else:
        overall = "보유"

    return {"overall": overall, "signals": signals}


def parse_csv(csv_text: str) -> list[dict]:
    """CSV 텍스트 → 포트폴리오 항목 리스트 파싱"""
    items = []
    reader = csv.reader(io.StringIO(csv_text))
    
    # 종목명 <-> 코드 맵핑 캐시 활용
    from app.services.dart_service import get_corp_codes
    corp_codes = get_corp_codes()
    name_to_code = {v["corp_name"]: k for k, v in corp_codes.items()}

    for i, row in enumerate(reader):
        if not row or len(row) < 3:
            continue
        try:
            # 4열 이상이면 [계좌명, 종목명/코드, 매수가, 수량]
            if len(row) >= 4:
                account = row[0].strip()
                name_or_code = row[1].strip()
                buy_price = float(row[2].strip().replace(",", ""))
                quantity = int(row[3].strip().replace(",", ""))
            else:
                account = "기본계좌"
                name_or_code = row[0].strip()
                buy_price = float(row[1].strip().replace(",", ""))
                quantity = int(row[2].strip().replace(",", ""))

            code = name_or_code
            if not code.isdigit() or len(code) != 6:
                matched_code = name_to_code.get(name_or_code)
                if not matched_code:
                    for corp_name, ccode in name_to_code.items():
                        if name_or_code in corp_name or corp_name in name_or_code:
                            matched_code = ccode
                            break
                if matched_code:
                    code = matched_code
                else:
                    logger.warning(f"[CSV] 맵핑 실패, 건너뜀: {name_or_code}")
                    continue

            if buy_price > 0 and quantity > 0 and code.isdigit() and len(code) == 6:
                items.append({"account": account, "code": code, "buy_price": buy_price, "quantity": quantity})
        except (ValueError, IndexError):
            if i == 0:
                continue
            logger.warning(f"[CSV] {i+1}행 파싱 실패: {row}")

    return items


# 샘플 포트폴리오 (테스트용)
SAMPLE_PORTFOLIO = [
    {"account": "주계좌", "code": "005930", "buy_price": 58000, "quantity": 100},
    {"account": "주계좌", "code": "000660", "buy_price": 155000, "quantity": 30},
    {"account": "연금계좌", "code": "005380", "buy_price": 210000, "quantity": 20},
    {"account": "연금계좌", "code": "035420", "buy_price": 320000, "quantity": 15},
    {"account": "주계좌", "code": "105560", "buy_price": 55000, "quantity": 50},
]
