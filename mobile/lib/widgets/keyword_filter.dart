import 'package:flutter/material.dart';

class KeywordFilter extends StatelessWidget {
  final List<String> keywords;
  final String? selectedKeyword;
  final Function(String?) onSelectKeyword;
  final Map<String, int?> issueCounts;
  final int? totalCount;

  const KeywordFilter({
    super.key,
    required this.keywords,
    required this.selectedKeyword,
    required this.onSelectKeyword,
    required this.issueCounts,
    this.totalCount,
  });

  int? get totalIssues {
    if (totalCount != null) {
      return totalCount;
    }
    if (issueCounts.values.any((count) => count == null)) {
      return null;
    }
    return issueCounts.values.fold<int>(
      0,
      (sum, count) => sum + (count ?? 0),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _FilterChip(
            label: '전체',
            count: totalIssues,
            isSelected: selectedKeyword == null,
            onTap: () => onSelectKeyword(null),
          ),
          const SizedBox(width: 8),
          ...keywords.map((keyword) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: _FilterChip(
                  label: keyword,
                  count: issueCounts[keyword],
                  isSelected: selectedKeyword == keyword,
                  onTap: () => onSelectKeyword(keyword),
                ),
              )),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final int? count;
  final bool isSelected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.count,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        height: 32,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFFFF6B35) : Colors.white,
          border: Border.all(
            color: isSelected
                ? const Color(0xFFFF6B35)
                : Colors.black.withOpacity(0.1),
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : const Color(0xFF030213),
                fontWeight: FontWeight.w500,
                fontSize: 14,
                fontFamily: 'Noto Sans KR',
              ),
            ),
            const SizedBox(width: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: BoxDecoration(
                color: isSelected ? Colors.white : const Color(0xFFF3F4F6),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                count?.toString() ?? '--',
                style: TextStyle(
                  color: isSelected
                      ? const Color(0xFF364153)
                      : const Color(0xFF4A5565),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  fontFamily: 'Noto Sans KR',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
