import 'package:flutter/material.dart';

class KeywordInput extends StatefulWidget {
  final Function(String) onAddKeyword;
  final bool disabled;

  const KeywordInput({
    super.key,
    required this.onAddKeyword,
    this.disabled = false,
  });

  @override
  State<KeywordInput> createState() => _KeywordInputState();
}

class _KeywordInputState extends State<KeywordInput> {
  final _controller = TextEditingController();

  void _handleSubmit() {
    final keyword = _controller.text.trim();
    if (keyword.isNotEmpty && !widget.disabled) {
      widget.onAddKeyword(keyword);
      _controller.clear();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Container(
            height: 36,
            decoration: BoxDecoration(
              color: const Color(0xFFF3F3F5).withOpacity(widget.disabled ? 0.5 : 1.0),
              borderRadius: BorderRadius.circular(8),
            ),
            child: TextField(
              controller: _controller,
              enabled: !widget.disabled,
              style: const TextStyle(
                fontSize: 14,
                color: Color(0xFF717182),
                fontFamily: 'Noto Sans KR',
              ),
              decoration: InputDecoration(
                hintText: '최대 3개까지 등록 가능',
                hintStyle: const TextStyle(
                  fontSize: 14,
                  color: Color(0xFF717182),
                  fontFamily: 'Noto Sans KR',
                ),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 4,
                ),
              ),
              onSubmitted: (_) => _handleSubmit(),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: const Color(0xFFFF6B35).withOpacity(widget.disabled ? 0.5 : 1.0),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: widget.disabled ? null : _handleSubmit,
              borderRadius: BorderRadius.circular(8),
              child: const Center(
                child: Icon(
                  Icons.add,
                  size: 16,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}



