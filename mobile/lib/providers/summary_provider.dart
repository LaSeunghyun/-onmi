import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../models/summary.dart';

/// 일일 요약 상태
class DailySummaryState {
  final Summary? summary;
  final bool isLoading;
  final String? error;

  DailySummaryState({
    this.summary,
    this.isLoading = false,
    this.error,
  });

  DailySummaryState copyWith({
    Summary? summary,
    bool? isLoading,
    String? error,
  }) {
    return DailySummaryState(
      summary: summary ?? this.summary,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

/// 일일 요약 Provider
final dailySummaryProvider =
    StateNotifierProvider<DailySummaryNotifier, DailySummaryState>((ref) {
  return DailySummaryNotifier();
});

class DailySummaryNotifier extends StateNotifier<DailySummaryState> {
  DailySummaryNotifier() : super(DailySummaryState()) {
    loadSummary();
  }

  final _apiService = getApiService();

  Future<void> loadSummary() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final summary = await _apiService.getDailySummary();
      state = state.copyWith(
        summary: summary,
        isLoading: false,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> refresh() async {
    await loadSummary();
  }
}

/// 키워드별 요약 Provider (키워드 ID별로 관리)
final keywordSummaryProvider = StateNotifierProvider.family<
    KeywordSummaryNotifier, DailySummaryState, String>((ref, keywordId) {
  return KeywordSummaryNotifier(keywordId);
});

class KeywordSummaryNotifier extends StateNotifier<DailySummaryState> {
  final String keywordId;
  KeywordSummaryNotifier(this.keywordId) : super(DailySummaryState()) {
    loadSummary();
  }

  final _apiService = getApiService();

  Future<void> loadSummary() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final summary = await _apiService.getKeywordSummary(keywordId);
      state = state.copyWith(
        summary: summary,
        isLoading: false,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> refresh() async {
    await loadSummary();
  }
}

