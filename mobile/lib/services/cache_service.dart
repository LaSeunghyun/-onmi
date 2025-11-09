import 'package:hive_flutter/hive_flutter.dart';
import '../models/article.dart';
import '../models/keyword.dart';

class CacheService {
  static const String _articlesBoxName = 'articles';
  static const String _keywordsBoxName = 'keywords';
  
  late Box<Map> _articlesBox;
  late Box<Map> _keywordsBox;

  Future<void> init() async {
    _articlesBox = await Hive.openBox<Map>(_articlesBoxName);
    _keywordsBox = await Hive.openBox<Map>(_keywordsBoxName);
  }

  // 기사 캐시
  Future<void> cacheArticles(List<Article> articles) async {
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

  Future<List<Article>> getCachedArticles() async {
    final articles = <Article>[];
    for (final key in _articlesBox.keys) {
      final data = _articlesBox.get(key);
      if (data != null) {
        articles.add(Article.fromJson(Map<String, dynamic>.from(data)));
      }
    }
    return articles;
  }

  Future<void> clearArticlesCache() async {
    await _articlesBox.clear();
  }

  // 키워드 캐시
  Future<void> cacheKeywords(List<Keyword> keywords) async {
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

  Future<List<Keyword>> getCachedKeywords() async {
    final keywords = <Keyword>[];
    for (final key in _keywordsBox.keys) {
      final data = _keywordsBox.get(key);
      if (data != null) {
        keywords.add(Keyword.fromJson(Map<String, dynamic>.from(data)));
      }
    }
    return keywords;
  }

  Future<void> clearKeywordsCache() async {
    await _keywordsBox.clear();
  }
}



