import 'package:hive/hive.dart';

part 'keyword.g.dart';

@HiveType(typeId: 0)
class Keyword {
  @HiveField(0)
  final String id;
  
  @HiveField(1)
  final String text;
  
  @HiveField(2)
  final String status;
  
  @HiveField(3)
  final String notifyLevel;
  
  @HiveField(4)
  final bool autoShareEnabled;
  
  @HiveField(5)
  final List<String> autoShareChannels;
  
  @HiveField(6)
  final DateTime createdAt;
  
  @HiveField(7)
  final DateTime? lastCrawledAt;

  Keyword({
    required this.id,
    required this.text,
    required this.status,
    required this.notifyLevel,
    required this.autoShareEnabled,
    required this.autoShareChannels,
    required this.createdAt,
    this.lastCrawledAt,
  });

  static DateTime? _parseDateTime(dynamic value) {
    if (value == null) return null;
    try {
      if (value is String) {
        return DateTime.parse(value);
      } else if (value is DateTime) {
        return value;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  factory Keyword.fromJson(Map<String, dynamic> json) {
    final createdAt = _parseDateTime(json['created_at'] ?? json['createdAt']);
    if (createdAt == null) {
      throw FormatException('created_at 필드가 필수입니다.');
    }
    
    return Keyword(
      id: json['id'] as String,
      text: json['text'] as String,
      status: json['status'] as String,
      notifyLevel: json['notify_level'] ?? json['notifyLevel'] as String,
      autoShareEnabled: (json['auto_share_enabled'] ?? json['autoShareEnabled']) as bool? ?? false,
      autoShareChannels: (json['auto_share_channels'] ?? json['autoShareChannels'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      createdAt: createdAt,
      lastCrawledAt: _parseDateTime(json['last_crawled_at'] ?? json['lastCrawledAt']),
    );
  }
}

