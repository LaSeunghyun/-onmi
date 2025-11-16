import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/summary.dart';
import '../../models/article.dart';
import '../../models/keyword.dart';
import '../../utils/responsive.dart';
import '../../utils/summary_parser.dart';
import '../../providers/feed_provider.dart';
import '../../providers/keyword_provider.dart';
import '../article_detail/article_detail_screen.dart';

class SummaryDetailScreen extends ConsumerWidget {
  final Summary summary;
  final String title;
  final List<Article>? articles;
  final List<Keyword>? keywords;

  const SummaryDetailScreen({
    super.key,
    required this.summary,
    required this.title,
    this.articles,
    this.keywords,
  });

  String _sanitizeSummary(String raw) {
    var text = raw.trim();
    if (text.startsWith('주요 뉴스 요약:')) {
      text = text.replaceFirst('주요 뉴스 요약:', '').trimLeft();
    }
    return text;
  }

  /// 섹션 제목과 키워드를 매칭하여 해당 키워드를 반환
  String? _findMatchingKeyword(String sectionTitle, List<Keyword> keywords) {
    final normalizedTitle = sectionTitle.toLowerCase().trim();
    
    for (final keyword in keywords) {
      final keywordText = keyword.text.toLowerCase().trim();
      // 섹션 제목에 키워드가 포함되어 있으면 매칭
      if (normalizedTitle.contains(keywordText) || keywordText.contains(normalizedTitle)) {
        return keyword.text;
      }
    }
    return null;
  }

  /// 키워드에 해당하는 기사만 필터링
  List<Article> _filterArticlesByKeyword(List<Article> allArticles, String? keywordText) {
    if (keywordText == null || keywordText.isEmpty) {
      return allArticles;
    }
    
    final normalizedKeyword = keywordText.toLowerCase().trim();
    return allArticles.where((article) {
      // 기사의 키워드 목록에 매칭되는 키워드가 있는지 확인
      return article.keywords.any((articleKeyword) => 
        articleKeyword.toLowerCase().trim() == normalizedKeyword
      );
    }).toList();
  }

  /// 텍스트를 파싱하여 클릭 가능한 위젯으로 변환
  List<TextSpan> _buildTextSpans(String text, List<Article> articles, BuildContext context) {
    if (articles.isEmpty) {
      return [TextSpan(text: text)];
    }

    final spans = <TextSpan>[];
    final pattern = RegExp(r'기사\s*(\d+)');
    int lastIndex = 0;

    for (final match in pattern.allMatches(text)) {
      // 매치 전의 텍스트 추가
      if (match.start > lastIndex) {
        spans.add(TextSpan(text: text.substring(lastIndex, match.start)));
      }

      // 기사 번호 파싱
      final articleIndex = int.tryParse(match.group(1) ?? '') ?? 0;
      final index = articleIndex - 1;

      if (index >= 0 && index < articles.length) {
        final article = articles[index];
        // 클릭 가능한 제목 추가
        spans.add(
          TextSpan(
            text: article.title,
            style: const TextStyle(
              color: Color(0xFFFF6B35),
              decoration: TextDecoration.underline,
              fontWeight: FontWeight.w500,
            ),
            recognizer: TapGestureRecognizer()
              ..onTap = () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => ArticleDetailScreen(article: article),
                  ),
                );
              },
          ),
        );
      } else {
        // 매치된 텍스트 그대로 추가
        spans.add(TextSpan(text: match.group(0) ?? ''));
      }

      lastIndex = match.end;
    }

    // 남은 텍스트 추가
    if (lastIndex < text.length) {
      spans.add(TextSpan(text: text.substring(lastIndex)));
    }

    return spans.isEmpty ? [TextSpan(text: text)] : spans;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryText = _sanitizeSummary(summary.summaryText);
    final sections = parseSummarySections(summaryText, fallbackTitle: title);
    final displayedSections = sections.isEmpty
        ? [
            SummarySection(
              title: title,
              lines: summaryText.split('\n').where((line) => line.trim().isNotEmpty).toList(),
            ),
          ]
        : sections;
    final allArticles = articles ?? ref.watch(feedProvider).articles;
    final List<Keyword> keywordsList = keywords ?? ref.watch(keywordProvider);
    final effectiveKeywords = keywordsList.isNotEmpty ? keywordsList : <Keyword>[];

    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            // 커스텀 헤더 - 전체 너비
            Builder(
              builder: (context) {
                final padding = Responsive.getPadding(context);
                final headerHeight = padding * 3.5; // 모바일: 16*3.5=56, 태블릿: 24*3.5=84, 데스크톱: 32*3.5=112
                final titleFontSize = Responsive.getTextSize(context, 16);
                final iconSize = Responsive.getTextSize(context, 24);
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
                      // 뒤로가기 버튼
                      Positioned(
                        left: padding * 0.5,
                        top: headerHeight * 0.23,
                        child: Container(
                          width: buttonSize,
                          height: buttonSize,
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () => Navigator.pop(context),
                              borderRadius: BorderRadius.circular(8),
                              child: Center(
                                child: Icon(
                                  Icons.arrow_back,
                                  size: iconSize,
                                  color: const Color(0xFF030213),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      // 제목 - 중앙 정렬
                      Center(
                        child: Text(
                          title,
                          style: TextStyle(
                            fontSize: titleFontSize,
                            fontWeight: FontWeight.w500,
                            color: const Color(0xFF030213),
                            fontFamily: 'Noto Sans KR',
                            height: 1.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
            // 본문 - 상단 정렬
            Expanded(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(
                  parent: AlwaysScrollableScrollPhysics(),
                ),
                child: Align(
                  alignment: Alignment.topCenter,
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      maxWidth: Responsive.getMaxContentWidth(context),
                    ),
                    child: Padding(
                      padding: Responsive.getAllPadding(context),
                      child: SelectionArea(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (final section in displayedSections) ...[
                              Builder(
                                builder: (context) {
                                  // 섹션 제목과 키워드 매칭
                                  final matchedKeyword = effectiveKeywords.isNotEmpty
                                      ? _findMatchingKeyword(section.title, effectiveKeywords)
                                      : null;
                                  // 키워드에 해당하는 기사만 필터링
                                  final filteredArticles = matchedKeyword != null
                                      ? _filterArticlesByKeyword(allArticles, matchedKeyword)
                                      : allArticles;
                                  
                                  return _SummaryDetailSection(
                                    section: section,
                                    buildSpans: (text) => _buildTextSpans(text, filteredArticles, context),
                                  );
                                },
                              ),
                              const SizedBox(height: 20),
                            ],
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

class _SummaryDetailSection extends StatelessWidget {
  const _SummaryDetailSection({
    required this.section,
    required this.buildSpans,
  });

  final SummarySection section;
  final List<TextSpan> Function(String) buildSpans;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          section.title,
          style: const TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
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
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '•',
                        style: TextStyle(
                          color: Color(0xFFFF6B35),
                          fontSize: 15,
                          height: 1.5,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: RichText(
                          text: TextSpan(
                            style: const TextStyle(
                              fontSize: 16,
                              height: 1.7,
                              color: Color(0xFF2D3748),
                              fontFamily: 'Noto Sans KR',
                            ),
                            children: buildSpans(line),
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
    );
  }
}

