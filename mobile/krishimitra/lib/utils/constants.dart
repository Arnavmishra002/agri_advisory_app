/// KrishiMitra App Constants
library;

class AppConfig {
  // ── API Base URL ──────────────────────────────────────────────────────────
  // Change to your production URL when deploying
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://agri-advisory-app.onrender.com',
  );

  // Local dev (when running Django on same machine):
  // static const String baseUrl = 'http://10.0.2.2:8000'; // Android emulator
  // static const String baseUrl = 'http://localhost:8000'; // iOS simulator

  static const String apiV1 = '$baseUrl/api';

  // ── API Endpoints ─────────────────────────────────────────────────────────
  static const String chatEndpoint       = '$apiV1/chatbot/query/';
  static const String weatherEndpoint    = '$apiV1/weather/';
  static const String mandisEndpoint     = '$apiV1/market-prices/mandis/';
  static const String marketEndpoint     = '$apiV1/market-prices/';
  static const String mandiPricesEndpoint= '$apiV1/market-prices/mandi-prices/';
  static const String schemesEndpoint    = '$apiV1/schemes/';
  static const String cropsEndpoint      = '$apiV1/crops/';
  static const String cropRecEndpoint    = '$apiV1/advisories/crop-recommendation/';
  static const String diagnosticsEndpoint= '$apiV1/diagnostics/analyze/';
  static const String farmerProfileEndpoint = '$apiV1/farmer-profile/';
  static const String fieldAdvisoryEndpoint = '$apiV1/field-advisory/';

  // ── App Config ────────────────────────────────────────────────────────────
  static const String appName            = 'KrishiMitra AI';
  static const String appVersion         = '1.0.0';
  static const int    chatHistoryLimit   = 50;
  static const int    mandiRadiusKm      = 150;
  static const int    cacheExpiryMinutes = 30;
}

class AppColors {
  static const int primary      = 0xFF2D7D32; // Forest green
  static const int primaryLight = 0xFF4CAF50;
  static const int primaryDark  = 0xFF1B5E20;
  static const int accent       = 0xFFF9A825; // Warm amber (wheat/sun)
  static const int background   = 0xFFF5F5F0; // Off-white warm
  static const int surface      = 0xFFFFFFFF;
  static const int error        = 0xFFD32F2F;
  static const int success      = 0xFF388E3C;
  static const int warning      = 0xFFF57C00;
  static const int textPrimary  = 0xFF212121;
  static const int textSecondary= 0xFF757575;
  static const int divider      = 0xFFBDBDBD;
  static const int cardBg       = 0xFFFFFFFF;
  static const int chipGreen    = 0xFFE8F5E9;
  static const int chipAmber    = 0xFFFFF8E1;
}

class AppStrings {
  // Supported languages
  static const Map<String, String> languages = {
    'hi':  'हिन्दी',
    'en':  'English',
    'bn':  'বাংলা',
    'te':  'తెలుగు',
    'mr':  'मराठी',
    'ta':  'தமிழ்',
    'gu':  'ગુજરાતી',
    'kn':  'ಕನ್ನಡ',
    'ml':  'മലയാളം',
    'pa':  'ਪੰਜਾਬੀ',
    'or':  'ଓଡ଼ିଆ',
    'as':  'অসমীয়া',
    'ur':  'اردو',
  };
}
