import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/cse_query_usage.dart';
import '../services/api_service.dart';

class CseQueryUsageState {
  final CseQueryUsage? usage;
  final bool isLoading;
  final String? error;
  final String? keywordId;

  const CseQueryUsageState({
    this.usage,
    this.isLoading = false,
    this.error,
    this.keywordId,
  });

  CseQueryUsageState copyWith({
    CseQueryUsage? usage,
    bool? isLoading,
    String? error,
    String? keywordId,
  }) {
    return CseQueryUsageState(
      usage: usage ?? this.usage,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      keywordId: keywordId ?? this.keywordId,
    );
  }
}

final cseQueryUsageProvider =
    StateNotifierProvider<CseQueryUsageNotifier, CseQueryUsageState>((ref) {
  final apiService = getApiService();
  return CseQueryUsageNotifier(apiService);
});

class CseQueryUsageNotifier extends StateNotifier<CseQueryUsageState> {
  final ApiService _apiService;

  CseQueryUsageNotifier(this._apiService)
      : super(const CseQueryUsageState(isLoading: true)) {
    loadUsage();
  }

  Future<void> loadUsage({String? keywordId}) async {
    state = state.copyWith(
      isLoading: true,
      error: null,
      keywordId: keywordId ?? state.keywordId,
    );

    try {
      final usage =
          await _apiService.getCseQueryUsage(keywordId: keywordId ?? state.keywordId);
      state = CseQueryUsageState(
        usage: usage,
        isLoading: false,
        keywordId: keywordId ?? state.keywordId,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> refresh() async {
    await loadUsage(keywordId: state.keywordId);
  }
}

