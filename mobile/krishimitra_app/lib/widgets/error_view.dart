import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';

/// Generic full-screen error with retry button.
/// Accepts either a String message or an ApiException for richer display.
class ErrorView extends StatelessWidget {
  final dynamic error;   // String | ApiException | Object
  final VoidCallback onRetry;
  final String? title;

  const ErrorView({
    super.key,
    required this.error,
    required this.onRetry,
    this.title,
  });

  bool get _isOffline =>
      error is ApiException && (error as ApiException).statusCode == null ||
      (error is String && (error as String).contains('offline'));

  String get _message {
    if (error is ApiException) return (error as ApiException).displayMessage;
    if (error is String) {
      final s = error as String;
      if (s == 'offline')  return 'इंटरनेट कनेक्शन नहीं है।';
      if (s == 'network')  return 'सर्वर से संपर्क नहीं हो सका।';
      if (s == 'cache_parse') return 'कैश डेटा पढ़ने में त्रुटि।';
      return s;
    }
    return error.toString();
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: _isOffline ? Colors.orange.shade50 : Colors.red.shade50,
                shape: BoxShape.circle,
              ),
              child: Icon(
                _isOffline ? Icons.wifi_off_rounded : Icons.error_outline_rounded,
                size: 48,
                color: _isOffline ? Colors.orange : Colors.red.shade300,
              ),
            ),
            const SizedBox(height: 20),
            if (title != null) ...[
              Text(
                title!,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
            ],
            Text(
              _message,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey[600], fontSize: 14, height: 1.5),
            ),
            if (_isOffline) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Server: ${AppConfig.baseUrl}',
                  style: TextStyle(fontSize: 11, color: Colors.grey[500]),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
            const SizedBox(height: 24),
            ElevatedButton.icon(
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('दोबारा कोशिश करें'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(AppColors.primary),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: onRetry,
            ),
          ],
        ),
      ),
    );
  }
}
