"""
스크리닝 API 라우터
-- 유망 종목 Top N 반환
-- 캐시 6시간
"""

import logging
import io
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.screening_engine import get_top_picks
from app.services.excel_export import generate_screening_excel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/screening", tags=["스크리닝"])


@router.get("/top-picks")
async def top_picks(limit: int = 10):
    """스크리닝 Top N 유망 종목 반환"""
    try:
        result = get_top_picks(limit=limit)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"[스크리닝 API] 오류: {e}")
        return {"status": "error", "error": str(e), "top_picks": []}


@router.get("/export")
async def export_picks():
    """유망 종목 엑셀 내보내기 (수식 포함)"""
    try:
        # 데이터 수집 (캐시 활용)
        data = get_top_picks(limit=20)
        picks = data.get("top_picks", [])
        if not picks:
            return {"status": "error", "message": "내보낼 데이터가 없습니다."}

        # 엑셀 생성
        excel_data = generate_screening_excel(picks)

        filename = f"Quant_Screening_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"[엑셀 내보내기] 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
