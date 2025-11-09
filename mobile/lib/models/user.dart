class User {
  final String id;
  final String email;
  final String locale;

  User({
    required this.id,
    required this.email,
    required this.locale,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      email: json['email'] as String,
      locale: json['locale'] as String? ?? 'ko-KR',
    );
  }
}




