"""기사 리포지토리"""
from typing import Dict, List, Optional
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.connection import get_db_connection


class ArticleRepository:
    """기사 데이터 접근 리포지토리"""
    
    @staticmethod
    async def fetch_recent_by_user(user_id: UUID, limit: int = 100, include_archived: bool = False) -> List[Dict]:
        """사용자의 모든 키워드에 대한 최근 기사 조회"""
        async with get_db_connection() as conn:
            status_filter = "k.status = 'active'"
            if include_archived:
                status_filter = "k.status IN ('active', 'archived')"

            rows = await conn.fetch(
                """
                SELECT DISTINCT
                    a.id, a.title, a.snippet, a.source, a.url, a.published_at,
                    a.thumbnail_url_hash, a.created_at,
                    s.label as sentiment_label, s.score as sentiment_score,
                    s.rationale as sentiment_rationale
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                LEFT JOIN sentiments s ON a.id = s.article_id
                WHERE k.user_id = $1 AND {status_filter}
                ORDER BY a.published_at DESC NULLS LAST, a.created_at DESC
                LIMIT $2
                """.format(status_filter=status_filter),
                user_id, limit
            )
            return [dict(row) for row in rows]
    
    @staticmethod
    async def fetch_recent_by_keyword(keyword_id: UUID, limit: int = 50, include_archived: bool = False) -> List[Dict]:
        """키워드별 최근 기사 조회"""
        async with get_db_connection() as conn:
            status_filter = ""
            if include_archived:
                status_filter = "AND k.status IN ('active', 'archived')"
            else:
                status_filter = "AND k.status = 'active'"

            rows = await conn.fetch(
                """
                SELECT DISTINCT
                    a.id, a.title, a.snippet, a.source, a.url, a.published_at,
                    a.thumbnail_url_hash, a.created_at,
                    s.label as sentiment_label, s.score as sentiment_score,
                    s.rationale as sentiment_rationale
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                LEFT JOIN sentiments s ON a.id = s.article_id
                WHERE ka.keyword_id = $1
                  {status_filter}
                ORDER BY a.published_at DESC NULLS LAST, a.created_at DESC
                LIMIT $2
                """.format(status_filter=status_filter),
                keyword_id, limit
            )
            return [dict(row) for row in rows]
    
    @staticmethod
    async def count_recent_by_user(user_id: UUID, include_archived: bool = False) -> int:
        """사용자의 최근 기사 수를 조회"""
        async with get_db_connection() as conn:
            status_filter = "k.status = 'active'"
            if include_archived:
                status_filter = "k.status IN ('active', 'archived')"

            count = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT a.id)
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE k.user_id = $1 AND {status_filter}
                """.format(status_filter=status_filter),
                user_id,
            )
            return count or 0

    @staticmethod
    async def count_recent_by_keyword(keyword_id: UUID, include_archived: bool = False) -> int:
        """키워드별 최근 기사 수를 조회"""
        async with get_db_connection() as conn:
            status_filter = ""
            if include_archived:
                status_filter = "AND k.status IN ('active', 'archived')"
            else:
                status_filter = "AND k.status = 'active'"

            count = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT a.id)
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE ka.keyword_id = $1
                  {status_filter}
                """.format(status_filter=status_filter),
                keyword_id,
            )
            return count or 0

    @staticmethod
    async def upsert_batch(articles: List[Dict]) -> List[UUID]:
        """기사 일괄 저장 또는 업데이트"""
        article_ids = []
        async with get_db_connection() as conn:
            for article in articles:
                article_id = await conn.fetchval(
                    """
                    INSERT INTO articles (url, title, snippet, source, published_at, lang)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (url) DO UPDATE SET title = EXCLUDED.title
                    RETURNING id
                    """,
                    article.get('url'),
                    article.get('title'),
                    article.get('snippet'),
                    article.get('source'),
                    article.get('published_at'),
                    article.get('lang', 'ko')
                )
                article_ids.append(article_id)
        return article_ids

