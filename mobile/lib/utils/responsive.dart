import 'package:flutter/material.dart';

/// 반응형 디자인을 위한 유틸리티 클래스
class Responsive {
  /// 화면 너비를 기반으로 디바이스 타입을 판단
  static bool isMobile(BuildContext context) {
    return MediaQuery.of(context).size.width < 600;
  }

  static bool isTablet(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    return width >= 600 && width < 1200;
  }

  static bool isDesktop(BuildContext context) {
    return MediaQuery.of(context).size.width >= 1200;
  }

  /// 화면 너비에 따른 최대 콘텐츠 너비 반환
  static double getMaxContentWidth(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    if (width < 600) {
      // 모바일: 전체 너비 사용
      return width;
    } else if (width < 1200) {
      // 태블릿: 최대 600px
      return 600;
    } else {
      // 데스크톱: 최대 800px
      return 800;
    }
  }

  /// 화면 너비에 따른 패딩 값 반환
  static double getPadding(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    if (width < 600) {
      return 16.0;
    } else if (width < 1200) {
      return 24.0;
    } else {
      return 32.0;
    }
  }

  /// 화면 너비에 따른 수평 패딩 반환
  static EdgeInsets getHorizontalPadding(BuildContext context) {
    final padding = getPadding(context);
    return EdgeInsets.symmetric(horizontal: padding);
  }

  /// 화면 너비에 따른 전체 패딩 반환
  static EdgeInsets getAllPadding(BuildContext context) {
    final padding = getPadding(context);
    return EdgeInsets.all(padding);
  }

  /// 화면 너비의 비율에 따른 값 반환
  static double width(BuildContext context, double percentage) {
    return MediaQuery.of(context).size.width * percentage / 100;
  }

  /// 화면 높이의 비율에 따른 값 반환
  static double height(BuildContext context, double percentage) {
    return MediaQuery.of(context).size.height * percentage / 100;
  }

  /// 텍스트 크기를 화면 크기에 따라 조정
  static double getTextSize(BuildContext context, double baseSize) {
    final width = MediaQuery.of(context).size.width;
    if (width < 600) {
      return baseSize;
    } else if (width < 1200) {
      return baseSize * 1.1;
    } else {
      return baseSize * 1.2;
    }
  }

  /// 로그인 화면의 카드 너비 계산
  static double getLoginCardWidth(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final padding = getPadding(context) * 2;
    final availableWidth = width - padding;
    
    if (width < 600) {
      // 모바일: 최소 278px, 최대 사용 가능한 너비
      return availableWidth.clamp(278.0, double.infinity);
    } else {
      // 태블릿 이상: 고정 너비 400px
      return 400.0;
    }
  }
}








