import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/date_selector.dart';
import '../../widgets/keyword_filter.dart';
import '../../widgets/daily_report.dart';
import '../../widgets/token_limit_banner.dart';
import '../../providers/keyword_provider.dart';
import '../../providers/feed_provider.dart';
import '../../providers/token_usage_provider.dart';
import '../../providers/summary_provider.dart';
import '../../providers/cse_query_usage_provider.dart';
import '../../screens/article_detail/article_detail_screen.dart';
import '../../screens/settings/settings_screen.dart';
import '../../utils/responsive.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  DateTime _selectedDate = DateTime.now();
  String? _selectedKeyword;

  @override
  Widget build(BuildContext context) {
    final keywords = ref.watch(keywordProvider);
    final feedState = ref.watch(feedProvider);
    final tokenUsage = ref.watch(tokenUsageProvider);
    final cseUsageState = ref.watch(cseQueryUsageProvider);
    // 선택된 키워드가 있으면 키워드별 요약, 없으면 일일 요약
    final summaryState = _selectedKeyword != null && keywords.isNotEmpty
        ? ref.watch(keywordSummaryProvider(
            keywords.firstWhere((k) => k.text == _selectedKeyword, orElse: () => keywords.first).id))
        : ref.watch(dailySummaryProvider);


    // 키워드별 기사 개수 계산
    final issueCounts = <String, int>{};
    for (final keyword in keywords) {
      issueCounts[keyword.text] = feedState.articles
          .where((a) => a.keywords.contains(keyword.text))
          .length;
    }

    // 선택된 키워드로 필터링된 기사
    final filteredArticles = _selectedKeyword == null
        ? feedState.articles
        : feedState.articles
            .where((a) => a.keywords.contains(_selectedKeyword))
            .toList();

    final totalIssues = filteredArticles.length;

    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            // 토큰 제한 경고 배너
            if (tokenUsage != null)
              TokenLimitBanner(
                tokenUsage: tokenUsage,
                onDismiss: () {
                  // 배너 닫기 (선택사항)
                },
              ),
            // 커스텀 헤더 - 전체 너비
            Container(
              height: 57,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.25),
                    blurRadius: 4,
                    offset: const Offset(0, 4),
                  ),
                ],
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(8),
                  bottomRight: Radius.circular(8),
                ),
              ),
              child: Stack(
                children: [
                  // #onmi 로고
                  Positioned(
                    left: 8,
                    top: 16,
                    child: Container(
                      width: 80,
                      height: 32,
                      child: Image.network(
                        'https://www.figma.com/api/mcp/asset/82a1b8cf-db18-47bc-bafb-4ce0d0a05cac',
                        fit: BoxFit.contain,
                        errorBuilder: (context, error, stackTrace) {
                          return Container(
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: [
                                  Color(0xFFFF6B35),
                                  Color(0xFFFF8F5C),
                                ],
                              ),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: const Center(
                              child: Text(
                                '#onmi',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white,
                                  fontFamily: 'Noto Sans KR',
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  // 설정 버튼
                  Positioned(
                    right: 8,
                    top: 13,
                    child: Container(
                      width: 32,
                      height: 32,
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => const SettingsScreen(),
                              ),
                            );
                          },
                          borderRadius: BorderRadius.circular(8),
                          child: const Center(
                            child: Icon(
                              Icons.settings,
                              size: 20,
                              color: Color(0xFF030213),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // 본문 - 중앙 정렬
            Expanded(
              child: RefreshIndicator(
                onRefresh: () async {
                  await ref.read(feedProvider.notifier).refresh();
                  if (_selectedKeyword != null) {
                    final keywordId = keywords
                        .firstWhere((k) => k.text == _selectedKeyword)
                        .id;
                    await ref.read(keywordSummaryProvider(keywordId).notifier).refresh();
                  } else {
                    await ref.read(dailySummaryProvider.notifier).refresh();
                  }
                },
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: BoxConstraints(
                        maxWidth: Responsive.getMaxContentWidth(context),
                      ),
                      child: Padding(
                        padding: Responsive.getAllPadding(context),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            DateSelector(
                              selectedDate: _selectedDate,
                              onSelectDate: (date) {
                                setState(() {
                                  _selectedDate = date;
                                });
                                ref.read(feedProvider.notifier).loadFeed();
                              },
                            ),
                            const SizedBox(height: 16),
                            // 오늘의 요약 카드
                            _SummaryCard(
                              summaryState: summaryState,
                              selectedKeyword: _selectedKeyword,
                              totalIssues: totalIssues,
                              keywordsCount: keywords.length,
                              cseUsageState: cseUsageState,
                              onRetry: () {
                                if (_selectedKeyword != null && keywords.isNotEmpty) {
                                  try {
                                    final keywordId = keywords
                                        .firstWhere((k) => k.text == _selectedKeyword)
                                        .id;
                                    ref.read(keywordSummaryProvider(keywordId).notifier).refresh();
                                    ref
                                        .read(cseQueryUsageProvider.notifier)
                                        .loadUsage(keywordId: keywordId);
                                  } catch (e) {
                                    ref.read(dailySummaryProvider.notifier).refresh();
                                    ref
                                        .read(cseQueryUsageProvider.notifier)
                                        .loadUsage(keywordId: null);
                                  }
                                } else {
                                  ref.read(dailySummaryProvider.notifier).refresh();
                                  ref
                                      .read(cseQueryUsageProvider.notifier)
                                      .loadUsage(keywordId: null);
                                }
                              },
                            ),
                            const SizedBox(height: 16),
                            // 키워드 필터
                            if (keywords.isNotEmpty)
                              KeywordFilter(
                                keywords: keywords.map((k) => k.text).toList(),
                                selectedKeyword: _selectedKeyword,
                                onSelectKeyword: (keyword) {
                                  setState(() {
                                    _selectedKeyword = keyword;
                                  });
                                  // 키워드 선택 시 해당 키워드의 요약 로드
                                  if (keyword != null && keywords.isNotEmpty) {
                                    try {
                                      final keywordId = keywords
                                          .firstWhere((k) => k.text == keyword)
                                          .id;
                                      ref.read(keywordSummaryProvider(keywordId).notifier).loadSummary();
                                    ref.read(cseQueryUsageProvider.notifier).loadUsage(
                                          keywordId: keywordId,
                                        );
                                    } catch (e) {
                                      // 키워드를 찾을 수 없으면 일일 요약 로드
                                      ref.read(dailySummaryProvider.notifier).loadSummary();
                                    ref.read(cseQueryUsageProvider.notifier).loadUsage(
                                          keywordId: null,
                                        );
                                    }
                                  } else {
                                    // 전체 선택 시 일일 요약 로드
                                    ref.read(dailySummaryProvider.notifier).loadSummary();
                                  ref
                                      .read(cseQueryUsageProvider.notifier)
                                      .loadUsage(keywordId: null);
                                  }
                                },
                                issueCounts: issueCounts,
                              ),
                            const SizedBox(height: 16),
                            // 기사 목록
                            if (feedState.isLoading)
                              const Center(
                                child: Padding(
                                  padding: EdgeInsets.all(32.0),
                                  child: CircularProgressIndicator(),
                                ),
                              )
                            else if (feedState.error != null)
                              Center(
                                child: Padding(
                                  padding: const EdgeInsets.all(32.0),
                                  child: Text(
                                    '오류: ${feedState.error}',
                                    style: const TextStyle(color: Colors.red),
                                  ),
                                ),
                              )
                            else
                              DailyReport(
                                date: _selectedDate,
                                articles: filteredArticles,
                                onArticleTap: (article) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => ArticleDetailScreen(
                                        article: article,
                                      ),
                                    ),
                                  );
                                },
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 요약 카드 위젯
class _SummaryCard extends StatelessWidget {
  final DailySummaryState summaryState;
  final String? selectedKeyword;
  final int totalIssues;
  final int keywordsCount;
  final VoidCallback? onRetry;
  final CseQueryUsageState cseUsageState;

  const _SummaryCard({
    required this.summaryState,
    this.selectedKeyword,
    required this.totalIssues,
    required this.keywordsCount,
    this.onRetry,
    required this.cseUsageState,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        Responsive.getPadding(context),
        Responsive.getPadding(context),
        Responsive.getPadding(context),
        20,
      ),
      width: double.infinity,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFFFF6B35),
            Color(0xFFFF8F5C),
          ],
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '오늘의 요약',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w500,
                  fontFamily: 'Noto Sans KR',
                  height: 1.5,
                ),
              ),
              if (summaryState.isLoading)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          if (cseUsageState.isLoading && cseUsageState.usage == null)
            Text(
              '조회 가능 쿼리수 계산 중...',
              style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 14,
                fontFamily: 'Noto Sans KR',
                fontWeight: FontWeight.w500,
              ),
            )
          else if (cseUsageState.error != null)
            Text(
              '조회 가능 쿼리수를 불러오지 못했습니다',
              style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 14,
                fontFamily: 'Noto Sans KR',
                fontWeight: FontWeight.w500,
              ),
            )
          else
            Row(
              children: [
                Text(
                  '조회 가능 쿼리수 : ',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    fontSize: 15,
                    fontFamily: 'Noto Sans KR',
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  '${cseUsageState.usage?.userRemaining ?? '-'}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontFamily: 'Noto Sans KR',
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          const SizedBox(height: 8),
          if (summaryState.error != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.error_outline,
                        color: Colors.white,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '요약을 불러오는 중 오류가 발생했습니다',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.95),
                            fontSize: 14,
                            fontFamily: 'Noto Sans KR',
                            fontWeight: FontWeight.w500,
                            height: 1.43,
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (onRetry != null) ...[
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: onRetry,
                        icon: const Icon(Icons.refresh, size: 16, color: Colors.white),
                        label: const Text(
                          '다시 시도',
                          style: TextStyle(
                            fontFamily: 'Noto Sans KR',
                            fontSize: 14,
                            color: Colors.white,
                          ),
                        ),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Colors.white, width: 1),
                          padding: const EdgeInsets.symmetric(vertical: 8),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            )
          else if (summaryState.summary != null)
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  summaryState.summary!.summaryText.replaceFirst('주요 뉴스 요약:', '').trim(),
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.95),
                    fontSize: 14,
                    fontFamily: 'Noto Sans KR',
                    height: 1.5,
                  ),
                  maxLines: 4,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            )
          else
            Text(
              selectedKeyword != null
                  ? '$totalIssues개의 이슈를 발견했습니다'
                  : '$keywordsCount개의 키워드에 대한 $totalIssues개의 이슈를 발견했습니다',
              style: TextStyle(
                color: Colors.white.withOpacity(0.9),
                fontSize: 14,
                fontFamily: 'Noto Sans KR',
                height: 1.43,
              ),
            ),
        ],
      ),
    );
  }
}

