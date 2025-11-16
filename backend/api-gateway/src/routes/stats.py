"""통계 관련 라우터"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from uuid import UUID
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.routes.auth import get_current_user
from database.connection import get_db_connection
from services.token_tracker import TokenTracker
from services.cse_query_limit_service import CSEQueryLimitService

# timezone_utils는 shared/utils에 있으므로 직접 import
shared_utils_path = os.path.join(os.path.dirname(__file__), '../../../shared/utils')
if shared_utils_path not in sys.path:
    sys.path.insert(0, shared_utils_path)
from timezone_utils import now_kst

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
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="키워드를 찾을 수 없습니다"
                )
            
            # 시작 날짜 계산 (한국 시간 기준)
            end_date = now_kst().date()
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


class TokenUsageResponse(BaseModel):
    """토큰 사용량 응답 모델"""
    today_usage: int
    daily_limit: int
    usage_percentage: float
    predicted_daily_usage: int
    is_limit_exceeded: bool
    can_make_request: bool
    reset_at: str
    message: str


@router.get("/token-usage", response_model=TokenUsageResponse)
async def get_token_usage():
    """시스템 전체 토큰 사용량 조회 (인증 불필요, 모든 사용자 동일 정보)
    
    시스템 전체 일일 토큰 사용량과 예측 정보를 조회합니다.
    모든 사용자가 동일한 정보를 받습니다.
    """
    try:
        token_tracker = TokenTracker()
        status_info = await token_tracker.get_usage_status()
        
        return TokenUsageResponse(
            today_usage=status_info['today_usage'],
            daily_limit=status_info['daily_limit'],
            usage_percentage=status_info['usage_percentage'],
            predicted_daily_usage=status_info['predicted_daily_usage'],
            is_limit_exceeded=status_info['is_limit_exceeded'],
            can_make_request=status_info['can_make_request'],
            reset_at=status_info['reset_at'],
            message=status_info['message']
        )
    except Exception as e:
        logger.error(f"토큰 사용량 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 사용량을 불러오는 중 오류가 발생했습니다"
        )


class CSEQueryUsageResponse(BaseModel):
    """Google CSE 쿼리 사용량 응답 모델"""
    usage_date: str
    user_quota: int
    user_used: int
    user_remaining: int
    keyword_quota: Optional[int] = None
    keyword_used: Optional[int] = None
    keyword_remaining: Optional[int] = None
    reset_at: str


@router.get("/cse-query-usage", response_model=CSEQueryUsageResponse)
async def get_cse_query_usage(
    keyword_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Google CSE 쿼리 사용 가능 수 조회"""
    try:
        quota_service = CSEQueryLimitService()
        user_uuid = UUID(str(current_user["id"]))

        user_usage = await quota_service.get_user_available_queries(user_uuid)

        response_data = {
            "usage_date": user_usage["usage_date"],
            "user_quota": user_usage["user_quota"],
            "user_used": user_usage["user_used"],
            "user_remaining": user_usage["user_remaining"],
            "reset_at": user_usage["reset_at"],
        }

        if keyword_id:
            try:
                keyword_uuid = UUID(keyword_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="유효하지 않은 키워드 ID입니다"
                )

            async with get_db_connection() as conn:
                keyword_exists = await conn.fetchval(
                    """
                    SELECT 1
                    FROM keywords
                    WHERE id = $1
                      AND user_id = $2
                      AND status = 'active'
                    """,
                    keyword_uuid,
                    user_uuid
                )

                if not keyword_exists:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="키워드를 찾을 수 없습니다"
                    )

            keyword_usage = await quota_service.calculate_keyword_quota(
                user_uuid,
                keyword_uuid
            )

            response_data.update(
                keyword_quota=keyword_usage["keyword_quota"],
                keyword_used=keyword_usage["keyword_used"],
                keyword_remaining=keyword_usage["keyword_remaining"],
            )

        return CSEQueryUsageResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSE 쿼리 사용량 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google CSE 쿼리 사용량을 불러오는 중 오류가 발생했습니다"
        )


