import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/article.dart';

class DailyReport extends StatelessWidget {
  final DateTime date;
  final List<Article> articles;
  final Function(Article)? onArticleTap;

  const DailyReport({
    super.key,
    required this.date,
    required this.articles,
    this.onArticleTap,
  });

  String _formatDate(DateTime date) {
    return DateFormat('yyyy년 M월 d일', 'ko_KR').format(date);
  }

  String _formatTime(DateTime? dateTime) {
    if (dateTime == null) return '';
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inDays > 0) {
      return '${difference.inDays}일 전';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}시간 전';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}분 전';
    } else {
      return '방금 전';
    }
  }

  Widget _getSentimentIcon(String label) {
    switch (label) {
      case 'positive':
        return const Icon(Icons.thumb_up, size: 16, color: Colors.green);
      case 'negative':
        return const Icon(Icons.thumb_down, size: 16, color: Colors.red);
      default:
        return const Icon(Icons.remove, size: 16, color: Colors.grey);
    }
  }

  String _getSentimentText(String label) {
    switch (label) {
      case 'positive':
        return '긍정';
      case 'negative':
        return '부정';
      default:
        return '중립';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              _formatDate(date),
              style: const TextStyle(
                color: Color(0xFF6A7282),
                fontSize: 16,
                fontFamily: 'Noto Sans KR',
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF4F0),
                border: Border.all(color: const Color(0xFFFF6B35)),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '${articles.length}개의 이슈',
                style: const TextStyle(
                  color: Color(0xFFFF6B35),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  fontFamily: 'Noto Sans KR',
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (articles.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Center(
                child: Text(
                  '오늘의 이슈가 없습니다',
                  style: TextStyle(color: Colors.grey[400]),
                ),
              ),
            ),
          )
        else
          ...articles.map((article) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _ArticleCard(
                  article: article,
                  onTap: () => onArticleTap?.call(article),
                  formatTime: _formatTime,
                  getSentimentIcon: _getSentimentIcon,
                  getSentimentText: _getSentimentText,
                ),
              )),
      ],
    );
  }
}

class _ArticleCard extends StatelessWidget {
  final Article article;
  final VoidCallback? onTap;
  final String Function(DateTime?) formatTime;
  final Widget Function(String) getSentimentIcon;
  final String Function(String) getSentimentText;

  const _ArticleCard({
    required this.article,
    this.onTap,
    required this.formatTime,
    required this.getSentimentIcon,
    required this.getSentimentText,
  });

  @override
  Widget build(BuildContext context) {
    final keyword = article.keywords.isNotEmpty ? article.keywords.first : '';
    
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(
          color: Colors.black.withOpacity(0.1),
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 키워드 배지 및 감성 아이콘
              Row(
                children: [
                  if (keyword.isNotEmpty)
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
                        keyword,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          fontFamily: 'Noto Sans KR',
                        ),
                      ),
                    ),
                  if (keyword.isNotEmpty) const SizedBox(width: 8),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      getSentimentIcon(article.sentimentLabel),
                      const SizedBox(width: 4),
                      Text(
                        getSentimentText(article.sentimentLabel),
                        style: const TextStyle(
                          color: Color(0xFF6A7282),
                          fontSize: 12,
                          fontFamily: 'Noto Sans KR',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 4),
              // 제목
              Text(
                article.title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.normal,
                  color: Color(0xFF030213),
                  fontFamily: 'Noto Sans KR',
                  height: 1.5,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              // 출처 및 시간
              Row(
                children: [
                  Text(
                    article.source,
                    style: const TextStyle(
                      color: Color(0xFF717182),
                      fontSize: 12,
                      fontFamily: 'Noto Sans KR',
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    '•',
                    style: TextStyle(
                      color: Color(0xFF717182),
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    formatTime(article.publishedAt),
                    style: const TextStyle(
                      color: Color(0xFF717182),
                      fontSize: 12,
                      fontFamily: 'Noto Sans KR',
                    ),
                  ),
                ],
              ),
              if (article.snippet.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  article.snippet,
                  style: const TextStyle(
                    color: Color(0xFF4A5565),
                    fontSize: 14,
                    fontFamily: 'Noto Sans KR',
                    height: 1.43,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}



