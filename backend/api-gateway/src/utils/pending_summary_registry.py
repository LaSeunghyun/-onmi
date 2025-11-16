"""요약 생성 대기열 레지스트리.

요약 생성은 Gemini API 호출로 인해 시간이 오래 걸릴 수 있으므로,
동일 키워드에 대한 중복 생성 요청을 방지하고 현재 진행 상태를
추적하기 위해 경량 레지스트리를 제공한다.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict


class PendingSummaryRegistry:
    """키워드별 요약 생성 진행 상태를 추적하는 레지스트리."""

    _lock: asyncio.Lock = asyncio.Lock()
    _pending: Dict[str, datetime] = {}
    _ttl: timedelta = timedelta(minutes=10)

    @classmethod
    def build_key(cls, keyword_id: str, user_id: str, target_date: str | None) -> str:
        """레지스트리 키를 생성한다."""
        suffix = target_date or "latest"
        return f"{user_id}:{keyword_id}:{suffix}"

    @classmethod
    async def mark_pending(cls, key: str) -> None:
        """키를 대기 상태로 표시한다."""
        async with cls._lock:
            cls._purge_expired()
            cls._pending[key] = cls._now()

    @classmethod
    async def clear_pending(cls, key: str) -> None:
        """키 대기 상태를 해제한다."""
        async with cls._lock:
            cls._pending.pop(key, None)

    @classmethod
    async def is_pending(cls, key: str) -> bool:
        """키가 대기 상태인지 확인한다."""
        async with cls._lock:
            cls._purge_expired()
            return key in cls._pending

    @classmethod
    def _purge_expired(cls) -> None:
        """만료된 키를 제거한다."""
        now = cls._now()
        expired = [
            key for key, timestamp in cls._pending.items() if now - timestamp > cls._ttl
        ]
        for key in expired:
            cls._pending.pop(key, None)

    @staticmethod
    def _now() -> datetime:
        """UTC 기준 현재 시간을 반환한다."""
        return datetime.now(timezone.utc)




