"""요약 세션 리포지토리"""
from typing import Dict, Optional, List
from datetime import date
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

    @staticmethod
    async def get_daily_by_date(user_id: UUID, target_date: date) -> Optional[Dict]:
        """특정 날짜의 일일 요약 조회 (한국 시간 기준)
        
        target_date는 한국 시간(KST, UTC+9) 기준 날짜입니다.
        created_at이 UTC로 저장되어 있으므로, 한국 시간으로 변환하여 날짜를 비교합니다.
        """
        async with get_db_connection() as conn:
            session = await conn.fetchrow(
                """
                SELECT id, keyword_id, user_id, summary_text, summary_type,
                       summarization_config, created_at
                FROM summary_sessions
                WHERE user_id = $1
                  AND keyword_id IS NULL
                  AND summary_type = 'daily'
                  AND DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul') = $2
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id, target_date
            )
            return dict(session) if session else None

    @staticmethod
    async def get_keyword_by_date(keyword_id: UUID, user_id: UUID, target_date: date) -> Optional[Dict]:
        """특정 날짜의 키워드별 요약 조회 (한국 시간 기준)
        
        target_date는 한국 시간(KST, UTC+9) 기준 날짜입니다.
        created_at이 UTC로 저장되어 있으므로, 한국 시간으로 변환하여 날짜를 비교합니다.
        """
        async with get_db_connection() as conn:
            session = await conn.fetchrow(
                """
                SELECT id, keyword_id, user_id, summary_text, summary_type,
                       summarization_config, created_at
                FROM summary_sessions
                WHERE keyword_id = $1
                  AND user_id = $2
                  AND summary_type = 'keyword'
                  AND DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul') = $3
                ORDER BY created_at DESC
                LIMIT 1
                """,
                keyword_id, user_id, target_date
            )
            return dict(session) if session else None

    @staticmethod
    async def list_daily_dates(user_id: UUID) -> List[date]:
        """일일 요약이 존재하는 날짜 목록 조회 (한국 시간 기준)
        
        created_at이 UTC로 저장되어 있으므로, 한국 시간(KST, UTC+9)으로 변환하여
        날짜를 추출합니다.
        """
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul') AS summary_date
                FROM summary_sessions
                WHERE user_id = $1
                  AND keyword_id IS NULL
                  AND summary_type = 'daily'
                ORDER BY summary_date DESC
                """,
                user_id
            )
            return [row["summary_date"] for row in rows]

    @staticmethod
    async def list_keyword_dates(keyword_id: UUID, user_id: UUID) -> List[date]:
        """키워드별 요약이 존재하는 날짜 목록 조회 (한국 시간 기준)
        
        created_at이 UTC로 저장되어 있으므로, 한국 시간(KST, UTC+9)으로 변환하여
        날짜를 추출합니다.
        """
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul') AS summary_date
                FROM summary_sessions
                WHERE keyword_id = $1
                  AND user_id = $2
                  AND summary_type = 'keyword'
                ORDER BY summary_date DESC
                """,
                keyword_id, user_id
            )
            return [row["summary_date"] for row in rows]

    @staticmethod
    async def list_summary_texts(
        user_id: UUID,
        *,
        keyword_id: Optional[UUID] = None,
        summary_type: str = 'daily',
    ) -> List[str]:
        """요약 텍스트 전체 목록 조회 (최신순)
        
        Args:
            user_id (UUID): 사용자 ID
            keyword_id (UUID, optional): 키워드 ID (키워드 요약 시 필요)
            summary_type (str): 요약 유형 ('daily' 또는 'keyword')
        """
        async with get_db_connection() as conn:
            if keyword_id is None:
                rows = await conn.fetch(
                    """
                    SELECT summary_text
                    FROM summary_sessions
                    WHERE user_id = $1
                      AND keyword_id IS NULL
                      AND summary_type = $2
                    ORDER BY created_at DESC
                    """,
                    user_id,
                    summary_type,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT summary_text
                    FROM summary_sessions
                    WHERE user_id = $1
                      AND keyword_id = $2
                      AND summary_type = $3
                    ORDER BY created_at DESC
                    """,
                    user_id,
                    keyword_id,
                    summary_type,
                )
        return [
            row["summary_text"]
            for row in rows
            if row and isinstance(row["summary_text"], str)
        ]

