"""
포트폴리오 API 라우터
-- CSV 업로드 → 분석 결과 반환
-- 샘플 포트폴리오 제공
"""

import logging
from fastapi import APIRouter, Body

from app.services.portfolio_engine import (
    analyze_portfolio,
    parse_csv,
    SAMPLE_PORTFOLIO,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portfolio", tags=["포트폴리오"])


@router.post("/analyze")
async def analyze(body: dict = Body(...)):
    """
    포트폴리오 분석
    - body.items: [{"code": "005930", "buy_price": 60000, "quantity": 100}, ...]
    - body.csv: CSV 텍스트 (종목코드,매수가,수량)
    """
    try:
        items = body.get("items")
        csv_text = body.get("csv")

        if csv_text:
            items = parse_csv(csv_text)
        elif not items:
            return {"status": "error", "error": "포트폴리오 데이터를 입력해주세요."}

        result = analyze_portfolio(items)
        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"[포트폴리오 API] 오류: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/sample")
async def sample():
    """샘플 포트폴리오 분석 (테스트용)"""
    try:
        result = analyze_portfolio(SAMPLE_PORTFOLIO)
        return {"status": "success", "is_sample": True, **result}
    except Exception as e:
        logger.error(f"[포트폴리오 샘플] 오류: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/sample-csv")
async def get_sample_csv():
    """샘플 CSV 양식 다운로드"""
    from fastapi.responses import PlainTextResponse
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["계좌명", "종목명(또는 종목코드)", "매수가", "수량"])
    writer.writerow(["주계좌", "삼성전자", "60000", "150"])
    writer.writerow(["주계좌", "SK하이닉스", "150000", "50"])
    writer.writerow(["연금계좌", "NAVER", "200000", "30"])
    
    response = PlainTextResponse(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=sample_portfolio.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return response
