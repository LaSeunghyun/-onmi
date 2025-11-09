import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/date_selector.dart';
import '../../widgets/keyword_filter.dart';
import '../../widgets/daily_report.dart';
import '../../widgets/token_limit_banner.dart';
import '../../providers/keyword_provider.dart';
import '../../providers/feed_provider.dart';
import '../../providers/token_usage_provider.dart';
import '../../screens/article_detail/article_detail_screen.dart';
import '../../screens/settings/settings_screen.dart';

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
            // 커스텀 헤더
            Container(
              height: 57,
              width: 320,
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
                    top: 20,
                    child: Container(
                      width: 48,
                      height: 18,
                      child: Image.network(
                        'https://www.figma.com/api/mcp/asset/82a1b8cf-db18-47bc-bafb-4ce0d0a05cac',
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
                              borderRadius: BorderRadius.circular(33554400),
                            ),
                            child: const Center(
                              child: Text(
                                '#onmi',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.normal,
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
            // 본문
            Expanded(
              child: RefreshIndicator(
                onRefresh: () async {
                  await ref.read(feedProvider.notifier).refresh();
                },
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
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
                      Container(
                        padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
                        height: 106,
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
                                height: 1.5, // leading 30px / fontSize 20px
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _selectedKeyword != null
                                  ? '$totalIssues개의 이슈를 발견했습니다'
                                  : '${keywords.length}개의 키워드에 대한 $totalIssues개의 이슈를 발견했습니다',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.9),
                                fontSize: 14,
                                fontFamily: 'Noto Sans KR',
                                height: 1.43, // leading 20px / fontSize 14px
                              ),
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
          ],
        ),
      ),
    );
  }
}

