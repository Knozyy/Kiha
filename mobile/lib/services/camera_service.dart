import 'dart:async';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:kiha_mobile/services/frame_upload_service.dart';

/// Captures JPEG frames from the device camera at a fixed interval
/// and uploads them to the Kiha server via [FrameUploadService].
///
/// Usage:
///   final service = CameraService(uploadService: frameUploadService);
///   await service.initialize();
///   service.startCapture();   // starts periodic frame capture
///   service.stopCapture();    // stops
///   service.dispose();        // release camera
class CameraService {
  CameraService({
    required this.uploadService,
    this.captureIntervalSeconds = 2,
  });

  final FrameUploadService uploadService;
  final int captureIntervalSeconds;

  CameraController? _controller;
  Timer? _captureTimer;
  bool _isCapturing = false;
  List<String> _lastLabels = [];

  CameraController? get controller => _controller;
  bool get isCapturing => _isCapturing;
  bool get isInitialized => _controller?.value.isInitialized ?? false;
  List<String> get lastLabels => _lastLabels;
  int get uploadedCount => uploadService.uploadedCount;

  /// Initialize the camera (back camera preferred).
  Future<void> initialize() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return;

    // Prefer back camera
    final camera = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.back,
      orElse: () => cameras.first,
    );

    _controller = CameraController(
      camera,
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );

    await _controller!.initialize();
  }

  /// Start periodic frame capture and upload.
  void startCapture() {
    if (_isCapturing || _controller == null || !_controller!.value.isInitialized) return;

    _isCapturing = true;
    uploadService.resetCount();

    // Capture immediately, then every N seconds
    _captureAndUpload();
    _captureTimer = Timer.periodic(
      Duration(seconds: captureIntervalSeconds),
      (_) => _captureAndUpload(),
    );
  }

  /// Stop frame capture.
  void stopCapture() {
    _captureTimer?.cancel();
    _captureTimer = null;
    _isCapturing = false;
  }

  Future<void> _captureAndUpload() async {
    if (_controller == null || !_controller!.value.isInitialized) return;

    try {
      final xFile = await _controller!.takePicture();
      final Uint8List bytes = await xFile.readAsBytes();

      final labels = await uploadService.uploadFrame(bytes);
      if (labels != null) {
        _lastLabels = labels;
      }
    } catch (_) {
      // Camera busy or upload failed — skip this frame
    }
  }

  /// Release camera resources.
  void dispose() {
    stopCapture();
    _controller?.dispose();
    _controller = null;
  }
}
