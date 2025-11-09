"""통계 관련 라우터"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime, timedelta
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from src.routes.auth import get_current_user
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class KeywordStats(BaseModel):
    date: str
    positive_count: int
    negative_count: int
    neutral_count: int
    total_count: int


@router.get("/keywords/{keyword_id}")
async def get_keyword_stats(
    keyword_id: str,
    days: int = 7,
    current_user: dict = Depends(get_current_user)
):
    """키워드별 일자별 감성 통계"""
    try:
        if days > 30:
            days = 30  # 최대 30일
        
        async with get_db_connection() as conn:
            # 키워드 소유권 확인
            keyword = await conn.fetchrow(
                "SELECT id FROM keywords WHERE id = $1 AND user_id = $2 AND status = 'active'",
                keyword_id, current_user["id"]
            )
            
            if not keyword:
                raise HTTPException(
                    status_code=404,
                    detail="키워드를 찾을 수 없습니다"
                )
            
            # 시작 날짜 계산
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)
            
            # 일자별 통계 조회
            stats = await conn.fetch(
                """
                SELECT
                    DATE(a.published_at) as date,
                    s.label,
                    COUNT(*) as count
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN sentiments s ON a.id = s.article_id
                WHERE ka.keyword_id = $1
                  AND DATE(a.published_at) >= $2
                  AND DATE(a.published_at) <= $3
                GROUP BY DATE(a.published_at), s.label
                ORDER BY date DESC
                """,
                keyword_id, start_date, end_date
            )
            
            # 날짜별로 그룹화
            stats_by_date: Dict[str, Dict[str, int]] = {}
            for stat in stats:
                date_str = stat["date"].isoformat()
                if date_str not in stats_by_date:
                    stats_by_date[date_str] = {
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0
                    }
                stats_by_date[date_str][stat["label"]] = stat["count"]
            
            # 결과 생성 (모든 날짜 포함)
            result = []
            current_date = end_date
            for _ in range(days):
                date_str = current_date.isoformat()
                counts = stats_by_date.get(date_str, {"positive": 0, "negative": 0, "neutral": 0})
                total = counts["positive"] + counts["negative"] + counts["neutral"]
                result.append(KeywordStats(
                    date=date_str,
                    positive_count=counts["positive"],
                    negative_count=counts["negative"],
                    neutral_count=counts["neutral"],
                    total_count=total
                ))
                current_date -= timedelta(days=1)
            
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"키워드 통계 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="통계를 불러오는 중 오류가 발생했습니다"
        )


