import 'package:flutter/material.dart';
import '../core/constants.dart';

/// Mandatory Clinical Disclaimer widget.
/// Prominently displayed wherever analysis outputs are presented.
class ClinicalDisclaimerWidget extends StatelessWidget {
  final String? customText;

  const ClinicalDisclaimerWidget({super.key, this.customText});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF2F2),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFFECACA), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.warning_amber_rounded,
                color: Color(0xFFDC2626),
                size: 18,
              ),
              SizedBox(width: 8),
              Text(
                'MANDATORY CLINICAL DISCLAIMER',
                style: TextStyle(
                  color: Color(0xFFDC2626),
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            customText ?? AppConstants.mandatoryDisclaimer,
            style: const TextStyle(
              color: Color(0xFF7F1D1D),
              fontSize: 12,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}
