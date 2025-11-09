import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user.dart';
import '../services/api_service.dart';

class AuthState {
  final User? user;
  final bool isLoading;
  final String? error;

  AuthState({
    this.user,
    this.isLoading = false,
    this.error,
  });

  bool get isAuthenticated => user != null;

  AuthState copyWith({
    User? user,
    bool? isLoading,
    String? error,
  }) {
    return AuthState(
      user: user ?? this.user,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiService _apiService;

  AuthNotifier(this._apiService) : super(AuthState());

  Future<void> signUp(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final token = await _apiService.signUp(email, password);
      final user = await _apiService.getCurrentUser(token);
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> signIn(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final token = await _apiService.signIn(email, password);
      final user = await _apiService.getCurrentUser(token);
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) {
      String errorMessage = '로그인에 실패했습니다';
      if (e.toString().contains('422')) {
        errorMessage = '입력 정보를 확인해주세요';
      } else if (e.toString().contains('401')) {
        errorMessage = '이메일 또는 비밀번호가 올바르지 않습니다';
      } else if (e.toString().contains('connection')) {
        errorMessage = '서버에 연결할 수 없습니다';
      }
      state = state.copyWith(isLoading: false, error: errorMessage);
    }
  }

  void signOut() {
    _apiService.clearToken();
    state = AuthState();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ApiService());
});


