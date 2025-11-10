"""CSE와 Gemini API 사용량 확인 테스트 스크립트"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID
from datetime import date, datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

load_dotenv()

from repositories.token_usage_repository import TokenUsageRepository

async def check_cse_gemini_usage():
    """CSE와 Gemini API 사용량 확인"""
    print("=" * 60)
    print("CSE와 Gemini API 사용량 확인")
    print("=" * 60)
    
    # 환경변수 확인
    print("\n[1/4] 환경변수 확인 중...")
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("   ❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    print("   ✅ DATABASE_URL 확인 완료")
    
    # CSE API 키 확인
    cse_api_key = os.getenv('GOOGLE_CSE_API_KEY')
    cse_cx = os.getenv('GOOGLE_CSE_CX')
    print(f"   - GOOGLE_CSE_API_KEY: {'설정됨' if cse_api_key else '설정 안됨'}")
    print(f"   - GOOGLE_CSE_CX: {'설정됨' if cse_cx else '설정 안됨'}")
    
    # Gemini API 키 확인
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL', 'models/gemini-1.5-flash-latest')
    print(f"   - GEMINI_API_KEY: {'설정됨' if gemini_api_key else '설정 안됨'}")
    print(f"   - GEMINI_MODEL: {gemini_model}")
    
    try:
        # 데이터베이스 연결
        print("\n[2/4] 데이터베이스 연결 시도 중...")
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        print("   ✅ 데이터베이스 연결 성공")
        
        # 1. 요약 세션에서 Gemini 사용 여부 추정
        print("\n[3/4] 요약 세션 통계 조회 중...")
        
        # 전체 요약 세션 수
        total_summaries = await conn.fetchval("""
            SELECT COUNT(*) FROM summary_sessions
        """)
        print(f"   - 전체 요약 세션: {total_summaries}개")
        
        # 일일 요약 세션 수
        daily_summaries = await conn.fetchval("""
            SELECT COUNT(*) FROM summary_sessions
            WHERE summary_type = 'daily'
        """)
        print(f"   - 일일 요약: {daily_summaries}개")
        
        # 키워드별 요약 세션 수
        keyword_summaries = await conn.fetchval("""
            SELECT COUNT(*) FROM summary_sessions
            WHERE summary_type = 'keyword'
        """)
        print(f"   - 키워드별 요약: {keyword_summaries}개")
        
        # 최근 7일간 생성된 요약 세션
        recent_summaries = await conn.fetchval("""
            SELECT COUNT(*) FROM summary_sessions
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        """)
        print(f"   - 최근 7일간 생성된 요약: {recent_summaries}개")
        
        # 2. 수집 이력에서 CSE 사용 추정
        print("\n[4/4] 수집 이력 통계 조회 중...")
        
        # fetch_history 테이블 존재 여부 확인
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'fetch_history'
            )
        """)
        
        if table_exists:
            # 전체 수집 이력 수
            total_fetches = await conn.fetchval("""
                SELECT COUNT(*) FROM fetch_history
            """)
            print(f"   - 전체 수집 이력: {total_fetches}개")
            
            # 최근 7일간 수집 이력
            recent_fetches = await conn.fetchval("""
                SELECT COUNT(*) FROM fetch_history
                WHERE actual_start >= CURRENT_DATE - INTERVAL '7 days'
            """)
            print(f"   - 최근 7일간 수집 이력: {recent_fetches}개")
            
            # 수집된 기사 총 개수
            total_articles_collected = await conn.fetchval("""
                SELECT COALESCE(SUM(articles_count), 0) FROM fetch_history
            """)
            print(f"   - 수집된 기사 총 개수: {total_articles_collected:,}개")
            
            # 최근 7일간 수집된 기사 개수
            recent_articles_collected = await conn.fetchval("""
                SELECT COALESCE(SUM(articles_count), 0) FROM fetch_history
                WHERE actual_start >= CURRENT_DATE - INTERVAL '7 days'
            """)
            print(f"   - 최근 7일간 수집된 기사: {recent_articles_collected:,}개")
        else:
            print("   ⚠️ fetch_history 테이블이 없습니다.")
        
        # 3. 토큰 사용량 조회 (Gemini 토큰 포함)
        print("\n[5/5] 토큰 사용량 조회 중...")
        
        # 오늘의 토큰 사용량
        today_usage = await TokenUsageRepository.get_today_usage()
        print(f"\n   📊 오늘의 토큰 사용량 (Gemini 포함):")
        print(f"   - 날짜: {today_usage.get('date')}")
        print(f"   - 총 토큰: {today_usage.get('total_tokens_used', 0):,}개")
        print(f"   - 입력 토큰: {today_usage.get('input_tokens', 0):,}개")
        print(f"   - 출력 토큰: {today_usage.get('output_tokens', 0):,}개")
        if today_usage.get('updated_at'):
            print(f"   - 마지막 업데이트: {today_usage.get('updated_at')}")
        
        # 최근 7일간의 토큰 사용량
        try:
            recent_usage = await TokenUsageRepository.get_recent_usage(days=7)
            if recent_usage:
                print(f"\n   📊 최근 7일간의 토큰 사용량 (Gemini 포함):")
                total_7days = sum(u.get('total_tokens_used', 0) for u in recent_usage)
                total_input = sum(u.get('input_tokens', 0) for u in recent_usage)
                total_output = sum(u.get('output_tokens', 0) for u in recent_usage)
                print(f"   - 7일간 총 토큰: {total_7days:,}개")
                print(f"   - 7일간 입력 토큰: {total_input:,}개")
                print(f"   - 7일간 출력 토큰: {total_output:,}개")
                print(f"\n   일별 상세:")
                for usage in recent_usage:
                    date_str = usage.get('date')
                    total = usage.get('total_tokens_used', 0)
                    input_tokens = usage.get('input_tokens', 0)
                    output_tokens = usage.get('output_tokens', 0)
                    print(f"   - {date_str}: 총 {total:,}개 (입력: {input_tokens:,}, 출력: {output_tokens:,})")
            else:
                print(f"\n   ⚠️ 최근 7일간의 토큰 사용량 데이터가 없습니다.")
        except Exception as e:
            print(f"\n   ⚠️ 최근 7일간의 토큰 사용량 조회 실패: {e}")
        
        # 4. CSE 사용량 추정 (Google CSE는 일일 100개 무료 쿼리 제한)
        print(f"\n   📊 CSE 사용량 추정:")
        print(f"   💡 참고: Google CSE는 일일 100개 무료 쿼리 제한이 있습니다.")
        if table_exists:
            # 최근 수집 이력에서 페이지 수 추정 (각 키워드당 여러 페이지 요청 가능)
            # CSE는 한 번에 최대 10개 결과를 반환하므로, 100개 기사를 수집하려면 약 10번의 쿼리 필요
            estimated_cse_queries = recent_articles_collected // 10 if recent_articles_collected else 0
            print(f"   - 최근 7일간 추정 CSE 쿼리 수: 약 {estimated_cse_queries}개")
            print(f"     (수집된 기사 수 / 10으로 추정)")
        
        await conn.close()
        print(f"\n✅ 확인 완료!")
        
        # 추가 정보
        print(f"\n📝 참고 사항:")
        print(f"   - Gemini 토큰 사용량은 summary_service에서 요약 생성 시 추적됩니다.")
        print(f"   - CSE 쿼리 사용량은 현재 별도 추적이 없습니다.")
        print(f"   - Google CSE 무료 할당량: 일일 100개 쿼리")
        print(f"   - Google Gemini 무료 할당량: 일일 15 RPM (분당 요청 수)")
        
    except Exception as e:
        print(f"\n❌ 오류 발생:")
        print(f"   오류 타입: {type(e).__name__}")
        print(f"   오류 메시지: {e}")
        print(f"\n   상세 스택 트레이스:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_cse_gemini_usage())

