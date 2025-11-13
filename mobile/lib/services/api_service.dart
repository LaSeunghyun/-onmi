import 'package:dio/dio.dart';
import 'package:intl/intl.dart';
import '../models/user.dart';
import '../models/keyword.dart';
import '../models/article.dart';
import '../models/token_usage.dart';
import '../models/summary.dart';
import '../models/cse_query_usage.dart';

// 싱글톤 ApiService 인스턴스
ApiService? _apiServiceInstance;

ApiService getApiService() {
  _apiServiceInstance ??= ApiService._internal();
  return _apiServiceInstance!;
}

class ApiService {
  final Dio _dio;
  String? _token;

  ApiService._internal() : _dio = Dio(
    BaseOptions(
      // 개발 환경: 환경에 따라 변경 필요
      // Android 에뮬레이터: http://10.0.2.2:8000
      // iOS 시뮬레이터: http://localhost:8000
      // 실제 기기: 컴퓨터의 IP 주소 (예: http://192.168.1.100:8000)
      baseUrl: const String.fromEnvironment(
        'API_BASE_URL',
        defaultValue: 'http://10.0.2.2:8000', // Android 에뮬레이터용
      ),
      headers: {'Content-Type': 'application/json'},
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ),
  ) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_token != null) {
          options.headers['Authorization'] = 'Bearer $_token';
        }
        final timestamp = DateFormat('HH:mm:ss.SSS').format(DateTime.now());
        options.extra['requestStart'] = DateTime.now().microsecondsSinceEpoch;
        print('[$timestamp] [API Request] ${options.method} ${options.uri}');
        return handler.next(options);
      },
      onResponse: (response, handler) {
        final timestamp = DateFormat('HH:mm:ss.SSS').format(DateTime.now());
        final startMicros =
            response.requestOptions.extra['requestStart'] as int? ?? 0;
        final elapsedMs = startMicros == 0
            ? null
            : (DateTime.now().microsecondsSinceEpoch - startMicros) / 1000.0;
        final durationMessage =
            elapsedMs != null ? ' (${elapsedMs.toStringAsFixed(1)} ms)' : '';
        print(
          '[$timestamp] [API Response] ${response.statusCode} ${response.requestOptions.uri}$durationMessage',
        );
        return handler.next(response);
      },
      onError: (error, handler) {
        final timestamp = DateFormat('HH:mm:ss.SSS').format(DateTime.now());
        final startMicros =
            error.requestOptions.extra['requestStart'] as int? ?? 0;
        final elapsedMs = startMicros == 0
            ? null
            : (DateTime.now().microsecondsSinceEpoch - startMicros) / 1000.0;
        final durationMessage =
            elapsedMs != null ? ' (${elapsedMs.toStringAsFixed(1)} ms)' : '';
        print(
          '[$timestamp] [API Error] ${error.type} ${error.requestOptions.uri}$durationMessage',
        );
        print('[$timestamp] [API Error] Request Data: ${error.requestOptions.data}');
        if (error.response != null) {
          print('[$timestamp] [API Error] Status: ${error.response?.statusCode}');
          print('[$timestamp] [API Error] Response Body: ${error.response?.data}');
          // 422 오류의 경우 상세 정보 출력
          if (error.response?.statusCode == 422) {
            final detail = error.response?.data;
            if (detail is Map && detail['detail'] != null) {
              print('[$timestamp] [API Error] Validation Details: ${detail['detail']}');
            }
          }
        } else {
          print('[$timestamp] [API Error] Message: ${error.message}');
        }
        return handler.next(error);
      },
    ));
  }

  void setToken(String token) {
    _token = token;
  }

  void clearToken() {
    _token = null;
  }

  Future<String> signUp(String email, String password) async {
    final response = await _dio.post('/auth/signup', data: {
      'email': email,
      'password': password,
    });
    final token = response.data['access_token'] as String;
    setToken(token);
    return token;
  }

  Future<String> signIn(String email, String password) async {
    // JSON 형식의 로그인 엔드포인트 사용 (더 간단하고 안정적)
    final response = await _dio.post('/auth/signin-json', data: {
      'email': email,
      'password': password,
    });
    final token = response.data['access_token'] as String;
    setToken(token);
    return token;
  }

  Future<User> getCurrentUser(String token) async {
    setToken(token);
    final response = await _dio.get('/auth/me');
    return User.fromJson(response.data);
  }

  Future<List<Keyword>> getKeywords() async {
    final response = await _dio.get('/keywords');
    return (response.data as List)
        .map((json) => Keyword.fromJson(json))
        .toList();
  }

  Future<Keyword> createKeyword(String text) async {
    final response = await _dio.post('/keywords', data: {'text': text});
    return Keyword.fromJson(response.data);
  }

  Future<void> deleteKeyword(String id) async {
    await _dio.delete('/keywords/$id');
  }

  Future<FeedResponse> getFeed({
    String? keywordId,
    String? filterSentiment,
    String sort = 'recent',
    int page = 1,
    int pageSize = 20,
  }) async {
    final queryParams = {
      'sort': sort,
      'page': page,
      'page_size': pageSize,
      if (keywordId != null) 'keyword_id': keywordId,
      if (filterSentiment != null) 'filter_sentiment': filterSentiment,
    };
    final response = await _dio.get('/feed', queryParameters: queryParams);
    return FeedResponse.fromJson(response.data);
  }

  Future<Article> getArticle(String id) async {
    final response = await _dio.get('/articles/$id');
    return Article.fromJson(response.data);
  }

  Future<void> submitFeedback(String articleId, String label, {String? comment}) async {
    await _dio.post('/articles/$articleId/feedback', data: {
      'label': label,
      if (comment != null) 'comment': comment,
    });
  }

  Future<void> shareArticle(String articleId, String channel, {String? recipient}) async {
    await _dio.post('/share/articles/$articleId', data: {
      'channel': channel,
      if (recipient != null) 'recipient': recipient,
    });
  }

  Future<TokenUsage> getTokenUsage() async {
    final response = await _dio.get('/stats/token-usage');
    return TokenUsage.fromJson(response.data);
  }

  Future<CseQueryUsage> getCseQueryUsage({String? keywordId}) async {
    final query = <String, dynamic>{};
    if (keywordId != null) {
      query['keyword_id'] = keywordId;
    }
    final response = await _dio.get(
      '/stats/cse-query-usage',
      queryParameters: query.isEmpty ? null : query,
    );
    return CseQueryUsage.fromJson(response.data as Map<String, dynamic>);
  }

  Future<String> signInWithGoogle(String idToken) async {
    final response = await _dio.post('/auth/google/token', data: {
      'id_token': idToken,
    });
    final token = response.data['access_token'] as String;
    setToken(token);
    return token;
  }

  Future<Map<String, dynamic>> getPreferences() async {
    final response = await _dio.get('/preferences');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updatePreferences({
    int? notificationTimeHour,
  }) async {
    final data = <String, dynamic>{};
    if (notificationTimeHour != null) {
      data['notification_time_hour'] = notificationTimeHour;
    }
    final response = await _dio.put('/preferences', data: data);
    return response.data as Map<String, dynamic>;
  }

  /// 일일 요약 조회
  Future<Summary> getDailySummary({String? date}) async {
    final queryParameters = <String, dynamic>{};
    if (date != null && date.isNotEmpty) {
      queryParameters['date'] = date;
    }
    final response = await _dio.get(
      '/summaries/daily',
      queryParameters: queryParameters.isEmpty ? null : queryParameters,
    );
    return Summary.fromJson(response.data);
  }

  /// 키워드별 요약 조회
  Future<Summary> getKeywordSummary(String keywordId, {String? date}) async {
    final queryParameters = <String, dynamic>{};
    if (date != null && date.isNotEmpty) {
      queryParameters['date'] = date;
    }
    final response = await _dio.get(
      '/summaries/keywords/$keywordId',
      queryParameters: queryParameters.isEmpty ? null : queryParameters,
    );
    return Summary.fromJson(response.data);
  }

  /// 요약 피드백 제출
  Future<void> submitSummaryFeedback(
    String sessionId, {
    required int rating,
    String? comment,
  }) async {
    await _dio.post('/summaries/$sessionId/feedback', data: {
      'rating': rating,
      if (comment != null) 'comment': comment,
    });
  }
}
