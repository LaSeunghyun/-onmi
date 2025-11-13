import 'package:flutter/material.dart';

import '../../utils/responsive.dart';
import 'skeleton_box.dart';

/// 요약 카드 모양을 모사한 스켈레톤 위젯.
class SummarySkeletonCard extends StatelessWidget {
  const SummarySkeletonCard({
    super.key,
    this.titleWidth = 120,
    this.lineCount = 4,
  });

  /// 상단 배지 너비.
  final double titleWidth;

  /// 본문 플레이스홀더 줄 수.
  final int lineCount;

  @override
  Widget build(BuildContext context) {
    final padding = Responsive.getPadding(context) * 1.5;
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(
          color: Colors.black.withOpacity(0.08),
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: EdgeInsets.all(padding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SkeletonBox(
              width: titleWidth,
              height: 20,
              borderRadius: BorderRadius.circular(10),
            ),
            const SizedBox(height: 16),
            for (int index = 0; index < lineCount; index++) ...[
              SkeletonBox(
                width: index == lineCount - 1 ? 220 : double.infinity,
                height: 16,
              ),
              if (index != lineCount - 1) const SizedBox(height: 10),
            ],
          ],
        ),
      ),
    );
  }
}

