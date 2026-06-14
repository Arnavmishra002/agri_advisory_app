/// KrishiMitra Weather Screen — hyperlocal weather + farming advice
library;

import 'package:flutter/material.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../utils/constants.dart';

class WeatherScreen extends StatefulWidget {
  final String language;
  const WeatherScreen({super.key, required this.language});
  @override
  State<WeatherScreen> createState() => _WeatherScreenState();
}

class _WeatherScreenState extends State<WeatherScreen> {
  final _api    = ApiService();
  final _locSvc = LocationService();

  WeatherData? _data;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final loc  = _locSvc.current;
      final data = await _api.getWeather(
        location: loc.displayName,
        lat:      loc.latitude,
        lon:      loc.longitude,
        language: widget.language,
      );
      setState(() { _data = data; _loading = false; });
    } catch (e) {
      setState(() { _loading = false; _error = e.toString(); });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1565C0),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('🌤️ मौसम', style: TextStyle(color: Colors.white)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white70),
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: Colors.white))
          : _error != null
              ? _buildError()
              : _buildWeather(),
    );
  }

  Widget _buildWeather() {
    final d = _data!;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Current weather card
        _currentWeatherCard(d),
        const SizedBox(height: 16),
        // Farming advice card
        if (d.farmingAdvice.isNotEmpty) _adviceCard(d.farmingAdvice),
        const SizedBox(height: 16),
        // 7-day forecast
        if (d.forecast.isNotEmpty) _forecastCard(d.forecast),
      ],
    );
  }

  Widget _currentWeatherCard(WeatherData d) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(children: [
        Text(d.location,
            style: const TextStyle(color: Colors.white70, fontSize: 16)),
        const SizedBox(height: 8),
        Text('${d.temperature?.toStringAsFixed(1) ?? '--'}°C',
            style: const TextStyle(
                color: Colors.white, fontSize: 64, fontWeight: FontWeight.w200)),
        Text(d.conditionLocal.isNotEmpty ? d.conditionLocal : d.condition,
            style: const TextStyle(color: Colors.white, fontSize: 18)),
        const SizedBox(height: 16),
        Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
          _statChip('💧 नमी', '${d.humidity?.toStringAsFixed(0) ?? '--'}%'),
          _statChip('🌧️ बारिश', '${d.rainfallMm?.toStringAsFixed(1) ?? '0'} mm'),
          _statChip('📡 स्रोत', d.isLive ? 'Live' : 'Cache'),
        ]),
      ]),
    );
  }

  Widget _statChip(String label, String value) => Column(children: [
    Text(label, style: const TextStyle(color: Colors.white60, fontSize: 11)),
    const SizedBox(height: 2),
    Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
  ]);

  Widget _adviceCard(String advice) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('🌾 ', style: TextStyle(fontSize: 20)),
        Expanded(
          child: Text(advice,
              style: const TextStyle(
                  fontSize: 14,
                  height: 1.5,
                  color: Color(AppColors.textPrimary))),
        ),
      ]),
    );
  }

  Widget _forecastCard(List<WeatherForecastDay> days) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.15),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Text('📅 7 दिन का पूर्वानुमान',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
          ...days.map((day) => ListTile(
            dense: true,
            title: Text(day.date,
                style: const TextStyle(color: Colors.white, fontSize: 13)),
            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
              Text('${day.rainfallMm?.toStringAsFixed(1) ?? '0'} mm',
                  style: const TextStyle(color: Colors.lightBlue, fontSize: 12)),
              const SizedBox(width: 12),
              Text('${day.maxTemp?.toStringAsFixed(0) ?? '--'}°C',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ]),
          )),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  Widget _buildError() => Center(
    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      const Icon(Icons.cloud_off, size: 48, color: Colors.white54),
      const SizedBox(height: 12),
      const Text('मौसम डेटा उपलब्ध नहीं।',
          style: TextStyle(color: Colors.white, fontSize: 16)),
      const SizedBox(height: 8),
      ElevatedButton(onPressed: _load, child: const Text('दोबारा कोशिश करें')),
    ]),
  );
}
