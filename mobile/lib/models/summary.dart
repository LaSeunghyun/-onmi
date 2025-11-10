class Summary {
  final String sessionId;
  final String summaryText;
  final String summaryType; // 'daily' or 'keyword'
  final int articlesCount;
  final DateTime? createdAt;

  Summary({
    required this.sessionId,
    required this.summaryText,
    required this.summaryType,
    required this.articlesCount,
    this.createdAt,
  });

  static DateTime? _parseDateTime(dynamic value) {
    if (value == null || value == '') return null;
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

  factory Summary.fromJson(Map<String, dynamic> json) {
    return Summary(
      sessionId: json['session_id'] as String? ?? '',
      summaryText: json['summary_text'] as String? ?? '',
      summaryType: json['summary_type'] as String? ?? 'daily',
      articlesCount: json['articles_count'] as int? ?? 0,
      createdAt: _parseDateTime(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'session_id': sessionId,
      'summary_text': summaryText,
      'summary_type': summaryType,
      'articles_count': articlesCount,
      'created_at': createdAt?.toIso8601String(),
    };
  }
}

