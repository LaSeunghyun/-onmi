"""피드 관련 라우터"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
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


class ArticleFeedItem(BaseModel):
    id: str
    title: str
    snippet: str
    source: str
    url: str
    published_at: Optional[datetime]
    sentiment_label: str
    sentiment_score: float
    keyword: str


@router.get("")
async def get_feed(
    keyword_id: Optional[str] = Query(None, description="키워드 ID 필터"),
    filter_sentiment: Optional[str] = Query(None, description="감성 필터 (positive/negative/neutral)"),
    sort: str = Query("recent", description="정렬 방식 (recent/score)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """피드 조회 (필터, 정렬, 페이지네이션)"""
    try:
        async with get_db_connection() as conn:
            # 키워드 소유권 확인
            if keyword_id:
                keyword = await conn.fetchrow(
                    "SELECT id FROM keywords WHERE id = $1 AND user_id = $2 AND status = 'active'",
                    keyword_id, current_user["id"]
                )
                if not keyword:
                    return {"items": [], "total": 0, "page": page, "page_size": page_size}
            
            # WHERE 조건 구성
            where_conditions = ["ka.keyword_id IN (SELECT id FROM keywords WHERE user_id = $1 AND status = 'active')"]
            params = [current_user["id"]]
            param_idx = 2
            
            if keyword_id:
                where_conditions.append(f"ka.keyword_id = ${param_idx}")
                params.append(keyword_id)
                param_idx += 1
            
            if filter_sentiment:
                where_conditions.append(f"s.label = ${param_idx}")
                params.append(filter_sentiment)
                param_idx += 1
            
            where_clause = " AND ".join(where_conditions)
            
            # 정렬
            order_by = "a.published_at DESC" if sort == "recent" else "s.score DESC"
            
            # 전체 개수 조회
            count_query = f"""
                SELECT COUNT(DISTINCT a.id)
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN sentiments s ON a.id = s.article_id
                WHERE {where_clause}
            """
            total = await conn.fetchval(count_query, *params)
            
            # 페이지네이션
            offset = (page - 1) * page_size
            
            # 기사 조회
            query = f"""
                SELECT DISTINCT
                    a.id, a.title, a.snippet, a.source, a.url, a.published_at,
                    s.label as sentiment_label, s.score as sentiment_score,
                    k.text as keyword
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN sentiments s ON a.id = s.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """
            params.extend([page_size, offset])
            
            articles = await conn.fetch(query, *params)
            
            return {
                "items": [
                    ArticleFeedItem(
                        id=str(a["id"]),
                        title=a["title"],
                        snippet=a["snippet"] or "",
                        source=a["source"] or "",
                        url=a["url"],
                        published_at=a["published_at"],
                        sentiment_label=a["sentiment_label"],
                        sentiment_score=float(a["sentiment_score"]),
                        keyword=a["keyword"]
                    )
                    for a in articles
                ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"피드 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="피드를 불러오는 중 오류가 발생했습니다"
        )


