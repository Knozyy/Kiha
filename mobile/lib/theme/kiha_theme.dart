import 'package:flutter/material.dart';

/// Kiha app theme system — Dark & Light themes
/// Based on Stitch design specifications.
class KihaTheme {
  KihaTheme._();

  // ─── Dark Theme Colors (Primary) ───
  static const Color darkBackground = Color(0xFF06141A);
  static const Color darkSurface = Color(0xFF0A1F29);
  static const Color darkSurfaceDarker = Color(0xFF081820);
  static const Color darkBorder = Color(0xFF133342);

  // ─── Light Theme Colors ───
  static const Color lightBackground = Color(0xFFF2F2F7);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightBorder = Color(0xFFE5E5EA);
  static const Color lightTextMain = Color(0xFF1C1C1E);
  static const Color lightTextSecondary = Color(0xFF8E8E93);

  // ─── Shared Colors ───
  static const Color primary = Color(0xFF00E676);
  static const Color primaryDark = Color(0xFF00D661);
  static const Color error = Color(0xFFEF5350);

  // ─── Glass Effect Colors ───
  static const Color darkGlass = Color(0x12FFFFFF); // rgba(255,255,255,0.03)
  static const Color darkGlassBorder = Color(0x1AFFFFFF); // rgba(255,255,255,0.1)
  static const Color lightGlass = Color(0xB3FFFFFF); // rgba(255,255,255,0.7)
  static const Color lightGlassBorder = Color(0x0D000000); // rgba(0,0,0,0.05)

  /// Dark Theme
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      fontFamily: 'Inter',
      scaffoldBackgroundColor: darkBackground,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        surface: darkSurface,
        onPrimary: darkBackground,
        onSurface: Colors.white,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: darkSurface.withOpacity(0.7),
        indicatorColor: Colors.transparent,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: primary,
              fontFamily: 'Inter',
            );
          }
          return TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w500,
            color: Colors.white.withOpacity(0.4),
            fontFamily: 'Inter',
          );
        }),
      ),
    );
  }

  /// Light Theme
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      fontFamily: 'Inter',
      scaffoldBackgroundColor: lightBackground,
      colorScheme: const ColorScheme.light(
        primary: primaryDark,
        surface: lightSurface,
        onPrimary: Colors.white,
        onSurface: lightTextMain,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white.withOpacity(0.8),
        indicatorColor: Colors.transparent,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: primaryDark,
              fontFamily: 'Inter',
            );
          }
          return TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: lightTextSecondary,
            fontFamily: 'Inter',
          );
        }),
      ),
    );
  }
}
