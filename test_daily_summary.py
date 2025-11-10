"""일일 요약 데이터 조회 테스트 스크립트"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from uuid import UUID

load_dotenv()

async def test_daily_summary():
    """일일 요약 데이터 조회"""
    print("=" * 60)
    print("일일 요약 데이터 조회 테스트")
    print("=" * 60)
    
    # 환경변수 확인
    print("\n[1/5] 환경변수 확인 중...")
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("   ❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    print("   ✅ DATABASE_URL 확인 완료")
    
    try:
        # 데이터베이스 연결
        print("\n[2/5] 데이터베이스 연결 시도 중...")
        print(f"   연결 URL: {database_url[:50]}...")
        conn = await asyncpg.connect(database_url)
        print("   ✅ 데이터베이스 연결 성공")
        
        # 1. 사용자 목록 조회
        print("\n[3/5] 사용자 목록 조회 중...")
        print("   쿼리 실행: SELECT id, email FROM users LIMIT 5")
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
        
        # 2. 일일 요약 조회
        print(f"\n[4/5] 일일 요약 조회 중...")
        print(f"   사용자 ID: {test_user_id}")
        print("   쿼리 실행: SELECT ... FROM summary_sessions WHERE user_id = $1 AND summary_type = 'daily'")
        summary = await conn.fetchrow("""
            SELECT id, keyword_id, user_id, summary_text, summary_type,
                   summarization_config, created_at
            FROM summary_sessions
            WHERE user_id = $1 
              AND keyword_id IS NULL 
              AND summary_type = 'daily'
            ORDER BY created_at DESC
            LIMIT 1
        """, test_user_id)
        print(f"   쿼리 완료: {'결과 발견' if summary else '결과 없음'}")
        
        if summary:
            print(f"   ✅ 일일 요약 발견!")
            print(f"\n   📋 요약 정보:")
            print(f"   - 세션 ID: {summary['id']}")
            print(f"   - 요약 타입: {summary['summary_type']}")
            print(f"   - 생성 시간: {summary['created_at']}")
            print(f"   - 설정: {summary['summarization_config']}")
            
            summary_text = summary['summary_text']
            print(f"\n   📄 요약 텍스트 처리 중...")
            if summary_text:
                text_length = len(summary_text)
                print(f"   텍스트 길이: {text_length}자")
                if text_length > 500:
                    print(f"   (500자로 제한하여 표시)")
                    print(f"\n   {summary_text[:500]}...")
                    print(f"\n   (전체 길이: {text_length}자)")
                else:
                    print(f"\n   {summary_text}")
            else:
                print(f"   ⚠️ 요약 텍스트가 비어있습니다.")
        else:
            print(f"   ⚠️ 일일 요약이 없습니다.")
            print(f"   💡 API를 호출하면 새로 생성됩니다.")
            
            # 사용자의 키워드 확인
            print(f"\n   🔍 사용자의 키워드 확인 중...")
            print("   쿼리 실행: SELECT id, text, status FROM keywords WHERE user_id = $1")
            keywords = await conn.fetch("""
                SELECT id, text, status 
                FROM keywords 
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, test_user_id)
            print(f"   쿼리 완료: {len(keywords)}개 결과 반환")
            
            if keywords:
                print(f"   ✅ {len(keywords)}개의 키워드 발견:")
                display_count = min(5, len(keywords))
                for i, kw in enumerate(keywords[:display_count], 1):
                    print(f"   {i}. {kw['text']} (상태: {kw['status']})")
                if len(keywords) > display_count:
                    print(f"   ... 외 {len(keywords) - display_count}개 더 있음")
            else:
                print(f"   ⚠️ 키워드가 없습니다.")
                print(f"   💡 키워드를 추가하면 일일 요약을 생성할 수 있습니다.")
        
        # 3. 전체 요약 세션 통계
        print(f"\n[5/5] 요약 세션 통계 조회 중...")
        print("   쿼리 실행: SELECT COUNT(*) ... FROM summary_sessions WHERE user_id = $1")
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN summary_type = 'daily' THEN 1 END) as daily_count,
                COUNT(CASE WHEN summary_type = 'keyword' THEN 1 END) as keyword_count
            FROM summary_sessions
            WHERE user_id = $1
        """, test_user_id)
        print("   쿼리 완료")
        
        print(f"\n   📊 통계 결과:")
        print(f"   - 전체 요약: {stats['total_count']}개")
        print(f"   - 일일 요약: {stats['daily_count']}개")
        print(f"   - 키워드별 요약: {stats['keyword_count']}개")
        
        print(f"\n   🔌 데이터베이스 연결 종료 중...")
        await conn.close()
        print("   ✅ 연결 종료 완료")
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
    asyncio.run(test_daily_summary())
