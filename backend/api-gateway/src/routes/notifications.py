"""알림 관련 라우터"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from src.routes.auth import get_current_user
from database.connection import get_db_connection

# timezone_utils는 shared/utils에 있으므로 직접 import
shared_utils_path = os.path.join(os.path.dirname(__file__), '../../../shared/utils')
if shared_utils_path not in sys.path:
    sys.path.insert(0, shared_utils_path)
from timezone_utils import now_kst

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationConfig(BaseModel):
    keyword_id: str
    enabled: bool
    threshold: str = "standard"  # simple, standard, sensitive


@router.post("/detect-negative-surge")
async def detect_negative_surge(
    keyword_id: str,
    current_user: dict = Depends(get_current_user)
):
    """부정 급증 감지"""
    try:
        async with get_db_connection() as conn:
            # 키워드 소유권 확인
            keyword = await conn.fetchrow(
                "SELECT id FROM keywords WHERE id = $1 AND user_id = $2 AND status = 'active'",
                keyword_id, current_user["id"]
            )
            
            if not keyword:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="키워드를 찾을 수 없습니다"
                )
            
            # 최근 6시간 부정 기사 수 (한국 시간 기준)
            six_hours_ago = now_kst() - timedelta(hours=6)
            recent_negative = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN sentiments s ON a.id = s.article_id
                WHERE ka.keyword_id = $1
                  AND a.published_at >= $2
                  AND s.label = 'negative'
                """,
                keyword_id, six_hours_ago
            )
            
            # 최근 6시간 전체 기사 수
            recent_total = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                WHERE ka.keyword_id = $1
                  AND a.published_at >= $2
                """,
                keyword_id, six_hours_ago
            )
            
            # 최근 7일 평균 부정 비율 (한국 시간 기준)
            seven_days_ago = now_kst() - timedelta(days=7)
            avg_negative = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN sentiments s ON a.id = s.article_id
                WHERE ka.keyword_id = $1
                  AND a.published_at >= $2
                  AND s.label = 'negative'
                """,
                keyword_id, seven_days_ago
            )
            
            avg_total = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                WHERE ka.keyword_id = $1
                  AND a.published_at >= $2
                """,
                keyword_id, seven_days_ago
            )
            
            if recent_total == 0 or avg_total == 0:
                return {
                    "surge_detected": False,
                    "recent_negative_ratio": 0.0,
                    "average_negative_ratio": 0.0
                }
            
            recent_ratio = recent_negative / recent_total
            avg_ratio = avg_negative / avg_total
            
            # 임계값: 평균의 1.5배 이상이고 최소 3건 이상
            threshold = avg_ratio * 1.5
            surge_detected = recent_ratio > threshold and recent_negative >= 3
            
            return {
                "surge_detected": surge_detected,
                "recent_negative_ratio": recent_ratio,
                "average_negative_ratio": avg_ratio,
                "recent_negative_count": recent_negative,
                "threshold": threshold
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"부정 급증 감지 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="부정 급증 감지 중 오류가 발생했습니다"
        )


