import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'app.dart';
import 'services/cache_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Hive 초기화
  await Hive.initFlutter();
  
  // 캐시 서비스 초기화
  final cacheService = CacheService();
  await cacheService.init();
  
  runApp(
    const ProviderScope(
      child: OnmiApp(),
    ),
  );
}

