import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'dart:ui';
import 'app.dart';
import 'services/cache_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // 전역 에러 핸들러 설정
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    // 개발 중에는 콘솔에 출력
    print('Flutter Error: ${details.exception}');
    print('Stack trace: ${details.stack}');
  };
  
  // 비동기 에러 핸들러 설정
  PlatformDispatcher.instance.onError = (error, stack) {
    print('Platform Error: $error');
    print('Stack trace: $stack');
    return true;
  };
  
  try {
    // Hive 초기화
    await Hive.initFlutter();
    
    // intl 로케일 데이터 초기화 (한국어)
    await initializeDateFormatting('ko_KR', null);
    
    // 캐시 서비스 초기화
    final cacheService = CacheService();
    await cacheService.init();
  } catch (e) {
    print('초기화 중 오류 발생: $e');
    // 초기화 실패해도 앱은 실행되도록 함
  }
  
  runApp(
    const ProviderScope(
      child: OnmiApp(),
    ),
  );
}

