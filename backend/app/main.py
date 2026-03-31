"""
FastAPI 메인 앱 엔트리포인트
-- CORS 설정, 라우터 등록, 헬스체크
-- uvicorn으로 실행: uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.routers import macro
from app.routers import ai_analysis
from app.routers import screening
from app.routers import portfolio

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="📊 주식 투자 판단 대시보드 API",
    description="거시 경제, 시장 스크리닝, 포트폴리오 분석을 위한 백엔드 API",
    version="1.0.0",
)

# === CORS 설정 (프론트엔드에서 API 호출 허용) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=False, # '*' 사용 시 False로 설정해야 브라우저에서 차단하지 않음
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 간단한 요청 로깅 (디버깅용) ===
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"[Request] {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"[Response] Status: {response.status_code}")
    return response

# === 라우터 등록 ===
app.include_router(macro.router)
app.include_router(ai_analysis.router)
app.include_router(screening.router)
app.include_router(portfolio.router)


# === 헬스체크 ===
@app.get("/", tags=["상태"])
def health_check():
    """서버 상태 확인"""
    return {
        "status": "running",
        "message": "📊 주식 투자 판단 대시보드 API가 정상 동작 중입니다.",
        "version": "1.0.0",
    }


@app.get("/api/health", tags=["상태"])
def api_health():
    """API 상세 상태 확인"""
    from app.cache.cache_manager import cache
    return {
        "status": "healthy",
        "cache_stats": cache.stats(),
        "api_keys": {
            "FRED": bool(settings.FRED_API_KEY and settings.FRED_API_KEY != "your_fred_api_key_here"),
            "ECOS": bool(settings.ECOS_API_KEY and settings.ECOS_API_KEY != "your_ecos_api_key_here"),
            "DART": bool(settings.DART_API_KEY and settings.DART_API_KEY != "your_dart_api_key_here"),
            "GEMINI": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here"),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.BACKEND_PORT, reload=True)
