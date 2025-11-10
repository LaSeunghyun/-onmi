"""요약 세션 리포지토리"""
from typing import Dict, Optional
from uuid import UUID
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.connection import get_db_connection


class SummarySessionRepository:
    """요약 세션 데이터 접근 리포지토리"""
    
    @staticmethod
    async def create(
        keyword_id: Optional[UUID],
        user_id: UUID,
        summary_text: str,
        summary_type: str,
        summarization_config: Optional[Dict] = None
    ) -> Dict:
        """요약 세션 생성"""
        # JSONB 타입에 딕셔너리를 저장하기 위해 JSON 문자열로 변환
        config_json = json.dumps(summarization_config) if summarization_config else None
        
        async with get_db_connection() as conn:
            session_id = await conn.fetchval(
                """
                INSERT INTO summary_sessions (
                    keyword_id, user_id, summary_text, summary_type, summarization_config
                )
                VALUES ($1, $2, $3, $4, $5::jsonb)
                RETURNING id
                """,
                keyword_id, user_id, summary_text, summary_type, config_json
            )
            # 생성된 세션 조회
            session = await conn.fetchrow(
                """
                SELECT id, keyword_id, user_id, summary_text, summary_type,
                       summarization_config, created_at
                FROM summary_sessions
                WHERE id = $1
                """,
                session_id
            )
            return dict(session)
    
    @staticmethod
    async def get_latest_daily(user_id: UUID) -> Optional[Dict]:
        """사용자의 최신 일일 요약 조회"""
        async with get_db_connection() as conn:
            session = await conn.fetchrow(
                """
                SELECT id, keyword_id, user_id, summary_text, summary_type,
                       summarization_config, created_at
                FROM summary_sessions
                WHERE user_id = $1 
                  AND keyword_id IS NULL 
                  AND summary_type = 'daily'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id
            )
            return dict(session) if session else None
    
    @staticmethod
    async def get_latest_by_keyword(keyword_id: UUID, user_id: UUID) -> Optional[Dict]:
        """특정 키워드의 최신 요약 조회"""
        async with get_db_connection() as conn:
            session = await conn.fetchrow(
                """
                SELECT id, keyword_id, user_id, summary_text, summary_type,
                       summarization_config, created_at
                FROM summary_sessions
                WHERE keyword_id = $1 
                  AND user_id = $2 
                  AND summary_type = 'keyword'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                keyword_id, user_id
            )
            return dict(session) if session else None

