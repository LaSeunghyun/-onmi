"""오늘 생성된 요약 확인 스크립트"""
import asyncio
import asyncpg
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# KST는 UTC+9
KST = timezone(timedelta(hours=9))

load_dotenv()

async def check_today_summary():
    """오늘 생성된 요약 확인"""
    print("=" * 80)
    print("오늘 생성된 요약 확인")
    print("=" * 80)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    
    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        # admin@onmi.com 사용자 조회
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            "admin@onmi.com"
        )
        
        if not user:
            print("❌ admin@onmi.com 사용자를 찾을 수 없습니다.")
            await conn.close()
            return
        
        user_id = user['id']
        print(f"✅ 사용자 확인: {user['email']} (ID: {user_id})")
        
        # 알림 시간 설정 확인
        print(f"\n{'='*80}")
        print("알림 시간 설정 확인")
        print(f"{'='*80}")
        preference = await conn.fetchrow(
            "SELECT preferences FROM user_preferences WHERE user_id = $1",
            user_id
        )
        
        if preference and preference['preferences']:
            import json
            prefs_raw = preference['preferences']
            # JSONB는 dict 또는 str일 수 있음
            if isinstance(prefs_raw, str):
                try:
                    prefs = json.loads(prefs_raw)
                except:
                    prefs = {}
            else:
                prefs = prefs_raw
            
            notification_hour = prefs.get('notification_time_hour')
            if notification_hour is not None:
                print(f"✅ 알림 시간 설정: {notification_hour}시 (KST)")
            else:
                print(f"⚠️ 알림 시간이 설정되지 않았습니다.")
        else:
            print(f"⚠️ 선호도 설정이 없습니다.")
        
        # 오늘 날짜 (KST 기준)
        now_kst = datetime.now(KST)
        today_kst = now_kst.date()
        print(f"\n현재 시간 (KST): {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"오늘 날짜 (KST): {today_kst}")
        
        # 오늘 생성된 일일 요약 조회
        print(f"\n{'='*80}")
        print("오늘 생성된 일일 요약 확인")
        print(f"{'='*80}")
        
        today_start = datetime.combine(today_kst, datetime.min.time()).replace(tzinfo=KST)
        today_end = datetime.combine(today_kst, datetime.max.time()).replace(tzinfo=KST)
        
        # UTC로 변환
        today_start_utc = today_start.astimezone(timezone.utc)
        today_end_utc = today_end.astimezone(timezone.utc)
        
        summaries = await conn.fetch("""
            SELECT 
                id, 
                summary_text, 
                summary_type,
                created_at
            FROM summary_sessions
            WHERE user_id = $1 
              AND keyword_id IS NULL 
              AND summary_type = 'daily'
              AND created_at >= $2
              AND created_at <= $3
            ORDER BY created_at DESC
        """, user_id, today_start_utc, today_end_utc)
        
        if summaries:
            print(f"✅ 오늘 생성된 요약: {len(summaries)}개")
            for i, summary in enumerate(summaries, 1):
                if summary['created_at'].tzinfo is None:
                    created_at_utc = summary['created_at'].replace(tzinfo=timezone.utc)
                else:
                    created_at_utc = summary['created_at']
                created_at_kst = created_at_utc.astimezone(KST)
                print(f"\n[{i}] 요약 세션:")
                print(f"   - 세션 ID: {summary['id']}")
                print(f"   - 생성 시간 (UTC): {created_at_utc}")
                print(f"   - 생성 시간 (KST): {created_at_kst.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   - 요약 길이: {len(summary['summary_text'])}자")
        else:
            print(f"❌ 오늘 생성된 요약이 없습니다.")
        
        # 최신 일일 요약 조회 (오늘 이전 포함)
        print(f"\n{'='*80}")
        print("최신 일일 요약 (전체)")
        print(f"{'='*80}")
        
        latest_summary = await conn.fetchrow("""
            SELECT 
                id, 
                summary_text, 
                summary_type,
                created_at
            FROM summary_sessions
            WHERE user_id = $1 
              AND keyword_id IS NULL 
              AND summary_type = 'daily'
            ORDER BY created_at DESC
            LIMIT 1
        """, user_id)
        
        if latest_summary:
            if latest_summary['created_at'].tzinfo is None:
                created_at_utc = latest_summary['created_at'].replace(tzinfo=timezone.utc)
            else:
                created_at_utc = latest_summary['created_at']
            created_at_kst = created_at_utc.astimezone(KST)
            print(f"✅ 최신 요약:")
            print(f"   - 세션 ID: {latest_summary['id']}")
            print(f"   - 생성 시간 (UTC): {created_at_utc}")
            print(f"   - 생성 시간 (KST): {created_at_kst.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   - 요약 길이: {len(latest_summary['summary_text'])}자")
            
            # 오늘인지 확인
            if created_at_kst.date() == today_kst:
                print(f"   ✅ 오늘 생성된 요약입니다!")
            else:
                days_diff = (today_kst - created_at_kst.date()).days
                print(f"   ⚠️ {days_diff}일 전에 생성된 요약입니다.")
        else:
            print(f"❌ 일일 요약이 없습니다.")
        
        # 최근 요약 생성 이력 (최근 5개)
        print(f"\n{'='*80}")
        print("최근 요약 생성 이력 (최근 5개)")
        print(f"{'='*80}")
        
        recent_summaries = await conn.fetch("""
            SELECT 
                id, 
                summary_type,
                created_at
            FROM summary_sessions
            WHERE user_id = $1 
              AND keyword_id IS NULL 
              AND summary_type = 'daily'
            ORDER BY created_at DESC
            LIMIT 5
        """, user_id)
        
        if recent_summaries:
            for i, summary in enumerate(recent_summaries, 1):
                if summary['created_at'].tzinfo is None:
                    created_at_utc = summary['created_at'].replace(tzinfo=timezone.utc)
                else:
                    created_at_utc = summary['created_at']
                created_at_kst = created_at_utc.astimezone(KST)
                print(f"[{i}] {created_at_kst.strftime('%Y-%m-%d %H:%M:%S')} (KST) - 세션 ID: {summary['id']}")
        else:
            print("요약 이력이 없습니다.")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_today_summary())

