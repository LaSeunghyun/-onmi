"""SummaryService와 Routes 로직 테스트 스크립트"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

load_dotenv()

from services.summary_service import SummaryService
from repositories.summary_session_repository import SummarySessionRepository
from repositories.article_repository import ArticleRepository
from repositories.token_usage_repository import TokenUsageRepository

async def test_summary_service_and_routes():
    """SummaryService와 Routes 로직 테스트"""
    print("=" * 60)
    print("SummaryService와 Routes 로직 테스트")
    print("=" * 60)
    
    # 환경변수 확인
    print("\n[1/5] 환경변수 확인 중...")
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("   ❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    print("   ✅ DATABASE_URL 확인 완료")
    
    try:
        # 테스트용 사용자 ID (실제 DB에서 조회한 값 사용)
        # admin@onmi.com의 ID
        test_user_id = UUID("a2770519-118e-4160-b606-4090e5394eb4")
        print(f"\n[2/5] 테스트 사용자 ID: {test_user_id}")
        
        # SummaryService 인스턴스 생성
        summary_service = SummaryService()
        
        # 1. 일일 요약 생성 테스트 (generate_daily_summary)
        print(f"\n[3/5] 일일 요약 생성 테스트 (SummaryService.generate_daily_summary)...")
        try:
            daily_result = await summary_service.generate_daily_summary(test_user_id)
            print(f"   ✅ 일일 요약 생성 성공!")
            print(f"\n   📋 생성된 요약 정보:")
            print(f"   - 세션 ID: {daily_result.get('session_id')}")
            print(f"   - 기사 수: {daily_result.get('articles_count')}개")
            print(f"   - 생성 시간: {daily_result.get('created_at', 'N/A')}")
            print(f"   - 요약 텍스트 길이: {len(daily_result.get('summary_text', ''))}자")
            
            summary_text = daily_result.get('summary_text', '')
            if summary_text:
                text_length = len(summary_text)
                print(f"\n   📄 요약 텍스트 (처음 300자):")
                if text_length > 300:
                    print(f"   {summary_text[:300]}...")
                else:
                    print(f"   {summary_text}")
        except Exception as e:
            print(f"   ❌ 일일 요약 생성 실패: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. 최신 일일 요약 조회 테스트 (Routes 로직 시뮬레이션)
        print(f"\n[4/5] 최신 일일 요약 조회 테스트 (Routes 로직 시뮬레이션)...")
        try:
            latest_summary = await SummarySessionRepository.get_latest_daily(test_user_id)
            
            if latest_summary:
                print(f"   ✅ 최신 일일 요약 발견!")
                print(f"\n   📋 조회된 요약 정보:")
                print(f"   - 세션 ID: {latest_summary.get('id')}")
                print(f"   - 요약 타입: {latest_summary.get('summary_type')}")
                print(f"   - 생성 시간: {latest_summary.get('created_at')}")
                
                # Routes에서 하는 것처럼 실제 기사 개수 조회
                articles = await ArticleRepository.fetch_recent_by_user(test_user_id, limit=100)
                articles_count = len(articles)
                print(f"   - 실제 기사 개수: {articles_count}개")
                
                summary_text = latest_summary.get('summary_text', '')
                if summary_text:
                    text_length = len(summary_text)
                    print(f"   - 요약 텍스트 길이: {text_length}자")
                    print(f"\n   📄 요약 텍스트 (처음 300자):")
                    if text_length > 300:
                        print(f"   {summary_text[:300]}...")
                    else:
                        print(f"   {summary_text}")
            else:
                print(f"   ⚠️ 최신 일일 요약이 없습니다.")
        except Exception as e:
            print(f"   ❌ 최신 일일 요약 조회 실패: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. 키워드별 요약 생성 테스트
        print(f"\n[5/5] 키워드별 요약 생성 테스트...")
        try:
            # 먼저 사용자의 키워드 조회 (간접적으로)
            # 실제로는 키워드 ID를 알아야 하지만, 테스트를 위해
            # 키워드 ID를 직접 지정하거나 조회해야 함
            # 여기서는 oci 키워드 ID 사용
            test_keyword_id = UUID("c7223c6d-6d5e-4d11-a858-86adfbf7e727")
            
            keyword_result = await summary_service.generate_keyword_summary(
                keyword_id=test_keyword_id,
                user_id=test_user_id
            )
            
            print(f"   ✅ 키워드별 요약 생성 성공!")
            print(f"\n   📋 생성된 요약 정보:")
            print(f"   - 세션 ID: {keyword_result.get('session_id')}")
            print(f"   - 기사 수: {keyword_result.get('articles_count')}개")
            print(f"   - 요약 텍스트 길이: {len(keyword_result.get('summary_text', ''))}자")
            
            summary_text = keyword_result.get('summary_text', '')
            if summary_text:
                text_length = len(summary_text)
                print(f"\n   📄 요약 텍스트 (처음 300자):")
                if text_length > 300:
                    print(f"   {summary_text[:300]}...")
                else:
                    print(f"   {summary_text}")
        except Exception as e:
            print(f"   ❌ 키워드별 요약 생성 실패: {e}")
            import traceback
            traceback.print_exc()
        
        # 4. 토큰 사용량 조회
        print(f"\n[6/6] 토큰 사용량 조회 중...")
        try:
            # 오늘의 토큰 사용량
            today_usage = await TokenUsageRepository.get_today_usage()
            print(f"\n   📊 오늘의 토큰 사용량:")
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
                    print(f"\n   📊 최근 7일간의 토큰 사용량:")
                    total_7days = sum(u.get('total_tokens_used', 0) for u in recent_usage)
                    print(f"   - 7일간 총 토큰: {total_7days:,}개")
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
        except Exception as e:
            print(f"   ❌ 토큰 사용량 조회 실패: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n✅ 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 오류 발생:")
        print(f"   오류 타입: {type(e).__name__}")
        print(f"   오류 메시지: {e}")
        print(f"\n   상세 스택 트레이스:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_summary_service_and_routes())

