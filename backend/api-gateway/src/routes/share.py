"""공유 관련 라우터"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from src.routes.auth import get_current_user
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class ShareRequest(BaseModel):
    channel: str  # 'kakao', 'email', 'sms', 'clipboard', 'auto'
    recipient: Optional[str] = None  # 이메일 주소, 전화번호 등


class ShareHistoryItem(BaseModel):
    id: str
    article_id: str
    article_title: str
    keyword_id: Optional[str]
    keyword_text: Optional[str]
    channel: str
    recipient: Optional[str]
    shared_at: datetime


@router.post("/articles/{article_id}")
async def share_article(
    article_id: str,
    share_request: ShareRequest,
    current_user: dict = Depends(get_current_user)
):
    """기사 공유"""
    try:
        valid_channels = ['kakao', 'email', 'sms', 'clipboard', 'auto']
        if share_request.channel not in valid_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"channel은 {valid_channels} 중 하나여야 합니다"
            )
        
        async with get_db_connection() as conn:
            # 기사 접근 권한 확인 및 키워드 조회
            article_info = await conn.fetchrow(
                """
                SELECT a.id, a.title, ka.keyword_id
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE a.id = $1 AND k.user_id = $2 AND k.status = 'active'
                LIMIT 1
                """,
                article_id, current_user["id"]
            )
            
            if not article_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="기사를 찾을 수 없습니다"
                )
            
            # 공유 히스토리 저장
            share_id = await conn.fetchval(
                """
                INSERT INTO share_history (user_id, article_id, keyword_id, channel, recipient)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                current_user["id"],
                article_id,
                article_info["keyword_id"],
                share_request.channel,
                share_request.recipient
            )
            
            # user_actions에도 기록
            await conn.execute(
                """
                INSERT INTO user_actions (user_id, article_id, action, payload)
                VALUES ($1, $2, 'share', $3)
                """,
                current_user["id"],
                article_id,
                {"channel": share_request.channel, "recipient": share_request.recipient}
            )
            
            return {
                "message": "공유가 완료되었습니다",
                "share_id": str(share_id)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"기사 공유 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="기사 공유 중 오류가 발생했습니다"
        )


@router.get("/history")
async def get_share_history(
    keyword_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """공유 히스토리 조회"""
    try:
        async with get_db_connection() as conn:
            # WHERE 조건
            where_conditions = ["sh.user_id = $1"]
            params = [current_user["id"]]
            param_idx = 2
            
            if keyword_id:
                where_conditions.append(f"sh.keyword_id = ${param_idx}")
                params.append(keyword_id)
                param_idx += 1
            
            where_clause = " AND ".join(where_conditions)
            
            # 전체 개수
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM share_history sh WHERE {where_clause}",
                *params
            )
            
            # 페이지네이션
            offset = (page - 1) * page_size
            
            # 히스토리 조회
            history = await conn.fetch(
                f"""
                SELECT
                    sh.id, sh.article_id, sh.keyword_id, sh.channel, sh.recipient, sh.shared_at,
                    a.title as article_title,
                    k.text as keyword_text
                FROM share_history sh
                INNER JOIN articles a ON sh.article_id = a.id
                LEFT JOIN keywords k ON sh.keyword_id = k.id
                WHERE {where_clause}
                ORDER BY sh.shared_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """,
                *params, page_size, offset
            )
            
            return {
                "items": [
                    ShareHistoryItem(
                        id=str(h["id"]),
                        article_id=str(h["article_id"]),
                        article_title=h["article_title"],
                        keyword_id=str(h["keyword_id"]) if h["keyword_id"] else None,
                        keyword_text=h["keyword_text"],
                        channel=h["channel"],
                        recipient=h["recipient"],
                        shared_at=h["shared_at"]
                    )
                    for h in history
                ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"공유 히스토리 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="공유 히스토리를 불러오는 중 오류가 발생했습니다"
        )


