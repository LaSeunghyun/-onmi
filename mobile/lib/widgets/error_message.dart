import 'package:flutter/material.dart';

/// 오류 메시지를 표시하는 재사용 가능한 위젯
class ErrorMessage extends StatelessWidget {
  final String message;
  final String? detail;
  final VoidCallback? onRetry;
  final IconData icon;
  final Color? backgroundColor;
  final Color? textColor;

  const ErrorMessage({
    Key? key,
    required this.message,
    this.detail,
    this.onRetry,
    this.icon = Icons.error_outline,
    this.backgroundColor,
    this.textColor,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final bgColor = backgroundColor ?? Colors.red.shade50;
    final txtColor = textColor ?? Colors.red.shade900;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Colors.red.shade200,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                icon,
                color: txtColor,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  message,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: txtColor,
                    fontFamily: 'Noto Sans KR',
                  ),
                ),
              ),
            ],
          ),
          if (detail != null) ...[
            const SizedBox(height: 8),
            Text(
              detail!,
              style: TextStyle(
                fontSize: 12,
                color: txtColor.withOpacity(0.8),
                fontFamily: 'Noto Sans KR',
              ),
            ),
          ],
          if (onRetry != null) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text(
                  '다시 시도',
                  style: TextStyle(
                    fontFamily: 'Noto Sans KR',
                    fontSize: 14,
                  ),
                ),
                style: OutlinedButton.styleFrom(
                  foregroundColor: txtColor,
                  side: BorderSide(color: txtColor),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}






