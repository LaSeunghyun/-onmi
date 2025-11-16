import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/date_selector.dart';
import '../../widgets/keyword_filter.dart';
import '../../widgets/token_limit_banner.dart';
import '../../providers/keyword_provider.dart';
import '../../providers/feed_provider.dart';
import '../../providers/token_usage_provider.dart';
import '../../providers/summary_provider.dart';
import '../../providers/cse_query_usage_provider.dart';
import '../../screens/settings/settings_screen.dart';
import '../../utils/responsive.dart';
import '../../utils/summary_parser.dart';
import '../../widgets/insight_summary_card.dart';
import '../../widgets/skeleton/summary_skeleton_card.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen>
    with WidgetsBindingObserver {
  String? _selectedKeyword;
  Timer? _midnightTimer;

  int? _sectionCountFromSummary({
    required DailySummaryState state,
    required String fallbackTitle,
  }) {
    if (state.status == SummaryStatus.loading ||
        state.status == SummaryStatus.pending) {
      return null;
    }
    final summaryText = state.summary?.summaryText.trim();
    if (summaryText == null || summaryText.isEmpty) {
      return 0;
    }
    return parseSummarySections(
      summaryText,
      fallbackTitle: fallbackTitle,
    ).length;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _scheduleMidnightRefresh();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _cancelMidnightRefresh();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    // 앱이 포그라운드로 돌아올 때 데이터 새로고침
    if (state == AppLifecycleState.resumed) {
      _refreshData();
      _scheduleMidnightRefresh();
    }
  }

  void _cancelMidnightRefresh() {
    _midnightTimer?.cancel();
    _midnightTimer = null;
  }

  void _scheduleMidnightRefresh() {
    _cancelMidnightRefresh();
    final now = DateTime.now();
    final nextMidnight = DateTime(now.year, now.month, now.day).add(
      const Duration(days: 1),
    );
    final duration = nextMidnight.difference(now);
    _midnightTimer = Timer(duration, () async {
      await _refreshForMidnight();
      _scheduleMidnightRefresh();
    });
  }

  /// 데이터 새로고침 메서드
  Future<void> _refreshData() async {
    if (!mounted) return;

    // 키워드 목록 새로고침
    await ref.read(keywordProvider.notifier).loadKeywords();

    final keywords = ref.read(keywordProvider);

    // 피드 새로고침
    await ref.read(feedProvider.notifier).refresh();

    // 요약 새로고침
    if (_selectedKeyword != null && keywords.isNotEmpty) {
      try {
        final keywordId =
            keywords.firstWhere((k) => k.text == _selectedKeyword).id;
        await ref.read(keywordSummaryProvider(keywordId).notifier).refresh();
      } catch (e) {
        await ref.read(dailySummaryProvider.notifier).refresh();
      }
    } else {
      await ref.read(dailySummaryProvider.notifier).refresh();
    }
  }

  Future<void> _refreshForMidnight() async {
    if (!mounted) {
      return;
    }

    final today = DateTime.now();
    final normalizedToday = DateTime(today.year, today.month, today.day);

    await ref.read(keywordProvider.notifier).loadKeywords();
    final keywords = ref.read(keywordProvider);

    if (_selectedKeyword != null && keywords.isNotEmpty) {
      try {
        final keywordId =
            keywords.firstWhere((k) => k.text == _selectedKeyword).id;
        await ref
            .read(keywordSummaryProvider(keywordId).notifier)
            .setDate(normalizedToday);
      } catch (_) {
        await ref.read(dailySummaryProvider.notifier).setDate(normalizedToday);
      }
    } else {
      await ref.read(dailySummaryProvider.notifier).setDate(normalizedToday);
    }

    await ref.read(feedProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context) {
    final keywords = ref.watch(keywordProvider);
    final feedState = ref.watch(feedProvider);
    final tokenUsage = ref.watch(tokenUsageProvider);
    final cseUsageState = ref.watch(cseQueryUsageProvider);
    final dailySummaryState = ref.watch(dailySummaryProvider);
    final keywordSummaryStates = <String, DailySummaryState>{
      for (final keyword in keywords)
        keyword.id: ref.watch(keywordSummaryProvider(keyword.id)),
    };
    final selectedKeywordModel =
        _selectedKeyword != null && keywords.isNotEmpty
            ? keywords.firstWhere(
                (k) => k.text == _selectedKeyword,
                orElse: () => keywords.first,
              )
            : null;
    final summaryState = selectedKeywordModel != null
        ? keywordSummaryStates[selectedKeywordModel.id] ?? dailySummaryState
        : dailySummaryState;
    final selectedDate = summaryState.selectedDate;
    final availableDates = summaryState.availableDates;
    final int? totalSectionCount = _sectionCountFromSummary(
      state: dailySummaryState,
      fallbackTitle: '오늘의 인사이트',
    );
    final issueCounts = <String, int?>{};
    for (final keyword in keywords) {
      final keywordState = keywordSummaryStates[keyword.id];
      issueCounts[keyword.text] = keywordState == null
          ? null
          : _sectionCountFromSummary(
              state: keywordState,
              fallbackTitle: '${keyword.text} 요약',
            );
    }

    // 선택된 키워드로 필터링된 기사
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
            Builder(
              builder: (context) {
                final padding = Responsive.getPadding(context);
                final headerHeight = padding *
                    3.5; // 모바일: 16*3.5=56, 태블릿: 24*3.5=84, 데스크톱: 32*3.5=112
                final logoFontSize = Responsive.getTextSize(context, 18);
                final iconSize = Responsive.getTextSize(context, 20);
                final buttonSize = padding * 2;

                return Container(
                  height: headerHeight.clamp(56.0, 112.0),
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
                        left: padding * 0.5,
                        top: headerHeight * 0.28,
                        child: Container(
                          width: 80,
                          height: headerHeight * 0.56,
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
                                child: Center(
                                  child: Text(
                                    '#onmi',
                                    style: TextStyle(
                                      fontSize: logoFontSize,
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
                        right: padding * 0.5,
                        top: headerHeight * 0.23,
                        child: Container(
                          width: buttonSize,
                          height: buttonSize,
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () async {
                                // 설정 화면으로 이동하고 결과를 기다림
                                final result = await Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) =>
                                        const SettingsScreen(),
                                  ),
                                );

                                // 설정 화면에서 저장 후 돌아왔을 때만 데이터 새로고침
                                if (result == true && mounted) {
                                  _refreshData();
                                }
                              },
                              borderRadius: BorderRadius.circular(8),
                              child: Center(
                                child: Icon(
                                  Icons.settings,
                                  size: iconSize,
                                  color: const Color(0xFF030213),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
            // 본문 - 중앙 정렬
            Expanded(
              child: RefreshIndicator(
                onRefresh: _refreshData,
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
                              selectedDate: selectedDate,
                              availableDates: availableDates,
                              onSelectDate: (date) {
                                final normalizedDate = DateTime(
                                  date.year,
                                  date.month,
                                  date.day,
                                );
                                if (_selectedKeyword != null &&
                                    keywords.isNotEmpty) {
                                  try {
                                    final keywordId = keywords
                                        .firstWhere(
                                            (k) => k.text == _selectedKeyword)
                                        .id;
                                    ref
                                        .read(keywordSummaryProvider(keywordId)
                                            .notifier)
                                        .setDate(normalizedDate);
                                  } catch (e) {
                                    ref
                                        .read(dailySummaryProvider.notifier)
                                        .setDate(normalizedDate);
                                  }
                                } else {
                                  ref
                                      .read(dailySummaryProvider.notifier)
                                      .setDate(normalizedDate);
                                }
                                ref.read(feedProvider.notifier).loadFeed();
                              },
                            ),
                            const SizedBox(height: 16),
                            // 오늘의 요약 카드 (쿼리 수 표시용)
                            Container(
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
                                  const SizedBox(height: 8),
                                  if (cseUsageState.isLoading &&
                                      cseUsageState.usage == null)
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
                                            color:
                                                Colors.white.withOpacity(0.9),
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
                                ],
                              ),
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
                                      ref
                                          .read(
                                              keywordSummaryProvider(keywordId)
                                                  .notifier)
                                          .setDate(selectedDate);
                                      ref
                                          .read(cseQueryUsageProvider.notifier)
                                          .loadUsage(
                                            keywordId: keywordId,
                                          );
                                    } catch (e) {
                                      // 키워드를 찾을 수 없으면 일일 요약 로드
                                      ref
                                          .read(dailySummaryProvider.notifier)
                                          .setDate(selectedDate);
                                      ref
                                          .read(cseQueryUsageProvider.notifier)
                                          .loadUsage(
                                            keywordId: null,
                                          );
                                    }
                                  } else {
                                    // 전체 선택 시 일일 요약 로드
                                    ref
                                        .read(dailySummaryProvider.notifier)
                                        .setDate(selectedDate);
                                    ref
                                        .read(cseQueryUsageProvider.notifier)
                                        .loadUsage(keywordId: null);
                                  }
                                },
                                issueCounts: issueCounts,
                                totalCount: totalSectionCount,
                              ),
                            const SizedBox(height: 16),
                            // 오늘의 인사이트 제목
                            const Align(
                              alignment: Alignment.center,
                              child: Text(
                                '오늘의 인사이트',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: Color(0xFF030213),
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                  fontFamily: 'Noto Sans KR',
                                ),
                              ),
                            ),
                            const SizedBox(height: 12),
                            // 인사이트 카드 (기존 뉴스 카드 위치)
                            if (feedState.isLoading)
                              const SummarySkeletonCard(lineCount: 5)
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
                              InsightSummaryCard(
                                summaryState: summaryState,
                                cseUsageState: cseUsageState,
                                title: _selectedKeyword != null
                                    ? '${_selectedKeyword!} 인사이트'
                                    : '오늘의 인사이트',
                                onRetry: () {
                                  if (_selectedKeyword != null &&
                                      keywords.isNotEmpty) {
                                    try {
                                      final keywordId = keywords
                                          .firstWhere(
                                              (k) => k.text == _selectedKeyword)
                                          .id;
                                      ref
                                          .read(
                                              keywordSummaryProvider(keywordId)
                                                  .notifier)
                                          .refresh();
                                      ref
                                          .read(cseQueryUsageProvider.notifier)
                                          .loadUsage(keywordId: keywordId);
                                    } catch (e) {
                                      ref
                                          .read(dailySummaryProvider.notifier)
                                          .refresh();
                                      ref
                                          .read(cseQueryUsageProvider.notifier)
                                          .loadUsage(keywordId: null);
                                    }
                                  } else {
                                    ref
                                        .read(dailySummaryProvider.notifier)
                                        .refresh();
                                    ref
                                        .read(cseQueryUsageProvider.notifier)
                                        .loadUsage(keywordId: null);
                                  }
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
