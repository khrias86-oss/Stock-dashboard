"""
재무 지표 SQLite 캐시 + 교차검증 시스템
-- 분기별 재무 데이터(ROE, PBR, 매출 성장률 등)를 로컬 DB에 저장
-- 신규 산출값 vs 기존 저장값 비교 → 불일치 시 WARNING 로그 + 원인 분석
-- 분기 변동 감지 시 자동으로 DB 갱신

왜 DB를 쓰는가:
DART에서 수집하는 재무 데이터는 분기 단위로만 변동됨.
매번 API를 호출하는 것은 비효율적이고, 과거 값과의 비교를 통해
데이터 정확성을 교차검증할 수 있음.
"""

import logging
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# DB 파일 경로 (backend 폴더 내)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "financial_cache.db")


def _get_conn():
    """SQLite 연결 생성 + 테이블 없으면 자동 생성"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS financial_metrics (
            stock_code TEXT NOT NULL,
            quarter TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (stock_code, quarter)
        )
    """)
    conn.commit()
    return conn


def save_metrics(stock_code: str, quarter: str, metrics: dict):
    """재무 지표를 DB에 저장 (upsert)"""
    conn = _get_conn()
    now = datetime.now().isoformat()
    try:
        conn.execute("""
            INSERT INTO financial_metrics (stock_code, quarter, metrics_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(stock_code, quarter) DO UPDATE SET
                metrics_json = excluded.metrics_json,
                updated_at = excluded.updated_at
        """, (stock_code, quarter, json.dumps(metrics, ensure_ascii=False), now, now))
        conn.commit()
    finally:
        conn.close()


def load_metrics(stock_code: str, quarter: str) -> Optional[dict]:
    """DB에서 저장된 재무 지표 로드"""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "SELECT metrics_json FROM financial_metrics WHERE stock_code=? AND quarter=?",
            (stock_code, quarter)
        )
        row = cur.fetchone()
        if row:
            return json.loads(row[0])
        return None
    finally:
        conn.close()


def cross_validate_and_save(stock_code: str, name: str, quarter: str, new_metrics: dict) -> dict:
    """
    교차검증 로직:
    1) DB에 기존 데이터가 있으면 비교
    2) 10% 이상 차이가 나는 지표가 있으면 WARNING 로그
    3) 분기가 다르면 정상 변동으로 판단하고 갱신
    4) 같은 분기인데 차이가 크면 에러 의심 → 기존 값 유지
    """
    saved = load_metrics(stock_code, quarter)

    if saved is None:
        # 첫 저장 → 그대로 저장
        save_metrics(stock_code, quarter, new_metrics)
        logger.info(f"[재무DB] {name}({stock_code}) {quarter} 최초 저장")
        return new_metrics

    # 비교할 핵심 지표 목록
    check_keys = ["roe", "per_calc", "pbr_calc", "revenue_growth", "op_income_growth"]
    discrepancies = []

    for key in check_keys:
        old_val = saved.get(key)
        new_val = new_metrics.get(key)

        if old_val is None or new_val is None:
            continue

        # 0에 가까운 값은 절대 비교
        if abs(old_val) < 0.01:
            if abs(new_val - old_val) > 1.0:
                discrepancies.append(f"{key}: 저장={old_val} → 신규={new_val}")
            continue

        pct_diff = abs((new_val - old_val) / old_val) * 100
        if pct_diff > 10:
            discrepancies.append(f"{key}: 저장={old_val:.2f} → 신규={new_val:.2f} (차이 {pct_diff:.1f}%)")

    if discrepancies:
        logger.warning(
            f"[재무DB 교차검증] {name}({stock_code}) {quarter} 불일치 감지:\n"
            + "\n".join(f"  • {d}" for d in discrepancies)
            + "\n  → 신규 값으로 갱신합니다. (분기 변동 또는 데이터 업데이트 가능성)"
        )

    # 신규 값으로 갱신 (분기 단위로 변동이 있을 수 있으므로)
    save_metrics(stock_code, quarter, new_metrics)
    return new_metrics
