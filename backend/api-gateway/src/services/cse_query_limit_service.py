"""Google CSE 쿼리 제한 서비스

Google Custom Search Engine의 일일 쿼리 제한을 유저/키워드 단위로 관리합니다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from math import floor
from typing import Optional, Dict
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from config.settings import settings  # noqa: E402
from repositories.cse_query_usage_repository import (  # noqa: E402
    CSEQueryUsageRepository,
)


@dataclass
class QuotaSnapshot:
    """쿼리 제한 및 사용 현황 스냅샷"""

    usage_date: date
    user_quota: int
    keyword_quota: int
    user_used: int
    keyword_used: int

    @property
    def user_remaining(self) -> int:
        return max(0, self.user_quota - self.user_used)

    @property
    def keyword_remaining(self) -> int:
        return max(0, self.keyword_quota - self.keyword_used)


class CSEQueryLimitService:
    """Google CSE 쿼리 제한 로직을 담당하는 서비스"""

    def __init__(self) -> None:
        self._daily_limit = max(0, settings.daily_cse_query_limit)
        self._reset_hour = max(0, min(23, settings.cse_query_reset_hour_utc))

    def _current_usage_date(self) -> date:
        """현재 시간 기준 사용량이 기록될 날짜를 계산합니다."""
        return CSEQueryUsageRepository.get_effective_date(self._reset_hour)

    def _next_reset_at(self) -> datetime:
        """다음 리셋 시각(UTC)을 반환합니다."""
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        reset_today = now.replace(
            hour=self._reset_hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        if now >= reset_today:
            reset_today += timedelta(days=1)
        return reset_today

    async def _load_usage_snapshot(
        self,
        user_id: UUID,
        keyword_id: Optional[UUID]
    ) -> QuotaSnapshot:
        """유저/키워드별 쿼리 제한 및 사용량을 조회합니다."""
        usage_date = self._current_usage_date()

        active_user_count = await CSEQueryUsageRepository.get_total_active_users()
        active_user_count = max(1, active_user_count)

        user_quota = floor(self._daily_limit / active_user_count) if self._daily_limit else 0
        user_quota = max(1, user_quota) if self._daily_limit else 0

        active_keywords = await CSEQueryUsageRepository.get_user_active_keywords_count(user_id)
        if active_keywords <= 0:
            keyword_quota = user_quota
        else:
            keyword_quota = floor(user_quota / active_keywords)
            keyword_quota = max(1, keyword_quota) if user_quota else 0

        user_used = await CSEQueryUsageRepository.get_user_daily_usage(user_id, usage_date)
        keyword_used = 0
        if keyword_id is not None:
            keyword_used = await CSEQueryUsageRepository.get_keyword_daily_usage(
                user_id,
                keyword_id,
                usage_date
            )

        return QuotaSnapshot(
            usage_date=usage_date,
            user_quota=user_quota,
            keyword_quota=keyword_quota,
            user_used=user_used,
            keyword_used=keyword_used,
        )

    async def calculate_user_quota(self, user_id: UUID) -> Dict[str, int]:
        """유저의 일일 쿼리 할당량과 사용량을 반환합니다."""
        snapshot = await self._load_usage_snapshot(user_id, None)
        return {
            "usage_date": snapshot.usage_date.isoformat(),
            "user_quota": snapshot.user_quota,
            "user_used": snapshot.user_used,
            "user_remaining": snapshot.user_remaining,
        }

    async def calculate_keyword_quota(
        self,
        user_id: UUID,
        keyword_id: UUID
    ) -> Dict[str, int]:
        """특정 키워드의 일일 쿼리 할당량과 사용량을 반환합니다."""
        snapshot = await self._load_usage_snapshot(user_id, keyword_id)
        return {
            "usage_date": snapshot.usage_date.isoformat(),
            "user_quota": snapshot.user_quota,
            "keyword_quota": snapshot.keyword_quota,
            "user_used": snapshot.user_used,
            "user_remaining": snapshot.user_remaining,
            "keyword_used": snapshot.keyword_used,
            "keyword_remaining": snapshot.keyword_remaining,
        }

    async def can_make_query(
        self,
        user_id: UUID,
        keyword_id: Optional[UUID],
        required_queries: int = 1
    ) -> bool:
        """쿼리 호출 가능 여부를 확인합니다."""
        if required_queries <= 0:
            return True

        snapshot = await self._load_usage_snapshot(user_id, keyword_id)
        if snapshot.user_remaining < required_queries:
            return False
        if keyword_id is not None and snapshot.keyword_remaining < required_queries:
            return False
        return True

    async def get_remaining_queries(
        self,
        user_id: UUID,
        keyword_id: Optional[UUID]
    ) -> Dict[str, int]:
        """남은 쿼리 수를 조회합니다."""
        snapshot = await self._load_usage_snapshot(user_id, keyword_id)
        return {
            "user_remaining": snapshot.user_remaining,
            "keyword_remaining": snapshot.keyword_remaining,
            "reset_at": self._next_reset_at().isoformat(),
        }

    async def get_user_available_queries(self, user_id: UUID) -> Dict[str, int]:
        """프론트엔드 표시용 유저 전체 쿼리 가능 수를 반환합니다."""
        snapshot = await self._load_usage_snapshot(user_id, None)
        return {
            "usage_date": snapshot.usage_date.isoformat(),
            "user_quota": snapshot.user_quota,
            "user_used": snapshot.user_used,
            "user_remaining": snapshot.user_remaining,
            "reset_at": self._next_reset_at().isoformat(),
        }

    async def record_usage(
        self,
        user_id: UUID,
        keyword_id: Optional[UUID],
        queries_used: int = 1
    ) -> None:
        """쿼리 사용량을 누적 기록합니다."""
        if queries_used <= 0:
            return

        usage_date = self._current_usage_date()
        await CSEQueryUsageRepository.increment_usage(
            user_id=user_id,
            keyword_id=keyword_id,
            count=queries_used,
            usage_date=usage_date
        )

