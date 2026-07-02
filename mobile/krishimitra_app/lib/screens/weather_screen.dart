import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/cache_service.dart';
import '../services/location_service.dart';
import '../utils/constants.dart';
import '../widgets/error_view.dart';

class WeatherScreen extends StatefulWidget {
  final String lang;
  const WeatherScreen({super.key, required this.lang});
  @override State<WeatherScreen> createState() => _WeatherScreenState();
}

class _WeatherScreenState extends State<WeatherScreen>
    with AutomaticKeepAliveClientMixin {
  final _api   = ApiService();
  final _loc   = LocationService();
  final _cache = CacheService();

  WeatherData? _data;
  bool   _loading   = true;
  String? _err;
  bool   _fromCache = false;
  int?   _cacheAge; // hours

  @override bool get wantKeepAlive => true;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load({bool forceRefresh = false}) async {
    setState(() { _loading = true; _err = null; _fromCache = false; });
    final l       = _loc.current;
    final cacheKey = CacheService.key('weather', l.name, widget.lang);

    // ── Check connectivity first ───────────────────────────────
    final conn = await Connectivity().checkConnectivity();
    final offline = conn.contains(ConnectivityResult.none);

    if (offline) {
      final cached = _cache.get(cacheKey, CacheService.weatherTtl);
      if (cached != null) {
        setState(() {
          _data      = WeatherData.fromJson(Map<String, dynamic>.from(cached as Map));
          _fromCache = true;
          _cacheAge  = _cache.ageHours(cacheKey);
          _loading   = false;
        });
        return;
      }
      setState(() { _loading = false; _err = 'offline'; });
      return;
    }

    // ── Online: fetch then cache ───────────────────────────────
    try {
      // When user pulls to refresh, hit /api/weather/refresh/ to bypass server cache
      final d = forceRefresh
          ? await _api.getWeatherFresh(
              location: l.name, lat: l.lat, lon: l.lon, lang: widget.lang)
          : await _api.getWeather(
              location: l.name, lat: l.lat, lon: l.lon, lang: widget.lang);
      await _cache.set(cacheKey, _weatherToJson(d));
      setState(() { _data = d; _loading = false; _fromCache = false; });
    } catch (_) {
      // Network error — try cache even if not expired
      final cached = _cache.get(cacheKey, const Duration(hours: 24));
      if (cached != null) {
        setState(() {
          _data      = WeatherData.fromJson(Map<String, dynamic>.from(cached as Map));
          _fromCache = true;
          _cacheAge  = _cache.ageHours(cacheKey);
          _loading   = false;
        });
      } else {
        setState(() { _loading = false; _err = 'network'; });
      }
    }
  }

  // Minimal JSON serializer for WeatherData (cache only needs the raw backend shape)
  static Map<String, dynamic> _weatherToJson(WeatherData d) => {
    'location':         d.location,
    'is_live':          d.isLive,
    'data_source':      d.dataSource,
    'farming_advice':   d.farmingAdvice,
    'data_age_minutes': d.dataAgeMinutes,
    'fetched_at':       d.fetchedAt,
    'current': {
      'temperature':     d.temperature,
      'humidity':        d.humidity,
      'rainfall_mm':     d.rainfallMm,
      'condition':       d.condition,
      'condition_local': d.conditionLocal,
    },
    'forecast_7day': d.forecast.map((f) => {
      'date': f.date, 'max_temp': f.maxTemp, 'min_temp': f.minTemp,
      'rainfall_mm': f.rainfallMm, 'rain_probability': f.rainProb,
    }).toList(),
  };

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF0D1B2A), Color(0xFF1565C0), Color(0xFF1976D2)],
            begin: Alignment.topCenter, end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: _loading
              ? _loadingView()
              : _err != null && _data == null
                  ? ErrorView(
                      error: _err == 'offline'
                          ? 'इंटरनेट नहीं है और कोई कैश नहीं मिला'
                          : _err!,
                      onRetry: _load,
                      title: 'मौसम डेटा उपलब्ध नहीं',
                    )
                  : _body(),
        ),
      ),
    );
  }

  Widget _loadingView() => Center(child: Column(
    mainAxisAlignment: MainAxisAlignment.center, children: [
    const SizedBox(
      width: 40, height: 40,
      child: CircularProgressIndicator(color: Colors.white70, strokeWidth: 2.5)),
    const SizedBox(height: 16),
    Text(
      widget.lang == 'hi' ? 'मौसम डेटा लोड हो रहा है...' : 'Loading weather...',
      style: const TextStyle(color: Colors.white70, fontSize: 14)),
  ]));

  Widget _body() {
    final d = _data!;
    return RefreshIndicator(
      onRefresh: () => _load(forceRefresh: true),
      color: Colors.white,
      backgroundColor: const Color(AppColors.primary),
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.all(20),
            sliver: SliverList(delegate: SliverChildListDelegate([
              // Offline banner
              if (_fromCache) _offlineBanner(),
              if (_fromCache) const SizedBox(height: 14),
              _currentCard(d),
              const SizedBox(height: 20),
              if (d.farmingAdvice.isNotEmpty) _adviceCard(d.farmingAdvice),
              if (d.farmingAdvice.isNotEmpty) const SizedBox(height: 20),
              if (d.forecast.isNotEmpty) _forecastCard(d.forecast),
              const SizedBox(height: 12),
              _sourceCard(d),
              const SizedBox(height: 24),
            ])),
          ),
        ],
      ),
    );
  }

  Widget _offlineBanner() => Container(
    padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
    decoration: BoxDecoration(
      color: Colors.orange.withValues(alpha: 0.2),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: Colors.orange.withValues(alpha: 0.4)),
    ),
    child: Row(children: [
      const Icon(Icons.wifi_off_rounded, color: Colors.orange, size: 16),
      const SizedBox(width: 8),
      Expanded(child: Text(
        widget.lang == 'hi'
            ? '📶 ऑफ़लाइन — ${_cacheAge ?? 0} घंटे पहले का डेटा'
            : '📶 Offline — showing data from ${_cacheAge ?? 0} hours ago',
        style: const TextStyle(color: Colors.orange, fontSize: 12),
      )),
    ]),
  );

  Widget _currentCard(WeatherData d) {
    return Column(children: [
      // Header row
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Row(children: [
          const Icon(Icons.location_on, color: Colors.white60, size: 14),
          const SizedBox(width: 4),
          Flexible(child: Text(d.location,
              style: const TextStyle(color: Colors.white70, fontSize: 14),
              overflow: TextOverflow.ellipsis)),
        ]),
        GestureDetector(
          onTap: () => _load(forceRefresh: true),
          child: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.refresh_rounded, color: Colors.white, size: 18),
          ),
        ),
      ]),
      const SizedBox(height: 28),
      // Temperature display
      Row(mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(
          '${d.temperature?.toStringAsFixed(0) ?? '--'}',
          style: const TextStyle(color: Colors.white, fontSize: 96,
              fontWeight: FontWeight.w100, height: 1.0),
        ),
        const Padding(
          padding: EdgeInsets.only(top: 14),
          child: Text('°C', style: TextStyle(color: Colors.white60, fontSize: 28,
              fontWeight: FontWeight.w200)),
        ),
      ]),
      const SizedBox(height: 4),
      Text(
        d.conditionLocal.isNotEmpty ? d.conditionLocal : d.condition,
        style: const TextStyle(color: Colors.white, fontSize: 18,
            fontWeight: FontWeight.w300, letterSpacing: 0.5),
      ),
      if (d.ageLabel.isNotEmpty) ...[
        const SizedBox(height: 6),
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          const Icon(Icons.access_time_rounded, color: Colors.white38, size: 12),
          const SizedBox(width: 4),
          Text(d.ageLabel,
              style: const TextStyle(color: Colors.white38, fontSize: 11)),
        ]),
      ],
      const SizedBox(height: 28),
      // Stats row
      Container(
        padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 20),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.13),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
        ),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
          _stat('💧', widget.lang == 'hi' ? 'नमी' : 'Humidity',
              '${d.humidity?.toStringAsFixed(0) ?? '--'}%'),
          _vDivider(),
          _stat('🌧️', widget.lang == 'hi' ? 'बारिश' : 'Rain',
              '${d.rainfallMm?.toStringAsFixed(1) ?? '0'} mm'),
          _vDivider(),
          _stat('📡', widget.lang == 'hi' ? 'स्रोत' : 'Source',
              d.isLive ? 'Live' : 'Cache'),
        ]),
      ),
    ]);
  }

  Widget _vDivider() =>
      Container(height: 40, width: 1, color: Colors.white.withValues(alpha: 0.2));

  Widget _stat(String emoji, String label, String value) =>
      Column(mainAxisSize: MainAxisSize.min, children: [
    Text(emoji, style: const TextStyle(fontSize: 22)),
    const SizedBox(height: 4),
    Text(label, style: const TextStyle(color: Colors.white54, fontSize: 10)),
    const SizedBox(height: 3),
    Text(value, style: const TextStyle(
        color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
  ]);

  Widget _adviceCard(String advice) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      boxShadow: [BoxShadow(
          color: Colors.black.withValues(alpha: 0.12),
          blurRadius: 12, offset: const Offset(0, 4))],
    ),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(AppColors.chipGreen),
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Text('🌾', style: TextStyle(fontSize: 24)),
      ),
      const SizedBox(width: 12),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(
          widget.lang == 'hi' ? 'कृषि सलाह' : 'Farming Advisory',
          style: const TextStyle(fontWeight: FontWeight.bold,
              fontSize: 14, color: Color(AppColors.primary)),
        ),
        const SizedBox(height: 6),
        Text(advice, style: const TextStyle(fontSize: 13, height: 1.55,
            color: Color(AppColors.textPrimary))),
      ])),
    ]),
  );

  Widget _forecastCard(List<ForecastDay> days) => Container(
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: 0.13),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
    ),
    child: Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
        child: Row(children: [
          const Icon(Icons.calendar_month_outlined, color: Colors.white70, size: 16),
          const SizedBox(width: 6),
          Text(
            widget.lang == 'hi' ? '7 दिन का पूर्वानुमान' : '7-Day Forecast',
            style: const TextStyle(color: Colors.white,
                fontWeight: FontWeight.w600, fontSize: 14),
          ),
        ]),
      ),
      const Divider(color: Colors.white24, height: 1),
      ...days.take(7).map(_forecastRow),
      const SizedBox(height: 8),
    ]),
  );

  Widget _forecastRow(ForecastDay day) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
    child: Row(children: [
      Expanded(child: Text(day.date,
          style: const TextStyle(color: Colors.white70, fontSize: 13))),
      if (day.rainProb != null && day.rainProb! > 15)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          margin: const EdgeInsets.only(right: 10),
          decoration: BoxDecoration(
            color: Colors.blue.withValues(alpha: 0.25),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text('🌧 ${day.rainProb}%',
              style: const TextStyle(color: Colors.lightBlue, fontSize: 11)),
        ),
      Text('${day.minTemp?.toStringAsFixed(0) ?? '--'}°',
          style: const TextStyle(color: Colors.white60, fontSize: 13)),
      const SizedBox(width: 8),
      Text('${day.maxTemp?.toStringAsFixed(0) ?? '--'}°',
          style: const TextStyle(color: Colors.white,
              fontWeight: FontWeight.bold, fontSize: 13)),
    ]),
  );

  Widget _sourceCard(WeatherData d) => Center(
    child: Text(d.dataSource,
        style: const TextStyle(color: Colors.white30, fontSize: 10),
        textAlign: TextAlign.center),
  );
}
