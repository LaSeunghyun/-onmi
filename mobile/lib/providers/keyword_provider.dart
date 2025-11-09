import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/keyword.dart';
import '../services/api_service.dart';
import '../services/cache_service.dart';

final keywordProvider = StateNotifierProvider<KeywordNotifier, List<Keyword>>((ref) {
  return KeywordNotifier(ApiService());
});

class KeywordNotifier extends StateNotifier<List<Keyword>> {
  final ApiService _apiService;
  final CacheService _cacheService = CacheService();

  KeywordNotifier(this._apiService) : super([]) {
    _loadFromCache();
    loadKeywords();
  }

  Future<void> _loadFromCache() async {
    try {
      final cachedKeywords = await _cacheService.getCachedKeywords();
      if (cachedKeywords.isNotEmpty) {
        state = cachedKeywords;
      }
    } catch (e) {
      // 캐시 로드 실패는 무시
    }
  }

  Future<void> loadKeywords() async {
    try {
      final keywords = await _apiService.getKeywords();
      state = keywords;
      // 캐시에 저장
      await _cacheService.cacheKeywords(keywords);
    } catch (e) {
      // 오프라인 모드: 캐시에서 로드
      try {
        final cachedKeywords = await _cacheService.getCachedKeywords();
        if (cachedKeywords.isNotEmpty) {
          state = cachedKeywords;
        }
      } catch (cacheError) {
        // 에러 처리
        print('키워드 로드 오류: $e');
      }
    }
  }

  Future<void> addKeyword(String text) async {
    try {
      final keyword = await _apiService.createKeyword(text);
      state = [...state, keyword];
      // 캐시 업데이트
      await _cacheService.cacheKeywords(state);
    } catch (e) {
      throw Exception('키워드 추가 실패: $e');
    }
  }

  Future<void> removeKeyword(String id) async {
    try {
      await _apiService.deleteKeyword(id);
      state = state.where((k) => k.id != id).toList();
      // 캐시 업데이트
      await _cacheService.cacheKeywords(state);
    } catch (e) {
      throw Exception('키워드 삭제 실패: $e');
    }
  }
}

