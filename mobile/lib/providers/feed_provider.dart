import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/article.dart';
import '../services/api_service.dart';
import '../services/cache_service.dart';

class FeedState {
  final List<Article> articles;
  final bool isLoading;
  final String? error;
  final int total;
  final int page;

  FeedState({
    this.articles = const [],
    this.isLoading = false,
    this.error,
    this.total = 0,
    this.page = 1,
  });

  FeedState copyWith({
    List<Article>? articles,
    bool? isLoading,
    String? error,
    int? total,
    int? page,
  }) {
    return FeedState(
      articles: articles ?? this.articles,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      total: total ?? this.total,
      page: page ?? this.page,
    );
  }
}

final feedProvider = StateNotifierProvider<FeedNotifier, FeedState>((ref) {
  return FeedNotifier(getApiService());
});

class FeedNotifier extends StateNotifier<FeedState> {
  final ApiService _apiService;
  final CacheService _cacheService = CacheService();

  FeedNotifier(this._apiService) : super(FeedState()) {
    _loadFromCache();
    loadFeed();
  }

  Future<void> _loadFromCache() async {
    try {
      final cachedArticles = await _cacheService.getCachedArticles();
      if (cachedArticles.isNotEmpty) {
        state = state.copyWith(articles: cachedArticles);
      }
    } catch (e) {
      // 캐시 로드 실패는 무시
    }
  }

  Future<void> loadFeed({
    String? keywordId,
    String? filterSentiment,
    String sort = 'recent',
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await _apiService.getFeed(
        keywordId: keywordId,
        filterSentiment: filterSentiment,
        sort: sort,
      );
      
      // 캐시에 저장
      await _cacheService.cacheArticles(response.items);
      
      state = state.copyWith(
        articles: response.items,
        total: response.total,
        isLoading: false,
      );
    } catch (e) {
      // 오프라인 모드: 캐시에서 로드
      try {
        final cachedArticles = await _cacheService.getCachedArticles();
        state = state.copyWith(
          articles: cachedArticles,
          isLoading: false,
          error: '오프라인 모드: 캐시된 데이터를 표시합니다',
        );
      } catch (cacheError) {
        state = state.copyWith(
          isLoading: false,
          error: e.toString(),
        );
      }
    }
  }

  Future<void> refresh() async {
    await loadFeed();
  }
}

