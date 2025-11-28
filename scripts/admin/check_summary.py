"""일일 요약 내용 확인 스크립트"""
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def check_summary():
    """일일 요약 내용 확인"""
    print("=" * 60)
    print("일일 요약 내용 확인")
    print("=" * 60)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    
    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        # admin@onmi.com 사용자의 최신 일일 요약 조회
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            "admin@onmi.com"
        )
        
        if not user:
            print("❌ admin@onmi.com 사용자를 찾을 수 없습니다.")
            await conn.close()
            return
        
        user_id = user['id']
        
        # 최신 일일 요약 조회
        summary = await conn.fetchrow("""
            SELECT 
                id, 
                keyword_id, 
                user_id, 
                summary_text, 
                summary_type,
                summarization_config,
                created_at
            FROM summary_sessions
            WHERE user_id = $1 
              AND keyword_id IS NULL 
              AND summary_type = 'daily'
            ORDER BY created_at DESC
            LIMIT 1
        """, user_id)
        
        if not summary:
            print("❌ 일일 요약을 찾을 수 없습니다.")
            await conn.close()
            return
        
        print(f"\n✅ 일일 요약 발견!")
        print(f"\n{'='*60}")
        print(f"요약 정보")
        print(f"{'='*60}")
        print(f"세션 ID: {summary['id']}")
        print(f"요약 타입: {summary['summary_type']}")
        print(f"생성 시간: {summary['created_at']}")
        
        if summary['summarization_config']:
            config_str = summary['summarization_config']
            # JSON 문자열인 경우 파싱
            if isinstance(config_str, str):
                try:
                    config = json.loads(config_str)
                except:
                    config = {}
            else:
                config = config_str
            
            print(f"\n요약 설정:")
            print(f"  - 상세도: {config.get('detail_level', 'N/A')}")
            print(f"  - 최대 길이: {config.get('max_length', 'N/A')}자")
            print(f"  - 감성 분석 포함: {config.get('include_sentiment', False)}")
            print(f"  - 키워드 포함: {config.get('include_keywords', False)}")
            print(f"  - 출처 포함: {config.get('include_sources', False)}")
            print(f"  - 주요 기사 개수: {config.get('top_articles_count', 0)}개")
        
        print(f"\n{'='*60}")
        print(f"요약 내용")
        print(f"{'='*60}")
        summary_text = summary['summary_text']
        if summary_text:
            print(f"\n{summary_text}")
            print(f"\n{'='*60}")
            print(f"통계")
            print(f"{'='*60}")
            print(f"요약 길이: {len(summary_text)}자")
            print(f"줄 수: {len(summary_text.split(chr(10)))}줄")
        else:
            print("(요약 텍스트 없음)")
        
        # 사용자의 키워드 정보도 함께 표시
        print(f"\n{'='*60}")
        print(f"관련 키워드")
        print(f"{'='*60}")
        keywords = await conn.fetch("""
            SELECT id, text, status 
            FROM keywords 
            WHERE user_id = $1 AND status = 'active'
            ORDER BY created_at DESC
        """, user_id)
        
        if keywords:
            for kw in keywords:
                print(f"  - {kw['text']} (상태: {kw['status']})")
        else:
            print("  (활성 키워드 없음)")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_summary())

