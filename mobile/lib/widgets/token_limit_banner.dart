import 'package:flutter/material.dart';
import '../models/token_usage.dart';
import '../utils/responsive.dart';

class TokenLimitBanner extends StatelessWidget {
  final TokenUsage tokenUsage;
  final VoidCallback? onDismiss;

  const TokenLimitBanner({
    Key? key,
    required this.tokenUsage,
    this.onDismiss,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (!tokenUsage.isLimitExceeded) {
      return const SizedBox.shrink();
    }

    final padding = Responsive.getPadding(context);
    final baseFontSize = Responsive.getTextSize(context, 16);
    final smallFontSize = Responsive.getTextSize(context, 14);
    final extraSmallFontSize = Responsive.getTextSize(context, 12);

    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(padding),
      color: Colors.red.shade50,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Colors.red.shade700),
              SizedBox(width: padding * 0.5),
              Expanded(
                child: Text(
                  '시스템 일일 토큰 제한 초과',
                  style: TextStyle(
                    fontSize: baseFontSize,
                    fontWeight: FontWeight.bold,
                    color: Colors.red.shade900,
                  ),
                ),
              ),
              if (onDismiss != null)
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: onDismiss,
                  color: Colors.red.shade700,
                ),
            ],
          ),
          SizedBox(height: padding * 0.5),
          Text(
            tokenUsage.message,
            style: TextStyle(
              fontSize: smallFontSize,
              color: Colors.red.shade800,
            ),
          ),
          SizedBox(height: padding * 0.25),
          Text(
            '사용량: ${_formatNumber(tokenUsage.todayUsage)} / ${_formatNumber(tokenUsage.dailyLimit)} 토큰',
            style: TextStyle(
              fontSize: extraSmallFontSize,
              color: Colors.red.shade700,
            ),
          ),
          SizedBox(height: padding * 0.25),
          Text(
            '복구 예정: ${_formatResetTime(tokenUsage.resetAt)}',
            style: TextStyle(
              fontSize: extraSmallFontSize,
              color: Colors.red.shade700,
            ),
          ),
        ],
      ),
    );
  }

  String _formatNumber(int number) {
    if (number >= 1000000) {
      return '${(number / 1000000).toStringAsFixed(1)}M';
    } else if (number >= 1000) {
      return '${(number / 1000).toStringAsFixed(1)}K';
    }
    return number.toString();
  }

  String _formatResetTime(String resetAt) {
    try {
      final dateTime = DateTime.parse(resetAt);
      final now = DateTime.now();
      final difference = dateTime.difference(now);
      
      if (difference.inHours > 0) {
        return '${difference.inHours}시간 ${difference.inMinutes % 60}분 후';
      } else if (difference.inMinutes > 0) {
        return '${difference.inMinutes}분 후';
      } else {
        return '곧';
      }
    } catch (e) {
      return resetAt;
    }
  }
}




