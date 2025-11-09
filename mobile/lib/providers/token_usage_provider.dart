import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/token_usage.dart';
import '../services/api_service.dart';
import '../services/token_validator.dart';
import 'dart:async';

final tokenUsageProvider = StateNotifierProvider<TokenUsageNotifier, TokenUsage?>((ref) {
  final apiService = ApiService();
  final validator = TokenValidator(apiService);
  return TokenUsageNotifier(validator);
});

class TokenUsageNotifier extends StateNotifier<TokenUsage?> {
  final TokenValidator _validator;
  Timer? _refreshTimer;

  TokenUsageNotifier(this._validator) : super(null) {
    // 초기 로드
    loadTokenUsage();
    
    // 5분마다 자동 갱신
    _refreshTimer = Timer.periodic(const Duration(minutes: 5), (_) {
      loadTokenUsage();
    });
  }

  Future<void> loadTokenUsage({bool forceRefresh = false}) async {
    try {
      final usage = await _validator.getTokenUsage(forceRefresh: forceRefresh);
      state = usage;
    } catch (e) {
      // 오류 발생 시 상태 유지 (마지막 값 유지)
      print('토큰 사용량 조회 실패: $e');
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}

