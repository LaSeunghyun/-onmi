"""키워드-기사 매핑 리포지토리"""
from typing import List
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.connection import get_db_connection


class KeywordArticleMapper:
    """키워드-기사 매핑 데이터 접근 리포지토리"""
    
    @staticmethod
    async def link(keyword_id: UUID, article_ids: List[UUID]) -> None:
        """키워드와 기사 연결"""
        async with get_db_connection() as conn:
            for article_id in article_ids:
                await conn.execute(
                    """
                    INSERT INTO keyword_articles (keyword_id, article_id, match_score, match_type)
                    VALUES ($1, $2, 1.0, 'exact')
                    ON CONFLICT (keyword_id, article_id) DO NOTHING
                    """,
                    keyword_id, article_id
                )

