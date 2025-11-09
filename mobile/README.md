# #onmi Flutter 앱

키워드 기반 뉴스 트래킹 & 감성분석 모바일 앱

## 시작하기

### 의존성 설치

```bash
flutter pub get
```

### 앱 실행

```bash
flutter run
```

## API 연결 설정

앱이 백엔드 API에 연결하려면 `lib/services/api_service.dart`의 `baseUrl`을 환경에 맞게 설정하세요.

### 개발 환경별 설정

**Android 에뮬레이터:**
```dart
baseUrl: 'http://10.0.2.2:8000'
```

**iOS 시뮬레이터:**
```dart
baseUrl: 'http://localhost:8000'
```

**실제 기기:**
```dart
baseUrl: 'http://YOUR_COMPUTER_IP:8000'
// 예: http://192.168.1.100:8000
```

### 환경 변수로 설정 (권장)

빌드 시 환경 변수로 설정할 수 있습니다:

```bash
# Android
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

# iOS
flutter run --dart-define=API_BASE_URL=http://localhost:8000

# 실제 기기
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8000
```

## 프로젝트 구조

```
lib/
├── main.dart                 # 앱 진입점
├── app.dart                  # 앱 루트 위젯
├── models/                   # 데이터 모델
│   ├── user.dart
│   ├── keyword.dart
│   └── article.dart
├── screens/                  # 화면
│   ├── login/
│   ├── home/
│   ├── article_detail/
│   └── settings/
├── widgets/                  # 재사용 위젯
│   ├── keyword_input.dart
│   ├── keyword_list.dart
│   ├── keyword_filter.dart
│   ├── date_selector.dart
│   └── daily_report.dart
├── providers/                # 상태 관리
│   ├── auth_provider.dart
│   ├── keyword_provider.dart
│   └── feed_provider.dart
└── services/                 # 서비스 레이어
    ├── api_service.dart
    └── cache_service.dart
```

## 주요 기능

- ✅ 사용자 인증 (로그인/회원가입)
- ✅ 키워드 관리 (최대 3개)
- ✅ 뉴스 피드 조회
- ✅ 감성 분석 (긍정/부정/중립)
- ✅ 기사 상세 보기
- ✅ 공유 기능
- ✅ 피드백 제출
- ✅ 오프라인 캐시 지원

## 빌드

### Android APK

```bash
flutter build apk --release
```

### iOS

```bash
flutter build ios --release
```

## 문제 해결

### API 연결 오류

1. 백엔드 서버가 실행 중인지 확인
2. `baseUrl`이 올바른지 확인
3. 방화벽 설정 확인
4. 실제 기기 사용 시 같은 네트워크에 연결되어 있는지 확인

### 빌드 오류

```bash
flutter clean
flutter pub get
flutter run
```



