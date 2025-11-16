"""크론 쿼리 로직 테스트 스크립트"""
import asyncio
import asyncpg
import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# KST는 UTC+9
KST = timezone(timedelta(hours=9))

load_dotenv()

async def test_cron_query():
    """크론 쿼리 로직 테스트"""
    print("=" * 80)
    print("크론 쿼리 로직 테스트")
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
        
        # 현재 시간 시뮬레이션 (크론이 실행되는 방식과 동일)
        print(f"\n{'='*80}")
        print("시간 변환 테스트")
        print(f"{'='*80}")
        
        # 크론이 실행되는 시간들 테스트 (UTC 21시 = KST 6시)
        test_times = [
            (21, 0),  # UTC 21:00 = KST 06:00 (다음날)
            (22, 0),  # UTC 22:00 = KST 07:00 (다음날)
            (23, 0),  # UTC 23:00 = KST 08:00 (다음날)
            (0, 0),   # UTC 00:00 = KST 09:00
            (1, 0),   # UTC 01:00 = KST 10:00
        ]
        
        for utc_hour, utc_minute in test_times:
            # 크론 실행 시점 시뮬레이션
            now_utc = datetime.now(timezone.utc).replace(
                hour=utc_hour, 
                minute=utc_minute, 
                second=0, 
                microsecond=0
            )
            now_kst = now_utc.astimezone(KST)
            current_hour = now_kst.hour
            
            print(f"\nUTC {utc_hour:02d}:{utc_minute:02d} → KST {now_kst.hour:02d}:{now_kst.minute:02d}")
            print(f"  current_hour = {current_hour}")
            
            # 크론 쿼리 실행
            rows = await conn.fetch(
                """
                SELECT user_id
                FROM user_preferences
                WHERE preferences ? 'notification_time_hour'
                  AND (preferences->>'notification_time_hour')::int = $1
                """,
                current_hour
            )
            
            user_ids = [row['user_id'] for row in rows]
            
            if user_id in user_ids:
                print(f"  ✅ 조회 성공! (총 {len(user_ids)}명)")
            else:
                print(f"  ❌ 조회 실패! (총 {len(user_ids)}명, admin@onmi.com 미포함)")
        
        # 실제 현재 시간으로 테스트
        print(f"\n{'='*80}")
        print("실제 현재 시간 테스트")
        print(f"{'='*80}")
        
        now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        now_kst = now_utc.astimezone(KST)
        current_hour = now_kst.hour
        
        print(f"현재 UTC 시간: {now_utc}")
        print(f"현재 KST 시간: {now_kst}")
        print(f"current_hour: {current_hour}")
        
        rows = await conn.fetch(
            """
            SELECT user_id
            FROM user_preferences
            WHERE preferences ? 'notification_time_hour'
              AND (preferences->>'notification_time_hour')::int = $1
            """,
            current_hour
        )
        
        user_ids = [row['user_id'] for row in rows]
        print(f"\n조회된 사용자 수: {len(user_ids)}")
        if user_id in user_ids:
            print(f"✅ admin@onmi.com이 조회되었습니다!")
        else:
            print(f"❌ admin@onmi.com이 조회되지 않았습니다.")
            print(f"   (현재 시간: KST {current_hour:02d}:00, 설정된 알림 시간: 6시)")
        
        # preferences 필드 직접 확인
        print(f"\n{'='*80}")
        print("preferences 필드 직접 확인")
        print(f"{'='*80}")
        
        preference = await conn.fetchrow(
            "SELECT preferences FROM user_preferences WHERE user_id = $1",
            user_id
        )
        
        if preference and preference['preferences']:
            prefs_raw = preference['preferences']
            if isinstance(prefs_raw, str):
                prefs = json.loads(prefs_raw)
            else:
                prefs = prefs_raw
            
            notification_hour = prefs.get('notification_time_hour')
            print(f"notification_time_hour 값: {notification_hour} (타입: {type(notification_hour)})")
            
            # 쿼리 조건 테스트
            print(f"\n쿼리 조건 테스트:")
            print(f"  preferences ? 'notification_time_hour': {prefs_raw is not None and 'notification_time_hour' in prefs}")
            print(f"  (preferences->>'notification_time_hour')::int = 6: {notification_hour == 6}")
            
            # 직접 쿼리 실행
            test_row = await conn.fetchrow(
                """
                SELECT user_id
                FROM user_preferences
                WHERE user_id = $1
                  AND preferences ? 'notification_time_hour'
                  AND (preferences->>'notification_time_hour')::int = $2
                """,
                user_id, 6
            )
            
            if test_row:
                print(f"  ✅ 직접 쿼리 테스트 성공!")
            else:
                print(f"  ❌ 직접 쿼리 테스트 실패!")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cron_query())

