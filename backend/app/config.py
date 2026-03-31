"""
환경변수 및 설정 관리 모듈
-- API Key가 없어도 앱이 동작하도록 기본값을 제공합니다.
-- .env 파일 또는 시스템 환경변수에서 값을 읽습니다.
"""

import os
from dotenv import load_dotenv
import logging

# .env 파일 로딩 (있으면 사용, 없으면 무시)
load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """앱 전체 설정을 중앙 관리하는 클래스"""

    def __init__(self):
        # --- API Keys (없으면 빈 문자열 → 해당 기능은 Fallback 처리) ---
        self.FRED_API_KEY = os.getenv("FRED_API_KEY", "")
        self.ECOS_API_KEY = os.getenv("ECOS_API_KEY", "")
        self.DART_API_KEY = os.getenv("DART_API_KEY", "")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

        # --- 서버 설정 ---
        self.FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

        # --- 캐시 TTL (초 단위) ---
        self.CACHE_TTL_MARKET_HOURS = 3600       # 장중: 1시간
        self.CACHE_TTL_AFTER_MARKET = 43200      # 장 마감 후: 12시간

        # 보유 중인 API Key 상태를 로그로 알려줌
        self._log_api_status()

    def _log_api_status(self):
        """어떤 API Key가 설정되어 있는지 로그 출력"""
        keys = {
            "FRED": self.FRED_API_KEY,
            "ECOS": self.ECOS_API_KEY,
            "DART": self.DART_API_KEY,
            "GEMINI": self.GEMINI_API_KEY,
        }
        for name, key in keys.items():
            if key and key != f"your_{name.lower()}_api_key_here":
                logger.info(f"✅ {name} API Key: 설정됨")
            else:
                logger.warning(f"⚠️ {name} API Key: 미설정 → Fallback 데이터 사용")


# 싱글톤 인스턴스 (앱 전체에서 이 인스턴스를 import하여 사용)
settings = Settings()
