/// 요약 섹션을 표현하는 데이터 모델.
class SummarySection {
  /// 섹션 제목 (볼드 처리된 헤더와 매핑된다).
  final String title;

  /// 섹션 본문을 구성하는 문장 또는 불릿 라인 목록.
  final List<String> lines;

  const SummarySection({
    required this.title,
    required this.lines,
  });

  /// 본문이 비어 있는 섹션인지 여부.
  bool get isEmpty => lines.isEmpty || lines.every((line) => line.trim().isEmpty);
}

final RegExp _headingPattern = RegExp(r'\*\*(.+?)\*\*');
final RegExp _leadingBulletPattern = RegExp(r'^[\-\•\·\s]+');

/// Gemini가 반환한 원시 요약 텍스트를 섹션 단위로 파싱한다.
///
/// - 볼드(`**제목**`)로 표시된 구간을 제목으로 간주하고, 다음 제목 전까지의
///   텍스트를 섹션 본문으로 묶는다.
/// - 볼드 제목이 하나도 없는 경우 전체 텍스트를 단일 섹션으로 반환한다.
/// - 각 본문은 줄 단위로 분리하며, 맨 앞의 불릿(`-`, `•`, `·`)과 공백을 제거한 뒤
///   깨끗한 라인 목록으로 정리한다.
List<SummarySection> parseSummarySections(
  String rawText, {
  String fallbackTitle = '전체 요약',
}) {
  final normalized = rawText.replaceAll('\r\n', '\n').trim();
  if (normalized.isEmpty) {
    return const [];
  }

  final matches = _headingPattern.allMatches(normalized).toList();
  if (matches.isEmpty) {
    return [
      SummarySection(
        title: fallbackTitle,
        lines: _sanitizeLines(normalized.split('\n')),
      ),
    ];
  }

  final sections = <SummarySection>[];

  // 첫 번째 제목 이전의 텍스트가 있다면 fallback 섹션으로 추가한다.
  final firstMatch = matches.first;
  if (firstMatch.start > 0) {
    final preface = normalized.substring(0, firstMatch.start).trim();
    if (preface.isNotEmpty) {
      sections.add(
        SummarySection(
          title: fallbackTitle,
          lines: _sanitizeLines(preface.split('\n')),
        ),
      );
    }
  }

  for (var index = 0; index < matches.length; index++) {
    final match = matches[index];
    final title = match.group(1)?.trim() ?? fallbackTitle;
    final contentStart = match.end;
    final contentEnd =
        index + 1 < matches.length ? matches[index + 1].start : normalized.length;
    final body = normalized.substring(contentStart, contentEnd).trim();
    final lines = _sanitizeLines(body.split('\n'));

    sections.add(
      SummarySection(
        title: title.isEmpty ? fallbackTitle : title,
        lines: lines,
      ),
    );
  }

  return sections.where((section) => !section.isEmpty).toList();
}

List<String> _sanitizeLines(List<String> lines) {
  return lines
      .map((line) => line.trim())
      .map((line) => line.replaceFirst(_leadingBulletPattern, ''))
      .map((line) => line.trim())
      .where((line) => line.isNotEmpty)
      .toList();
}

