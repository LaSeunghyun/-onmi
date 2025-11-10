"""데이터베이스 연결 테스트 스크립트"""
import asyncio
import asyncpg
import os
from urllib.parse import urlparse
import sys

# .env 파일에서 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

async def test_connection(database_url: str, description: str):
    """데이터베이스 연결 테스트"""
    print(f"\n{'='*80}")
    print(f"테스트: {description}")
    print(f"연결 문자열: {database_url.split('@')[1] if '@' in database_url else database_url[:50]}...")
    print(f"{'='*80}")
    
    try:
        # URL 파싱하여 정보 출력
        parsed = urlparse(database_url)
        print(f"호스트: {parsed.hostname}")
        print(f"포트: {parsed.port}")
        print(f"사용자명: {parsed.username}")
        print(f"데이터베이스: {parsed.path[1:]}")
        
        # 연결 시도
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url, timeout=10),
            timeout=15
        )
        
        # 간단한 쿼리 실행
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        print(f"✅ 연결 성공! (결과: {result})")
        return True
        
    except asyncio.TimeoutError:
        print(f"❌ 연결 타임아웃 (15초 초과)")
        return False
    except Exception as e:
        print(f"❌ 연결 실패: {type(e).__name__}: {str(e)}")
        return False


async def main():
    """메인 함수"""
    print("="*80)
    print("데이터베이스 연결 테스트 시작")
    print("="*80)
    
    # 현재 .env 파일의 DATABASE_URL 가져오기
    current_url = os.getenv("DATABASE_URL")
    if not current_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return
    
    print(f"\n현재 설정된 DATABASE_URL:")
    print(f"  {current_url}")
    
    # URL 파싱
    parsed = urlparse(current_url)
    username = parsed.username or ""
    password = parsed.password or ""
    hostname = parsed.hostname or ""
    port = parsed.port or 5432
    database = parsed.path[1:] if parsed.path else "postgres"
    project_ref = "giqqhzonfruynokwbguv"  # .env에서 확인한 프로젝트 ref
    
    # 다양한 연결 형식 테스트
    test_cases = []
    
    # 1. 현재 설정 (Pooler, 포트 5432)
    if 'pooler.supabase.com' in hostname:
        test_cases.append((
            current_url,
            "현재 설정 (Pooler, 포트 5432)"
        ))
        
        # 2. Pooler, 포트 6543
        pooler_url_6543 = f"postgresql://{username}:{password}@{hostname}:6543/{database}"
        test_cases.append((
            pooler_url_6543,
            "Pooler, 포트 6543"
        ))
        
        # 3. Pooler, 사용자명을 postgres로 변경
        if '.' in username:
            base_username = username.split('.')[0]
            pooler_url_simple_user = f"postgresql://{base_username}:{password}@{hostname}:6543/{database}"
            test_cases.append((
                pooler_url_simple_user,
                "Pooler, 포트 6543, 사용자명 postgres"
            ))
    
    # 4. 직접 연결 (db.[project-ref].supabase.co)
    direct_host = f"db.{project_ref}.supabase.co"
    direct_url = f"postgresql://postgres:{password}@{direct_host}:5432/{database}"
    test_cases.append((
        direct_url,
        "직접 연결 (db.[project-ref].supabase.co:5432)"
    ))
    
    # 5. 직접 연결, 사용자명에 프로젝트 ref 포함
    direct_url_with_ref = f"postgresql://postgres.{project_ref}:{password}@{direct_host}:5432/{database}"
    test_cases.append((
        direct_url_with_ref,
        "직접 연결, 사용자명에 프로젝트 ref 포함"
    ))
    
    # 테스트 실행
    results = []
    for url, description in test_cases:
        success = await test_connection(url, description)
        results.append((description, success))
        await asyncio.sleep(1)  # 각 테스트 사이에 1초 대기
    
    # 결과 요약
    print(f"\n{'='*80}")
    print("테스트 결과 요약")
    print(f"{'='*80}")
    for description, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status}: {description}")
    
    # 성공한 연결이 있으면 추천
    successful_tests = [desc for desc, success in results if success]
    if successful_tests:
        print(f"\n✅ 성공한 연결 형식:")
        for desc in successful_tests:
            print(f"  - {desc}")
        print(f"\n💡 .env 파일의 DATABASE_URL을 성공한 형식 중 하나로 업데이트하세요.")
    else:
        print(f"\n❌ 모든 연결 테스트가 실패했습니다.")
        print(f"\n확인 사항:")
        print(f"1. Supabase 프로젝트가 활성화되어 있는지 확인")
        print(f"2. Supabase 대시보드 > Settings > Database에서 정확한 연결 문자열 확인")
        print(f"3. 비밀번호가 올바른지 확인")
        print(f"4. 네트워크 연결 상태 확인")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

