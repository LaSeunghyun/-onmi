"""admin@onmi.com 오전 7시 갱신 상태 보고서 생성 스크립트."""
import asyncio
import asyncpg
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from dotenv import load_dotenv

KST = timezone(timedelta(hours=9))


def _to_kst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(KST)
    return dt.astimezone(KST)


def _format_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def _decide_window_hit(summaries: List[Tuple[str, datetime]]) -> Tuple[bool, Optional[Tuple[str, datetime]]]:
    today = datetime.now(KST).date()
    for session_id, created_at in summaries:
        if created_at.date() != today:
            continue
        if 6 <= created_at.hour <= 8:
            return True, (session_id, created_at)
    return False, None


async def _fetch_admin_id(conn) -> Optional[str]:
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1",
        "admin@onmi.com",
    )
    return str(row["id"]) if row else None


async def _fetch_recent_summaries(conn, user_id: str, limit: int = 10) -> List[Tuple[str, datetime]]:
    rows = await conn.fetch(
        """
        SELECT id, created_at
        FROM summary_sessions
        WHERE user_id = $1
          AND keyword_id IS NULL
          AND summary_type = 'daily'
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )
    results: List[Tuple[str, datetime]] = []
    for row in rows:
        created_at = row["created_at"]
        if isinstance(created_at, datetime):
            results.append((str(row["id"]), _to_kst(created_at)))
    return results


async def _fetch_last_crawl(conn, user_id: str) -> Optional[datetime]:
    row = await conn.fetchrow(
        """
        SELECT fh.actual_end
        FROM fetch_history fh
        INNER JOIN keywords k ON fh.keyword_id = k.id
        WHERE k.user_id = $1
        ORDER BY fh.actual_end DESC
        LIMIT 1
        """,
        user_id,
    )
    if not row:
        return None
    actual_end = row["actual_end"]
    if isinstance(actual_end, datetime):
        return _to_kst(actual_end)
    return None


def _render_report(
    summaries: List[Tuple[str, datetime]],
    window_hit: Tuple[bool, Optional[Tuple[str, datetime]]],
    last_crawl: Optional[datetime],
) -> str:
    success, hit_record = window_hit
    today_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S %Z")
    lines: List[str] = []
    lines.append("=" * 80)
    lines.append(f"admin@onmi.com 오전 7시 갱신 상태 리포트 ({today_str})")
    lines.append("=" * 80)
    lines.append("")
    if success and hit_record:
        lines.append(f"- 07:00 갱신 상태 : ✅ 성공 ({_format_dt(hit_record[1])})")
    else:
        lines.append("- 07:00 갱신 상태 : ⚠️ 실패 (해당 시간대 생성 기록 없음)")
    lines.append(f"- 최근 기사 수집 완료 : {_format_dt(last_crawl)}")
    lines.append(f"- 최근 요약 생성 건수 : {len(summaries)}")
    lines.append("")
    lines.append("최근 일일 요약 생성 타임라인 (KST 기준):")
    if summaries:
        for session_id, created_at in summaries:
            lines.append(f"  • {created_at.strftime('%Y-%m-%d %H:%M:%S')}  (session: {session_id})")
    else:
        lines.append("  • 기록 없음")
    lines.append("")
    if success:
        lines.append("상태 요약: 오전 7시 트리거가 정상 실행되었습니다.")
    else:
        lines.append("상태 요약: 오전 7시 트리거 결과가 누락되었습니다. 스케줄러와 크론 로그를 점검하세요.")
    lines.append("")
    lines.append("권장 조치:")
    if success:
        lines.append("  - 추가 조치 불필요. 로그만 주기적으로 모니터링하세요.")
    else:
        lines.append("  - Vercel/Scheduler 크론 로그에서 07:00 실행 여부 확인")
        lines.append("  - `daily-report` 작업을 수동 실행하여 즉시 요약을 생성")
        lines.append("  - 알림 웹훅으로 오류가 전파되었는지 점검")
    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)


async def generate_report():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    conn = await asyncpg.connect(database_url, statement_cache_size=0)
    try:
        user_id = await _fetch_admin_id(conn)
        if not user_id:
            raise RuntimeError("admin@onmi.com 사용자를 찾을 수 없습니다.")
        summaries = await _fetch_recent_summaries(conn, user_id)
        last_crawl = await _fetch_last_crawl(conn, user_id)
        window_hit = _decide_window_hit(summaries)
        report = _render_report(summaries, window_hit, last_crawl)
        print(report)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(generate_report())

