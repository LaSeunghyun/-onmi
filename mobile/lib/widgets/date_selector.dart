import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class DateSelector extends StatelessWidget {
  final DateTime selectedDate;
  final Function(DateTime) onSelectDate;
  final List<DateTime> availableDates;

  const DateSelector({
    super.key,
    required this.selectedDate,
    required this.onSelectDate,
    this.availableDates = const [],
  });

  DateTime _normalizeDate(DateTime date) =>
      DateTime(date.year, date.month, date.day);

  List<DateTime> get _sortedAvailableDates {
    final normalized = availableDates
        .map(_normalizeDate)
        .toSet()
        .toList()
      ..sort();
    return normalized;
  }

  bool _isDateAvailable(DateTime date) {
    if (availableDates.isEmpty) {
      return _isSameDay(date, selectedDate);
    }
    final normalized = _normalizeDate(date);
    return _sortedAvailableDates.any((d) => _isSameDay(d, normalized));
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  DateTime? _findAdjacentDate({required bool isPrevious}) {
    if (availableDates.isEmpty) {
      return null;
    }
    final normalizedSelected = _normalizeDate(selectedDate);
    final sortedDates = _sortedAvailableDates;
    if (isPrevious) {
      for (var i = sortedDates.length - 1; i >= 0; i--) {
        final candidate = sortedDates[i];
        if (candidate.isBefore(normalizedSelected)) {
          return candidate;
        }
      }
    } else {
      for (final candidate in sortedDates) {
        if (candidate.isAfter(normalizedSelected)) {
          return candidate;
        }
      }
    }
    return null;
  }

  bool get isToday {
    final now = DateTime.now();
    return selectedDate.year == now.year &&
        selectedDate.month == now.month &&
        selectedDate.day == now.day;
  }

  void _goToPreviousDay() {
    final newDate = _findAdjacentDate(isPrevious: true);
    if (newDate != null) {
      onSelectDate(newDate);
    }
  }

  void _goToNextDay() {
    final newDate = _findAdjacentDate(isPrevious: false);
    if (newDate != null) {
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
      selectableDayPredicate: (day) => _isDateAvailable(day),
    );
    if (picked != null && _isDateAvailable(picked)) {
      onSelectDate(picked);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('yyyy. MM. dd(E)', 'ko_KR');
    final dateStr = dateFormat.format(selectedDate);
    final hasPrevious = _findAdjacentDate(isPrevious: true) != null;
    final hasNext = _findAdjacentDate(isPrevious: false) != null;

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
              border: Border.all(
                color: hasPrevious
                    ? Colors.black.withOpacity(0.1)
                    : Colors.black.withOpacity(0.1 * 0.5),
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: hasPrevious ? _goToPreviousDay : null,
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
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 13),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.calendar_today,
                          size: 16,
                          color: Color(0xFF030213),
                        ),
                        Expanded(
                          child: Text(
                            dateStr,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: Color(0xFF030213),
                              fontFamily: 'Noto Sans KR',
                              height: 1.43, // leading 20px / fontSize 14px
                            ),
                          ),
                        ),
                        if (isToday)
                          const Text(
                            '오늘',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: Color(0xFFFF6B35),
                              fontFamily: 'Noto Sans KR',
                              height: 1.43,
                            ),
                          )
                        else
                          const SizedBox(width: 32), // "오늘" 텍스트가 없을 때 공간 확보
                      ],
                    ),
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
                color: hasNext
                    ? Colors.black.withOpacity(0.1)
                    : Colors.black.withOpacity(0.1 * 0.5),
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: hasNext ? _goToNextDay : null,
                borderRadius: BorderRadius.circular(8),
                child: Center(
                  child: Icon(
                    Icons.chevron_right,
                    size: 16,
                    color: hasNext
                        ? const Color(0xFF030213)
                        : Colors.black.withOpacity(0.5),
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


