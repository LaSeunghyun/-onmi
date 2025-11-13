import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';

/// 애플리케이션 전반의 성능 측정을 담당하는 유틸리티.
///
/// 네트워크 호출, 데이터 처리, 위젯 빌드 등 주요 구간의 실행 시간을
/// 측정하여 디버그 콘솔 및 개발자 도구(Timeline)에 기록합니다.
class PerformanceMonitor {
  PerformanceMonitor._();

  static final DateFormat _timestampFormat =
      DateFormat('HH:mm:ss.SSS', 'ko_KR');

  /// 비동기 작업의 실행 시간을 측정합니다.
  ///
  /// [label]에는 측정 구간을 명시적으로 작성하고,
  /// [action]은 실제 비동기 동작을 수행하는 콜백입니다.
  static Future<T> trackAsync<T>({
    required String label,
    required Future<T> Function() action,
    Map<String, Object?> metadata = const {},
  }) async {
    final stopwatch = Stopwatch()..start();
    try {
      return await action();
    } finally {
      stopwatch.stop();
      _log(label, stopwatch.elapsed, metadata);
    }
  }

  /// 동기 작업의 실행 시간을 측정합니다.
  ///
  /// [label]에는 측정 구간을 명시적으로 작성하고,
  /// [action]은 동기적으로 수행할 작업을 반환합니다.
  static T trackSync<T>({
    required String label,
    required T Function() action,
    Map<String, Object?> metadata = const {},
  }) {
    final stopwatch = Stopwatch()..start();
    try {
      return action();
    } finally {
      stopwatch.stop();
      _log(label, stopwatch.elapsed, metadata);
    }
  }

  static void _log(
    String label,
    Duration duration,
    Map<String, Object?> metadata,
  ) {
    final timestamp = _timestampFormat.format(DateTime.now());
    final durationMs = duration.inMilliseconds;
    final payload = {
      'label': label,
      'durationMs': durationMs,
      if (metadata.isNotEmpty) 'metadata': metadata,
    };

    if (kDebugMode) {
      debugPrint('[$timestamp] [PERF] $payload');
    }

    developer.Timeline.instantSync(
      'PerformanceMonitor',
      arguments: {
        'timestamp': timestamp,
        ...payload,
      },
    );
  }
}

