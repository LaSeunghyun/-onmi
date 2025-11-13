import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../models/article.dart';
import '../../utils/responsive.dart';

class ArticleDetailScreen extends ConsumerStatefulWidget {
  final Article article;

  const ArticleDetailScreen({
    super.key,
    required this.article,
  });

  @override
  ConsumerState<ArticleDetailScreen> createState() =>
      _ArticleDetailScreenState();
}

class _ArticleDetailScreenState extends ConsumerState<ArticleDetailScreen> {

  Widget _getSentimentIcon(String label) {
    switch (label) {
      case 'positive':
        return const Icon(Icons.thumb_up, size: 20, color: Colors.green);
      case 'negative':
        return const Icon(Icons.thumb_down, size: 20, color: Colors.red);
      default:
        return const Icon(Icons.remove, size: 20, color: Colors.grey);
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

  Future<void> _openOriginalUrl() async {
    final uri = Uri.parse(widget.article.url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('링크를 열 수 없습니다')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final keyword = widget.article.keywords.isNotEmpty 
        ? widget.article.keywords.first 
        : '';
    
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
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
                  // 뒤로가기 버튼
                  Positioned(
                    left: 8,
                    top: 13,
                    child: Container(
                      width: 32,
                      height: 32,
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: () => Navigator.pop(context),
                          borderRadius: BorderRadius.circular(8),
                          child: const Center(
                            child: Icon(
                              Icons.arrow_back,
                              size: 24,
                              color: Color(0xFF030213),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                  // 키워드 배지 - 중앙 정렬
                  if (keyword.isNotEmpty)
                    Center(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFF6B35),
                          borderRadius: BorderRadius.circular(33554400),
                        ),
                        child: Text(
                          keyword,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontFamily: 'Noto Sans KR',
                            height: 1.43, // leading 20px / fontSize 14px
                          ),
                        ),
                      ),
                    ),
                ],
              ),
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
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // 제목
                          Text(
                            widget.article.title,
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF030213),
                              fontFamily: 'Noto Sans KR',
                              height: 1.45,
                            ),
                          ),
                          const SizedBox(height: 12),
                          // 출처, 시간, 감성
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Wrap(
                                  spacing: 8,
                                  runSpacing: 4,
                                  children: [
                                    Text(
                                      widget.article.source,
                                      style: const TextStyle(
                                        color: Color(0xFF6A7282),
                                        fontSize: 15,
                                        fontFamily: 'Noto Sans KR',
                                      ),
                                    ),
                                    Text(
                                      '• ${_formatTime(widget.article.publishedAt)}',
                                      style: const TextStyle(
                                        color: Color(0xFF6A7282),
                                        fontSize: 15,
                                        fontFamily: 'Noto Sans KR',
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  _getSentimentIcon(widget.article.sentimentLabel),
                                  const SizedBox(width: 6),
                                  Text(
                                    _getSentimentText(widget.article.sentimentLabel),
                                    style: const TextStyle(
                                      fontSize: 14,
                                      color: Color(0xFF030213),
                                      fontFamily: 'Noto Sans KR',
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 20),
                          // 본문 내용
                          if (widget.article.snippet.isNotEmpty) ...[
                            SelectionArea(
                              child: Text(
                                widget.article.snippet,
                                style: const TextStyle(
                                  fontSize: 17,
                                  height: 1.7,
                                  color: Color(0xFF2D3748),
                                  fontFamily: 'Noto Sans KR',
                                ),
                              ),
                            ),
                            const SizedBox(height: 24),
                          ],
                          // 구분선
                          Container(
                            height: 1,
                            color: Colors.black.withOpacity(0.08),
                          ),
                          const SizedBox(height: 20),
                          // 원문 보기 버튼
                          SizedBox(
                            width: double.infinity,
                            height: 44,
                            child: ElevatedButton.icon(
                              onPressed: _openOriginalUrl,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.white,
                                foregroundColor: const Color(0xFF030213),
                                side: BorderSide(
                                  color: Colors.black.withOpacity(0.12),
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                elevation: 0,
                              ),
                              icon: const Icon(
                                Icons.open_in_new,
                                size: 18,
                              ),
                              label: const Text(
                                '원문 보기',
                                style: TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                  fontFamily: 'Noto Sans KR',
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),
                          // 안내 메시지
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: const Color(0xFFEFF6FF),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Text(
                              '💡 실제 서비스에서는 뉴스 API를 통해 완전한 기사 내용을 불러와 요약을 제공합니다.',
                              style: TextStyle(
                                fontSize: 14,
                                color: Color(0xFF4A5565),
                                fontFamily: 'Noto Sans KR',
                                height: 1.5,
                              ),
                            ),
                          ),
                        ],
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



