"""기사 리포지토리"""
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime
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
    async def fetch_recent_by_keyword_since(
        keyword_id: UUID, 
        since_datetime: Optional[datetime] = None,
        limit: int = 50, 
        include_archived: bool = False
    ) -> List[Dict]:
        """키워드별 최근 기사 조회 (날짜 필터 적용)
        
        Args:
            keyword_id: 키워드 ID
            since_datetime: 시작 시간 (None이면 필터 없음)
            limit: 최대 조회 개수
            include_archived: 아카이브된 키워드 포함 여부
            
        Returns:
            기사 목록
        """
        async with get_db_connection() as conn:
            status_filter = ""
            if include_archived:
                status_filter = "AND k.status IN ('active', 'archived')"
            else:
                status_filter = "AND k.status = 'active'"
            
            # 날짜 필터 조건 추가
            date_filter = ""
            params = [keyword_id]
            param_idx = 2
            
            if since_datetime is not None:
                date_filter = f"AND a.created_at >= ${param_idx}"
                params.append(since_datetime)
                param_idx += 1
            
            params.append(limit)
            
            query = f"""
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
                  {date_filter}
                ORDER BY a.published_at DESC NULLS LAST, a.created_at DESC
                LIMIT ${param_idx}
            """
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    @staticmethod
    async def fetch_recent_by_user_since(
        user_id: UUID,
        since_datetime: Optional[datetime] = None,
        limit: int = 100,
        include_archived: bool = False
    ) -> List[Dict]:
        """사용자의 모든 키워드에 대한 최근 기사 조회 (날짜 필터 적용)
        
        Args:
            user_id: 사용자 ID
            since_datetime: 시작 시간 (None이면 필터 없음)
            limit: 최대 조회 개수
            include_archived: 아카이브된 키워드 포함 여부
            
        Returns:
            기사 목록
        """
        async with get_db_connection() as conn:
            status_filter = "k.status = 'active'"
            if include_archived:
                status_filter = "k.status IN ('active', 'archived')"
            
            # 날짜 필터 조건 추가
            date_filter = ""
            params = [user_id]
            param_idx = 2
            
            if since_datetime is not None:
                date_filter = f"AND a.created_at >= ${param_idx}"
                params.append(since_datetime)
                param_idx += 1
            
            params.append(limit)
            
            query = f"""
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
                  {date_filter}
                ORDER BY a.published_at DESC NULLS LAST, a.created_at DESC
                LIMIT ${param_idx}
            """
            
            rows = await conn.fetch(query, *params)
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
    async def count_recent_by_keyword_since(
        keyword_id: UUID,
        since_datetime: Optional[datetime] = None,
        include_archived: bool = False
    ) -> int:
        """키워드별 최근 기사 수를 조회 (날짜 필터 적용)
        
        Args:
            keyword_id: 키워드 ID
            since_datetime: 시작 시간 (None이면 필터 없음)
            include_archived: 아카이브된 키워드 포함 여부
            
        Returns:
            기사 수
        """
        async with get_db_connection() as conn:
            status_filter = ""
            if include_archived:
                status_filter = "AND k.status IN ('active', 'archived')"
            else:
                status_filter = "AND k.status = 'active'"
            
            # 날짜 필터 조건 추가
            date_filter = ""
            params = [keyword_id]
            param_idx = 2
            
            if since_datetime is not None:
                date_filter = f"AND a.created_at >= ${param_idx}"
                params.append(since_datetime)
            
            query = f"""
                SELECT COUNT(DISTINCT a.id)
                FROM articles a
                INNER JOIN keyword_articles ka ON a.id = ka.article_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE ka.keyword_id = $1
                  {status_filter}
                  {date_filter}
            """
            
            count = await conn.fetchval(query, *params)
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

    @staticmethod
    async def link_keyword_article(keyword_id: UUID, article_id: UUID) -> None:
        """키워드와 기사 매핑 저장"""
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO keyword_articles (keyword_id, article_id, match_score, match_type)
                VALUES ($1, $2, 1.0, 'exact')
                ON CONFLICT (keyword_id, article_id) DO NOTHING
                """,
                keyword_id, article_id
            )

    @staticmethod
    async def save_sentiment(article_id: UUID, sentiment: Dict[str, Any]) -> None:
        """감성 분석 결과 저장"""
        import json
        
        rationale_value = sentiment.get('rationale')
        # rationale이 dict인 경우 JSON 문자열로 변환
        if isinstance(rationale_value, dict):
            rationale_value = json.dumps(rationale_value, ensure_ascii=False)
        elif rationale_value and not isinstance(rationale_value, str):
            rationale_value = json.dumps(rationale_value, ensure_ascii=False)
            
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO sentiments (article_id, label, score, rationale, model_ver)
                VALUES ($1, $2, $3, $4::jsonb, 'rule-based-v1')
                ON CONFLICT (article_id) DO UPDATE SET
                    label = EXCLUDED.label,
                    score = EXCLUDED.score,
                    rationale = EXCLUDED.rationale
                """,
                article_id,
                sentiment.get('label'),
                sentiment.get('score'),
                rationale_value
            )

