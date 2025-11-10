"""사용자 선호도 리포지토리"""
from typing import Dict, Any, Optional, List
from uuid import UUID
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.connection import get_db_connection


class PreferenceRepository:
    """사용자 선호도 데이터 접근 리포지토리"""
    
    @staticmethod
    async def get(user_id: UUID) -> Dict[str, Any]:
        """사용자 선호도 조회"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT preferences FROM user_preferences
                WHERE user_id = $1
                """,
                user_id
            )
            if row and row['preferences'] is not None:
                preferences = row['preferences']
                # JSONB는 이미 딕셔너리로 반환되지만, 안전하게 처리
                if isinstance(preferences, dict):
                    return preferences
                elif isinstance(preferences, str):
                    # 문자열인 경우 JSON 파싱
                    return json.loads(preferences)
                else:
                    # 그 외의 경우 dict()로 변환 시도
                    try:
                        return dict(preferences) if preferences else {}
                    except (TypeError, ValueError):
                        return {}
            return {}
    
    @staticmethod
    async def upsert(user_id: UUID, preferences: Dict[str, Any]) -> None:
        """사용자 선호도 저장 또는 업데이트"""
        # JSONB 타입에 딕셔너리를 저장하기 위해 JSON 문자열로 변환
        preferences_json = json.dumps(preferences)
        
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO user_preferences (user_id, preferences)
                VALUES ($1, $2::jsonb)
                ON CONFLICT (user_id) DO UPDATE SET
                    preferences = EXCLUDED.preferences,
                    updated_at = NOW()
                """,
                user_id, preferences_json
            )
    
    @staticmethod
    async def get_users_by_notification_time(hour: int) -> List[UUID]:
        """특정 시간에 알림을 받을 사용자 목록 조회"""
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id FROM user_preferences
                WHERE preferences->>'notification_time_hour' = $1
                """,
                str(hour)
            )
            return [row['user_id'] for row in rows]
