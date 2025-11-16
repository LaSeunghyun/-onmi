"""일일 요약 생성 스크립트 - 크론 작업과 동일한 로직 사용"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "ingestor" / "src"))
sys.path.insert(0, str(project_root / "backend" / "nlp-service" / "src"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))
sys.path.insert(0, str(project_root / "api"))

load_dotenv()

# 크론 작업 모듈 import
from config.settings import settings

# 하이픈이 있는 파일명을 import하기 위해 importlib 사용
import importlib.util
daily_report_path = project_root / "api" / "cron" / "daily-report.py"
spec = importlib.util.spec_from_file_location("daily_report", daily_report_path)
daily_report_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily_report_module)
DailyReportWorker = daily_report_module.DailyReportWorker


async def generate_daily_summary_for_user():
    """admin@onmi.com 사용자의 일일 요약 생성 (크론 작업과 동일한 로직)"""
    print("=" * 80)
    print("admin@onmi.com 오늘의 인사이트 갱신")
    print("=" * 80)
    
    database_url = os.getenv('DATABASE_URL') or settings.database_url
    if not database_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    
    try:
        # 사용자 ID 조회 (pgbouncer 호환을 위해 statement_cache_size=0 설정)
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            "admin@onmi.com"
        )
        
        if not user:
            print("❌ admin@onmi.com 사용자를 찾을 수 없습니다.")
            await conn.close()
            return
        
        user_id = UUID(str(user['id']))
        print(f"\n✅ 사용자 발견: {user['email']} (ID: {user_id})")
        
        # 키워드 확인
        keywords = await conn.fetch(
            "SELECT id, text, status FROM keywords WHERE user_id = $1 AND status = 'active'",
            user_id
        )
        
        if not keywords:
            print("❌ 활성 키워드가 없습니다.")
            await conn.close()
            return
        
        print(f"\n✅ {len(keywords)}개의 활성 키워드 발견:")
        for kw in keywords:
            print(f"   - {kw['text']} (ID: {kw['id']})")
        
        # DailyReportWorker를 사용하여 크론 작업과 동일한 로직 실행
        print(f"\n{'='*80}")
        print("크론 작업과 동일한 로직으로 일일 리포트 생성 시작")
        print(f"{'='*80}")
        
        worker = DailyReportWorker()
        result = await worker.generate_daily_report_for_user(user_id, conn)
        
        if result:
            print(f"\n{'='*80}")
            print("✅ 일일 리포트 생성 완료!")
            print(f"{'='*80}")
            print(f"생성된 요약 정보:")
            print(f"   - 세션 ID: {result.get('session_id')}")
            print(f"   - 기사 개수: {result.get('articles_count')}")
            print(f"   - 설정: {result.get('config')}")
            
            summary_text = result.get('summary_text', '')
            if summary_text:
                print(f"\n요약 텍스트 미리보기:")
                preview = summary_text[:300] + "..." if len(summary_text) > 300 else summary_text
                print(f"{preview}")
            
            # 알림 전송 상태
            notification_status = result.get('notification_status', 'unknown')
            print(f"\n알림 전송 상태: {notification_status}")
        else:
            print(f"\n❌ 일일 리포트 생성 실패")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(generate_daily_summary_for_user())
