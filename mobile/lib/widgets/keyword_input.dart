import 'package:flutter/material.dart';

class KeywordInput extends StatefulWidget {
  final Future<void> Function(String) onAddKeyword;
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
  final _focusNode = FocusNode();
  bool _isSubmitting = false;

  Future<void> _handleSubmit() async {
    final keyword = _controller.text.trim();
    if (keyword.isEmpty || widget.disabled || _isSubmitting) {
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    try {
      await widget.onAddKeyword(keyword);
      if (mounted) {
        _controller.clear();
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
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
              color: const Color(0xFFF3F3F5).withOpacity(
                widget.disabled || _isSubmitting ? 0.5 : 1.0,
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: TextField(
              controller: _controller,
              focusNode: _focusNode,
              enabled: !widget.disabled && !_isSubmitting,
              keyboardType: TextInputType.text,
              textInputAction: TextInputAction.done,
              enableInteractiveSelection: true,
              enableSuggestions: true,
              enableIMEPersonalizedLearning: true,
              autocorrect: false,
              style: const TextStyle(
                fontSize: 14,
                color: Color(0xFF717182),
                fontFamily: 'Noto Sans KR',
              ),
              decoration: InputDecoration(
                hintText: '최대 3개까지 등록 가능',
                hintStyle: const TextStyle(
                  fontSize: 14,
                  color: const Color(0xFF717182),
                  fontFamily: 'Noto Sans KR',
                ),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 4,
                ),
              ),
              onEditingComplete: () {
                // 한글 조합 완료 후 포커스 해제 및 제출
                _focusNode.unfocus();
                _handleSubmit();
              },
            ),
          ),
        ),
        const SizedBox(width: 8),
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: const Color(0xFFFF6B35).withOpacity(
              widget.disabled || _isSubmitting ? 0.5 : 1.0,
            ),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: widget.disabled || _isSubmitting ? null : _handleSubmit,
              borderRadius: BorderRadius.circular(8),
              child: Center(
                child: _isSubmitting
                    ? const SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : const Icon(
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



