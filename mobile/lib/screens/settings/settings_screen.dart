import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/keyword.dart';
import '../../providers/auth_provider.dart';
import '../../providers/keyword_provider.dart';
import '../../services/api_service.dart';
import '../../utils/responsive.dart';
import '../../widgets/keyword_input.dart';
import '../../widgets/keyword_list.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  String _notificationTime = '9';
  String _initialNotificationTime = '9';
  bool _isLoadingPreferences = true;
  bool _isSaving = false;
  bool _hasInitializedKeywords = false;
  bool _hasManualKeywordEdits = false;
  final ApiService _apiService = getApiService();

  List<Keyword> _initialKeywords = [];
  List<String> _draftKeywords = [];

  @override
  void initState() {
    super.initState();
    _loadPreferences();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      final keywords = ref.read(keywordProvider);
      _syncKeywordsFromProvider(keywords);
    });
  }

  Future<void> _loadPreferences() async {
    try {
      final preferences = await _apiService.getPreferences();
      final notificationTimeHour = preferences['notification_time_hour'];
      setState(() {
        if (notificationTimeHour != null) {
          _notificationTime = notificationTimeHour.toString();
          _initialNotificationTime = _notificationTime;
        } else {
          _initialNotificationTime = _notificationTime;
        }
      });
    } catch (e) {
      // 오류 발생 시 기본값 유지
      debugPrint('선호도 로드 오류: $e');
    } finally {
      setState(() {
        _isLoadingPreferences = false;
      });
    }
  }

  void _syncKeywordsFromProvider(List<Keyword> keywords) {
    setState(() {
      _initialKeywords = List<Keyword>.from(keywords);
      _draftKeywords = keywords.map((k) => k.text).toList();
      _hasInitializedKeywords = true;
      _hasManualKeywordEdits = false;
    });
  }

  bool get _hasKeywordChanges {
    final initialTexts = _initialKeywords.map((k) => k.text).toList();
    return !listEquals(initialTexts, _draftKeywords);
  }

  bool get _hasNotificationChanges =>
      _notificationTime != _initialNotificationTime;

  bool get _hasChanges => _hasKeywordChanges || _hasNotificationChanges;

  void _handleNotificationTimeChange(String value) {
    setState(() {
      _notificationTime = value;
    });
  }

  Future<void> _handleAddKeyword(String keyword) async {
    if (_draftKeywords
        .any((existing) => existing.toLowerCase() == keyword.toLowerCase())) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('이미 등록된 키워드입니다'),
            duration: Duration(seconds: 2),
          ),
        );
      }
      return;
    }

    if (_draftKeywords.length >= 3) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('키워드는 최대 3개까지 등록할 수 있습니다'),
            duration: Duration(seconds: 2),
          ),
        );
      }
      return;
    }

    setState(() {
      _draftKeywords = [..._draftKeywords, keyword];
      _hasManualKeywordEdits = true;
    });
  }

  void _handleRemoveKeyword(String keyword) {
    setState(() {
      _draftKeywords = _draftKeywords.where((k) => k != keyword).toList();
      _hasManualKeywordEdits = true;
    });
  }

  Future<void> _saveChanges() async {
    if (!_hasChanges || _isSaving) {
      return;
    }

    setState(() {
      _isSaving = true;
    });

    final messenger = ScaffoldMessenger.of(context);
    try {
      final currentKeywordTexts = _initialKeywords.map((k) => k.text).toList();
      final keywordsToAdd = _draftKeywords
          .where((keyword) => !currentKeywordTexts.contains(keyword))
          .toList();
      final keywordsToRemove = _initialKeywords
          .where((keyword) => !_draftKeywords.contains(keyword.text))
          .toList();

      for (final keyword in keywordsToRemove) {
        await _apiService.deleteKeyword(keyword.id);
      }

      for (final keyword in keywordsToAdd) {
        await _apiService.createKeyword(keyword);
      }

      await _apiService.updatePreferences(
        notificationTimeHour: int.parse(_notificationTime),
      );

      await ref.read(keywordProvider.notifier).loadKeywords();

      setState(() {
        _initialNotificationTime = _notificationTime;
        _hasManualKeywordEdits = false;
      });

      messenger.showSnackBar(
        const SnackBar(
          content: Text('설정이 저장되었습니다'),
          duration: Duration(seconds: 2),
        ),
      );
    } catch (e) {
      setState(() {
        _isSaving = false;
      });
      messenger.showSnackBar(
        SnackBar(
          content: Text('설정 저장에 실패했습니다: $e'),
          duration: const Duration(seconds: 3),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final topPadding = max(16.0, Responsive.getPadding(context) * 0.6);
    
    // 키워드 변경 감지 (build 메서드 내에서만 ref.listen 사용 가능)
    ref.listen<List<Keyword>>(keywordProvider, (previous, next) {
      if (!mounted) {
        return;
      }
      if (_isSaving) {
        setState(() {
          _initialKeywords = List<Keyword>.from(next);
          _draftKeywords = next.map((k) => k.text).toList();
          _hasManualKeywordEdits = false;
          _isSaving = false;
        });
        return;
      }
      if (!_hasManualKeywordEdits || !_hasInitializedKeywords) {
        _syncKeywordsFromProvider(next);
      }
    });

    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            // 커스텀 헤더 - 전체 너비
            Container(
              height: 57,
              width: double.infinity,
              decoration: const BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Color.fromRGBO(0, 0, 0, 0.25),
                    blurRadius: 4,
                    offset: Offset(0, 4),
                  ),
                ],
                borderRadius: BorderRadius.only(
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
                    child: SizedBox(
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
                  const Positioned(
                    left: 0,
                    right: 0,
                    top: 16.5,
                    child: Center(
                      child: Text(
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
                  ),
                ],
              ),
            ),
            // 본문 - 중앙 정렬
            Expanded(
              child: Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    maxWidth: Responsive.getMaxContentWidth(context),
                  ),
                  child: SingleChildScrollView(
                    padding: Responsive.getHorizontalPadding(context).copyWith(
                      top: topPadding,
                      bottom: 0,
                    ),
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
                                    height:
                                        1.43, // leading 20px / fontSize 14px
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
                                await _handleAddKeyword(keyword);
                              },
                              disabled: _draftKeywords.length >= 3 || _isSaving,
                            ),
                          ],
                        ),
                        const SizedBox(height: 24),
                        // 등록된 키워드
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '등록된 키워드 (${_draftKeywords.length}/3)',
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.normal,
                                color: Color(0xFF364153),
                                fontFamily: 'Noto Sans KR',
                              ),
                            ),
                            const SizedBox(height: 12),
                            KeywordList(
                              keywords: _draftKeywords,
                              onRemoveKeyword:
                                  _isSaving ? (_) {} : _handleRemoveKeyword,
                            ),
                          ],
                        ),
                        const SizedBox(height: 24),
                        // 구분선
                        Container(
                          height: 1,
                          color: const Color.fromRGBO(0, 0, 0, 0.1),
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
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 13),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFF3F3F5),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: DropdownButtonHideUnderline(
                                    child: DropdownButton<String>(
                                      value: _notificationTime,
                                      isExpanded: true,
                                      icon: const Icon(
                                          Icons.keyboard_arrow_down,
                                          size: 16),
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
                                      onChanged: _isLoadingPreferences
                                          ? null
                                          : (value) {
                                              if (value != null) {
                                                _handleNotificationTimeChange(
                                                    value);
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
                          color: const Color.fromRGBO(0, 0, 0, 0.1),
                        ),
                        const SizedBox(height: 16),
                        // 저장 버튼
                        SizedBox(
                          width: double.infinity,
                          height: 36,
                          child: ElevatedButton(
                            onPressed:
                                _hasChanges && !_isSaving ? _saveChanges : null,
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 16, vertical: 8),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ).copyWith(
                              backgroundColor:
                                  WidgetStateProperty.resolveWith((states) {
                                if (states.contains(WidgetState.disabled)) {
                                  return const Color(0xFFE5E7EB);
                                }
                                return const Color(0xFF2563EB);
                              }),
                              foregroundColor:
                                  WidgetStateProperty.resolveWith((states) {
                                if (states.contains(WidgetState.disabled)) {
                                  return const Color(0xFF9CA3AF);
                                }
                                return Colors.white;
                              }),
                            ),
                            child: _isSaving
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(
                                          Colors.white),
                                    ),
                                  )
                                : const Text(
                                    '저장',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w500,
                                      fontFamily: 'Noto Sans KR',
                                      height: 1.43,
                                    ),
                                  ),
                          ),
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
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 16, vertical: 8),
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
              ),
            )
          ],
        ),
      ),
    );
  }
}
