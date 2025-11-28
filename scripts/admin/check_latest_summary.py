"""최신 요약 텍스트 확인 스크립트"""
import asyncio
import asyncpg
import os
import re
from dotenv import load_dotenv

load_dotenv()

async def check_latest_summary():
    """최신 요약 텍스트 확인 및 기사 번호 참조 체크"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("[ERROR] DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    
    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            "admin@onmi.com"
        )
        
        if not user:
            print("[ERROR] admin@onmi.com 사용자를 찾을 수 없습니다.")
            await conn.close()
            return
        
        user_id = user['id']
        
        # 최신 일일 요약 조회
        summary = await conn.fetchrow("""
            SELECT summary_text, created_at
            FROM summary_sessions
            WHERE user_id = $1 
              AND keyword_id IS NULL 
              AND summary_type = 'daily'
            ORDER BY created_at DESC
            LIMIT 1
        """, user_id)
        
        if not summary:
            print("[ERROR] 일일 요약을 찾을 수 없습니다.")
            await conn.close()
            return
        
        summary_text = summary['summary_text']
        print(f"[OK] 최신 요약 발견 (생성 시간: {summary['created_at']})")
        print(f"\n{'='*80}")
        print("요약 텍스트 (전체):")
        print(f"{'='*80}")
        print(summary_text)
        print(f"\n{'='*80}")
        
        # 기사 번호 참조 패턴 체크
        patterns = [
            r'기사\s+\d+',
            r'\(기사\s+\d+',
            r'기사\s+\d+에\s+따르면',
        ]
        
        found_patterns = []
        for pattern in patterns:
            matches = re.findall(pattern, summary_text)
            if matches:
                found_patterns.extend(matches)
        
        if found_patterns:
            print(f"\n[WARN] 기사 번호 참조 발견: {len(found_patterns)}개")
            print("찾은 패턴:")
            for pattern in set(found_patterns):
                print(f"  - {pattern}")
        else:
            print("\n[OK] 기사 번호 참조가 없습니다.")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_latest_summary())

