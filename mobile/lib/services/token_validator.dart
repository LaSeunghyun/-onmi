import '../models/token_usage.dart';
import 'api_service.dart';

class TokenValidator {
  final ApiService _apiService;
  TokenUsage? _lastUsage;
  DateTime? _lastCheckTime;
  static const Duration _checkInterval = Duration(minutes: 5);

  TokenValidator(this._apiService);

  /// 토큰 사용량 조회 (캐시된 값이 있으면 사용)
  Future<TokenUsage> getTokenUsage({bool forceRefresh = false}) async {
    final now = DateTime.now();
    
    // 캐시된 값이 있고 최근에 확인했다면 캐시 사용
    if (!forceRefresh && 
        _lastUsage != null && 
        _lastCheckTime != null &&
        now.difference(_lastCheckTime!) < _checkInterval) {
      return _lastUsage!;
    }

    try {
      final usage = await _apiService.getTokenUsage();
      _lastUsage = usage;
      _lastCheckTime = now;
      return usage;
    } catch (e) {
      // API 호출 실패 시 마지막 캐시된 값 반환 또는 기본값 반환
      if (_lastUsage != null) {
        return _lastUsage!;
      }
      // 기본값: 제한 없음으로 가정
      rethrow;
    }
  }

  /// 요청 전 토큰 제한 확인
  Future<bool> canMakeRequest() async {
    try {
      final usage = await getTokenUsage();
      return usage.canMakeRequest;
    } catch (e) {
      // 확인 실패 시 요청 허용 (안전한 실패)
      return true;
    }
  }

  /// 토큰 제한 초과 여부 확인
  Future<bool> isLimitExceeded() async {
    try {
      final usage = await getTokenUsage();
      return usage.isLimitExceeded;
    } catch (e) {
      // 확인 실패 시 제한 없음으로 가정
      return false;
    }
  }

  /// 캐시 초기화
  void clearCache() {
    _lastUsage = null;
    _lastCheckTime = null;
  }
}


