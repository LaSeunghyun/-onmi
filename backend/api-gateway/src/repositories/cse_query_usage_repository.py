"""Google CSE 쿼리 사용량 리포지토리

유저별/키워드별 일일 쿼리 사용량을 추적하고 조회하기 위한 데이터 접근 계층입니다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Optional
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from database.connection import get_db_connection  # noqa: E402


class CSEQueryUsageRepository:
    """Google CSE 쿼리 사용량 리포지토리"""

    @staticmethod
    def _calculate_effective_date(reset_hour_utc: int, base_time: Optional[datetime] = None) -> date:
        """UTC 기준 리셋 시각을 고려한 효과적인 일자 계산"""
        if base_time is None:
            base_time = datetime.utcnow()
        effective_time = base_time - timedelta(hours=reset_hour_utc)
        return effective_time.date()

    @classmethod
    def get_effective_date(cls, reset_hour_utc: int, base_time: Optional[datetime] = None) -> date:
        """외부 서비스에서 사용할 수 있도록 공개"""
        return cls._calculate_effective_date(reset_hour_utc, base_time)

    @staticmethod
    async def increment_usage(
        user_id: UUID,
        keyword_id: Optional[UUID],
        count: int,
        usage_date: date
    ) -> None:
        """쿼리 사용량 증가"""
        if count <= 0:
            return

        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO cse_query_usage (date, user_id, keyword_id, queries_used)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (date, user_id, keyword_id) DO UPDATE SET
                    queries_used = cse_query_usage.queries_used + EXCLUDED.queries_used,
                    updated_at = NOW()
                """,
                usage_date,
                user_id,
                keyword_id,
                count
            )

    @staticmethod
    async def get_user_daily_usage(user_id: UUID, usage_date: date) -> int:
        """해당 일자의 유저 전체 사용량 조회"""
        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(queries_used), 0) AS total
                FROM cse_query_usage
                WHERE date = $1
                  AND user_id = $2
                """,
                usage_date,
                user_id
            )
            return int(record['total']) if record else 0

    @staticmethod
    async def get_keyword_daily_usage(
        user_id: UUID,
        keyword_id: Optional[UUID],
        usage_date: date
    ) -> int:
        """해당 일자의 특정 키워드 사용량 조회"""
        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                """
                SELECT COALESCE(queries_used, 0) AS total
                FROM cse_query_usage
                WHERE date = $1
                  AND user_id = $2
                  AND keyword_id = $3
                """,
                usage_date,
                user_id,
                keyword_id
            )
            return int(record['total']) if record else 0

    @staticmethod
    async def get_total_active_users() -> int:
        """활성 키워드를 가진 유저 수"""
        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                """
                SELECT COUNT(DISTINCT user_id) AS cnt
                FROM keywords
                WHERE status = 'active'
                """
            )
            count = record['cnt'] if record else 0
            return int(count) if count else 0

    @staticmethod
    async def get_user_active_keywords_count(user_id: UUID) -> int:
        """유저가 보유한 활성 키워드 수"""
        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                """
                SELECT COUNT(*) AS cnt
                FROM keywords
                WHERE user_id = $1
                  AND status = 'active'
                """,
                user_id
            )
            count = record['cnt'] if record else 0
            return int(count) if count else 0

