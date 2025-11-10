"""일일 요약 생성 스크립트"""
import asyncio
import asyncpg
import os
import sys
from dotenv import load_dotenv
from uuid import UUID

# 프로젝트 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'api-gateway', 'src'))

load_dotenv()

async def generate_daily_summary_for_user():
    """admin@onmi.com 사용자의 일일 요약 생성"""
    print("=" * 60)
    print("일일 요약 생성 테스트")
    print("=" * 60)
    
    database_url = os.getenv('DATABASE_URL')
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
        
        user_id = user['id']
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
        
        # 기사 확인
        print(f"\n📰 사용자의 기사 확인 중...")
        articles = await conn.fetch("""
            SELECT DISTINCT
                a.id, a.title, a.snippet, a.source, a.url, a.published_at,
                a.thumbnail_url_hash, a.created_at,
                s.label as sentiment_label, s.score as sentiment_score,
                s.rationale as sentiment_rationale
            FROM articles a
            INNER JOIN keyword_articles ka ON a.id = ka.article_id
            INNER JOIN keywords k ON ka.keyword_id = k.id
            LEFT JOIN sentiments s ON a.id = s.article_id
            WHERE k.user_id = $1 AND k.status = 'active'
            ORDER BY a.published_at DESC NULLS LAST, a.created_at DESC
            LIMIT 100
        """, user_id)
        
        print(f"   ✅ {len(articles)}개의 기사 발견")
        if articles:
            print(f"   최근 기사 제목:")
            for i, article in enumerate(articles[:5], 1):
                title = article.get('title', '제목 없음')
                print(f"   {i}. {title[:60]}...")
        else:
            print(f"   ⚠️ 기사가 없습니다. 먼저 기사를 수집해주세요.")
            await conn.close()
            return
        
        await conn.close()
        
        # SummaryService를 사용하여 일일 요약 생성
        print(f"\n📝 일일 요약 생성 중...")
        
        # 경로 설정
        backend_path = os.path.join(os.path.dirname(__file__), 'backend')
        shared_path = os.path.join(backend_path, 'shared')
        api_gateway_path = os.path.join(backend_path, 'api-gateway', 'src')
        
        sys.path.insert(0, shared_path)
        sys.path.insert(0, api_gateway_path)
        
        from services.summary_service import SummaryService
        
        summary_service = SummaryService()
        result = await summary_service.generate_daily_summary(user_id)
        
        print(f"\n✅ 일일 요약 생성 완료!")
        print(f"\n생성된 요약 정보:")
        print(f"   - 세션 ID: {result.get('session_id')}")
        print(f"   - 기사 개수: {result.get('articles_count')}")
        print(f"   - 설정: {result.get('config')}")
        
        summary_text = result.get('summary_text', '')
        print(f"\n요약 텍스트:")
        if summary_text:
            print(f"{summary_text}")
        else:
            print("(요약 텍스트 없음)")
        
        # 데이터베이스에서 저장된 요약 확인
        print(f"\n📊 데이터베이스에서 저장된 요약 확인 중...")
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        saved_summary = await conn.fetchrow("""
            SELECT id, summary_text, summary_type, created_at, summarization_config
            FROM summary_sessions
            WHERE user_id = $1 
              AND keyword_id IS NULL 
              AND summary_type = 'daily'
            ORDER BY created_at DESC
            LIMIT 1
        """, user_id)
        
        if saved_summary:
            print(f"   ✅ 저장된 요약 확인:")
            print(f"   - 세션 ID: {saved_summary['id']}")
            print(f"   - 생성 시간: {saved_summary['created_at']}")
            print(f"   - 요약 타입: {saved_summary['summary_type']}")
            print(f"   - 설정: {saved_summary['summarization_config']}")
        else:
            print(f"   ⚠️ 저장된 요약을 찾을 수 없습니다.")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(generate_daily_summary_for_user())

