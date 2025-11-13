import 'package:collection/collection.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/cse_query_usage_provider.dart';
import '../providers/summary_provider.dart';
import '../providers/feed_provider.dart';
import '../models/summary.dart';
import '../utils/responsive.dart';
import '../utils/summary_parser.dart';
import '../screens/summary_detail/summary_detail_screen.dart';
import 'skeleton/summary_skeleton_card.dart';

/// 오늘의 인사이트 요약 카드를 표시한다.
class InsightSummaryCard extends ConsumerWidget {
  final DailySummaryState summaryState;
  final CseQueryUsageState cseUsageState;
  final String title;
  final VoidCallback? onRetry;

  const InsightSummaryCard({
    super.key,
    required this.summaryState,
    required this.cseUsageState,
    required this.title,
    this.onRetry,
  });

  bool get _hasSummaryText {
    final text = summaryState.summary?.summaryText.trim();
    return text != null && text.isNotEmpty;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 상태에 따라 UI 분기
    switch (summaryState.status) {
      case SummaryStatus.loading:
        if (summaryState.showSkeleton || summaryState.summary == null) {
          return const SummarySkeletonCard();
        }
        // 로딩 중이지만 캐시된 데이터가 있으면 조회중 카드 표시
        return _SummaryLoadingCard(
          title: title,
          summary: summaryState.summary,
        );

      case SummaryStatus.pending:
        return _SummaryPendingCard(
          title: title,
          summaryState: summaryState,
          onRetry: onRetry,
        );

      case SummaryStatus.error:
        return _SummaryErrorCard(
          message: summaryState.error ?? '알 수 없는 오류가 발생했습니다',
          summaryState: summaryState,
          onRetry: onRetry,
        );

      case SummaryStatus.success:
        if (!_hasSummaryText) {
          return const SummarySkeletonCard();
        }
        break;
    }

    final summaryText = _sanitizeSummary(summaryState.summary!.summaryText);
    final sections = parseSummarySections(summaryText, fallbackTitle: title);
    final overviewSection = sections.firstWhereOrNull(
          (section) =>
              section.title.contains('전체 요약') ||
              section.title == title ||
              section.title.contains('요약'),
        ) ??
        sections.firstOrNull;
    final detailSections = sections
        .where((section) => section != overviewSection)
        .toList(growable: false);

    return Stack(
      children: [
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(
              color: Colors.black.withOpacity(0.1),
            ),
            borderRadius: BorderRadius.circular(14),
          ),
          child: InkWell(
            onTap: () {
              final articles = ref.read(feedProvider).articles;
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => SummaryDetailScreen(
                    summary: summaryState.summary!,
                    title: title,
                    articles: articles,
                  ),
                ),
              );
            },
            borderRadius: BorderRadius.circular(14),
            child: Padding(
              padding: EdgeInsets.all(Responsive.getPadding(context) * 1.5),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 9,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFF6B35),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        fontFamily: 'Noto Sans KR',
                      ),
                    ),
                  ),
                  if (overviewSection != null) ...[
                    const SizedBox(height: 12),
                    _OverviewSection(section: overviewSection),
                  ],
                  if (detailSections.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: detailSections
                          .map(
                            (section) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: _SummarySectionCard(section: section),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
        if (summaryState.status == SummaryStatus.loading)
          Positioned(
            top: 12,
            right: 12,
            child: Container(
              width: 20,
              height: 20,
              padding: const EdgeInsets.all(2),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.black.withOpacity(0.08),
                ),
              ),
              child: const CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFFFF6B35)),
              ),
            ),
          ),
      ],
    );
  }

  String _sanitizeSummary(String raw) {
    var text = raw.trim();
    if (text.startsWith('주요 뉴스 요약:')) {
      text = text.replaceFirst('주요 뉴스 요약:', '').trimLeft();
    }
    return text;
  }
}

class _OverviewSection extends StatelessWidget {
  const _OverviewSection({required this.section});

  final SummarySection section;

  @override
  Widget build(BuildContext context) {
    final content = section.lines.join('\n');
    return Text(
      content,
      style: const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.normal,
        color: Color(0xFF030213),
        fontFamily: 'Noto Sans KR',
        height: 1.5,
      ),
    );
  }
}

class _SummarySectionCard extends StatelessWidget {
  const _SummarySectionCard({required this.section});

  final SummarySection section;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFF7F8FA),
        borderRadius: BorderRadius.circular(10),
      ),
      padding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 12,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            section.title,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: Color(0xFF030213),
              fontFamily: 'Noto Sans KR',
            ),
          ),
          const SizedBox(height: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: section.lines
                .map(
                  (line) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '•',
                          style: TextStyle(
                            color: Color(0xFFFF6B35),
                            fontSize: 14,
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            line,
                            style: const TextStyle(
                              fontSize: 14,
                              height: 1.5,
                              color: Color(0xFF2D3748),
                              fontFamily: 'Noto Sans KR',
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

/// 조회 중 상태를 표시하는 카드.
class _SummaryLoadingCard extends StatelessWidget {
  const _SummaryLoadingCard({
    required this.title,
    this.summary,
  });

  final String title;
  final Summary? summary;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(
          color: Colors.black.withOpacity(0.08),
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      padding: EdgeInsets.all(Responsive.getPadding(context) * 1.5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Color(0xFFFF6B35)),
                ),
              ),
              const SizedBox(width: 8),
              const Text(
                '조회중',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'Noto Sans KR',
                  color: Color(0xFF030213),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            summary != null
                ? '$title 요약을 업데이트하고 있습니다...'
                : '$title 요약을 조회하고 있습니다...',
            style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF6A7282),
              fontFamily: 'Noto Sans KR',
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

/// 요약이 아직 생성되지 않았음을 안내하는 카드.
class _SummaryPendingCard extends StatelessWidget {
  const _SummaryPendingCard({
    required this.title,
    required this.summaryState,
    this.onRetry,
  });

  final String title;
  final DailySummaryState summaryState;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final isRetryAvailable = onRetry != null;
    final isLoading = summaryState.status == SummaryStatus.loading;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(
          color: Colors.black.withOpacity(0.08),
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      padding: EdgeInsets.all(Responsive.getPadding(context) * 1.5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.hourglass_empty,
                color: Color(0xFFFF6B35),
              ),
              const SizedBox(width: 8),
              const Text(
                '조회전',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'Noto Sans KR',
                  color: Color(0xFF030213),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '$title 요약이 아직 생성되지 않았습니다.\n아래 버튼을 눌러 요약 생성을 시도해보세요.',
            style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF6A7282),
              fontFamily: 'Noto Sans KR',
              height: 1.5,
            ),
          ),
          if (isRetryAvailable) ...[
            const SizedBox(height: 12),
            TextButton.icon(
              onPressed: isLoading ? null : onRetry,
              icon: isLoading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          Color(0xFF9CA3AF),
                        ),
                      ),
                    )
                  : const Icon(Icons.refresh),
              label: Text(
                isLoading ? '생성 중...' : '요약 생성',
                style: const TextStyle(
                  fontSize: 14,
                  fontFamily: 'Noto Sans KR',
                ),
              ),
              style: TextButton.styleFrom(
                foregroundColor: const Color(0xFFFF6B35),
                disabledForegroundColor: const Color(0xFF9CA3AF),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SummaryErrorCard extends StatelessWidget {
  const _SummaryErrorCard({
    required this.message,
    required this.summaryState,
    this.onRetry,
  });

  final String message;
  final DailySummaryState summaryState;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final isRetryAvailable = onRetry != null;
    final isLoading = summaryState.status == SummaryStatus.loading;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(
          color: Colors.red.withOpacity(0.2),
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      padding: EdgeInsets.all(Responsive.getPadding(context) * 1.5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.warning_amber_rounded,
                color: Color(0xFFFF6B35),
              ),
              const SizedBox(width: 8),
              const Text(
                '요약을 불러오지 못했습니다',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'Noto Sans KR',
                  color: Color(0xFF030213),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            message,
            style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF6A7282),
              fontFamily: 'Noto Sans KR',
            ),
          ),
          if (isRetryAvailable) ...[
            const SizedBox(height: 12),
            TextButton.icon(
              onPressed: isLoading ? null : onRetry,
              icon: isLoading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          Color(0xFF9CA3AF),
                        ),
                      ),
                    )
                  : const Icon(Icons.refresh),
              label: const Text(
                '다시 시도',
                style: TextStyle(
                  fontSize: 14,
                  fontFamily: 'Noto Sans KR',
                ),
              ),
              style: TextButton.styleFrom(
                foregroundColor: const Color(0xFFFF6B35),
                disabledForegroundColor: const Color(0xFF9CA3AF),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
