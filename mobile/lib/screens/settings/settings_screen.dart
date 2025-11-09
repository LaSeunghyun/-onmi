import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/keyword_input.dart';
import '../../widgets/keyword_list.dart';
import '../../providers/keyword_provider.dart';
import '../../providers/auth_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  String _notificationTime = '9';

  @override
  Widget build(BuildContext context) {
    final keywords = ref.watch(keywordProvider);
    final keywordNotifier = ref.read(keywordProvider.notifier);

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
                  // 설정 타이틀 - 중앙 정렬
                  Positioned(
                    left: 145.27,
                    top: 16.5,
                    child: const Text(
                      '설정',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.normal,
                        color: Color(0xFF030213),
                        fontFamily: 'Noto Sans KR',
                        height: 1.5, // leading 24px / fontSize 16px
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // 본문
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 키워드 관리 섹션
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '키워드 관리',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.normal,
                            color: Color(0xFF364153),
                            fontFamily: 'Noto Sans KR',
                          ),
                        ),
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                          height: 72,
                          decoration: BoxDecoration(
                            color: const Color(0xFFF9FAFB),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Align(
                            alignment: Alignment.topLeft,
                            child: Text(
                              '💡 관심 있는 주제, 기술, 산업 등 키워드를 입력해주세요.',
                              style: TextStyle(
                                fontSize: 14,
                                color: Color(0xFF4A5565),
                                fontFamily: 'Noto Sans KR',
                                height: 1.43, // leading 20px / fontSize 14px
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          '최대 3개까지 등록 가능합니다',
                          style: TextStyle(
                            fontSize: 14,
                            color: Color(0xFF6A7282),
                            fontFamily: 'Noto Sans KR',
                          ),
                        ),
                        const SizedBox(height: 12),
                        KeywordInput(
                          onAddKeyword: (keyword) async {
                            try {
                              await keywordNotifier.addKeyword(keyword);
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('키워드가 추가되었습니다')),
                                );
                              }
                            } catch (e) {
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('오류: $e')),
                                );
                              }
                            }
                          },
                          disabled: keywords.length >= 3,
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    // 등록된 키워드
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '등록된 키워드 (${keywords.length}/3)',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.normal,
                            color: Color(0xFF364153),
                            fontFamily: 'Noto Sans KR',
                          ),
                        ),
                        const SizedBox(height: 12),
                        KeywordList(
                          keywords: keywords.map((k) => k.text).toList(),
                          onRemoveKeyword: (keyword) async {
                            final keywordObj = keywords.firstWhere((k) => k.text == keyword);
                            try {
                              await keywordNotifier.removeKeyword(keywordObj.id);
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('키워드가 삭제되었습니다')),
                                );
                              }
                            } catch (e) {
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('오류: $e')),
                                );
                              }
                            }
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    // 구분선
                    Container(
                      height: 1,
                      color: Colors.black.withOpacity(0.1),
                    ),
                    const SizedBox(height: 25),
                    // 알림 설정 섹션
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '알림 설정',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.normal,
                            color: Color(0xFF364153),
                            fontFamily: 'Noto Sans KR',
                          ),
                        ),
                        const SizedBox(height: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              '일일 리포트 알림 시간',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: Color(0xFF030213),
                                fontFamily: 'Noto Sans KR',
                              ),
                            ),
                            const SizedBox(height: 8),
                            Container(
                              height: 36,
                              padding: const EdgeInsets.symmetric(horizontal: 13),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF3F3F5),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: DropdownButtonHideUnderline(
                                child: DropdownButton<String>(
                                  value: _notificationTime,
                                  isExpanded: true,
                                  icon: const Icon(Icons.keyboard_arrow_down, size: 16),
                                  style: const TextStyle(
                                    fontSize: 14,
                                    color: Color(0xFF030213),
                                    fontFamily: 'Noto Sans KR',
                                  ),
                                  items: List.generate(24, (index) {
                                    final hour = index;
                                    String label;
                                    if (hour == 0) {
                                      label = '오전 12시';
                                    } else if (hour < 12) {
                                      label = '오전 $hour시';
                                    } else if (hour == 12) {
                                      label = '오후 12시';
                                    } else {
                                      label = '오후 ${hour - 12}시';
                                    }
                                    return DropdownMenuItem(
                                      value: hour.toString(),
                                      child: Text(label),
                                    );
                                  }),
                                  onChanged: (value) {
                                    if (value != null) {
                                      setState(() {
                                        _notificationTime = value;
                                      });
                                    }
                                  },
                                ),
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              '매일 설정한 시간에 등록된 키워드의 최신 이슈를 알려드립니다.',
                              style: TextStyle(
                                fontSize: 14,
                                color: Color(0xFF6A7282),
                                fontFamily: 'Noto Sans KR',
                                height: 1.43,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    // 구분선
                    Container(
                      height: 1,
                      color: Colors.black.withOpacity(0.1),
                    ),
                    const SizedBox(height: 25),
                    // 로그아웃 버튼
                    SizedBox(
                      width: double.infinity,
                      height: 36,
                      child: ElevatedButton(
                        onPressed: () {
                          ref.read(authProvider.notifier).signOut();
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFFFB2C36),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                        child: const Text(
                          '로그아웃',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
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


