import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'screens/chat_screen.dart';
import 'screens/mandi_screen.dart';
import 'screens/weather_screen.dart';
import 'screens/crop_rec_screen.dart';
import 'screens/more_screen.dart';
import 'services/location_service.dart';
import 'services/storage_service.dart';
import 'services/cache_service.dart';
import 'utils/constants.dart';
import 'widgets/location_picker.dart';

// DSN injected at build time: --dart-define=SENTRY_DSN=https://...
const _sentryDsn = String.fromEnvironment('SENTRY_DSN', defaultValue: '');

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // ── Offline cache (Hive) ───────────────────────────────────────
  await Hive.initFlutter();
  await CacheService().init();

  Future<void> launchApp() async {
    await SystemChrome.setPreferredOrientations(
        [DeviceOrientation.portraitUp, DeviceOrientation.portraitDown]);
    await LocationService().init();
    runApp(const KrishiMitraApp());
  }

  // ── Sentry (Task 7 / RAG-6) ───────────────────────────────────
  if (_sentryDsn.isNotEmpty) {
    await SentryFlutter.init(
      (options) {
        options.dsn = _sentryDsn;
        options.tracesSampleRate = 0.1;
        options.debug = false;
      },
      appRunner: launchApp,
    );
  } else {
    await launchApp();
  }
}

class KrishiMitraApp extends StatelessWidget {
  const KrishiMitraApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: AppConfig.appName,
    debugShowCheckedModeBanner: false,
    theme: _buildTheme(),
    localizationsDelegates: const [
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: const [
      Locale('hi', 'IN'), Locale('en', 'IN'), Locale('mr', 'IN'),
      Locale('ta', 'IN'), Locale('te', 'IN'), Locale('gu', 'IN'),
      Locale('pa', 'IN'), Locale('bn', 'IN'),
    ],
    home: const HomeShell(),
  );

  ThemeData _buildTheme() => ThemeData(
    useMaterial3: true,
    colorSchemeSeed: const Color(AppColors.primary),
    fontFamily: 'Roboto',
    cardTheme: CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      color: Colors.white,
    ),
    appBarTheme: const AppBarTheme(
      elevation: 0,
      scrolledUnderElevation: 2,
    ),
  );
}

// ── Home shell ────────────────────────────────────────────────────────────────
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int     _tab    = 0;
  String  _lang   = 'hi';
  String  _sessId = '';
  LocData _loc    = LocData.delhi;
  bool    _ready  = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    _lang   = await StorageService().getLanguage();
    _sessId = await StorageService().getOrCreateSession();
    final gps = await LocationService().detectGps();
    _loc = gps ?? LocationService().current;
    if (mounted) setState(() => _ready = true);
  }

  void _onLocChanged(LocData loc) => setState(() => _loc = loc);

  @override
  Widget build(BuildContext context) {
    if (!_ready) return _splash();

    final screens = [
      ChatScreen(lang: _lang, sessId: _sessId),
      MandiScreen(lang: _lang),
      WeatherScreen(lang: _lang),
      CropRecScreen(lang: _lang),
      MoreScreen(lang: _lang, onLangChange: (l) async {
        await StorageService().setLanguage(l);
        setState(() => _lang = l);
      }),
    ];

    return Scaffold(
      body: Column(children: [
        _LocationBar(loc: _loc, onTap: _openLocationPicker),
        Expanded(child: IndexedStack(index: _tab, children: screens)),
      ]),
      bottomNavigationBar: _buildNavBar(),
    );
  }

  void _openLocationPicker() {
    LocationPickerSheet.show(context, onSelected: (loc) {
      _onLocChanged(loc);
      setState(() {});
    });
  }

  Widget _buildNavBar() => NavigationBar(
    selectedIndex: _tab,
    onDestinationSelected: (i) => setState(() => _tab = i),
    backgroundColor: Colors.white,
    elevation: 8,
    indicatorColor: const Color(AppColors.primary).withValues(alpha: 0.12),
    destinations: const [
      NavigationDestination(
        icon: Icon(Icons.chat_bubble_outline),
        selectedIcon: Icon(Icons.chat_bubble, color: Color(AppColors.primary)),
        label: 'Chat'),
      NavigationDestination(
        icon: Icon(Icons.storefront_outlined),
        selectedIcon: Icon(Icons.storefront, color: Color(AppColors.primary)),
        label: 'Mandi'),
      NavigationDestination(
        icon: Icon(Icons.wb_sunny_outlined),
        selectedIcon: Icon(Icons.wb_sunny, color: Color(AppColors.primary)),
        label: 'Mausam'),
      NavigationDestination(
        icon: Icon(Icons.grass_outlined),
        selectedIcon: Icon(Icons.grass, color: Color(AppColors.primary)),
        label: 'Fasal'),
      NavigationDestination(
        icon: Icon(Icons.apps_outlined),
        selectedIcon: Icon(Icons.apps, color: Color(AppColors.primary)),
        label: 'More'),
    ],
  );

  Widget _splash() => Scaffold(
    backgroundColor: const Color(AppColors.primary),
    body: Center(child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Animated logo
        TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.5, end: 1.0),
          duration: const Duration(milliseconds: 800),
          curve: Curves.elasticOut,
          builder: (_, v, child) => Transform.scale(scale: v, child: child),
          child: Container(
            width: 100, height: 100,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(28),
            ),
            child: const Center(
              child: Text('🌾', style: TextStyle(fontSize: 60)),
            ),
          ),
        ),
        const SizedBox(height: 24),
        const Text('KrishiMitra AI',
          style: TextStyle(color: Colors.white, fontSize: 32,
              fontWeight: FontWeight.bold, letterSpacing: 0.5)),
        const SizedBox(height: 6),
        const Text('आपका स्मार्ट कृषि सहायक',
          style: TextStyle(color: Colors.white70, fontSize: 15)),
        const SizedBox(height: 48),
        const SizedBox(
          width: 32, height: 32,
          child: CircularProgressIndicator(
            color: Colors.white70, strokeWidth: 2.5),
        ),
        const SizedBox(height: 14),
        const Text('📍 गाँव खोज रहे हैं...',
          style: TextStyle(color: Colors.white54, fontSize: 12)),
      ],
    )),
  );
}

// ── Location bar ──────────────────────────────────────────────────────────────
class _LocationBar extends StatelessWidget {
  final LocData loc;
  final VoidCallback onTap;
  const _LocationBar({required this.loc, required this.onTap});

  @override
  Widget build(BuildContext context) => Material(
    elevation: 2,
    color: Colors.white,
    child: InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 8, 12, 8),
        child: Row(children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: const Color(AppColors.primary).withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.location_on,
                color: Color(AppColors.primary), size: 18),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                loc.name.isEmpty ? 'लोकेशन चुनें' : loc.name,
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 14,
                    color: Color(AppColors.textPrimary)),
                maxLines: 1, overflow: TextOverflow.ellipsis,
              ),
              if (loc.district.isNotEmpty || loc.state.isNotEmpty)
                Text(
                  [if (loc.district.isNotEmpty) loc.district,
                   if (loc.state.isNotEmpty) loc.state].join(', '),
                  style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                ),
            ],
          )),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              border: Border.all(
                  color: const Color(AppColors.primary).withValues(alpha: 0.4)),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Row(mainAxisSize: MainAxisSize.min, children: [
              Text('बदलें',
                  style: TextStyle(fontSize: 11, color: Color(AppColors.primary),
                      fontWeight: FontWeight.w600)),
              SizedBox(width: 2),
              Icon(Icons.keyboard_arrow_down,
                  size: 14, color: Color(AppColors.primary)),
            ]),
          ),
        ]),
      ),
    ),
  );
}
