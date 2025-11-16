# 환경변수 및 데이터베이스 연결 확인 스크립트
Write-Host "=== #onmi 환경 검증 스크립트 ===" -ForegroundColor Cyan
Write-Host ""

# 프로젝트 루트 경로 찾기
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envFile = Join-Path $projectRoot ".env"

Write-Host "프로젝트 루트: $projectRoot" -ForegroundColor Yellow
Write-Host ".env 파일 경로: $envFile" -ForegroundColor Yellow
Write-Host ""

# 1. .env 파일 존재 확인
Write-Host "1. .env 파일 확인" -ForegroundColor Cyan
if (Test-Path $envFile) {
    Write-Host "   ✅ .env 파일이 존재합니다" -ForegroundColor Green
} else {
    Write-Host "   ❌ .env 파일이 없습니다" -ForegroundColor Red
    Write-Host "   경로: $envFile" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   .env 파일을 생성하고 다음 내용을 추가하세요:" -ForegroundColor Yellow
    Write-Host "   DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres" -ForegroundColor Gray
    Write-Host ""
}

# 2. 환경변수 확인
Write-Host "2. 환경변수 확인" -ForegroundColor Cyan

# DATABASE_URL 확인
$databaseUrl = $env:DATABASE_URL
if ($databaseUrl) {
    Write-Host "   ✅ DATABASE_URL이 설정되어 있습니다" -ForegroundColor Green
    # 민감한 정보 제외하고 표시
    if ($databaseUrl -match '@(.+?)/') {
        $hostPart = $matches[1]
        Write-Host "   호스트: $hostPart" -ForegroundColor Gray
    }
} else {
    Write-Host "   ❌ DATABASE_URL이 설정되지 않았습니다" -ForegroundColor Red
}

# SUPABASE_DB_URL 확인
$supabaseDbUrl = $env:SUPABASE_DB_URL
if ($supabaseDbUrl) {
    Write-Host "   ✅ SUPABASE_DB_URL이 설정되어 있습니다" -ForegroundColor Green
    if ($supabaseDbUrl -match '@(.+?)/') {
        $hostPart = $matches[1]
        Write-Host "   호스트: $hostPart" -ForegroundColor Gray
    }
} else {
    Write-Host "   ⚠️  SUPABASE_DB_URL이 설정되지 않았습니다 (선택사항)" -ForegroundColor Yellow
}

# PYTHONPATH 확인
$pythonPath = $env:PYTHONPATH
if ($pythonPath) {
    Write-Host "   ✅ PYTHONPATH가 설정되어 있습니다: $pythonPath" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  PYTHONPATH가 설정되지 않았습니다" -ForegroundColor Yellow
    Write-Host "   권장: $projectRoot\backend\shared" -ForegroundColor Gray
}

# PYTHONIOENCODING 확인
$pythonIoEncoding = $env:PYTHONIOENCODING
if ($pythonIoEncoding) {
    Write-Host "   ✅ PYTHONIOENCODING이 설정되어 있습니다: $pythonIoEncoding" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  PYTHONIOENCODING이 설정되지 않았습니다 (권장: utf-8)" -ForegroundColor Yellow
}

Write-Host ""

# 3. Python 및 필수 모듈 확인
Write-Host "3. Python 환경 확인" -ForegroundColor Cyan

# Python 버전 확인
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✅ Python이 설치되어 있습니다: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Python을 찾을 수 없습니다" -ForegroundColor Red
    Write-Host "   Python을 설치하거나 PATH에 추가하세요" -ForegroundColor Yellow
    exit 1
}

# 가상환경 확인
$venvPath = Join-Path $PSScriptRoot "venv"
if (Test-Path $venvPath) {
    Write-Host "   ✅ 가상환경이 존재합니다: $venvPath" -ForegroundColor Green
    
    # 가상환경 활성화 시도
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Write-Host "   가상환경 활성화 중..." -ForegroundColor Yellow
        & $activateScript
    }
} else {
    Write-Host "   ⚠️  가상환경이 없습니다" -ForegroundColor Yellow
    Write-Host "   'python -m venv venv'를 실행하여 생성하세요" -ForegroundColor Gray
}

# 필수 모듈 확인
Write-Host ""
Write-Host "   필수 모듈 확인 중..." -ForegroundColor Yellow
$requiredModules = @("fastapi", "uvicorn", "asyncpg", "pydantic")
$missingModules = @()

foreach ($module in $requiredModules) {
    try {
        $result = python -c "import $module" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ $module" -ForegroundColor Green
        } else {
            Write-Host "   ❌ $module (설치 필요)" -ForegroundColor Red
            $missingModules += $module
        }
    } catch {
        Write-Host "   ❌ $module (확인 실패)" -ForegroundColor Red
        $missingModules += $module
    }
}

if ($missingModules.Count -gt 0) {
    Write-Host ""
    Write-Host "   설치 명령: pip install -r requirements.txt" -ForegroundColor Yellow
}

Write-Host ""

# 4. 데이터베이스 연결 테스트
Write-Host "4. 데이터베이스 연결 테스트" -ForegroundColor Cyan

if (-not $databaseUrl -and -not $supabaseDbUrl) {
    Write-Host "   ⚠️  데이터베이스 URL이 설정되지 않아 연결 테스트를 건너뜁니다" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "검증 완료" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "다음 단계:" -ForegroundColor Yellow
    Write-Host "  1. .env 파일에 DATABASE_URL을 설정하세요" -ForegroundColor Gray
    Write-Host "  2. start_server.ps1을 실행하여 서버를 시작하세요" -ForegroundColor Gray
    exit 0
}

# Python 스크립트로 데이터베이스 연결 테스트
$testScript = @"
import sys
import os
import asyncio

# Windows 인코딩 설정
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 공통 모듈 경로 추가
sys.path.append(r'$projectRoot\backend\shared')

try:
    from database.connection import init_db_pool, close_db_pool
    
    async def test_connection():
        try:
            print('데이터베이스 연결 시도 중...')
            pool = await init_db_pool()
            print('✅ 데이터베이스 연결 성공!')
            await close_db_pool()
            return True
        except Exception as e:
            print(f'❌ 데이터베이스 연결 실패: {str(e)}')
            return False
    
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
except ImportError as e:
    print(f'❌ 모듈 import 실패: {str(e)}')
    print('필수 모듈이 설치되지 않았을 수 있습니다.')
    sys.exit(1)
except Exception as e:
    print(f'❌ 예상치 못한 오류: {str(e)}')
    sys.exit(1)
"@

# 임시 파일에 스크립트 저장
$tempScript = Join-Path $env:TEMP "check_db_connection_$(Get-Random).py"
$testScript | Out-File -FilePath $tempScript -Encoding UTF8

try {
    # PYTHONPATH 설정
    $env:PYTHONPATH = "$projectRoot\backend\shared"
    $env:PYTHONIOENCODING = "utf-8"
    
    Write-Host "   데이터베이스 연결 테스트 실행 중..." -ForegroundColor Yellow
    python $tempScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ 데이터베이스 연결 테스트 성공" -ForegroundColor Green
    } else {
        Write-Host "   ❌ 데이터베이스 연결 테스트 실패" -ForegroundColor Red
        Write-Host ""
        Write-Host "   가능한 원인:" -ForegroundColor Yellow
        Write-Host "     1. DATABASE_URL이 잘못되었습니다" -ForegroundColor Gray
        Write-Host "     2. 네트워크 연결 문제" -ForegroundColor Gray
        Write-Host "     3. 데이터베이스 서버가 다운되었습니다" -ForegroundColor Gray
        Write-Host "     4. 인증 정보가 잘못되었습니다" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ 연결 테스트 실행 실패: $_" -ForegroundColor Red
} finally {
    # 임시 파일 삭제
    if (Test-Path $tempScript) {
        Remove-Item $tempScript -Force
    }
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "검증 완료" -ForegroundColor Cyan
Write-Host ""
Write-Host "문제가 있으면 다음을 확인하세요:" -ForegroundColor Yellow
Write-Host "  1. .env 파일의 DATABASE_URL 형식이 올바른지 확인" -ForegroundColor Gray
Write-Host "  2. 모든 필수 모듈이 설치되었는지 확인 (pip install -r requirements.txt)" -ForegroundColor Gray
Write-Host "  3. 네트워크 연결 상태 확인" -ForegroundColor Gray
Write-Host "  4. Supabase 대시보드에서 데이터베이스 상태 확인" -ForegroundColor Gray
Write-Host ""








