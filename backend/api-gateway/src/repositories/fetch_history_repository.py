"""수집 이력 리포지토리"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
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
    
    @staticmethod
    async def get_latest_fetch_end_by_keyword(keyword_id: UUID) -> Optional[datetime]:
        """키워드별 마지막 수집 종료 시간 조회
        
        Args:
            keyword_id: 키워드 ID
            
        Returns:
            마지막 수집 종료 시간 (actual_end), 없으면 None
        """
        async with get_db_connection() as conn:
            result = await conn.fetchrow(
                """
                SELECT actual_end
                FROM fetch_history
                WHERE keyword_id = $1
                ORDER BY actual_end DESC
                LIMIT 1
                """,
                keyword_id
            )
            return result['actual_end'] if result else None
    
    @staticmethod
    async def get_latest_fetch_end_by_user(user_id: UUID) -> Optional[datetime]:
        """사용자별 모든 키워드 중 가장 오래된 마지막 수집 시간 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            사용자의 모든 키워드 중 가장 오래된 마지막 수집 종료 시간, 없으면 None
        """
        async with get_db_connection() as conn:
            result = await conn.fetchrow(
                """
                SELECT MIN(fh.actual_end) as latest_fetch_end
                FROM fetch_history fh
                INNER JOIN keywords k ON fh.keyword_id = k.id
                WHERE k.user_id = $1
                  AND k.status = 'active'
                """,
                user_id
            )
            return result['latest_fetch_end'] if result and result['latest_fetch_end'] else None

