"""성능 측정과 로깅을 위한 도우미."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, Iterator, Optional, AsyncIterator


@dataclass
class PerformanceEvent:
    """성능 측정 이벤트를 표현하는 데이터 클래스."""

    label: str
    logger: logging.Logger
    threshold_ms: int = 200
    metadata: Dict[str, object] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    _start_time: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        """측정을 시작합니다."""
        self._start_time = time.perf_counter()
        self.logger.info(
            "[PERF][START] %s id=%s metadata=%s",
            self.label,
            self.event_id,
            self.metadata,
        )

    def finish(self) -> float:
        """측정을 종료하고 경과 시간을 밀리초 단위로 반환합니다."""
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000.0
        log_message = "[PERF][END] %s id=%s elapsed=%.2fms metadata=%s"
        if elapsed_ms >= self.threshold_ms:
            self.logger.warning(
                log_message,
                self.label,
                self.event_id,
                elapsed_ms,
                self.metadata,
            )
        else:
            self.logger.info(
                log_message,
                self.label,
                self.event_id,
                elapsed_ms,
                self.metadata,
            )
        return elapsed_ms


@contextmanager
def track_performance(
    label: str,
    logger: logging.Logger,
    *,
    threshold_ms: int = 200,
    metadata: Optional[Dict[str, object]] = None,
) -> Iterator[PerformanceEvent]:
    """동기 코드 블록의 실행 시간을 측정합니다."""
    event = PerformanceEvent(
        label=label,
        logger=logger,
        threshold_ms=threshold_ms,
        metadata=metadata or {},
    )
    try:
        yield event
    finally:
        event.finish()


@asynccontextmanager
async def track_async_performance(
    label: str,
    logger: logging.Logger,
    *,
    threshold_ms: int = 200,
    metadata: Optional[Dict[str, object]] = None,
) -> AsyncIterator[PerformanceEvent]:
    """비동기 코드 블록의 실행 시간을 측정합니다."""
    event = PerformanceEvent(
        label=label,
        logger=logger,
        threshold_ms=threshold_ms,
        metadata=metadata or {},
    )
    try:
        yield event
    finally:
        event.finish()

