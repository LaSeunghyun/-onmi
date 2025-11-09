"""데이터베이스 마이그레이션 실행 스크립트"""
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


async def run_migration(conn, migration_file: Path):
    """단일 마이그레이션 파일 실행"""
    print(f"실행 중: {migration_file.name}...")
    try:
        sql_content = migration_file.read_text(encoding='utf-8')
        if sql_content.strip():
            await conn.execute(sql_content)
            print(f"[OK] {migration_file.name} 완료")
            return True
        else:
            print(f"[SKIP] {migration_file.name} 비어있음, 건너뜀")
            return True
    except Exception as e:
        print(f"[ERROR] {migration_file.name} 실패: {e}")
        return False


async def main():
    """모든 마이그레이션 실행"""
    print("=== 데이터베이스 마이그레이션 시작 ===\n")
    
    # 데이터베이스 연결
    database_url = settings.database_url
    if not database_url:
        print("오류: DATABASE_URL이 설정되어 있지 않습니다.")
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
                print("\n확인 사항:")
                print("1. .env 파일에 DATABASE_URL이 올바르게 설정되어 있는지 확인")
                print("2. 인터넷 연결 상태 확인")
                print("3. Supabase 데이터베이스가 활성화되어 있는지 확인")
                print("4. Supabase 대시보드에서 데이터베이스 상태 확인")
                print("\n대안: Supabase 대시보드 > SQL Editor에서 직접 실행")
                print("   파일: supabase_complete_migration.sql")
                sys.exit(1)
    
    if conn is None:
        sys.exit(1)
    
    try:
        # 마이그레이션 파일 디렉토리
        migrations_dir = Path(__file__).parent / "migrations"
        
        # 마이그레이션 파일 목록 (순서대로)
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        if not migration_files:
            print("마이그레이션 파일을 찾을 수 없습니다.")
            return
        
        print(f"발견된 마이그레이션 파일: {len(migration_files)}개\n")
        
        # 각 마이그레이션 실행
        success_count = 0
        for migration_file in migration_files:
            success = await run_migration(conn, migration_file)
            if success:
                success_count += 1
            print()  # 빈 줄
        
        print("=== 마이그레이션 완료 ===")
        print(f"성공: {success_count}/{len(migration_files)}")
        
    finally:
        await conn.close()
        print("\n데이터베이스 연결 종료")


if __name__ == "__main__":
    asyncio.run(main())

