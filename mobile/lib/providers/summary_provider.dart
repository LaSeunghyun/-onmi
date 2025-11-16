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
  if (summary.isPending) {
    return SummaryStatus.pending;
  }
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
          
          // available_dates에서 가장 최근 날짜 자동 선택
          DateTime autoSelectedDate = targetDate;
          final availableDates = summary.availableDates;
          if (availableDates.isNotEmpty) {
            final now = _normalizeDate(DateTime.now());
            final isTodaySelected = _normalizeDate(targetDate) == now;
            final isSelectedDateAvailable = availableDates.any(
              (d) => _normalizeDate(d) == _normalizeDate(targetDate),
            );
            
            // 현재 선택된 날짜가 available_dates에 없거나, 오늘이 선택되었는데 오늘 데이터가 없으면 가장 최근 날짜로 자동 선택
            if (!isSelectedDateAvailable || (isTodaySelected && !isSelectedDateAvailable)) {
              // available_dates는 내림차순으로 정렬되어 있으므로 첫 번째가 가장 최근 날짜
              autoSelectedDate = availableDates.first;
            }
          }
          
          state = state.copyWith(
            summary: summary,
            status: _resolveSummaryStatus(summary),
            error: null,
            selectedDate: autoSelectedDate,
            availableDates: availableDates,
            showSkeleton: false,
            clearError: true,
          );
        } on DioException catch (e) {
          if (e.response?.statusCode == 404) {
            final detail = e.response?.data;
            final pendingDates = detail is Map<String, dynamic>
                ? _parseAvailableDates(previousDates, detail['available_dates'])
                : previousDates;
            
            // available_dates가 있으면 가장 최근 날짜로 자동 선택
            DateTime autoSelectedDate = targetDate;
            if (pendingDates.isNotEmpty) {
              autoSelectedDate = pendingDates.first;
            }
            
            state = state.copyWith(
              status: SummaryStatus.pending,
              error: null,
              selectedDate: autoSelectedDate,
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
  Timer? _pendingRetryTimer;
  int _pendingRetryCount = 0;
  static const int _maxPendingRetries = 5;
  static const Duration _pendingRetryDelay = Duration(seconds: 3);

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

  void _resetPendingRetry() {
    _pendingRetryTimer?.cancel();
    _pendingRetryTimer = null;
    _pendingRetryCount = 0;
  }

  void _schedulePendingRetry(DateTime targetDate) {
    final normalizedTarget = _normalizeDate(targetDate);
    if (_pendingRetryCount >= _maxPendingRetries) {
      state = state.copyWith(
        status: SummaryStatus.error,
        error: '요약 생성이 예상보다 오래 걸리고 있습니다. 잠시 후 다시 시도해주세요.',
        showSkeleton: false,
      );
      return;
    }
    _pendingRetryCount += 1;
    _pendingRetryTimer?.cancel();
    _pendingRetryTimer = Timer(_pendingRetryDelay, () {
      unawaited(loadSummary(date: normalizedTarget));
    });
  }

  void _handlePendingSummaryResponse(Summary summary, DateTime targetDate) {
    final normalizedTarget = _normalizeDate(targetDate);
    final pendingDatesSource = summary.availableDates.isNotEmpty
        ? summary.availableDates
        : state.availableDates;
    final normalizedDates = pendingDatesSource
        .map(_parseDateValue)
        .whereType<DateTime>()
        .toList(growable: false);
    final selectedDate =
        normalizedDates.isNotEmpty ? normalizedDates.first : normalizedTarget;
    state = state.copyWith(
      status: SummaryStatus.pending,
      selectedDate: selectedDate,
      availableDates: normalizedDates,
      clearSummary: true,
      showSkeleton: false,
      clearError: true,
    );
    _schedulePendingRetry(selectedDate);
  }

  @override
  void dispose() {
    _pendingRetryTimer?.cancel();
    super.dispose();
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
          if (summary.isPending) {
            _handlePendingSummaryResponse(summary, targetDate);
            return;
          }

          _resetPendingRetry();

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
          
          // available_dates에서 가장 최근 날짜 자동 선택
          DateTime autoSelectedDate = targetDate;
          final availableDates = summary.availableDates;
          if (availableDates.isNotEmpty) {
            final now = _normalizeDate(DateTime.now());
            final isTodaySelected = _normalizeDate(targetDate) == now;
            final isSelectedDateAvailable = availableDates.any(
              (d) => _normalizeDate(d) == _normalizeDate(targetDate),
            );
            
            // 현재 선택된 날짜가 available_dates에 없거나, 오늘이 선택되었는데 오늘 데이터가 없으면 가장 최근 날짜로 자동 선택
            if (!isSelectedDateAvailable || (isTodaySelected && !isSelectedDateAvailable)) {
              // available_dates는 내림차순으로 정렬되어 있으므로 첫 번째가 가장 최근 날짜
              autoSelectedDate = availableDates.first;
            }
          }
          
          state = state.copyWith(
            summary: summary,
            status: _resolveSummaryStatus(summary),
            error: null,
            selectedDate: autoSelectedDate,
            availableDates: availableDates,
            showSkeleton: false,
            clearError: true,
          );
        } on DioException catch (e) {
          if (e.response?.statusCode == 404) {
            final detail = e.response?.data;
            final pendingDates = detail is Map<String, dynamic>
                ? _parseAvailableDates(previousDates, detail['available_dates'])
                : previousDates;
            
            // available_dates가 있으면 가장 최근 날짜로 자동 선택
            DateTime autoSelectedDate = targetDate;
            if (pendingDates.isNotEmpty) {
              autoSelectedDate = pendingDates.first;
            }
            
            state = state.copyWith(
              status: SummaryStatus.pending,
              error: null,
              selectedDate: autoSelectedDate,
              availableDates: pendingDates,
              clearSummary: true,
              showSkeleton: false,
              clearError: true,
            );
            _schedulePendingRetry(autoSelectedDate);
          } else {
            state = state.copyWith(
              status: SummaryStatus.error,
              error: e.message ?? e.toString(),
              showSkeleton: false,
            );
            _resetPendingRetry();
          }
        } catch (e) {
          state = state.copyWith(
            status: SummaryStatus.error,
            error: e.toString(),
            availableDates: previousDates,
            clearSummary: true,
            showSkeleton: false,
          );
          _resetPendingRetry();
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
