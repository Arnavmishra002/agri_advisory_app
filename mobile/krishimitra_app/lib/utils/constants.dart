import 'package:flutter/foundation.dart' show kIsWeb, kDebugMode;

class AppConfig {
  // ── API base URL ──────────────────────────────────────────────
  // Priority:
  //   1. --dart-define=API_BASE_URL=https://... (CI/release builds)
  //   2. Auto-detect: debug on web → localhost:8000
  //                   debug on Android emulator → 10.0.2.2:8000
  //                   production → Render URL
  static const String _defined = String.fromEnvironment('API_BASE_URL', defaultValue: '');

  static String get baseUrl {
    if (_defined.isNotEmpty) return _defined;
    if (kDebugMode) {
      if (kIsWeb) return 'http://localhost:8000';
      // Android emulator maps 10.0.2.2 to host machine localhost
      return 'http://10.0.2.2:8000';
    }
    return 'https://agri-advisory-app.onrender.com';
  }

  static String get apiV1 => '$baseUrl/api';

  static String get chatEndpoint          => '$apiV1/chatbot/query/';
  static String get chatStreamEndpoint    => '$apiV1/chatbot/stream/';
  static String get weatherEndpoint       => '$apiV1/weather/';
  static String get weatherRefreshEndpoint=> '$apiV1/weather/refresh/';
  static String get mandisEndpoint        => '$apiV1/market-prices/mandis/';
  static String get marketEndpoint        => '$apiV1/market-prices/';
  static String get mandiPricesEndpoint   => '$apiV1/market-prices/mandi-prices/';
  static String get schemesEndpoint       => '$apiV1/schemes/';
  static String get cropRecEndpoint       => '$apiV1/advisories/';
  static String get diagnosticsEndpoint   => '$apiV1/diagnostics/predict/';
  static String get farmerProfileEndpoint => '$apiV1/farmer-profile/';
  static String get dataFreshnessEndpoint => '$apiV1/health/data-freshness/';

  static const String appName    = 'KrishiMitra AI';
  static const String appVersion = '1.0.0';
  static const int    mandiRadiusKm = 150;

  // Web can't do file upload natively
  static bool get supportsCamera => !kIsWeb;
}

class AppColors {
  static const int primary       = 0xFF2D7D32;
  static const int primaryLight  = 0xFF4CAF50;
  static const int primaryDark   = 0xFF1B5E20;
  static const int accent        = 0xFFF9A825;
  static const int background    = 0xFFF5F5F0;
  static const int surface       = 0xFFFFFFFF;
  static const int error         = 0xFFD32F2F;
  static const int success       = 0xFF388E3C;
  static const int warning       = 0xFFF57C00;
  static const int textPrimary   = 0xFF212121;
  static const int textSecondary = 0xFF757575;
  static const int chipGreen     = 0xFFE8F5E9;
  static const int chipAmber     = 0xFFFFF8E1;
  static const int weatherBg     = 0xFF1565C0;
}

class AppStrings {
  static const Map<String, String> languages = {
    'hi': 'हिन्दी',
    'en': 'English',
    'bn': 'বাংলা',
    'te': 'తెలుగు',
    'mr': 'मराठी',
    'ta': 'தமிழ்',
    'gu': 'ગુજરાતી',
    'kn': 'ಕನ್ನಡ',
    'ml': 'മലയാളം',
    'pa': 'ਪੰਜਾਬੀ',
    'or': 'ଓଡ଼ିଆ',
    'as': 'অসমীয়া',
    'ur': 'اردو',
  };
}
