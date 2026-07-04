# KrishiMitra AI — Flutter Mobile App

Smart agricultural advisory app for Indian farmers. Works with the Django backend.

## Screens

| Screen | Feature |
|--------|---------|
| 💬 Chat | AI chatbot — 19 intents, 22 languages, Hinglish |
| 🏪 Mandi | Nearby mandis (GPS-sorted), live prices |
| 🌤️ Mausam | Hyperlocal weather + farming advice |
| 🌾 Fasal | Crop recommendations for your location |
| 🔬 KrishiRaksha | ML crop disease detection from photo |
| 🏛️ Schemes | PM-Kisan, PMFBY, KCC, PM-KUSUM |

## Setup

### 1. Install Flutter
```bash
# macOS
brew install flutter
# or download from https://docs.flutter.dev/get-started/install
flutter doctor
```

### 2. Create project and copy files
```bash
cd /Users/arnavmishra/ai/agri_advisory_app/mobile
flutter create krishimitra_fresh --org com.krishimitra --platforms android,ios
# Copy lib/, pubspec.yaml from this folder into krishimitra_fresh/
cp -r krishimitra/lib/   krishimitra_fresh/lib/
cp    krishimitra/pubspec.yaml krishimitra_fresh/pubspec.yaml
cd krishimitra_fresh
flutter pub get
```

### 3. Configure API URL
Use `--dart-define` for release builds so the same source works across dev,
staging, and production:
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
flutter build apk --release --dart-define=API_BASE_URL=https://your-render-url.onrender.com
flutter build appbundle --release --dart-define=API_BASE_URL=https://your-render-url.onrender.com
```

### 4. Android permissions
Add to `android/app/src/main/AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
```

### 5. iOS permissions
Add to `ios/Runner/Info.plist`:
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>नज़दीकी मंडी और मौसम के लिए GPS आवश्यक है</string>
<key>NSCameraUsageDescription</key>
<string>KrishiRaksha रोग पहचान के लिए कैमरा</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>फसल की तस्वीर अपलोड करें</string>
```

### 6. Run
```bash
flutter run                    # debug on connected device
flutter build apk --release    # release APK for Android
flutter build ios --release    # release for iOS (needs Xcode)
```

## Production APK
```bash
flutter build apk --release --dart-define=API_BASE_URL=https://agri-advisory-app.onrender.com
flutter build appbundle --release --dart-define=API_BASE_URL=https://agri-advisory-app.onrender.com
```
APK will be at: `build/app/outputs/flutter-apk/app-release.apk`

## Architecture

```
lib/
├── main.dart                    # App entry + HomeShell (bottom nav)
├── models/app_models.dart       # ChatMessage, WeatherData, MandiInfo, etc.
├── services/
│   ├── api_service.dart         # All backend REST calls
│   ├── location_service.dart    # GPS + SharedPrefs persistence
│   └── storage_service.dart     # Chat history, language, session
├── screens/
│   ├── chat_screen.dart         # AI chatbot
│   ├── mandi_screen.dart        # Nearby mandi + prices
│   ├── weather_screen.dart      # Weather forecast
│   ├── crop_recommendation_screen.dart
│   ├── disease_detection_screen.dart  # KrishiRaksha
│   └── schemes_screen.dart      # Govt schemes
├── widgets/
│   ├── chat_bubble.dart
│   └── suggested_queries.dart
└── utils/constants.dart         # AppConfig, AppColors, AppStrings
```
