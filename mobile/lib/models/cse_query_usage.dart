class CseQueryUsage {
  final String usageDate;
  final int userQuota;
  final int userUsed;
  final int userRemaining;
  final String resetAt;
  final int? keywordQuota;
  final int? keywordUsed;
  final int? keywordRemaining;

  CseQueryUsage({
    required this.usageDate,
    required this.userQuota,
    required this.userUsed,
    required this.userRemaining,
    required this.resetAt,
    this.keywordQuota,
    this.keywordUsed,
    this.keywordRemaining,
  });

  factory CseQueryUsage.fromJson(Map<String, dynamic> json) {
    return CseQueryUsage(
      usageDate: json['usage_date'] as String,
      userQuota: (json['user_quota'] ?? 0) as int,
      userUsed: (json['user_used'] ?? 0) as int,
      userRemaining: (json['user_remaining'] ?? 0) as int,
      resetAt: json['reset_at'] as String,
      keywordQuota: json['keyword_quota'] as int?,
      keywordUsed: json['keyword_used'] as int?,
      keywordRemaining: json['keyword_remaining'] as int?,
    );
  }
}

