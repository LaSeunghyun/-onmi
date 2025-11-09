class Article {
  final String id;
  final String title;
  final String snippet;
  final String source;
  final String url;
  final DateTime? publishedAt;
  final String? thumbnailUrlHash;
  final String sentimentLabel;
  final double sentimentScore;
  final Map<String, dynamic>? sentimentRationale;
  final List<String> keywords;

  Article({
    required this.id,
    required this.title,
    required this.snippet,
    required this.source,
    required this.url,
    this.publishedAt,
    this.thumbnailUrlHash,
    required this.sentimentLabel,
    required this.sentimentScore,
    this.sentimentRationale,
    required this.keywords,
  });

  static DateTime? _parseDateTime(dynamic value) {
    if (value == null) return null;
    try {
      if (value is String) {
        return DateTime.parse(value);
      } else if (value is DateTime) {
        return value;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  factory Article.fromJson(Map<String, dynamic> json) {
    // 피드 API는 keyword (단수)를 반환하고, 상세 API는 keywords (복수)를 반환합니다
    List<String> keywordsList = [];
    if (json['keywords'] != null) {
      keywordsList = (json['keywords'] as List<dynamic>)
          .map((e) => e as String)
          .toList();
    } else if (json['keyword'] != null) {
      // 피드 API 응답: keyword 필드가 단일 문자열인 경우
      keywordsList = [json['keyword'] as String];
    }
    
    return Article(
      id: json['id'] as String,
      title: json['title'] as String,
      snippet: json['snippet'] as String? ?? '',
      source: json['source'] as String? ?? '',
      url: json['url'] as String,
      publishedAt: _parseDateTime(json['published_at'] ?? json['publishedAt']),
      thumbnailUrlHash: json['thumbnail_url_hash'] as String?,
      sentimentLabel: json['sentiment_label'] ?? json['sentimentLabel'] as String,
      sentimentScore: (json['sentiment_score'] ?? json['sentimentScore'] as num).toDouble(),
      sentimentRationale: json['sentiment_rationale'] ?? json['sentimentRationale'] as Map<String, dynamic>?,
      keywords: keywordsList,
    );
  }
}

class FeedResponse {
  final List<Article> items;
  final int total;
  final int page;
  final int pageSize;

  FeedResponse({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  factory FeedResponse.fromJson(Map<String, dynamic> json) {
    return FeedResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => Article.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
      page: json['page'] as int,
      pageSize: json['page_size'] as int,
    );
  }
}

