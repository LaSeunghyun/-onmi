"""Vercel Cron Job - 일일 리포트 생성 및 알림

이 크론 작업은 한국 시간(KST, UTC+9) 기준으로 매 시간 정각에 실행됩니다.
크론은 Vercel에서 UTC 기준으로 실행되지만, 코드 내부에서 UTC+9로 변환하여
한국 시간 기준으로 사용자를 조회하고 요약을 생성합니다.
"""
import sys
import os
from pathlib import Path
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

# 한국 시간대 (KST = UTC+9)
KST = timezone(timedelta(hours=9))

import requests

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "ingestor" / "src"))
sys.path.insert(0, str(project_root / "backend" / "nlp-service" / "src"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))
sys.path.insert(0, str(project_root / "api"))

import asyncpg
from config.settings import settings
from repositories.preference_repository import PreferenceRepository
from repositories.summary_session_repository import SummarySessionRepository
from services.summary_service import SummaryService
from cron.crawl import CrawlerWorker


class DailyReportWorker:
    """일일 리포트 생성 워커 클래스"""
    
    def __init__(self):
        self.summary_service = SummaryService()
        self._notification_url = settings.notification_webhook_url
        self._notification_secret = settings.notification_webhook_secret
        self._crawler_worker = CrawlerWorker()

    async def _crawl_user_keywords(self, user_id: UUID, db_conn) -> int:
        """사용자별 활성 키워드를 크롤링하고 저장된 기사 수를 반환"""
        keywords = await db_conn.fetch(
            """
            SELECT id, text
            FROM keywords
            WHERE user_id = $1
              AND status = 'active'
            ORDER BY created_at DESC
            """,
            user_id,
        )

        if not keywords:
            print(f"사용자 ID {user_id}의 활성 키워드가 없어 크롤링을 건너뜁니다.")
            return 0

        total_saved_articles = 0

        print(
            f"사용자 ID {user_id} 크롤링 시작: {len(keywords)}개 키워드 대상"
        )
        for keyword in keywords:
            keyword_id = keyword["id"]
            keyword_text = keyword["text"]
            try:
                saved_count = await self._crawler_worker.crawl_keyword(
                    keyword_id,
                    user_id,
                    keyword_text,
                    db_conn,
                )
                total_saved_articles += saved_count
            except Exception as exc:
                print(
                    f"키워드 크롤링 오류 (사용자 ID {user_id}, 키워드 {keyword_text}): {exc}"
                )
                continue

        print(
            f"사용자 ID {user_id} 크롤링 완료: 총 {total_saved_articles}개 기사 저장"
        )
        return total_saved_articles

    async def _prefetch_keyword_summaries(
        self,
        user_id: UUID,
        db_conn,
    ) -> int:
        """사용자의 키워드 요약을 사전 생성하여 API 지연을 줄인다."""
        keywords = await db_conn.fetch(
            """
            SELECT id, text
            FROM keywords
            WHERE user_id = $1
              AND status = 'active'
            ORDER BY created_at DESC
            """,
            user_id,
        )

        if not keywords:
            return 0

        generated = 0
        now_utc = datetime.now(timezone.utc)
        freshness_ttl = timedelta(hours=6)

        for keyword in keywords:
            keyword_id = keyword["id"]
            keyword_text = keyword["text"]
            try:
                latest_summary = await SummarySessionRepository.get_latest_by_keyword(
                    keyword_id, user_id
                )
            except Exception as exc:
                print(
                    f"키워드 요약 조회 실패 (사용자 ID {user_id}, 키워드 {keyword_text}): {exc}"
                )
                latest_summary = None

            should_generate = False
            if not latest_summary:
                should_generate = True
            else:
                created_at = latest_summary.get("created_at")
                if created_at:
                    created_at_utc = (
                        created_at.replace(tzinfo=timezone.utc)
                        if created_at.tzinfo is None
                        else created_at.astimezone(timezone.utc)
                    )
                    if now_utc - created_at_utc > freshness_ttl:
                        should_generate = True

            if not should_generate:
                continue

            try:
                await self.summary_service.generate_keyword_summary(keyword_id, user_id)
                generated += 1
                print(
                    f"키워드 요약 사전 생성 완료 (사용자 ID {user_id}, 키워드 {keyword_text})"
                )
            except Exception as exc:
                print(
                    f"키워드 요약 사전 생성 실패 (사용자 ID {user_id}, 키워드 {keyword_text}): {exc}"
                )
                continue

        return generated

    async def _fetch_user_profile(self, user_id: UUID, db_conn) -> Optional[Dict[str, Any]]:
        """사용자 프로필 정보 조회"""
        row = await db_conn.fetchrow(
            """
            SELECT email, locale
            FROM users
            WHERE id = $1
            """,
            user_id,
        )
        if not row:
            return None
        return {
            "email": row["email"],
            "locale": row["locale"] or "ko-KR",
        }

    async def _send_notification(
        self,
        user_id: UUID,
        user_profile: Dict[str, Any],
        summary_result: Dict[str, Any],
    ) -> Optional[bool]:
        """요약 결과를 알림으로 전송"""
        if not self._notification_url:
            print("알림 웹훅 URL이 설정되지 않아 알림 전송을 건너뜁니다.")
            return None

        payload = {
            "user": {
                "id": str(user_id),
                "email": user_profile["email"],
                "locale": user_profile.get("locale"),
            },
            "summary": {
                "session_id": summary_result.get("session_id"),
                "articles_count": summary_result.get("articles_count"),
                "summary_text": summary_result.get("summary_text"),
                "created_at": summary_result.get("created_at"),
            },
            "meta": {
                "dispatched_at_utc": datetime.now(timezone.utc).isoformat(),
                "dispatched_at_kst": datetime.now(KST).isoformat(),
                "channel": "webhook",
            },
        }

        headers = {"Content-Type": "application/json"}
        if self._notification_secret:
            headers["Authorization"] = f"Bearer {self._notification_secret}"

        loop = asyncio.get_running_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self._notification_url,
                    json=payload,
                    headers=headers,
                    timeout=15,
                ),
            )
            response.raise_for_status()
            print(f"알림 전송 성공: 사용자 ID {user_id}, 이메일 {user_profile['email']}")
            return True
        except Exception as e:
            print(f"알림 전송 실패 (사용자 ID {user_id}): {e}")
            return False
    
    async def generate_daily_report_for_user(self, user_id: UUID, db_conn):
        """사용자별 일일 리포트 생성"""
        try:
            print(f"일일 리포트 생성 시작: 사용자 ID {user_id}")

            # 사용자 키워드 크롤링 선행
            crawled_articles = await self._crawl_user_keywords(user_id, db_conn)
            print(
                f"크롤링 결과 (사용자 ID {user_id}): {crawled_articles}개 기사 저장"
            )
            
            prefetched_summaries = await self._prefetch_keyword_summaries(
                user_id, db_conn
            )
            print(
                f"키워드 요약 사전 생성 결과 (사용자 ID {user_id}): {prefetched_summaries}건"
            )
            
            # 일일 요약 생성
            result = await self.summary_service.generate_daily_summary(user_id)
            
            print(f"일일 리포트 생성 완료: 사용자 ID {user_id}")
            print(f"  - 세션 ID: {result['session_id']}")
            print(f"  - 기사 수: {result['articles_count']}")
            
            user_profile = await self._fetch_user_profile(user_id, db_conn)
            if not user_profile:
                print(f"사용자 정보를 찾을 수 없어 알림 전송을 건너뜁니다 (사용자 ID {user_id}).")
                result["notification_sent"] = False
                result["notification_status"] = "missing_user"
            else:
                notification_status = await self._send_notification(
                    user_id=user_id,
                    user_profile=user_profile,
                    summary_result=result,
                )
                if notification_status is None:
                    result["notification_sent"] = False
                    result["notification_status"] = "skipped"
                else:
                    result["notification_sent"] = notification_status
                    result["notification_status"] = (
                        "sent" if notification_status else "failed"
                    )
                    if notification_status:
                        print(f"사용자 알림 전송 완료: {user_profile['email']}")
                    else:
                        print(f"사용자 알림 전송 실패: {user_profile['email']}")
            
            return result
        except Exception as e:
            print(f"일일 리포트 생성 오류 (사용자 ID {user_id}): {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_daily_report_job(self):
        """일일 리포트 생성 작업 실행 (KST 기준)
        
        크론이 실행되면 현재 UTC 시간을 한국 시간(KST)으로 변환하여,
        해당 시간에 알림을 받도록 설정한 사용자들을 조회하고 요약을 생성합니다.
        """
        # 현재 UTC 시간을 한국 시간(KST)으로 변환
        now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        now_kst = now_utc.astimezone(KST)
        current_hour = now_kst.hour  # 한국 시간 기준 시간 (0-23)
        current_date_kst = now_kst.date()  # 한국 시간 기준 날짜
        
        print(
            "일일 리포트 생성 작업 시작 (KST 기준):"
            f" {now_kst.isoformat()} (KST)"
        )
        print(
            f"현재 한국 시간: {current_date_kst} {current_hour:02d}:00"
        )
        
        # 데이터베이스 연결
        conn = await asyncpg.connect(settings.database_url)
        
        try:
            # 한국 시간 기준으로 현재 시간에 알림을 받을 사용자 목록 조회
            user_ids = await PreferenceRepository.get_users_by_notification_time(current_hour)
            
            print(f"알림 대상 사용자 수: {len(user_ids)}명 (한국 시간 {current_hour:02d}:00 기준)")
            if user_ids:
                print("알림 대상 사용자 목록:")
                for uid in user_ids:
                    print(f"  - {uid}")
            
            if not user_ids:
                print("알림을 받을 사용자가 없습니다.")
                return
            
            # 각 사용자별로 일일 리포트 생성
            success_count = 0
            fail_count = 0
            notification_sent_count = 0
            notification_failed_count = 0
            notification_skipped_count = 0
            
            for user_id in user_ids:
                try:
                    result = await self.generate_daily_report_for_user(user_id, conn)
                    if result:
                        success_count += 1
                        status = result.get("notification_status")
                        if status == "sent":
                            notification_sent_count += 1
                        elif status in {"failed", "missing_user"}:
                            notification_failed_count += 1
                        elif status == "skipped":
                            notification_skipped_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    print(f"사용자별 리포트 생성 오류 (사용자 ID {user_id}): {e}")
                    fail_count += 1
                    continue
            
            completed_utc = datetime.now(timezone.utc)
            completed_kst = completed_utc.astimezone(KST)
            print(
                "일일 리포트 생성 작업 완료 (KST 기준):"
                f" {completed_kst.isoformat()} (KST)"
            )
            print(f"  - 요약 생성 성공: {success_count}개")
            print(f"  - 요약 생성 실패: {fail_count}개")
            print(f"  - 알림 전송 성공: {notification_sent_count}개")
            print(f"  - 알림 전송 실패: {notification_failed_count}개")
            print(f"  - 알림 전송 생략: {notification_skipped_count}개")
        
        finally:
            await conn.close()


async def handler(request):
    """Vercel Cron Job 핸들러"""
    try:
        worker = DailyReportWorker()
        await worker.run_daily_report_job()
        return {
            "statusCode": 200,
            "body": {
                "message": "일일 리포트 생성 작업이 완료되었습니다",
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        print(f"일일 리포트 생성 작업 오류: {e}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }

