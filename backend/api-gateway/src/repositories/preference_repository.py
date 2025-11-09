"""사용자 선호도 리포지토리"""
from typing import Optional, Dict, Any
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from database.connection import get_db_connection


class PreferenceRepository:
    """사용자 선호도 데이터 접근 리포지토리"""
    
    @staticmethod
    async def upsert(
        user_id: UUID,
        preferred_detail_level: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        keyword_id: Optional[UUID] = None
    ) -> None:
        """사용자 선호도 저장 또는 업데이트"""
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO user_preferences (user_id, keyword_id, preferred_detail_level, preferences)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, keyword_id) DO UPDATE SET
                    preferred_detail_level = EXCLUDED.preferred_detail_level,
                    preferences = EXCLUDED.preferences,
                    updated_at = NOW()
                """,
                user_id, keyword_id, preferred_detail_level, preferences or {}
            )
    
    @staticmethod
    async def get(
        user_id: UUID,
        keyword_id: Optional[UUID] = None
    ) -> Optional[dict]:
        """사용자 선호도 조회"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, keyword_id, preferred_detail_level, preferences, created_at, updated_at
                FROM user_preferences
                WHERE user_id = $1 AND (keyword_id = $2 OR ($2 IS NULL AND keyword_id IS NULL))
                """,
                user_id, keyword_id
            )
            return dict(row) if row else None
    
    @staticmethod
    async def get_detail_level(
        user_id: UUID,
        keyword_id: Optional[UUID] = None
    ) -> Optional[str]:
        """선호하는 상세 수준 조회"""
        pref = await PreferenceRepository.get(user_id, keyword_id)
        return pref.get('preferred_detail_level') if pref else None

