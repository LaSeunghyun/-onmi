"""기사 관련 라우터"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from src.routes.auth import get_current_user
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class ArticleDetail(BaseModel):
    id: str
    title: str
    snippet: str
    source: str
    url: str
    published_at: Optional[datetime]
    thumbnail_url_hash: Optional[str]
    sentiment_label: str
    sentiment_score: float
    sentiment_rationale: Optional[Dict[str, Any]]
    keywords: List[str]


class FeedbackRequest(BaseModel):
    label: str  # positive, negative, neutral
    comment: Optional[str] = None


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: str,
    current_user: dict = Depends(get_current_user)
):
    """기사 상세 조회"""
    try:
        async with get_db_connection() as conn:
            # 기사 조회 (사용자의 키워드와 연결된 기사만)
            article = await conn.fetchrow(
                """
                SELECT DISTINCT
                    a.id, a.title, a.snippet, a.source, a.url, a.published_at,
                    a.thumbnail_url_hash,
                    s.label as sentiment_label, s.score as sentiment_score,
                    s.rationale as sentiment_rationale
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN sentiments s ON a.id = s.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE a.id = $1 AND k.user_id = $2 AND k.status = 'active'
                """,
                article_id, current_user["id"]
            )
            
            if not article:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="기사를 찾을 수 없습니다"
                )
            
            # 키워드 목록 조회
            keywords = await conn.fetch(
                """
                SELECT DISTINCT k.text
                FROM keywords k
                INNER JOIN keyword_articles ka ON k.id = ka.keyword_id
                WHERE ka.article_id = $1 AND k.user_id = $2 AND k.status = 'active'
                """,
                article_id, current_user["id"]
            )
            
            # sentiment_score가 None일 수 있으므로 기본값 처리
            sentiment_score = float(article["sentiment_score"]) if article["sentiment_score"] is not None else 0.0
            
            return ArticleDetail(
                id=str(article["id"]),
                title=article["title"],
                snippet=article["snippet"] or "",
                source=article["source"] or "",
                url=article["url"],
                published_at=article["published_at"],
                thumbnail_url_hash=article["thumbnail_url_hash"],
                sentiment_label=article["sentiment_label"],
                sentiment_score=sentiment_score,
                sentiment_rationale=article["sentiment_rationale"],
                keywords=[kw["text"] for kw in keywords]
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"기사 상세 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="기사를 불러오는 중 오류가 발생했습니다"
        )


@router.post("/{article_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    article_id: str,
    feedback: FeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """감성 분류 피드백 제출"""
    try:
        if feedback.label not in ["positive", "negative", "neutral"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="label은 positive, negative, neutral 중 하나여야 합니다"
            )
        
        async with get_db_connection() as conn:
            # 기사 접근 권한 확인
            article = await conn.fetchrow(
                """
                SELECT a.id
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE a.id = $1 AND k.user_id = $2 AND k.status = 'active'
                """,
                article_id, current_user["id"]
            )
            
            if not article:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="기사를 찾을 수 없습니다"
                )
            
            # 피드백 저장 (JSONB 타입에 딕셔너리를 저장하기 위해 JSON 문자열로 변환)
            payload_dict = {"label": feedback.label, "comment": feedback.comment}
            payload_json = json.dumps(payload_dict)
            
            await conn.execute(
                """
                INSERT INTO user_actions (user_id, article_id, action, payload)
                VALUES ($1, $2, 'feedback', $3::jsonb)
                """,
                current_user["id"],
                article_id,
                payload_json
            )
            
            return {"message": "피드백이 제출되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"피드백 제출 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="피드백 제출 중 오류가 발생했습니다"
        )


