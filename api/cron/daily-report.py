"""Vercel Cron Job - 일일 리포트 생성 및 알림"""
import sys
import os
from pathlib import Path
import asyncio
from datetime import datetime
from uuid import UUID

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

import asyncpg
from config.settings import settings
from repositories.preference_repository import PreferenceRepository
from services.summary_service import SummaryService


class DailyReportWorker:
    """일일 리포트 생성 워커 클래스"""
    
    def __init__(self):
        self.summary_service = SummaryService()
    
    async def generate_daily_report_for_user(self, user_id: UUID, db_conn):
        """사용자별 일일 리포트 생성"""
        try:
            print(f"일일 리포트 생성 시작: 사용자 ID {user_id}")
            
            # 일일 요약 생성
            result = await self.summary_service.generate_daily_summary(user_id)
            
            print(f"일일 리포트 생성 완료: 사용자 ID {user_id}")
            print(f"  - 세션 ID: {result['session_id']}")
            print(f"  - 기사 수: {result['articles_count']}")
            
            # TODO: 여기에 알림 전송 로직 추가 (푸시 알림, 이메일 등)
            # 예: await send_notification(user_id, result['summary_text'])
            
            return result
        except Exception as e:
            print(f"일일 리포트 생성 오류 (사용자 ID {user_id}): {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_daily_report_job(self):
        """일일 리포트 생성 작업 실행"""
        current_hour = datetime.now().hour
        print(f"일일 리포트 생성 작업 시작: {datetime.now()}")
        print(f"현재 시간: {current_hour}시")
        
        # 데이터베이스 연결
        conn = await asyncpg.connect(settings.database_url)
        
        try:
            # 현재 시간에 알림을 받을 사용자 목록 조회
            user_ids = await PreferenceRepository.get_users_by_notification_time(current_hour)
            
            print(f"알림 대상 사용자 수: {len(user_ids)}")
            
            if not user_ids:
                print("알림을 받을 사용자가 없습니다.")
                return
            
            # 각 사용자별로 일일 리포트 생성
            success_count = 0
            fail_count = 0
            
            for user_id in user_ids:
                try:
                    result = await self.generate_daily_report_for_user(user_id, conn)
                    if result:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    print(f"사용자별 리포트 생성 오류 (사용자 ID {user_id}): {e}")
                    fail_count += 1
                    continue
            
            print(f"일일 리포트 생성 작업 완료: {datetime.now()}")
            print(f"  - 성공: {success_count}개")
            print(f"  - 실패: {fail_count}개")
        
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

