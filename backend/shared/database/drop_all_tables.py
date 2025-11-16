"""데이터베이스 전체 삭제 스크립트"""
import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "backend" / "shared"))

# .env 파일 로드
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

from config.settings import settings


async def main():
    """모든 테이블 삭제"""
    print("=" * 50)
    print("⚠️  경고: 모든 테이블과 데이터가 삭제됩니다!")
    print("=" * 50)
    
    # 확인 입력
    confirm = input("\n정말 삭제하시겠습니까? (yes 입력): ")
    if confirm.lower() != 'yes':
        print("취소되었습니다.")
        return
    
    print("\n=== 데이터베이스 삭제 시작 ===\n")
    
    # 데이터베이스 연결
    database_url = settings.database_url
    if not database_url:
        print("[ERROR] DATABASE_URL이 설정되어 있지 않습니다.")
        sys.exit(1)
    
    db_info = database_url.split('@')[1] if '@' in database_url else 'N/A'
    print(f"데이터베이스 연결 중... ({db_info})")
    
    # 연결 재시도 로직
    max_retries = 3
    retry_delay = 2
    conn = None
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"연결 시도 {attempt}/{max_retries}...")
            conn = await asyncpg.connect(database_url, timeout=10)
            print("[OK] 데이터베이스 연결 성공\n")
            break
        except Exception as e:
            if attempt < max_retries:
                print(f"[WARN] 연결 실패, {retry_delay}초 후 재시도... ({e})")
                await asyncio.sleep(retry_delay)
            else:
                print(f"[ERROR] 데이터베이스 연결 실패: {e}")
                sys.exit(1)
    
    if conn is None:
        sys.exit(1)
    
    try:
        # 삭제 SQL 파일 읽기
        drop_sql_file = Path(__file__).parent / "drop_all_tables.sql"
        if not drop_sql_file.exists():
            print(f"[ERROR] 삭제 스크립트 파일을 찾을 수 없습니다: {drop_sql_file}")
            sys.exit(1)
        
        sql_content = drop_sql_file.read_text(encoding='utf-8')
        
        print("테이블 삭제 중...")
        await conn.execute(sql_content)
        print("[OK] 모든 테이블이 삭제되었습니다.\n")
        
        print("=== 삭제 완료 ===")
        print("삭제된 테이블:")
        print("  - users")
        print("  - keywords")
        print("  - articles")
        print("  - keyword_articles")
        print("  - sentiments")
        print("  - user_actions")
        print("  - share_history")
        print("  - token_usage")
        print("\n트리거와 함수도 삭제되었습니다.")
        
    except Exception as e:
        print(f"[ERROR] 삭제 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        await conn.close()
        print("\n데이터베이스 연결 종료")


if __name__ == "__main__":
    asyncio.run(main())









