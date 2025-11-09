"""서버 테스트 스크립트"""
import sys
import os

# 공통 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

try:
    print("1. Python 경로 확인...")
    print(f"   Python: {sys.version}")
    print(f"   PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    print("\n2. asyncpg 확인...")
    import asyncpg
    print(f"   ✅ asyncpg {asyncpg.__version__} 설치됨")
    
    print("\n3. FastAPI 확인...")
    import fastapi
    print(f"   ✅ FastAPI {fastapi.__version__} 설치됨")
    
    print("\n4. 메인 앱 임포트 시도...")
    from src.main import app
    print("   ✅ 앱 임포트 성공!")
    
    print("\n5. 서버 시작 가능합니다!")
    
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


