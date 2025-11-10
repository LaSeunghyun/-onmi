"""키워드 리포지토리"""
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.connection import get_db_connection


class KeywordRepository:
    """키워드 데이터 접근 리포지토리"""
    
    @staticmethod
    async def get_by_id(keyword_id: UUID, user_id: UUID) -> Optional[Dict]:
        """키워드 조회"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM keywords WHERE id = $1 AND user_id = $2",
                keyword_id, user_id
            )
            return dict(row) if row else None
    
    @staticmethod
    async def update_last_crawled_at(keyword_id: UUID, crawled_at: datetime) -> None:
        """마지막 수집 시간 업데이트"""
        async with get_db_connection() as conn:
            await conn.execute(
                "UPDATE keywords SET last_crawled_at = $1 WHERE id = $2",
                crawled_at, keyword_id
            )

