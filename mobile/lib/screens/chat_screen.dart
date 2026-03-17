import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:kiha_mobile/theme/kiha_theme.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// Chat home screen — main screen of the Kiha app.
///
/// Shows an AI chat interface where users can ask questions
/// about recorded footage (e.g., "Where did I put my keys?").
///
/// Connects to the Kiha server via WebSocket for real-time responses.
/// Each AI response may include a photo (base64 JPEG) of the relevant frame.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<_ChatMessage> _messages = [];
  bool _isLoading = false;

  // WebSocket connection
  WebSocketChannel? _channel;
  bool _wsConnected = false;

  // Server configuration — update SERVER_HOST to your machine's IP when testing on a real device
  static const String _serverHost = 'localhost';
  static const int _serverPort = 8000;
  static const String _deviceId = 'kiha_glasses_01';
  static const String _sessionId = 'session_mobile_01';

  // Suggestion chips from Stitch design
  static const List<_SuggestionChip> _suggestions = [
    _SuggestionChip(emoji: '🔑', text: 'Anahtarlarımı nereye koydum?'),
    _SuggestionChip(emoji: '🍳', text: 'Ocağın altını kapattım mı?'),
    _SuggestionChip(emoji: '📱', text: 'Telefonumu en son nerede gördüm?'),
    _SuggestionChip(emoji: '🚗', text: 'Arabamı nereye park ettim?'),
  ];

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _channel?.sink.close();
    super.dispose();
  }

  void _connectWebSocket() {
    try {
      final uri = Uri.parse(
        'ws://$_serverHost:$_serverPort/api/v1/chat/ws/$_sessionId',
      );
      _channel = WebSocketChannel.connect(uri);

      _channel!.stream.listen(
        _onServerMessage,
        onError: (error) {
          if (!mounted) return;
          setState(() => _wsConnected = false);
        },
        onDone: () {
          if (!mounted) return;
          setState(() => _wsConnected = false);
          // Reconnect after 3 seconds
          Future.delayed(const Duration(seconds: 3), () {
            if (mounted) _connectWebSocket();
          });
        },
        cancelOnError: false,
      );

      setState(() => _wsConnected = true);
    } catch (_) {
      setState(() => _wsConnected = false);
    }
  }

  void _onServerMessage(dynamic raw) {
    if (!mounted) return;
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      final content = data['content'] as String? ?? '';
      final thumbnailB64 = data['frame_thumbnail_b64'] as String?;

      Uint8List? imageBytes;
      if (thumbnailB64 != null && thumbnailB64.isNotEmpty) {
        imageBytes = base64Decode(thumbnailB64);
      }

      setState(() {
        _messages.add(_ChatMessage(
          role: 'assistant',
          content: content,
          timestamp: DateTime.now(),
          imageBytes: imageBytes,
        ));
        _isLoading = false;
      });
      _scrollToBottom();
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  void _sendMessage(String text) {
    if (text.trim().isEmpty) return;

    setState(() {
      _messages.add(_ChatMessage(
        role: 'user',
        content: text.trim(),
        timestamp: DateTime.now(),
      ));
      _messageController.clear();
      _isLoading = true;
    });
    _scrollToBottom();

    if (_channel != null && _wsConnected) {
      final payload = jsonEncode({
        'message': text.trim(),
        'device_id': _deviceId,
        'session_id': _sessionId,
      });
      _channel!.sink.add(payload);
    } else {
      // WebSocket not connected — show error
      Future.delayed(const Duration(milliseconds: 300), () {
        if (!mounted) return;
        setState(() {
          _messages.add(_ChatMessage(
            role: 'assistant',
            content:
                '⚠️ Sunucuya bağlanılamadı. Lütfen bağlantınızı kontrol edin.',
            timestamp: DateTime.now(),
          ));
          _isLoading = false;
        });
      });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // ─── Top Bar ───
            _buildTopBar(isDark),

            // ─── Chat Area ───
            Expanded(
              child: _messages.isEmpty
                  ? _buildEmptyState(isDark)
                  : _buildMessageList(isDark),
            ),

            // ─── Input Area ───
            _buildInputBar(isDark),
          ],
        ),
      ),
    );
  }

  /// Top bar with Kiha logo, glasses icon, and connection status.
  Widget _buildTopBar(bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      decoration: BoxDecoration(
        color: isDark
            ? KihaTheme.darkBackground.withOpacity(0.8)
            : Colors.white.withOpacity(0.8),
        border: Border(
          bottom: BorderSide(
            color: isDark
                ? KihaTheme.darkBorder.withOpacity(0.5)
                : KihaTheme.lightBorder.withOpacity(0.5),
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Kiha logo + connection dot
          Row(
            children: [
              Text(
                'Kiha',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : KihaTheme.lightTextMain,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _wsConnected ? KihaTheme.primary : Colors.redAccent,
                  boxShadow: [
                    BoxShadow(
                      color: (_wsConnected
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
          // Glasses + battery
          Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isDark
                      ? KihaTheme.darkSurface
                      : KihaTheme.lightBackground,
                  border: Border.all(
                    color: isDark
                        ? KihaTheme.darkBorder
                        : Colors.transparent,
                  ),
                ),
                child: Icon(
                  Icons.visibility,
                  size: 18,
                  color: isDark
                      ? KihaTheme.primary
                      : KihaTheme.lightTextSecondary,
                ),
              ),
              const SizedBox(width: 12),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  color: isDark
                      ? KihaTheme.darkSurface
                      : KihaTheme.lightBackground,
                  border: Border.all(
                    color: isDark
                        ? KihaTheme.darkBorder
                        : Colors.transparent,
                  ),
                ),
                child: Row(
                  children: [
                    Text(
                      '78%',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: isDark
                            ? const Color(0xFFCBD5E1)
                            : KihaTheme.lightTextMain,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      Icons.battery_5_bar,
                      size: 16,
                      color: KihaTheme.primary,
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

  /// Empty state with welcome message and suggestion chips.
  Widget _buildEmptyState(bool isDark) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 48),

          // AI icon with glow
          Container(
            width: 96,
            height: 96,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(32),
              gradient: isDark
                  ? LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        KihaTheme.darkSurface,
                        KihaTheme.darkSurfaceDarker,
                      ],
                    )
                  : null,
              color: isDark ? null : Colors.white,
              border: Border.all(
                color: isDark
                    ? KihaTheme.primary.withOpacity(0.2)
                    : KihaTheme.lightBorder,
              ),
              boxShadow: [
                if (isDark)
                  BoxShadow(
                    color: KihaTheme.primary.withOpacity(0.15),
                    blurRadius: 30,
                  )
                else
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 20,
                    offset: const Offset(0, 4),
                  ),
              ],
            ),
            child: Icon(
              Icons.psychology,
              size: 48,
              color: KihaTheme.primary,
            ),
          ),

          const SizedBox(height: 24),

          Text(
            'Merhaba!',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: isDark ? Colors.white : KihaTheme.lightTextMain,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Kayıtlarınız hakkında bana her şeyi\nsorabilirsiniz.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: isDark
                  ? const Color(0xFF94A3B8)
                  : KihaTheme.lightTextSecondary,
              height: 1.5,
            ),
          ),

          const SizedBox(height: 40),

          Wrap(
            spacing: 12,
            runSpacing: 12,
            alignment: WrapAlignment.center,
            children: _suggestions.map((chip) {
              return _buildSuggestionChip(chip, isDark);
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSuggestionChip(_SuggestionChip chip, bool isDark) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => _sendMessage(chip.text),
        borderRadius: BorderRadius.circular(24),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            color: isDark ? KihaTheme.darkSurface : KihaTheme.lightBackground,
            border: Border.all(
              color: isDark ? KihaTheme.darkBorder : Colors.transparent,
            ),
            boxShadow: isDark
                ? null
                : [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.05),
                      blurRadius: 20,
                      offset: const Offset(0, 4),
                    ),
                  ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(chip.emoji, style: const TextStyle(fontSize: 16)),
              const SizedBox(width: 8),
              Text(
                chip.text,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: isDark
                      ? const Color(0xFFE2E8F0)
                      : KihaTheme.lightTextMain,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMessageList(bool isDark) {
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(16),
      itemCount: _messages.length + (_isLoading ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == _messages.length && _isLoading) {
          return _buildTypingIndicator(isDark);
        }
        return _buildMessageBubble(_messages[index], isDark);
      },
    );
  }

  /// Chat message bubble — shows text and optional photo.
  Widget _buildMessageBubble(_ChatMessage msg, bool isDark) {
    final bool isUser = msg.role == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: isUser
              ? (isDark ? KihaTheme.darkSurface : KihaTheme.lightBackground)
              : (isDark ? KihaTheme.darkSurfaceDarker : Colors.white),
          border: Border.all(
            color: isUser
                ? (isDark
                    ? KihaTheme.primary.withOpacity(0.3)
                    : KihaTheme.lightBorder)
                : (isDark ? KihaTheme.darkBorder : KihaTheme.lightBorder),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // AI badge
            if (!isUser)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.psychology, size: 16, color: KihaTheme.primary),
                    const SizedBox(width: 4),
                    Text(
                      'Kiha AI',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: KihaTheme.primary,
                      ),
                    ),
                  ],
                ),
              ),

            // Message text
            Text(
              msg.content,
              style: TextStyle(
                fontSize: 15,
                color: isDark ? Colors.white : KihaTheme.lightTextMain,
                height: 1.4,
              ),
            ),

            // Frame photo (AI responses only)
            if (!isUser && msg.imageBytes != null) ...[
              const SizedBox(height: 10),
              ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: Image.memory(
                  msg.imageBytes!,
                  fit: BoxFit.cover,
                  width: double.infinity,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTypingIndicator(bool isDark) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: isDark ? KihaTheme.darkSurfaceDarker : Colors.white,
          border: Border.all(
            color: isDark ? KihaTheme.darkBorder : KihaTheme.lightBorder,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.psychology, size: 16, color: KihaTheme.primary),
            const SizedBox(width: 8),
            SizedBox(
              width: 40,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: List.generate(3, (i) {
                  return TweenAnimationBuilder<double>(
                    tween: Tween(begin: 0, end: 1),
                    duration: Duration(milliseconds: 600 + (i * 200)),
                    builder: (context, value, child) {
                      return Opacity(
                        opacity: (1 - value).clamp(0.3, 1.0),
                        child: Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: KihaTheme.primary.withOpacity(0.6),
                          ),
                        ),
                      );
                    },
                  );
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInputBar(bool isDark) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: isDark
              ? [
                  KihaTheme.darkBackground.withOpacity(0),
                  KihaTheme.darkBackground.withOpacity(0.9),
                  KihaTheme.darkBackground,
                ]
              : [
                  Colors.white.withOpacity(0),
                  Colors.white.withOpacity(0.95),
                  Colors.white,
                ],
        ),
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: isDark
              ? KihaTheme.darkSurfaceDarker.withOpacity(0.6)
              : const Color(0x1F767680),
          border: isDark
              ? Border.all(color: KihaTheme.darkBorder.withOpacity(0.8))
              : null,
        ),
        padding: const EdgeInsets.all(6),
        child: Row(
          children: [
            IconButton(
              onPressed: () {
                // TODO: Implement voice input
              },
              icon: Icon(
                Icons.mic,
                color: isDark
                    ? const Color(0xFF94A3B8)
                    : KihaTheme.lightTextSecondary,
                size: 24,
              ),
            ),
            Expanded(
              child: TextField(
                controller: _messageController,
                style: TextStyle(
                  fontSize: 15,
                  color: isDark ? Colors.white : KihaTheme.lightTextMain,
                ),
                decoration: InputDecoration(
                  hintText: 'Bir şey sorun...',
                  hintStyle: TextStyle(
                    color: isDark
                        ? const Color(0xFF64748B)
                        : KihaTheme.lightTextSecondary.withOpacity(0.6),
                    fontSize: 15,
                  ),
                  border: InputBorder.none,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 8),
                ),
                onSubmitted: _sendMessage,
              ),
            ),
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(isDark ? 12 : 20),
                color: KihaTheme.primary,
                boxShadow: [
                  BoxShadow(
                    color: KihaTheme.primary.withOpacity(isDark ? 0.2 : 0.3),
                    blurRadius: 12,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: IconButton(
                onPressed: () => _sendMessage(_messageController.text),
                icon: Icon(
                  Icons.arrow_upward,
                  color: isDark ? KihaTheme.darkBackground : Colors.white,
                  size: 20,
                ),
                padding: EdgeInsets.zero,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Internal chat message data class.
class _ChatMessage {
  _ChatMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.imageBytes,
  });

  final String role;
  final String content;
  final DateTime timestamp;
  final Uint8List? imageBytes;   // decoded frame photo, null if none
}

/// Suggestion chip data class.
class _SuggestionChip {
  const _SuggestionChip({required this.emoji, required this.text});

  final String emoji;
  final String text;
}
