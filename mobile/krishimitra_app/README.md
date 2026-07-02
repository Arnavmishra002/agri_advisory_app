# KrishiMitra Mobile

Flutter client for KrishiMitra farmer advisory.

## Production Build

```bash
flutter pub get
flutter analyze
flutter build apk --release --dart-define=API_BASE_URL=https://agri-advisory-app.onrender.com
flutter build appbundle --release --dart-define=API_BASE_URL=https://agri-advisory-app.onrender.com
```

Use your deployed backend URL for `API_BASE_URL`. Local Android emulator builds can use:

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Flutter learning resources](https://docs.flutter.dev/reference/learning-resources)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.
