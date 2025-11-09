import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../models/article.dart';

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
                    Positioned(
                      left: 141.69,
                      top: 14.5,
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
            // 본문
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 제목
                    Text(
                      widget.article.title,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.normal,
                        color: Color(0xFF030213),
                        fontFamily: 'Noto Sans KR',
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    // 출처, 시간, 감성
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Text(
                              widget.article.source,
                              style: const TextStyle(
                                color: Color(0xFF6A7282),
                                fontSize: 14,
                                fontFamily: 'Noto Sans KR',
                              ),
                            ),
                            const SizedBox(width: 8),
                            const Text(
                              '•',
                              style: TextStyle(
                                color: Color(0xFF6A7282),
                                fontSize: 14,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              _formatTime(widget.article.publishedAt),
                              style: const TextStyle(
                                color: Color(0xFF6A7282),
                                fontSize: 14,
                                fontFamily: 'Noto Sans KR',
                              ),
                            ),
                          ],
                        ),
                        Row(
                          children: [
                            _getSentimentIcon(widget.article.sentimentLabel),
                            const SizedBox(width: 4),
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
                    const SizedBox(height: 12),
                    // 본문 내용
                    if (widget.article.snippet.isNotEmpty) ...[
                      Text(
                        widget.article.snippet,
                        style: const TextStyle(
                          fontSize: 16,
                          height: 1.625,
                          color: Color(0xFF364153),
                          fontFamily: 'Noto Sans KR',
                        ),
                      ),
                      const SizedBox(height: 12),
                    ],
                    // 구분선
                    Container(
                      height: 1,
                      color: Colors.black.withOpacity(0.1),
                    ),
                    const SizedBox(height: 17),
                    // 원문 보기 버튼
                    SizedBox(
                      width: double.infinity,
                      height: 36,
                      child: Stack(
                        children: [
                          Container(
                            decoration: BoxDecoration(
                              color: Colors.white,
                              border: Border.all(
                                color: Colors.black.withOpacity(0.1),
                              ),
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                          // 아이콘
                          Positioned(
                            left: 100.27,
                            top: 10,
                            child: const Icon(
                              Icons.open_in_new,
                              size: 16,
                              color: Color(0xFF030213),
                            ),
                          ),
                          // 텍스트
                          Positioned(
                            left: 132.27,
                            top: 6,
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: _openOriginalUrl,
                                borderRadius: BorderRadius.circular(8),
                                child: const Padding(
                                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                                  child: Text(
                                    '원문 보기',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w500,
                                      color: Color(0xFF030213),
                                      fontFamily: 'Noto Sans KR',
                                      height: 1.43, // leading 20px / fontSize 14px
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          // 전체 클릭 영역
                          Positioned.fill(
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: _openOriginalUrl,
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    // 안내 메시지
                    Container(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                      height: 72,
                      decoration: BoxDecoration(
                        color: const Color(0xFFEFF6FF),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Align(
                        alignment: Alignment.topLeft,
                        child: Text(
                          '💡 실제 서비스에서는 뉴스 API를 통해 실제 기사 내용을 가져옵니다.',
                          style: TextStyle(
                            fontSize: 14,
                            color: Color(0xFF4A5565),
                            fontFamily: 'Noto Sans KR',
                            height: 1.43, // leading 20px / fontSize 14px
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}



