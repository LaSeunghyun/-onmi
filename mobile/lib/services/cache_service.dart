import 'package:hive_flutter/hive_flutter.dart';

import '../models/article.dart';
import '../models/keyword.dart';
import '../models/summary.dart';

/// Hive 캐시 박스를 관리하는 서비스.
///
/// 앱 전역에서 동일한 인스턴스를 공유하며, 모든 퍼블릭 메서드는
/// 내부 박스가 초기화된 이후에만 동작하도록 보장한다.
class CacheService {
  CacheService._internal();

  /// 싱글턴 인스턴스.
  static final CacheService _instance = CacheService._internal();

  /// 인스턴스를 반환한다.
  factory CacheService() => _instance;

  static const String _articlesBoxName = 'articles';
  static const String _keywordsBoxName = 'keywords';
  static const String _summariesBoxName = 'summaries';

  late final Box<Map> _articlesBox;
  late final Box<Map> _keywordsBox;
  late final Box<Map> _summariesBox;

  bool _initialized = false;
  Future<void>? _initialization;

  /// Hive 박스를 초기화한다.
  ///
  /// 이미 초기화된 경우 기존 Future를 반환한다.
  Future<void> init() {
    if (_initialization != null) {
      return _initialization!;
    }

    _initialization = _initializeBoxes();
    return _initialization!;
  }

  Future<void> _initializeBoxes() async {
    if (_initialized) {
      return;
    }

    _articlesBox = await Hive.openBox<Map>(_articlesBoxName);
    _keywordsBox = await Hive.openBox<Map>(_keywordsBoxName);
    _summariesBox = await Hive.openBox<Map>(_summariesBoxName);
    _initialized = true;
  }

  Future<void> _ensureInitialized() async {
    if (_initialized) {
      return;
    }
    await init();
  }

  /// 기사 데이터를 캐시에 저장한다.
  Future<void> cacheArticles(List<Article> articles) async {
    await _ensureInitialized();

    for (final article in articles) {
      await _articlesBox.put(
        article.id,
        {
          'id': article.id,
          'title': article.title,
          'snippet': article.snippet,
          'source': article.source,
          'url': article.url,
          'publishedAt': article.publishedAt?.toIso8601String(),
          'sentimentLabel': article.sentimentLabel,
          'sentimentScore': article.sentimentScore,
          'keywords': article.keywords,
        },
      );
    }
  }

  /// 캐시에 저장된 기사 목록을 반환한다.
  Future<List<Article>> getCachedArticles() async {
    await _ensureInitialized();

    final articles = <Article>[];
    for (final key in _articlesBox.keys) {
      final data = _articlesBox.get(key);
      if (data != null) {
        articles.add(Article.fromJson(Map<String, dynamic>.from(data)));
      }
    }
    return articles;
  }

  /// 기사 캐시를 모두 삭제한다.
  Future<void> clearArticlesCache() async {
    await _ensureInitialized();
    await _articlesBox.clear();
  }

  /// 키워드 데이터를 캐시에 저장한다.
  Future<void> cacheKeywords(List<Keyword> keywords) async {
    await _ensureInitialized();

    for (final keyword in keywords) {
      await _keywordsBox.put(
        keyword.id,
        {
          'id': keyword.id,
          'text': keyword.text,
          'status': keyword.status,
          'notifyLevel': keyword.notifyLevel,
          'autoShareEnabled': keyword.autoShareEnabled,
          'autoShareChannels': keyword.autoShareChannels,
          'createdAt': keyword.createdAt.toIso8601String(),
          'lastCrawledAt': keyword.lastCrawledAt?.toIso8601String(),
        },
      );
    }
  }

  /// 캐시에 저장된 키워드 목록을 반환한다.
  Future<List<Keyword>> getCachedKeywords() async {
    await _ensureInitialized();

    final keywords = <Keyword>[];
    for (final key in _keywordsBox.keys) {
      final data = _keywordsBox.get(key);
      if (data != null) {
        keywords.add(Keyword.fromJson(Map<String, dynamic>.from(data)));
      }
    }
    return keywords;
  }

  /// 키워드 캐시를 모두 삭제한다.
  Future<void> clearKeywordsCache() async {
    await _ensureInitialized();
    await _keywordsBox.clear();
  }

  /// 요약 데이터를 캐시에 저장한다.
  Future<void> cacheSummary({
    required String cacheKey,
    required Summary summary,
  }) async {
    await _ensureInitialized();
    await _summariesBox.put(cacheKey, summary.toJson());
  }

  /// 캐시된 요약 데이터를 반환한다.
  Future<Summary?> getCachedSummary(String cacheKey) async {
    await _ensureInitialized();
    final data = _summariesBox.get(cacheKey);
    if (data == null) {
      return null;
    }
    return Summary.fromJson(Map<String, dynamic>.from(data));
  }

  /// 요약 캐시를 모두 삭제한다.
  Future<void> clearSummariesCache() async {
    await _ensureInitialized();
    await _summariesBox.clear();
  }
}