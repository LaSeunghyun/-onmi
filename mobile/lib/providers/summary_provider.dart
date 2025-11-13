import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../services/cache_service.dart';
import '../models/summary.dart';
import '../utils/performance_monitor.dart';

/// 요약 조회 상태
enum SummaryStatus {
  /// 조회 중
  loading,

  /// 조회전 (데이터가 아직 없음)
  pending,

  /// 에러 발생
  error,

  /// 성공 (데이터 있음)
  success,
}

/// 일일 요약 상태
class DailySummaryState {
  final Summary? summary;
  final SummaryStatus status;
  final String? error;
  final DateTime selectedDate;
  final List<DateTime> availableDates;
  final bool showSkeleton;

  DailySummaryState({
    this.summary,
    SummaryStatus? status,
    this.error,
    DateTime? selectedDate,
    List<DateTime>? availableDates,
    this.showSkeleton = false,
  })  : status = status ??
            (summary != null ? SummaryStatus.success : SummaryStatus.loading),
        selectedDate = _normalize(selectedDate ?? DateTime.now()),
        availableDates = availableDates ?? const [];

  static DateTime _normalize(DateTime date) =>
      DateTime(date.year, date.month, date.day);

  DailySummaryState copyWith({
    Summary? summary,
    SummaryStatus? status,
    String? error,
    DateTime? selectedDate,
    List<DateTime>? availableDates,
    bool clearSummary = false,
    bool? showSkeleton,
    bool clearError = false,
  }) {
    return DailySummaryState(
      summary: clearSummary ? null : (summary ?? this.summary),
      status: status ?? this.status,
      error: clearError ? null : (error ?? this.error),
      selectedDate: selectedDate ?? this.selectedDate,
      availableDates: availableDates ?? this.availableDates,
      showSkeleton: showSkeleton ?? this.showSkeleton,
    );
  }

  /// 조회 중인지 확인
  bool get isLoading => status == SummaryStatus.loading;

  /// 조회전 상태인지 확인
  bool get isPending => status == SummaryStatus.pending;

  /// 에러 상태인지 확인
  bool get hasError => status == SummaryStatus.error;
}

/// 일일 요약 Provider
final dailySummaryProvider =
    StateNotifierProvider<DailySummaryNotifier, DailySummaryState>((ref) {
  return DailySummaryNotifier();
});

SummaryStatus _resolveSummaryStatus(Summary summary) {
  final hasSummaryContent = summary.summaryText.trim().isNotEmpty;
  final hasArticles = summary.articlesCount > 0;
  return (hasSummaryContent || hasArticles)
      ? SummaryStatus.success
      : SummaryStatus.pending;
}

class DailySummaryNotifier extends StateNotifier<DailySummaryState> {
  DailySummaryNotifier()
      : super(
          DailySummaryState(
            selectedDate: DateTime.now(),
          ),
        ) {
    loadSummary(date: state.selectedDate);
  }

  final _apiService = getApiService();
  final _dateFormatter = DateFormat('yyyy-MM-dd');
  final CacheService _cacheService = CacheService();
  int _activeRequestId = 0;

  DateTime _normalizeDate(DateTime date) {
    return DateTime(date.year, date.month, date.day);
  }

  DateTime? _parseDateValue(dynamic value) {
    if (value is DateTime) {
      return _normalizeDate(value);
    }
    if (value is String && value.isNotEmpty) {
      try {
        final parsed = DateTime.parse(value);
        return _normalizeDate(parsed);
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  List<DateTime> _parseAvailableDates(
    List<DateTime> fallback,
    dynamic rawDates,
  ) {
    if (rawDates is List) {
      final parsed = rawDates
          .map(_parseDateValue)
          .whereType<DateTime>()
          .toList(growable: false);
      if (parsed.isNotEmpty) {
        return parsed;
      }
    }
    return fallback;
  }

  Future<void> loadSummary({DateTime? date}) async {
    final targetDate = _normalizeDate(date ?? state.selectedDate);
    final previousDates = state.availableDates;
    final cacheKey = 'daily:${_dateFormatter.format(targetDate)}';
    final requestId = DateTime.now().microsecondsSinceEpoch;
    _activeRequestId = requestId;

    Summary? cachedSummary;
    try {
      cachedSummary = await PerformanceMonitor.trackAsync(
        label: 'CacheService.getCachedSummary',
        metadata: {'key': cacheKey},
        action: () => _cacheService.getCachedSummary(cacheKey),
      );
    } catch (_) {
      cachedSummary = null;
    }

    await PerformanceMonitor.trackAsync(
      label: 'DailySummaryNotifier.loadSummary',
      metadata: {
        'date': _dateFormatter.format(targetDate),
      },
      action: () async {
        state = state.copyWith(
          status: SummaryStatus.loading,
          error: null,
          selectedDate: targetDate,
          showSkeleton: false,
          summary: cachedSummary ?? state.summary,
          clearError: true,
        );
        Future.delayed(const Duration(milliseconds: 900)).then((_) {
          if (_activeRequestId == requestId &&
              state.status == SummaryStatus.loading &&
              state.summary == null) {
            state = state.copyWith(showSkeleton: true);
          }
        });
        try {
          final summary = await PerformanceMonitor.trackAsync(
            label: 'ApiService.getDailySummary',
            metadata: {
              'date': _dateFormatter.format(targetDate),
            },
            action: () => _apiService.getDailySummary(
              date: _dateFormatter.format(targetDate),
            ),
          );
          unawaited(
            PerformanceMonitor.trackAsync(
              label: 'CacheService.cacheSummary',
              metadata: {'key': cacheKey},
              action: () => _cacheService.cacheSummary(
                cacheKey: cacheKey,
                summary: summary,
              ),
            ),
          );
          state = state.copyWith(
            summary: summary,
            status: _resolveSummaryStatus(summary),
            error: null,
            availableDates: summary.availableDates,
            showSkeleton: false,
            clearError: true,
          );
        } on DioException catch (e) {
          if (e.response?.statusCode == 404) {
            final detail = e.response?.data;
            final pendingDates = detail is Map<String, dynamic>
                ? _parseAvailableDates(previousDates, detail['available_dates'])
                : previousDates;
            state = state.copyWith(
              status: SummaryStatus.pending,
              error: null,
              availableDates: pendingDates,
              clearSummary: true,
              showSkeleton: false,
              clearError: true,
            );
          } else {
            state = state.copyWith(
              status: SummaryStatus.error,
              error: e.message ?? e.toString(),
              showSkeleton: false,
            );
          }
        } catch (e) {
          state = state.copyWith(
            status: SummaryStatus.error,
            error: e.toString(),
            availableDates: previousDates,
            clearSummary: true,
            showSkeleton: false,
          );
        }
      },
    );
  }

  Future<void> refresh() async {
    await loadSummary(date: state.selectedDate);
  }

  Future<void> setDate(DateTime date) async {
    await loadSummary(date: date);
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
  final _dateFormatter = DateFormat('yyyy-MM-dd');
  final CacheService _cacheService = CacheService();
  int _activeRequestId = 0;

  DateTime _normalizeDate(DateTime date) {
    return DateTime(date.year, date.month, date.day);
  }

  DateTime? _parseDateValue(dynamic value) {
    if (value is DateTime) {
      return _normalizeDate(value);
    }
    if (value is String && value.isNotEmpty) {
      try {
        final parsed = DateTime.parse(value);
        return _normalizeDate(parsed);
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  List<DateTime> _parseAvailableDates(
    List<DateTime> fallback,
    dynamic rawDates,
  ) {
    if (rawDates is List) {
      final parsed = rawDates
          .map(_parseDateValue)
          .whereType<DateTime>()
          .toList(growable: false);
      if (parsed.isNotEmpty) {
        return parsed;
      }
    }
    return fallback;
  }

  Future<void> loadSummary({DateTime? date}) async {
    final targetDate = _normalizeDate(date ?? state.selectedDate);
    final previousDates = state.availableDates;
    final cacheKey = 'keyword:$keywordId:${_dateFormatter.format(targetDate)}';
    final requestId = DateTime.now().microsecondsSinceEpoch;
    _activeRequestId = requestId;

    Summary? cachedSummary;
    try {
      cachedSummary = await PerformanceMonitor.trackAsync(
        label: 'CacheService.getCachedSummary',
        metadata: {'key': cacheKey},
        action: () => _cacheService.getCachedSummary(cacheKey),
      );
    } catch (_) {
      cachedSummary = null;
    }

    await PerformanceMonitor.trackAsync(
      label: 'KeywordSummaryNotifier.loadSummary',
      metadata: {
        'keywordId': keywordId,
        'date': _dateFormatter.format(targetDate),
      },
      action: () async {
        state = state.copyWith(
          status: SummaryStatus.loading,
          error: null,
          selectedDate: targetDate,
          summary: cachedSummary ?? state.summary,
          showSkeleton: false,
          clearError: true,
        );
        Future.delayed(const Duration(milliseconds: 900)).then((_) {
          if (_activeRequestId == requestId &&
              state.status == SummaryStatus.loading &&
              state.summary == null) {
            state = state.copyWith(showSkeleton: true);
          }
        });
        try {
          final summary = await PerformanceMonitor.trackAsync(
            label: 'ApiService.getKeywordSummary',
            metadata: {
              'keywordId': keywordId,
              'date': _dateFormatter.format(targetDate),
            },
            action: () => _apiService.getKeywordSummary(
              keywordId,
              date: _dateFormatter.format(targetDate),
            ),
          );
          unawaited(
            PerformanceMonitor.trackAsync(
              label: 'CacheService.cacheSummary',
              metadata: {'key': cacheKey},
              action: () => _cacheService.cacheSummary(
                cacheKey: cacheKey,
                summary: summary,
              ),
            ),
          );
          state = state.copyWith(
            summary: summary,
            status: _resolveSummaryStatus(summary),
            error: null,
            availableDates: summary.availableDates,
            showSkeleton: false,
            clearError: true,
          );
        } on DioException catch (e) {
          if (e.response?.statusCode == 404) {
            final detail = e.response?.data;
            final pendingDates = detail is Map<String, dynamic>
                ? _parseAvailableDates(previousDates, detail['available_dates'])
                : previousDates;
            state = state.copyWith(
              status: SummaryStatus.pending,
              error: null,
              availableDates: pendingDates,
              clearSummary: true,
              showSkeleton: false,
              clearError: true,
            );
          } else {
            state = state.copyWith(
              status: SummaryStatus.error,
              error: e.message ?? e.toString(),
              showSkeleton: false,
            );
          }
        } catch (e) {
          state = state.copyWith(
            status: SummaryStatus.error,
            error: e.toString(),
            availableDates: previousDates,
            clearSummary: true,
            showSkeleton: false,
          );
        }
      },
    );
  }

  Future<void> refresh() async {
    await loadSummary(date: state.selectedDate);
  }

  Future<void> setDate(DateTime date) async {
    await loadSummary(date: date);
  }
}
