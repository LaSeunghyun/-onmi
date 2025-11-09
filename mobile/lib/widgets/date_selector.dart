import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class DateSelector extends StatelessWidget {
  final DateTime selectedDate;
  final Function(DateTime) onSelectDate;

  const DateSelector({
    super.key,
    required this.selectedDate,
    required this.onSelectDate,
  });

  bool get isToday {
    final now = DateTime.now();
    return selectedDate.year == now.year &&
        selectedDate.month == now.month &&
        selectedDate.day == now.day;
  }

  void _goToPreviousDay() {
    final newDate = selectedDate.subtract(const Duration(days: 1));
    onSelectDate(newDate);
  }

  void _goToNextDay() {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final newDate = selectedDate.add(const Duration(days: 1));
    if (newDate.isBefore(today) || newDate.isAtSameMomentAs(today)) {
      onSelectDate(newDate);
    }
  }

  Future<void> _showDatePicker(BuildContext context) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: selectedDate,
      firstDate: DateTime(2000),
      lastDate: now,
      locale: const Locale('ko', 'KR'),
    );
    if (picked != null) {
      onSelectDate(picked);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('yyyy. MM. dd(E)', 'ko_KR');
    final dateStr = dateFormat.format(selectedDate);

    return Container(
      height: 36,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // 이전 날짜 버튼
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: Colors.black.withOpacity(0.1)),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: _goToPreviousDay,
                borderRadius: BorderRadius.circular(8),
                child: const Center(
                  child: Icon(
                    Icons.chevron_left,
                    size: 16,
                    color: Color(0xFF030213),
                  ),
                ),
              ),
            ),
          ),
          // 날짜 선택 버튼
          Expanded(
            child: Container(
              height: 36,
              margin: const EdgeInsets.symmetric(horizontal: 8),
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: Colors.black.withOpacity(0.1)),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => _showDatePicker(context),
                  borderRadius: BorderRadius.circular(8),
                  child: Stack(
                    children: [
                      // 캘린더 아이콘
                      Positioned(
                        left: 13,
                        top: 10,
                        child: const Icon(
                          Icons.calendar_today,
                          size: 16,
                          color: Color(0xFF030213),
                        ),
                      ),
                      // 날짜 텍스트
                      Positioned(
                        left: 45,
                        top: 6,
                        child: Text(
                          dateStr,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: Color(0xFF030213),
                            fontFamily: 'Noto Sans KR',
                            height: 1.43, // leading 20px / fontSize 14px
                          ),
                        ),
                      ),
                      // "오늘" 텍스트 (오늘인 경우)
                      if (isToday)
                        Positioned(
                          left: 163.91,
                          top: 8,
                          child: const Text(
                            '오늘',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: Color(0xFFFF6B35),
                              fontFamily: 'Noto Sans KR',
                              height: 1.43,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          // 다음 날짜 버튼 (오늘인 경우 비활성화)
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(
                color: isToday 
                    ? Colors.black.withOpacity(0.1 * 0.5)
                    : Colors.black.withOpacity(0.1),
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: isToday ? null : _goToNextDay,
                borderRadius: BorderRadius.circular(8),
                child: Center(
                  child: Icon(
                    Icons.chevron_right,
                    size: 16,
                    color: isToday 
                        ? Colors.black.withOpacity(0.5)
                        : const Color(0xFF030213),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}


