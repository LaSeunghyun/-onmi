class TokenUsage {
  final int todayUsage;
  final int dailyLimit;
  final double usagePercentage;
  final int predictedDailyUsage;
  final bool isLimitExceeded;
  final bool canMakeRequest;
  final String resetAt;
  final String message;

  TokenUsage({
    required this.todayUsage,
    required this.dailyLimit,
    required this.usagePercentage,
    required this.predictedDailyUsage,
    required this.isLimitExceeded,
    required this.canMakeRequest,
    required this.resetAt,
    required this.message,
  });

  factory TokenUsage.fromJson(Map<String, dynamic> json) {
    return TokenUsage(
      todayUsage: json['today_usage'] as int,
      dailyLimit: json['daily_limit'] as int,
      usagePercentage: (json['usage_percentage'] as num).toDouble(),
      predictedDailyUsage: json['predicted_daily_usage'] as int,
      isLimitExceeded: json['is_limit_exceeded'] as bool,
      canMakeRequest: json['can_make_request'] as bool,
      resetAt: json['reset_at'] as String,
      message: json['message'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'today_usage': todayUsage,
      'daily_limit': dailyLimit,
      'usage_percentage': usagePercentage,
      'predicted_daily_usage': predictedDailyUsage,
      'is_limit_exceeded': isLimitExceeded,
      'can_make_request': canMakeRequest,
      'reset_at': resetAt,
      'message': message,
    };
  }
}

