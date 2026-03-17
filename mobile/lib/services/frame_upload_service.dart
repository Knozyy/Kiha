import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

/// Sends JPEG frames to the Kiha server for AI analysis.
///
/// Each frame goes through: JPEG → POST /api/v1/chat/frame/{deviceId}
/// → YOLOv8 detection → SceneMemory storage.
class FrameUploadService {
  FrameUploadService({required this.serverAddress, this.deviceId = 'kiha_mobile_01'});

  final String serverAddress;
  final String deviceId;

  int _uploadedCount = 0;
  int get uploadedCount => _uploadedCount;

  /// Upload a single JPEG frame to the server.
  /// Returns detected labels on success, null on failure.
  Future<List<String>?> uploadFrame(Uint8List jpegBytes) async {
    final url = Uri.parse('http://$serverAddress/api/v1/chat/frame/$deviceId');

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'image/jpeg'},
        body: jpegBytes,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        _uploadedCount++;
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final labels = (data['labels'] as List?)?.cast<String>() ?? [];
        return labels;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  void resetCount() => _uploadedCount = 0;
}
