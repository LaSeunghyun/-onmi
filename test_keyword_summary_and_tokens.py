"""키워드별 요약 생성 및 토큰 사용량 확인 테스트 스크립트"""
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
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

load_dotenv()

from services.summary_service import SummaryService
from repositories.token_usage_repository import TokenUsageRepository

async def test_keyword_summary_and_tokens():
    """키워드별 요약 생성 및 토큰 사용량 확인"""
    print("=" * 60)
    print("키워드별 요약 생성 및 토큰 사용량 확인 테스트")
    print("=" * 60)
    
    # 환경변수 확인
    print("\n[1/6] 환경변수 확인 중...")
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("   ❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    print("   ✅ DATABASE_URL 확인 완료")
    
    try:
        # 데이터베이스 연결
        print("\n[2/6] 데이터베이스 연결 시도 중...")
        print(f"   연결 URL: {database_url[:50]}...")
        conn = await asyncpg.connect(database_url)
        print("   ✅ 데이터베이스 연결 성공")
        
        # 1. 사용자 목록 조회
        print("\n[3/6] 사용자 목록 조회 중...")
        users = await conn.fetch("SELECT id, email FROM users LIMIT 5")
        print(f"   쿼리 완료: {len(users)}개 결과 반환")
        
        if not users:
            print("   ❌ 사용자가 없습니다. 먼저 회원가입을 해주세요.")
            await conn.close()
            return
        
        print(f"   ✅ {len(users)}명의 사용자 발견")
        for i, user in enumerate(users, 1):
            print(f"   {i}. {user['email']} (ID: {user['id']})")
        
        # 첫 번째 사용자로 테스트
        test_user_id = users[0]['id']
        test_user_email = users[0]['email']
        print(f"\n   ✅ 테스트 사용자 선택: {test_user_email} (ID: {test_user_id})")
        
        # 2. 사용자의 키워드 조회
        print(f"\n[4/6] 사용자의 키워드 조회 중...")
        keywords = await conn.fetch("""
            SELECT id, text, status 
            FROM keywords 
            WHERE user_id = $1 AND status = 'active'
            ORDER BY created_at DESC
        """, test_user_id)
        print(f"   쿼리 완료: {len(keywords)}개 결과 반환")
        
        if not keywords:
            print("   ⚠️ 활성화된 키워드가 없습니다.")
            await conn.close()
            return
        
        print(f"   ✅ {len(keywords)}개의 활성 키워드 발견:")
        for i, kw in enumerate(keywords, 1):
            print(f"   {i}. {kw['text']} (ID: {kw['id']}, 상태: {kw['status']})")
        
        # 첫 번째 키워드로 요약 생성
        test_keyword_id = keywords[0]['id']
        test_keyword_text = keywords[0]['text']
        print(f"\n   ✅ 테스트 키워드 선택: {test_keyword_text} (ID: {test_keyword_id})")
        
        # 3. 키워드별 요약 생성
        print(f"\n[5/6] 키워드별 요약 생성 중...")
        print(f"   키워드: {test_keyword_text}")
        print(f"   사용자 ID: {test_user_id}")
        
        summary_service = SummaryService()
        result = await summary_service.generate_keyword_summary(
            keyword_id=test_keyword_id,
            user_id=test_user_id
        )
        
        print(f"   ✅ 요약 생성 완료!")
        print(f"\n   📋 요약 정보:")
        print(f"   - 세션 ID: {result.get('session_id')}")
        print(f"   - 기사 수: {result.get('articles_count')}개")
        print(f"   - 요약 텍스트 길이: {len(result.get('summary_text', ''))}자")
        
        summary_text = result.get('summary_text', '')
        if summary_text:
            text_length = len(summary_text)
            print(f"\n   📄 요약 텍스트:")
            if text_length > 500:
                print(f"   {summary_text[:500]}...")
                print(f"   (전체 길이: {text_length}자)")
            else:
                print(f"   {summary_text}")
        
        # 4. 토큰 사용량 조회
        print(f"\n[6/6] 토큰 사용량 조회 중...")
        
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
        
        print(f"\n✅ 테스트 완료!")
        
    except asyncpg.exceptions.InvalidPasswordError as e:
        print(f"\n❌ 데이터베이스 인증 실패:")
        print(f"   오류: {e}")
        print(f"   💡 DATABASE_URL의 비밀번호를 확인해주세요.")
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        print(f"\n❌ 데이터베이스 연결 실패:")
        print(f"   오류: {e}")
        print(f"   💡 DATABASE_URL이 올바른지 확인해주세요.")
    except Exception as e:
        print(f"\n❌ 오류 발생:")
        print(f"   오류 타입: {type(e).__name__}")
        print(f"   오류 메시지: {e}")
        print(f"\n   상세 스택 트레이스:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_keyword_summary_and_tokens())

