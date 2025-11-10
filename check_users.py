import asyncio
import sys
import os

# 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'shared'))

from database.connection import get_db_connection

async def main():
    try:
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                'SELECT id, email, created_at FROM users ORDER BY created_at DESC'
            )
            
            if not rows:
                print('가입된 사용자가 없습니다.')
            else:
                print(f'가입된 사용자 수: {len(rows)}')
                print('=' * 80)
                for row in rows:
                    print(f"ID: {row['id']}")
                    print(f"Email: {row['email']}")
                    print(f"가입일: {row['created_at']}")
                    print('-' * 80)
    except Exception as e:
        print(f'오류 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())

