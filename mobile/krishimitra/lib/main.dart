/// KrishiMitra AI — Flutter App Entry Point
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/chat_screen.dart';
import 'screens/mandi_screen.dart';
import 'screens/weather_screen.dart';
import 'screens/crop_recommendation_screen.dart';
import 'screens/disease_detection_screen.dart';
import 'screens/schemes_screen.dart';
import 'services/location_service.dart';
import 'services/storage_service.dart';
import 'utils/constants.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Lock to portrait
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  // Init services
  await LocationService().init();
  runApp(const KrishiMitraApp());
}

class KrishiMitraApp extends StatelessWidget {
  const KrishiMitraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title:         AppConfig.appName,
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3:    true,
        colorSchemeSeed: const Color(AppColors.primary),
        fontFamily:      'NotoSansDevanagari',
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(AppColors.primary),
          foregroundColor: Colors.white,
          elevation: 0,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor:  const Color(AppColors.primary),
            foregroundColor:  Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        cardTheme: const CardTheme(
          elevation: 2,
          shadowColor: Colors.black12,
        ),
      ),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('hi', 'IN'),
        Locale('en', 'IN'),
        Locale('mr', 'IN'),
        Locale('ta', 'IN'),
        Locale('te', 'IN'),
        Locale('gu', 'IN'),
        Locale('kn', 'IN'),
        Locale('ml', 'IN'),
        Locale('pa', 'IN'),
        Locale('bn', 'IN'),
      ],
      home: const HomeShell(),
    );
  }
}

// ── Home shell with bottom navigation ────────────────────────────────────────

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final _locSvc  = LocationService();
  final _storage = StorageService();

  int    _tab      = 0;
  String _language = 'hi';
  String _sessionId = '';
  bool   _initDone  = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    _language  = await _storage.getLanguage();
    _sessionId = await _storage.getOrCreateSessionId();
    // Try GPS on first launch
    await _locSvc.detectGps();
    if (mounted) setState(() => _initDone = true);
  }

  static const List<BottomNavigationBarItem> _navItems = [
    BottomNavigationBarItem(icon: Icon(Icons.chat),          label: 'Chat'),
    BottomNavigationBarItem(icon: Icon(Icons.storefront),    label: 'Mandi'),
    BottomNavigationBarItem(icon: Icon(Icons.wb_sunny),      label: 'Mausam'),
    BottomNavigationBarItem(icon: Icon(Icons.grass),         label: 'Fasal'),
    BottomNavigationBarItem(icon: Icon(Icons.more_horiz),    label: 'More'),
  ];

  @override
  Widget build(BuildContext context) {
    if (!_initDone) {
      return const Scaffold(
        backgroundColor: Color(AppColors.primary),
        body: Center(child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('🌾', style: TextStyle(fontSize: 72)),
            SizedBox(height: 12),
            Text('KrishiMitra AI',
                style: TextStyle(color: Colors.white, fontSize: 28,
                    fontWeight: FontWeight.bold)),
            SizedBox(height: 24),
            CircularProgressIndicator(color: Colors.white70),
          ],
        )),
      );
    }

    final screens = [
      ChatScreen(language: _language, sessionId: _sessionId),
      MandiScreen(language: _language),
      WeatherScreen(language: _language),
      CropRecommendationScreen(language: _language),
      MoreScreen(language: _language, onLanguageChange: _changeLanguage),
    ];

    return Scaffold(
      body: IndexedStack(index: _tab, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        backgroundColor: Colors.white,
        elevation: 8,
        destinations: const [
          NavigationDestination(icon: Icon(Icons.chat_bubble_outline),
              selectedIcon: Icon(Icons.chat_bubble), label: 'Chat'),
          NavigationDestination(icon: Icon(Icons.storefront_outlined),
              selectedIcon: Icon(Icons.storefront), label: 'Mandi'),
          NavigationDestination(icon: Icon(Icons.wb_sunny_outlined),
              selectedIcon: Icon(Icons.wb_sunny), label: 'Mausam'),
          NavigationDestination(icon: Icon(Icons.grass_outlined),
              selectedIcon: Icon(Icons.grass), label: 'Fasal'),
          NavigationDestination(icon: Icon(Icons.apps_outlined),
              selectedIcon: Icon(Icons.apps), label: 'More'),
        ],
      ),
    );
  }

  void _changeLanguage(String lang) async {
    await _storage.setLanguage(lang);
    setState(() => _language = lang);
  }
}

// ── More screen — settings, language, disease detection, schemes ─────────────

class MoreScreen extends StatelessWidget {
  final String language;
  final void Function(String) onLanguageChange;
  const MoreScreen({
    super.key,
    required this.language,
    required this.onLanguageChange,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: AppBar(
        backgroundColor: const Color(AppColors.primary),
        title: const Text('More', style: TextStyle(color: Colors.white)),
      ),
      body: ListView(
        children: [
          // Language selector
          ListTile(
            leading: const CircleAvatar(
              backgroundColor: Color(AppColors.chipGreen),
              child: Text('🌐', style: TextStyle(fontSize: 18)),
            ),
            title: const Text('भाषा / Language'),
            subtitle: Text(AppStrings.languages[language] ?? language),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _showLanguagePicker(context),
          ),
          const Divider(height: 1),
          // Disease detection
          ListTile(
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFFFF3E0),
              child: Text('🔬', style: TextStyle(fontSize: 18)),
            ),
            title: const Text('KrishiRaksha — रोग पहचान'),
            subtitle: const Text('फसल की फोटो से रोग AI पहचान'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => DiseaseDetectionScreen(language: language))),
          ),
          const Divider(height: 1),
          // Schemes
          ListTile(
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFE8EAF6),
              child: Text('🏛️', style: TextStyle(fontSize: 18)),
            ),
            title: const Text('सरकारी योजनाएं'),
            subtitle: const Text('PM-Kisan, PMFBY, KCC, PM-KUSUM'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => SchemesScreen(language: language))),
          ),
          const Divider(height: 1),
          // Location
          ListTile(
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFE3F2FD),
              child: Text('📍', style: TextStyle(fontSize: 18)),
            ),
            title: const Text('लोकेशन बदलें'),
            subtitle: Text(LocationService().current.displayName),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _showLocationPicker(context),
          ),
          const Divider(height: 1),
          // About
          const AboutListTile(
            icon: Icon(Icons.info_outline),
            applicationName: 'KrishiMitra AI',
            applicationVersion: AppConfig.appVersion,
            applicationLegalese: '© 2026 KrishiMitra AI\nOpen source under MIT License',
            child: Text('About'),
          ),
        ],
      ),
    );
  }

  void _showLanguagePicker(BuildContext ctx) {
    showModalBottomSheet(
      context: ctx,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => ListView(
        padding: const EdgeInsets.all(16),
        shrinkWrap: true,
        children: [
          const Text('भाषा चुनें / Select Language',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 12),
          ...AppStrings.languages.entries.map((e) => ListTile(
            title: Text(e.value),
            subtitle: Text(e.key),
            selected: language == e.key,
            selectedColor: const Color(AppColors.primary),
            trailing: language == e.key
                ? const Icon(Icons.check, color: Color(AppColors.primary))
                : null,
            onTap: () {
              onLanguageChange(e.key);
              Navigator.pop(ctx);
            },
          )),
        ],
      ),
    );
  }

  void _showLocationPicker(BuildContext ctx) {
    final locSvc = LocationService();
    showModalBottomSheet(
      context: ctx,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        maxChildSize: 0.9,
        minChildSize: 0.3,
        expand: false,
        builder: (_, ctrl) => ListView(
          controller: ctrl,
          padding: const EdgeInsets.all(16),
          children: [
            Row(children: [
              const Text('लोकेशन चुनें',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const Spacer(),
              TextButton.icon(
                icon: const Icon(Icons.gps_fixed, size: 16),
                label: const Text('GPS', style: TextStyle(fontSize: 12)),
                onPressed: () async {
                  final loc = await locSvc.detectGps();
                  if (loc != null && ctx.mounted) Navigator.pop(ctx);
                },
              ),
            ]),
            const Divider(),
            ...LocationService.popularCities.map((city) => ListTile(
              dense: true,
              leading: const Icon(Icons.location_city, size: 18),
              title: Text(city.displayName),
              subtitle: Text(city.state),
              selected: locSvc.current.displayName == city.displayName,
              onTap: () async {
                await locSvc.setLocation(city);
                if (ctx.mounted) Navigator.pop(ctx);
              },
            )),
          ],
        ),
      ),
    );
  }
}
