import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:kiha_mobile/screens/chat_screen.dart';
import 'package:kiha_mobile/screens/settings_screen.dart';
import 'package:kiha_mobile/theme/kiha_theme.dart';

/// Kiha Mobile App — AI-Powered Smart Glasses Companion
///
/// TÜBİTAK destekli AI tabanlı akıllı gözlük projesi mobil uygulaması.
/// State Management: Riverpod (MASTER.md kuralı).
void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Set status bar style
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
    ),
  );

  runApp(const KihaApp());
}

class KihaApp extends StatelessWidget {
  const KihaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kiha',
      debugShowCheckedModeBanner: false,
      theme: KihaTheme.lightTheme,
      darkTheme: KihaTheme.darkTheme,
      themeMode: ThemeMode.dark, // Default: dark theme (primary design)
      home: const KihaShell(),
    );
  }
}

/// App shell with bottom navigation (Chat + Ayarlar).
class KihaShell extends StatefulWidget {
  const KihaShell({super.key});

  @override
  State<KihaShell> createState() => _KihaShellState();
}

class _KihaShellState extends State<KihaShell> {
  int _currentIndex = 0;

  static const List<Widget> _screens = [
    ChatScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: _buildBottomNav(isDark),
    );
  }

  /// Bottom navigation bar matching Stitch glass-panel design.
  Widget _buildBottomNav(bool isDark) {
    return Container(
      decoration: BoxDecoration(
        color: isDark
            ? KihaTheme.darkSurface.withOpacity(0.7)
            : Colors.white.withOpacity(0.8),
        border: Border(
          top: BorderSide(
            color: isDark
                ? KihaTheme.darkGlassBorder
                : const Color(0x1A000000), // rgba(0,0,0,0.1)
          ),
        ),
      ),
      padding: EdgeInsets.only(
        top: 8,
        bottom: MediaQuery.of(context).padding.bottom + 8,
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _navItem(
            icon: Icons.chat,
            label: 'Chat',
            index: 0,
            isDark: isDark,
          ),
          _navItem(
            icon: Icons.settings,
            label: 'Ayarlar',
            index: 1,
            isDark: isDark,
          ),
        ],
      ),
    );
  }

  Widget _navItem({
    required IconData icon,
    required String label,
    required int index,
    required bool isDark,
  }) {
    final bool selected = _currentIndex == index;

    return GestureDetector(
      onTap: () => setState(() => _currentIndex = index),
      behavior: HitTestBehavior.opaque,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              color: selected
                  ? (isDark
                      ? KihaTheme.primary.withOpacity(0.2)
                      : const Color(0xFFF8FAFC))
                  : Colors.transparent,
            ),
            child: Icon(
              icon,
              size: 24,
              color: selected
                  ? KihaTheme.primary
                  : (isDark
                      ? const Color(0xFF64748B)
                      : const Color(0xFF94A3B8)),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: selected
                  ? KihaTheme.primary
                  : (isDark
                      ? const Color(0xFF64748B)
                      : const Color(0xFF94A3B8)),
              letterSpacing: -0.5,
            ),
          ),
        ],
      ),
    );
  }
}
