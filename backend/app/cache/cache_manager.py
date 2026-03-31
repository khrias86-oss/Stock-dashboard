"""
인메모리 TTL 캐시 매니저
-- 외부 API 호출 결과를 메모리에 저장하여 Rate Limit 방어
-- 프로덕션 환경에서는 Redis로 교체 가능한 구조
"""

import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """
    간단한 딕셔너리 기반 TTL 캐시
    - key: 문자열 식별자 (예: "macro_exchange_divergence")
    - value: 캐시할 데이터 (어떤 타입이든 가능)
    - ttl: Time To Live (초 단위). 이 시간이 지나면 캐시 무효화
    """

    def __init__(self):
        # { key: { "data": ..., "expires_at": timestamp } }
        self._store: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 데이터를 가져옴
        - 만료되었으면 None 반환 (자동 삭제)
        - 존재하지 않으면 None 반환
        """
        if key not in self._store:
            return None

        entry = self._store[key]
        if time.time() > entry["expires_at"]:
            # 만료된 캐시 삭제
            del self._store[key]
            logger.debug(f"캐시 만료됨: {key}")
            return None

        logger.debug(f"캐시 히트: {key}")
        return entry["data"]

    def set(self, key: str, data: Any, ttl: int = 3600) -> None:
        """
        데이터를 캐시에 저장
        - ttl: 생존 시간 (초). 기본값 1시간
        """
        self._store[key] = {
            "data": data,
            "expires_at": time.time() + ttl,
        }
        logger.debug(f"캐시 저장: {key} (TTL: {ttl}초)")

    def invalidate(self, key: str) -> None:
        """특정 키의 캐시를 수동으로 삭제"""
        if key in self._store:
            del self._store[key]
            logger.debug(f"캐시 무효화: {key}")

    def clear_all(self) -> None:
        """모든 캐시 삭제"""
        self._store.clear()
        logger.info("전체 캐시 클리어")

    def stats(self) -> dict:
        """캐시 상태 정보 반환 (디버깅용)"""
        now = time.time()
        active = sum(1 for v in self._store.values() if now <= v["expires_at"])
        expired = len(self._store) - active
        return {
            "total_keys": len(self._store),
            "active": active,
            "expired": expired,
        }


# 싱글톤 인스턴스
cache = CacheManager()
