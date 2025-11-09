import 'package:dio/dio.dart';
import '../models/user.dart';
import '../models/keyword.dart';
import '../models/article.dart';

class ApiService {
  final Dio _dio;
  String? _token;

  ApiService() : _dio = Dio(
    BaseOptions(
      // 개발 환경: 환경에 따라 변경 필요
      // Android 에뮬레이터: http://10.0.2.2:8000
      // iOS 시뮬레이터: http://localhost:8000
      // 실제 기기: 컴퓨터의 IP 주소 (예: http://192.168.1.100:8000)
      baseUrl: const String.fromEnvironment(
        'API_BASE_URL',
        defaultValue: 'http://localhost:8000',
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
        print('[API Request] ${options.method} ${options.uri}');
        return handler.next(options);
      },
      onResponse: (response, handler) {
        print('[API Response] ${response.statusCode} ${response.requestOptions.uri}');
        return handler.next(response);
      },
      onError: (error, handler) {
        print('[API Error] ${error.type} ${error.requestOptions.uri}');
        print('[API Error] Request Data: ${error.requestOptions.data}');
        if (error.response != null) {
          print('[API Error] Status: ${error.response?.statusCode}');
          print('[API Error] Response Body: ${error.response?.data}');
          // 422 오류의 경우 상세 정보 출력
          if (error.response?.statusCode == 422) {
            final detail = error.response?.data;
            if (detail is Map && detail['detail'] != null) {
              print('[API Error] Validation Details: ${detail['detail']}');
            }
          }
        } else {
          print('[API Error] Message: ${error.message}');
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
}

