import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _isSignUp = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;

    // 입력 검증
    if (email.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('이메일을 입력해주세요')),
      );
      return;
    }
    if (password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('비밀번호를 입력해주세요')),
      );
      return;
    }

    if (_isSignUp) {
      final confirmPassword = _confirmPasswordController.text;
      if (password != confirmPassword) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('비밀번호가 일치하지 않습니다')),
        );
        return;
      }
      await ref.read(authProvider.notifier).signUp(email, password);
    } else {
      await ref.read(authProvider.notifier).signIn(email, password);
    }

    if (mounted) {
      final authState = ref.read(authProvider);
      if (authState.error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(authState.error!)),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final cardHeight = _isSignUp ? 743.0 : 669.0;

    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFFF6B35),
              Color(0xFFFF8F5C),
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(vertical: 16.0),
              child: Center(
                child: Container(
                  width: 278,
                  height: cardHeight,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.1),
                      blurRadius: 20,
                      offset: const Offset(0, 10),
                    ),
                    BoxShadow(
                      color: Colors.black.withOpacity(0.06),
                      blurRadius: 8,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                padding: const EdgeInsets.fromLTRB(32, 32, 32, 32),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // #onmi 로고 및 타이틀
                    SizedBox(
                      height: 84,
                      width: 214,
                      child: Stack(
                        children: [
                          // #onmi 로고 - 정확한 위치 (left: 61.27px from card edge, 패딩 32px 고려)
                          Positioned(
                            left: 29.27, // 61.27 - 32 (카드 패딩)
                            top: 0,
                            child: Container(
                              height: 44,
                              width: 91.453,
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  begin: Alignment.topCenter,
                                  end: Alignment.bottomCenter,
                                  colors: [
                                    Color(0xFFFF6B35),
                                    Color(0xFFFF8F5C),
                                  ],
                                ),
                                borderRadius: BorderRadius.circular(33554400),
                              ),
                              child: Stack(
                                children: [
                                  // #onmi 텍스트 - 정확한 위치 (left: 16px from logo container, top: 7px)
                                  Positioned(
                                    left: 16,
                                    top: 7,
                                    child: SizedBox(
                                      height: 29,
                                      width: 59.453,
                                      child: const Center(
                                        child: Text(
                                          '#onmi',
                                          style: TextStyle(
                                            color: Colors.white,
                                            fontSize: 20,
                                            fontWeight: FontWeight.normal,
                                            fontFamily: 'Noto Sans KR',
                                            height: 1.4, // leading 28px / fontSize 20px
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          // 타이틀 텍스트 - 정확한 위치 (left: 0, top: 60px from card padding top)
                          const Positioned(
                            left: 0,
                            top: 60,
                            child: SizedBox(
                              width: 214,
                              height: 24,
                              child: Center(
                                child: Text(
                                  '오로지 나를 위한 서비스',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.normal,
                                    color: Color(0xFF101828),
                                    fontFamily: 'Noto Sans KR',
                                    height: 1.5, // leading 24px / fontSize 16px
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                    // 폼 영역 - Stack으로 absolute positioning 구현
                    SizedBox(
                      height: _isSignUp ? 310 : 236,
                      width: 214,
                      child: Stack(
                        children: [
                          // 이메일 입력 - top: 0
                          Positioned(
                            left: 0,
                            top: 0,
                            child: _EmailInput(
                              controller: _emailController,
                            ),
                          ),
                          // 비밀번호 입력 - top: 74px
                          Positioned(
                            left: 0,
                            top: 74,
                            child: _PasswordInput(
                              controller: _passwordController,
                            ),
                          ),
                          // 비밀번호 확인 입력 (회원가입 시) - top: 148px
                          if (_isSignUp)
                            Positioned(
                              left: 0,
                              top: 148,
                              child: _PasswordConfirmInput(
                                controller: _confirmPasswordController,
                              ),
                            ),
                          // 로그인/회원가입 버튼 - top: 148px (로그인) 또는 222px (회원가입)
                          Positioned(
                            left: 0,
                            top: _isSignUp ? 222 : 148,
                            child: _LoginButton(
                              isLoading: authState.isLoading,
                              isSignUp: _isSignUp,
                              onPressed: _handleSubmit,
                            ),
                          ),
                          // 회원가입/로그인 전환 링크 - 정확한 위치 (left: 22.47px from card edge, 패딩 고려)
                          Positioned(
                            left: 22.47, // 폼 컨테이너 내부에서의 위치 (패딩 고려 불필요)
                            top: _isSignUp ? 289 : 215,
                            child: SizedBox(
                              width: 169.063,
                              height: 20,
                              child: _SignUpLink(
                                isSignUp: _isSignUp,
                                onTap: () {
                                  setState(() {
                                    _isSignUp = !_isSignUp;
                                  });
                                },
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                    // 구분선 - 정확한 위치
                    SizedBox(
                      height: 16,
                      width: 214,
                      child: Stack(
                        children: [
                          // 구분선
                          Positioned(
                            left: 0,
                            top: 7.5,
                            child: Container(
                              width: 214,
                              height: 1,
                              color: const Color(0xFFE5E7EB),
                            ),
                          ),
                          // "또는" 텍스트 - 정확한 위치 (left: 87.95px from card edge, 패딩 고려)
                          Positioned(
                            left: 55.95, // 87.95 - 32 (카드 패딩)
                            top: 0,
                            child: Container(
                              height: 16,
                              width: 38.094,
                              color: Colors.white,
                              child: Stack(
                                children: [
                                  Positioned(
                                    left: 8,
                                    top: -2,
                                    child: const Text(
                                      '또는',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: Color(0xFF6A7282),
                                        fontFamily: 'Noto Sans KR',
                                        height: 1.33, // leading 16px / fontSize 12px
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                    // Google 로그인 버튼
                    SizedBox(
                      height: 92,
                      width: 214,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Google 로그인 버튼
                          SizedBox(
                            height: 48,
                            width: 214,
                            child: Stack(
                              children: [
                                Container(
                                  height: 48,
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    border: Border.all(color: const Color(0xFFD1D5DC)),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                ),
                                // Google 아이콘 - 정확한 위치 (left: 16.38px from card edge, 패딩 고려)
                                Positioned(
                                  left: 16.38, // 버튼 컨테이너 내부에서의 위치 (패딩 고려 불필요)
                                  top: 14,
                                  child: IgnorePointer(
                                    child: Container(
                                      width: 20,
                                      height: 20,
                                      child: Image.network(
                                        'https://www.figma.com/api/mcp/asset/f11ed94c-cfd9-4b38-9a57-c73c33823325',
                                        errorBuilder: (context, error, stackTrace) {
                                          return Container(
                                            decoration: BoxDecoration(
                                              color: Colors.white,
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: const Center(
                                              child: Text(
                                                'G',
                                                style: TextStyle(
                                                  color: Colors.blue,
                                                  fontWeight: FontWeight.bold,
                                                  fontSize: 14,
                                                ),
                                              ),
                                            ),
                                          );
                                        },
                                      ),
                                    ),
                                  ),
                                ),
                                // Google 로그인 텍스트 - 정확한 위치 (left: 52.38px from card edge, 패딩 고려)
                                Positioned(
                                  left: 52.38, // 버튼 컨테이너 내부에서의 위치 (패딩 고려 불필요)
                                  top: 12,
                                  child: IgnorePointer(
                                    child: authState.isLoading
                                        ? const SizedBox(
                                            height: 20,
                                            width: 20,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              valueColor: AlwaysStoppedAnimation<Color>(
                                                Color(0xFF364153),
                                              ),
                                            ),
                                          )
                                        : const Text(
                                            'Google 계정으로 로그인',
                                            style: TextStyle(
                                              fontSize: 14,
                                              fontWeight: FontWeight.w500,
                                              color: Color(0xFF364153),
                                              fontFamily: 'Noto Sans KR',
                                              height: 1.43, // leading 20px / fontSize 14px
                                            ),
                                          ),
                                  ),
                                ),
                                // 전체 버튼 클릭 영역
                                Positioned.fill(
                                  child: Material(
                                    color: Colors.transparent,
                                    child: InkWell(
                                      onTap: authState.isLoading ? null : () async {
                                        await ref.read(authProvider.notifier).signInWithGoogle();
                                        if (mounted) {
                                          final newAuthState = ref.read(authProvider);
                                          if (newAuthState.error != null) {
                                            ScaffoldMessenger.of(context).showSnackBar(
                                              SnackBar(content: Text(newAuthState.error!)),
                                            );
                                          }
                                        }
                                      },
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                          // 약관 동의 텍스트 - 정확한 위치 (중앙 정렬)
                          SizedBox(
                            height: 32,
                            width: 214,
                            child: Stack(
                              children: [
                                // 첫 번째 줄 - 정확한 위치 (left: 107.19px from card edge, 중앙 정렬)
                                Positioned(
                                  left: 107.19, // 컨테이너(214px)의 중앙 근처
                                  top: -2,
                                  child: Transform.translate(
                                    offset: const Offset(-50, 0), // translate-x-[-50%] - 텍스트 너비의 50%만큼 왼쪽으로 이동하여 중앙 정렬
                                    child: const Text(
                                      '로그인하면 서비스 이용약관 및',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: Color(0xFF99A1AF),
                                        fontFamily: 'Noto Sans KR',
                                        height: 1.33, // leading 16px / fontSize 12px
                                      ),
                                    ),
                                  ),
                                ),
                                // 두 번째 줄 - 정확한 위치 (left: 107.13px from card edge, 중앙 정렬)
                                Positioned(
                                  left: 107.13, // 컨테이너(214px)의 중앙 근처
                                  top: 14,
                                  child: Transform.translate(
                                    offset: const Offset(-50, 0), // translate-x-[-50%]
                                    child: const Text(
                                      '개인정보 처리방침에 동의하게 됩니다',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: Color(0xFF99A1AF),
                                        fontFamily: 'Noto Sans KR',
                                        height: 1.33,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    // 서비스 특징 - 정확한 위치
                    Container(
                      padding: const EdgeInsets.only(top: 17, bottom: 0),
                      decoration: const BoxDecoration(
                        border: Border(
                          top: BorderSide(
                            color: Color(0xFFF3F4F6),
                            width: 1,
                          ),
                        ),
                      ),
                      child: SizedBox(
                        height: 64,
                        width: 214,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _FeatureItem(
                              text: '최대 3개의 키워드 등록',
                            ),
                            const SizedBox(height: 8),
                            _FeatureItem(
                              text: '매일 아침 맞춤 리포트 제공',
                            ),
                            const SizedBox(height: 8),
                            _FeatureItem(
                              text: '긍정/부정/중립 이슈 분류',
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _EmailInput extends StatelessWidget {
  final TextEditingController controller;

  const _EmailInput({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '이메일',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: Color(0xFF030213),
            fontFamily: 'Noto Sans KR',
          ),
        ),
        const SizedBox(height: 8),
        Container(
          height: 36,
          width: 214,
          decoration: BoxDecoration(
            color: const Color(0xFFF3F3F5),
            borderRadius: BorderRadius.circular(8),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: TextField(
            controller: controller,
            style: const TextStyle(
              fontSize: 14,
              color: Color(0xFF717182),
              fontFamily: 'Noto Sans KR',
            ),
            decoration: const InputDecoration(
              hintText: 'email@example.com',
              hintStyle: TextStyle(
                color: Color(0xFF717182),
                fontSize: 14,
              ),
              border: InputBorder.none,
              contentPadding: EdgeInsets.zero,
            ),
            keyboardType: TextInputType.emailAddress,
          ),
        ),
      ],
    );
  }
}

class _PasswordInput extends StatelessWidget {
  final TextEditingController controller;

  const _PasswordInput({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '비밀번호',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: Color(0xFF030213),
            fontFamily: 'Noto Sans KR',
          ),
        ),
        const SizedBox(height: 8),
        Container(
          height: 36,
          width: 214,
          decoration: BoxDecoration(
            color: const Color(0xFFF3F3F5),
            borderRadius: BorderRadius.circular(8),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: TextField(
            controller: controller,
            obscureText: true,
            style: const TextStyle(
              fontSize: 14,
              color: Color(0xFF717182),
              fontFamily: 'Noto Sans KR',
            ),
            decoration: const InputDecoration(
              hintText: '••••••••',
              hintStyle: TextStyle(
                color: Color(0xFF717182),
                fontSize: 14,
              ),
              border: InputBorder.none,
              contentPadding: EdgeInsets.zero,
            ),
          ),
        ),
      ],
    );
  }
}

class _PasswordConfirmInput extends StatelessWidget {
  final TextEditingController controller;

  const _PasswordConfirmInput({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '비밀번호 확인',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: Color(0xFF030213),
            fontFamily: 'Noto Sans KR',
          ),
        ),
        const SizedBox(height: 8),
        Container(
          height: 36,
          width: 214,
          decoration: BoxDecoration(
            color: const Color(0xFFF3F3F5),
            borderRadius: BorderRadius.circular(8),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: TextField(
            controller: controller,
            obscureText: true,
            style: const TextStyle(
              fontSize: 14,
              color: Color(0xFF717182),
              fontFamily: 'Noto Sans KR',
            ),
            decoration: const InputDecoration(
              hintText: '••••••••',
              hintStyle: TextStyle(
                color: Color(0xFF717182),
                fontSize: 14,
              ),
              border: InputBorder.none,
              contentPadding: EdgeInsets.zero,
            ),
          ),
        ),
      ],
    );
  }
}

class _LoginButton extends StatelessWidget {
  final bool isLoading;
  final bool isSignUp;
  final VoidCallback onPressed;

  const _LoginButton({
    required this.isLoading,
    required this.isSignUp,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      width: 214,
      child: Stack(
        children: [
          // 버튼 배경 및 클릭 영역
          Positioned.fill(
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: isLoading ? null : onPressed,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Color(0xFFFF6B35),
                        Color(0xFFFF8F5C),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: isLoading
                      ? const Center(
                          child: SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                Colors.white,
                              ),
                            ),
                          ),
                        )
                      : null,
                ),
              ),
            ),
          ),
          // 버튼 텍스트 - 정확한 위치 (회원가입: left: 81.23px, 로그인: left: 87.67px from card edge, 패딩 고려)
          if (!isLoading)
            Positioned(
              left: isSignUp ? 49.23 : 55.67, // 회원가입: 81.23 - 32, 로그인: 87.67 - 32 (카드 패딩)
              top: 12,
              child: IgnorePointer(
                child: Text(
                  isSignUp ? '회원가입' : '로그인',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    fontFamily: 'Noto Sans KR',
                    height: 1.43, // leading 20px / fontSize 14px
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _SignUpLink extends StatelessWidget {
  final bool isSignUp;
  final VoidCallback onTap;

  const _SignUpLink({
    required this.isSignUp,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: onTap,
      style: TextButton.styleFrom(
        padding: EdgeInsets.zero,
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
      child: Text(
        isSignUp
            ? '이미 계정이 있으신가요? 로그인'
            : '계정이 없으신가요? 회원가입',
        style: const TextStyle(
          fontSize: 14,
          color: Color(0xFF4A5565),
          decoration: TextDecoration.underline,
          fontFamily: 'Noto Sans KR',
          height: 1.43,
        ),
      ),
    );
  }
}

class _FeatureItem extends StatelessWidget {
  final String text;

  const _FeatureItem({
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Text(
          '•',
          style: TextStyle(
            fontSize: 12,
            color: Color(0xFFFF6B35),
            fontFamily: 'Noto Sans KR',
          ),
        ),
        const SizedBox(width: 8),
        Text(
          text,
          style: const TextStyle(
            fontSize: 12,
            color: Color(0xFF6A7282),
            fontFamily: 'Noto Sans KR',
          ),
        ),
      ],
    );
  }
}


