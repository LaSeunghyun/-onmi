import 'package:flutter/material.dart';

class KeywordList extends StatelessWidget {
  final List<String> keywords;
  final Function(String) onRemoveKeyword;

  const KeywordList({
    super.key,
    required this.keywords,
    required this.onRemoveKeyword,
  });

  @override
  Widget build(BuildContext context) {
    if (keywords.isEmpty) {
      return const SizedBox.shrink();
    }

    return Wrap(
      spacing: 8,
      runSpacing: 0,
      children: keywords.map((keyword) {
        return Container(
          height: 30,
          padding: const EdgeInsets.symmetric(horizontal: 1, vertical: 1),
          decoration: BoxDecoration(
            color: const Color(0xFFF3F4F6),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 9),
                child: Text(
                  keyword,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFF030213),
                    fontFamily: 'Noto Sans KR',
                    height: 1.33, // leading 16px / fontSize 12px
                  ),
                ),
              ),
              const SizedBox(width: 10),
              GestureDetector(
                onTap: () => onRemoveKeyword(keyword),
                child: Container(
                  width: 12,
                  height: 12,
                  padding: const EdgeInsets.all(2),
                  child: const Icon(
                    Icons.close,
                    size: 8,
                    color: Color(0xFF030213),
                  ),
                ),
              ),
              const SizedBox(width: 1),
            ],
          ),
        );
      }).toList(),
    );
  }
}



