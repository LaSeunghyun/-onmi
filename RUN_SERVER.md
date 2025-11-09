# 백엔드 서버 실행 가이드

## 문제 해결: DioException 연결 오류

Flutter 앱에서 네트워크 오류가 발생하는 경우, 백엔드 서버가 실행되지 않았기 때문입니다.

## ⚠️ Python이 설치되지 않은 경우

`pip` 명령어를 인식하지 못하는 경우, Python이 설치되어 있지 않거나 PATH에 추가되지 않은 것입니다.

### Python 설치 방법

1. **Python 다운로드 및 설치**
   - [Python 공식 사이트](https://www.python.org/downloads/)에서 최신 버전 다운로드
   - 설치 시 **"Add Python to PATH"** 옵션을 반드시 체크하세요!
   - 설치 완료 후 PowerShell을 재시작하세요.

2. **설치 확인**
   ```powershell
   python --version
   pip --version
   ```

3. **설치 후에도 인식되지 않는 경우**
   ```powershell
   # Python 경로를 수동으로 PATH에 추가
   $env:PATH += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python3XX\Scripts"
   $env:PATH += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python3XX"
   ```

## 서버 실행 방법

### 방법 1: Python 직접 사용 (권장)

#### 1단계: Python 확인
```powershell
python --version
# 또는
py --version
```

Python이 설치되어 있지 않다면 위의 "Python 설치 방법"을 참고하세요.

#### 2단계: 의존성 설치
```powershell
cd C:\onmi\backend\api-gateway

# pip이 인식되지 않으면 python -m pip 사용
python -m pip install -r requirements.txt
# 또는
py -m pip install -r requirements.txt
```

#### 3단계: 서버 실행

**PowerShell에서 직접 실행**
```powershell
cd C:\onmi\backend\api-gateway
$env:PYTHONPATH = "$PWD\..\shared"

# uvicorn이 인식되지 않으면 python -m 사용
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
# 또는
py -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 방법 2: Docker 사용 (Python 설치 불필요)

Docker가 설치되어 있다면 Python 없이도 실행할 수 있습니다:

```powershell
cd C:\onmi

# 1. Docker 컨테이너로 서버 실행
docker-compose up -d

# 2. API Gateway를 Docker 컨테이너로 실행 (별도 설정 필요)
# 또는 기존 방법 사용
```

**방법 2: run.bat 파일 사용**
```powershell
cd C:\onmi\backend\api-gateway
.\run.bat
```

**방법 3: 제공된 스크립트 사용**
```powershell
cd C:\onmi
.\start_server.ps1
```

## 서버 실행 확인

서버가 정상적으로 실행되면 다음 주소에서 확인할 수 있습니다:

- **API 문서**: http://localhost:8000/docs
- **헬스 체크**: http://localhost:8000/health
- **루트**: http://localhost:8000/

## Flutter 앱 재시작

서버가 실행된 후 Flutter 앱을 다시 시작하세요:

```powershell
cd C:\onmi\mobile
C:\flutter\bin\flutter.bat run -d windows
```

또는 Flutter 앱에서 **Hot Reload** (R 키) 또는 **Hot Restart** (Shift+R)를 사용하세요.

## 문제 해결

### uvicorn을 찾을 수 없는 경우
```powershell
pip install uvicorn[standard]
```

### 포트 8000이 이미 사용 중인 경우
다른 포트로 실행:
```powershell
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

그리고 Flutter 앱의 `api_service.dart`에서 포트를 변경:
```dart
baseUrl: 'http://localhost:8001',
```

### 데이터베이스 연결 오류
`.env` 파일이 올바르게 설정되었는지 확인:
```powershell
# .env 파일 확인
cd C:\onmi
Get-Content .env
```

DATABASE_URL이 올바르게 설정되어 있어야 합니다:
```
DATABASE_URL=postgresql://onmi:onmi_dev_password@localhost:5432/onmi_db
```

