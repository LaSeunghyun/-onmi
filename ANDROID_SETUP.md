# Android에서 백엔드 접근 설정 가이드

## 현재 설정

- **백엔드 서버**: `0.0.0.0:8000` (모든 네트워크 인터페이스에서 접근 가능)
- **컴퓨터 IP 주소**: `172.16.24.127`
- **Windows 방화벽**: 포트 8000 허용됨

## Android 환경별 설정

### 1. Android 에뮬레이터 사용 시

에뮬레이터는 자동으로 `10.0.2.2`를 호스트 컴퓨터의 `localhost`로 매핑합니다.

**Flutter 앱 실행:**
```bash
cd mobile
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

또는 `api_service.dart`의 기본값(`http://10.0.2.2:8000`)을 그대로 사용하면 됩니다.

### 2. 실제 Android 기기 사용 시

실제 기기에서는 컴퓨터의 로컬 IP 주소를 사용해야 합니다.

**현재 컴퓨터 IP**: `172.16.24.127`

**Flutter 앱 실행:**
```bash
cd mobile
flutter run --dart-define=API_BASE_URL=http://172.16.24.127:8000
```

**주의사항:**
- Android 기기와 컴퓨터가 **같은 Wi-Fi 네트워크**에 연결되어 있어야 합니다
- 컴퓨터의 IP 주소가 변경되면 `API_BASE_URL`도 변경해야 합니다

### 3. IP 주소 확인 방법

컴퓨터의 IP 주소가 변경된 경우:

**Windows PowerShell:**
```powershell
ipconfig | findstr IPv4
```

**또는:**
```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*"} | Select-Object IPAddress
```

## 백엔드 서버 실행

```powershell
cd C:\onmi
.\start_server.ps1
```

서버가 정상적으로 실행되면:
- **로컬 접근**: http://localhost:8000
- **네트워크 접근**: http://172.16.24.127:8000

## 연결 확인

### 1. 컴퓨터에서 확인
```powershell
Invoke-WebRequest -Uri http://localhost:8000/health
```

### 2. Android 기기에서 확인
- 브라우저에서 `http://172.16.24.127:8000/health` 접속
- 또는 Flutter 앱에서 API 호출 테스트

## 문제 해결

### 연결이 안 되는 경우

1. **방화벽 확인**
   ```powershell
   netsh advfirewall firewall show rule name="Python Backend Port 8000"
   ```

2. **서버 실행 확인**
   ```powershell
   netstat -ano | findstr :8000
   ```

3. **같은 네트워크 확인**
   - Android 기기와 컴퓨터가 같은 Wi-Fi에 연결되어 있는지 확인

4. **IP 주소 재확인**
   - 컴퓨터 IP가 변경되었을 수 있으므로 다시 확인

5. **백엔드 로그 확인**
   ```powershell
   Get-Content backend\logs\api-gateway.log -Tail 50
   ```

## 로그 실시간 확인

```powershell
.\watch_logs.ps1
```

이 스크립트는 백엔드 로그를 실시간으로 표시합니다.




