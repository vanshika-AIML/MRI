import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/analysis.dart';

/// Pixel-space overlays on the original 2D scan, not a diagnostic segmentation.
class ScanPreview extends StatelessWidget {
  final File file;
  final AnalysisResponse result;
  const ScanPreview({super.key, required this.file, required this.result});

  @override
  Widget build(BuildContext context) {
    final prediction = result.prediction;
    if (prediction != null) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Research segmentation overlay · axial slice ${prediction.previewSliceIndex}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Image.memory(
              base64Decode(prediction.overlayPngBase64),
              fit: BoxFit.contain,
              errorBuilder: (_, error, stack) =>
                  const Text('Segmentation preview unavailable.'),
            ),
          ],
        ),
      );
    }
    if (!RegExp(
          r'\.(png|jpe?g|bmp)$',
          caseSensitive: false,
        ).hasMatch(file.path) ||
        result.inputMetadata.dimensions.length != 2) {
      return const Padding(
        padding: EdgeInsets.only(bottom: 16),
        child: Text(
          'Volume/DICOM preview is unavailable. Findings use voxel coordinates; review the source scan in a medical image viewer.',
        ),
      );
    }
    final shape = result.inputMetadata.dimensions;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: AspectRatio(
        aspectRatio: shape[1] / shape[0],
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.file(
              file,
              fit: BoxFit.fill,
              errorBuilder: (_, error, stack) =>
                  const Center(child: Text('Preview unavailable')),
            ),
            CustomPaint(painter: _Regions(result)),
          ],
        ),
      ),
    );
  }
}

class _Regions extends CustomPainter {
  final AnalysisResponse result;
  _Regions(this.result);
  @override
  void paint(Canvas canvas, Size size) {
    final shape = result.inputMetadata.dimensions;
    final paint = Paint()
      ..color = Colors.orange
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    for (final region in result.detectedRegions) {
      if (region.bbox.length != 4) continue;
      final box = region.bbox.map((v) => (v as num).toDouble()).toList();
      canvas.drawRect(
        Rect.fromLTRB(
          box[1] * size.width / shape[1],
          box[0] * size.height / shape[0],
          box[3] * size.width / shape[1],
          box[2] * size.height / shape[0],
        ),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _Regions oldDelegate) =>
      oldDelegate.result != result;
}
