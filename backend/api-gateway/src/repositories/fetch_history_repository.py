"""수집 이력 리포지토리"""
from typing import List, Optional
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.connection import get_db_connection
from models.fetch_history import FetchHistory


class FetchHistoryRepository:
    """수집 이력 데이터 접근 리포지토리"""
    
    @staticmethod
    async def list_by_keyword(keyword_id: UUID, order_by: str = "actual_start") -> List[FetchHistory]:
        """키워드별 수집 이력 조회"""
        # SQL 인젝션 방지를 위한 화이트리스트 검증
        allowed_order_by = ["actual_start", "actual_end", "requested_start", "requested_end", "created_at"]
        if order_by not in allowed_order_by:
            order_by = "actual_start"  # 기본값으로 폴백
        
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM fetch_history
                WHERE keyword_id = $1
                ORDER BY {order_by} DESC
                """,
                keyword_id
            )
            return [FetchHistory.from_db_row(row) for row in rows]
    
    @staticmethod
    async def insert(
        keyword_id: UUID,
        requested_start,
        requested_end,
        actual_start,
        actual_end,
        articles_count: int
    ) -> UUID:
        """수집 이력 저장"""
        async with get_db_connection() as conn:
            history_id = await conn.fetchval(
                """
                INSERT INTO fetch_history (
                    keyword_id, requested_start, requested_end,
                    actual_start, actual_end, articles_count
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                keyword_id, requested_start, requested_end,
                actual_start, actual_end, articles_count
            )
            return history_id

