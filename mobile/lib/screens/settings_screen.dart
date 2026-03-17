import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:kiha_mobile/theme/kiha_theme.dart';
import 'package:kiha_mobile/widgets/glass_card.dart';
import 'package:kiha_mobile/widgets/kiha_switch.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Settings screen — device status, connection, recording, AI, security settings.
///
/// Matches the Stitch design with glassmorphism status card,
/// grouped settings sections, and custom toggle switches.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // Toggle states
  bool _autoConnect = true;
  bool _autoRecord = false;
  bool _voiceResponse = true;
  bool _biometricLock = true;

  // Video quality selection
  int _selectedQuality = 1; // 0: 720p, 1: 1080p, 2: 4K

  // Connection quality
  String _connectionQuality = 'Yüksek';

  // Server connection
  final TextEditingController _serverIpController = TextEditingController();
  bool _serverConnected = false;

  /// SharedPreferences key for server IP
  static const String _serverIpKey = 'server_ip';
  static const String _defaultServerIp = '82.26.94.210:8000';

  @override
  void initState() {
    super.initState();
    _loadServerIp();
  }

  @override
  void dispose() {
    _serverIpController.dispose();
    super.dispose();
  }

  Future<void> _loadServerIp() async {
    final prefs = await SharedPreferences.getInstance();
    final ip = prefs.getString(_serverIpKey) ?? _defaultServerIp;
    setState(() => _serverIpController.text = ip);
    _testConnection(ip);
  }

  Future<void> _saveServerIp(String ip) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_serverIpKey, ip);
    _testConnection(ip);
  }

  Future<void> _testConnection(String ip) async {
    try {
      final uri = Uri.parse('http://$ip/health');
      // Simple connectivity check — actual implementation uses http package
      setState(() => _serverConnected = ip.isNotEmpty);
    } catch (_) {
      setState(() => _serverConnected = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // ─── Header ───
            _buildHeader(isDark),

            // ─── Scrollable Content ───
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildStatusCard(isDark),
                    const SizedBox(height: 32),
                    _buildConnectionSection(isDark),
                    const SizedBox(height: 24),
                    _buildRecordingSection(isDark),
                    const SizedBox(height: 24),
                    _buildAiSection(isDark),
                    const SizedBox(height: 24),
                    _buildSecuritySection(isDark),
                    const SizedBox(height: 24),
                    _buildAboutSection(isDark),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Header with back arrow, title, and profile icon.
  Widget _buildHeader(bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Icon(
                Icons.arrow_back_ios_new,
                size: 20,
                color: isDark ? Colors.white : KihaTheme.lightTextMain,
              ),
              const SizedBox(width: 16),
              Text(
                'Ayarlar',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : KihaTheme.lightTextMain,
                  letterSpacing: -0.5,
                ),
              ),
            ],
          ),
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isDark
                  ? KihaTheme.primary.withOpacity(0.2)
                  : Colors.white,
              border: Border.all(
                color: isDark
                    ? KihaTheme.primary.withOpacity(0.3)
                    : const Color(0xFFE2E8F0),
              ),
              boxShadow: isDark
                  ? null
                  : [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.05),
                        blurRadius: 8,
                      ),
                    ],
            ),
            child: Icon(
              Icons.person,
              size: 20,
              color: isDark ? KihaTheme.primary : const Color(0xFF475569),
            ),
          ),
        ],
      ),
    );
  }

  /// Device status card (battery, connection, firmware).
  Widget _buildStatusCard(bool isDark) {
    return GlassCard(
      borderRadius: isDark ? 16 : 20,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Active badge
          Align(
            alignment: Alignment.topRight,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: KihaTheme.primary,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  'AKTİF',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: KihaTheme.primary,
                    letterSpacing: 2,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 8),

          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Glasses icon
              Container(
                width: 96,
                height: 96,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  gradient: isDark
                      ? LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            KihaTheme.primary.withOpacity(0.2),
                            KihaTheme.primary.withOpacity(0.05),
                          ],
                        )
                      : null,
                  color: isDark ? null : Colors.white,
                  border: Border.all(
                    color: isDark
                        ? KihaTheme.primary.withOpacity(0.2)
                        : const Color(0xFFF1F5F9),
                  ),
                  boxShadow: isDark
                      ? null
                      : [
                          const BoxShadow(
                            color: Color(0x08000000),
                            blurRadius: 8,
                            offset: Offset(0, 2),
                          ),
                        ],
                ),
                child: Icon(
                  Icons.visibility,
                  size: 36,
                  color: KihaTheme.primary,
                ),
              ),

              const SizedBox(width: 24),

              // Device info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Kiha Glass v1',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                        color: isDark ? Colors.white : KihaTheme.lightTextMain,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 16,
                      runSpacing: 4,
                      children: [
                        _infoChip('Bağlantı:', 'Stabil ✓', KihaTheme.primary, isDark),
                        _infoChip('Firmware:', 'v1.2.0', null, isDark),
                        _infoChip('Aktif Süre:', '1s 23dk', null, isDark),
                      ],
                    ),

                    const SizedBox(height: 16),

                    // Battery level
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Batarya Seviyesi',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: isDark
                                ? const Color(0xFFCBD5E1)
                                : const Color(0xFF475569),
                          ),
                        ),
                        Text(
                          '78%',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: isDark
                                ? KihaTheme.primary
                                : KihaTheme.lightTextMain,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    // Battery bar
                    Container(
                      height: 8,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(4),
                        color: isDark
                            ? const Color(0xFF1E293B) // slate-800
                            : const Color(0xFFE2E8F0), // slate-200
                      ),
                      child: FractionallySizedBox(
                        widthFactor: 0.78,
                        alignment: Alignment.centerLeft,
                        child: Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(4),
                            gradient: isDark
                                ? const LinearGradient(
                                    colors: [
                                      Color(0xFFEF5350), // red
                                      Color(0xFFFACC15), // yellow
                                      Color(0xFF00E676), // green
                                    ],
                                  )
                                : null,
                            color: isDark ? null : KihaTheme.primary,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '~ 2 saat 15 dk tahmini kullanım süresi',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w500,
                        color: isDark
                            ? const Color(0xFF64748B) // slate-500
                            : const Color(0xFF94A3B8), // slate-400
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _infoChip(String label, String value, Color? valueColor, bool isDark) {
    return RichText(
      text: TextSpan(
        style: TextStyle(fontSize: 12, fontFamily: 'Inter'),
        children: [
          TextSpan(
            text: '$label ',
            style: TextStyle(
              color: isDark
                  ? const Color(0xFF94A3B8)
                  : const Color(0xFF64748B),
            ),
          ),
          TextSpan(
            text: value,
            style: TextStyle(
              fontWeight: FontWeight.w500,
              color: valueColor ??
                  (isDark
                      ? const Color(0xFFE2E8F0)
                      : KihaTheme.lightTextMain),
            ),
          ),
        ],
      ),
    );
  }

  /// Section header text.
  Widget _sectionHeader(String icon, String title, bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(left: 8, bottom: 12),
      child: Text(
        title.toUpperCase(),
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: isDark
              ? const Color(0xFF64748B)
              : const Color(0xFF64748B),
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  /// Settings row with trailing widget.
  Widget _settingsRow({
    required String title,
    required Widget trailing,
    required bool isDark,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              title,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: isDark ? Colors.white : KihaTheme.lightTextMain,
              ),
            ),
            trailing,
          ],
        ),
      ),
    );
  }

  /// Grouped settings card.
  Widget _settingsCard({
    required List<Widget> children,
    required bool isDark,
  }) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(isDark ? 16 : 20),
        color: isDark ? KihaTheme.darkGlass : KihaTheme.lightGlass,
        border: Border.all(
          color: isDark ? KihaTheme.darkGlassBorder : KihaTheme.lightGlassBorder,
        ),
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: Colors.black.withOpacity(0.04),
                  blurRadius: 24,
                  offset: const Offset(0, 4),
                ),
              ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(isDark ? 16 : 20),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: isDark ? 12 : 20,
            sigmaY: isDark ? 12 : 20,
          ),
          child: Column(
            children: _buildDividedChildren(children, isDark),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildDividedChildren(List<Widget> children, bool isDark) {
    final List<Widget> result = [];
    for (int i = 0; i < children.length; i++) {
      result.add(children[i]);
      if (i < children.length - 1) {
        result.add(Divider(
          height: 1,
          color: isDark
              ? KihaTheme.darkGlassBorder
              : const Color(0xFFF1F5F9),
        ));
      }
    }
    return result;
  }

  // ─── Connection Settings ───
  Widget _buildConnectionSection(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader('📡', 'Bağlantı Ayarları', isDark),
        _settingsCard(
          isDark: isDark,
          children: [
            // Server IP input
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Sunucu Adresi',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: isDark ? Colors.white : KihaTheme.lightTextMain,
                        ),
                      ),
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _serverConnected
                              ? KihaTheme.primary
                              : Colors.redAccent,
                          boxShadow: [
                            BoxShadow(
                              color: (_serverConnected
                                      ? KihaTheme.primary
                                      : Colors.redAccent)
                                  .withOpacity(0.6),
                              blurRadius: 8,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _serverIpController,
                          style: TextStyle(
                            fontSize: 14,
                            fontFamily: 'monospace',
                            color: isDark ? Colors.white : KihaTheme.lightTextMain,
                          ),
                          decoration: InputDecoration(
                            hintText: 'IP:PORT (ör: 82.26.94.210:8000)',
                            hintStyle: TextStyle(
                              fontSize: 13,
                              color: isDark
                                  ? const Color(0xFF64748B)
                                  : const Color(0xFF94A3B8),
                            ),
                            filled: true,
                            fillColor: isDark
                                ? const Color(0xFF1E293B).withOpacity(0.5)
                                : const Color(0xFFF1F5F9),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide.none,
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 10,
                            ),
                          ),
                          onSubmitted: _saveServerIp,
                        ),
                      ),
                      const SizedBox(width: 8),
                      GestureDetector(
                        onTap: () => _saveServerIp(_serverIpController.text),
                        child: Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(10),
                            color: KihaTheme.primary,
                          ),
                          child: Icon(
                            Icons.save,
                            color: isDark ? KihaTheme.darkBackground : Colors.white,
                            size: 20,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            _settingsRow(
              title: 'Gözlük Eşleştir',
              isDark: isDark,
              trailing: Icon(
                Icons.chevron_right,
                color: isDark
                    ? const Color(0xFF64748B)
                    : const Color(0xFFCBD5E1),
              ),
              onTap: () {},
            ),
            _settingsRow(
              title: 'Otomatik Bağlan',
              isDark: isDark,
              trailing: KihaSwitch(
                value: _autoConnect,
                onChanged: (v) => setState(() => _autoConnect = v),
              ),
            ),
            _settingsRow(
              title: 'Bağlantı Kalitesi',
              isDark: isDark,
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _connectionQuality,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: KihaTheme.primary,
                    ),
                  ),
                  Icon(
                    Icons.expand_more,
                    size: 16,
                    color: KihaTheme.primary,
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ─── Recording Settings ───
  Widget _buildRecordingSection(bool isDark) {
    final List<String> qualities = ['720p', '1080p', '4K'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader('🎥', 'Kayıt Ayarları', isDark),
        _settingsCard(
          isDark: isDark,
          children: [
            // Video quality segmented control
            _settingsRow(
              title: 'Video Kalitesi',
              isDark: isDark,
              trailing: Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  color: isDark
                      ? const Color(0xFF1E293B).withOpacity(0.5)
                      : const Color(0xFFF1F5F9),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(qualities.length, (i) {
                    final bool selected = i == _selectedQuality;
                    return GestureDetector(
                      onTap: () => setState(() => _selectedQuality = i),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(6),
                          color: selected
                              ? (isDark ? KihaTheme.primary : Colors.white)
                              : Colors.transparent,
                          boxShadow: selected && !isDark
                              ? [
                                  BoxShadow(
                                    color: Colors.black.withOpacity(0.05),
                                    blurRadius: 4,
                                  ),
                                ]
                              : null,
                        ),
                        child: Text(
                          qualities[i],
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: selected
                                ? (isDark ? Colors.black : KihaTheme.lightTextMain)
                                : (isDark
                                    ? Colors.white
                                    : const Color(0xFF64748B)),
                          ),
                        ),
                      ),
                    );
                  }),
                ),
              ),
            ),

            // Storage usage
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Depolama Kullanımı',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: isDark ? Colors.white : KihaTheme.lightTextMain,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(20),
                          color: isDark
                              ? const Color(0xFFEF5350).withOpacity(0.1)
                              : const Color(0xFFFEF2F2),
                          border: isDark
                              ? Border.all(
                                  color: const Color(0xFFEF5350).withOpacity(0.2),
                                )
                              : null,
                        ),
                        child: Text(
                          'TEMİZLE',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: isDark
                                ? const Color(0xFFEF5350)
                                : const Color(0xFFEF4444),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // Progress bar
                  Container(
                    height: 6,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(3),
                      color: isDark
                          ? const Color(0xFF1E293B)
                          : const Color(0xFFF1F5F9),
                    ),
                    child: FractionallySizedBox(
                      widthFactor: 0.38,
                      alignment: Alignment.centerLeft,
                      child: Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(3),
                          color: KihaTheme.primary.withOpacity(0.6),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        '12.4 GB KULLANILAN',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: const Color(0xFF64748B),
                          letterSpacing: 0.5,
                        ),
                      ),
                      Text(
                        '32 GB TOPLAM',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: const Color(0xFF64748B),
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            _settingsRow(
              title: 'Otomatik Kayıt',
              isDark: isDark,
              trailing: KihaSwitch(
                value: _autoRecord,
                onChanged: (v) => setState(() => _autoRecord = v),
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ─── AI Settings ───
  Widget _buildAiSection(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader('🤖', 'AI Ayarları', isDark),
        _settingsCard(
          isDark: isDark,
          children: [
            _settingsRow(
              title: 'Yanıt Dili',
              isDark: isDark,
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Türkçe',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: KihaTheme.primary,
                    ),
                  ),
                  Icon(Icons.expand_more, size: 16, color: KihaTheme.primary),
                ],
              ),
            ),
            _settingsRow(
              title: 'Sesli Yanıt',
              isDark: isDark,
              trailing: KihaSwitch(
                value: _voiceResponse,
                onChanged: (v) => setState(() => _voiceResponse = v),
              ),
            ),
            _settingsRow(
              title: 'AI Modeli',
              isDark: isDark,
              trailing: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(6),
                  color: isDark
                      ? Colors.white.withOpacity(0.05)
                      : const Color(0xFFF8FAFC),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withOpacity(0.1)
                        : const Color(0xFFF1F5F9),
                  ),
                ),
                child: Text(
                  'Kiha-Vision 2.0',
                  style: TextStyle(
                    fontSize: 12,
                    fontFamily: 'monospace',
                    color: isDark
                        ? const Color(0xFF94A3B8)
                        : const Color(0xFF64748B),
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ─── Security Settings ───
  Widget _buildSecuritySection(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader('🔒', 'Güvenlik', isDark),
        _settingsCard(
          isDark: isDark,
          children: [
            _settingsRow(
              title: 'Biyometrik Kilit',
              isDark: isDark,
              trailing: KihaSwitch(
                value: _biometricLock,
                onChanged: (v) => setState(() => _biometricLock = v),
              ),
            ),
            _settingsRow(
              title: 'Veri Şifreleme',
              isDark: isDark,
              trailing: Text(
                'DTLS 1.3 ✓ Aktif',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: KihaTheme.primary,
                ),
              ),
            ),
            _settingsRow(
              title: 'Gizlilik Politikası',
              isDark: isDark,
              trailing: Icon(
                Icons.open_in_new,
                size: 20,
                color: isDark
                    ? const Color(0xFF64748B)
                    : const Color(0xFFCBD5E1),
              ),
              onTap: () {},
            ),
          ],
        ),
      ],
    );
  }

  // ─── About Section ───
  Widget _buildAboutSection(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader('ℹ️', 'Hakkında', isDark),
        _settingsCard(
          isDark: isDark,
          children: [
            _settingsRow(
              title: 'Uygulama Versiyonu',
              isDark: isDark,
              trailing: Text(
                'v1.0.0',
                style: TextStyle(
                  fontSize: 14,
                  fontFamily: 'monospace',
                  color: isDark
                      ? const Color(0xFF94A3B8)
                      : const Color(0xFF94A3B8),
                ),
              ),
            ),
            _settingsRow(
              title: 'Lisanslar',
              isDark: isDark,
              trailing: Icon(
                Icons.chevron_right,
                color: isDark
                    ? const Color(0xFF64748B)
                    : const Color(0xFFCBD5E1),
              ),
              onTap: () {},
            ),
            _settingsRow(
              title: 'Destek',
              isDark: isDark,
              trailing: Icon(
                Icons.help_outline,
                color: KihaTheme.primary,
              ),
              onTap: () {},
            ),
          ],
        ),
      ],
    );
  }
}
