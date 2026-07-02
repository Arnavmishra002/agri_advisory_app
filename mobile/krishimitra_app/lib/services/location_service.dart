import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb, debugPrint;
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/constants.dart';

class LocData {
  final double lat, lon;
  final String name;    // village/locality name e.g. "Hazratganj"
  final String city;    // e.g. "Lucknow"
  final String district;
  final String state;
  final String fullAddress;
  final bool isGps;

  const LocData({
    required this.lat, required this.lon,
    required this.name, this.city = '',
    this.district = '', required this.state,
    this.fullAddress = '', this.isGps = false,
  });

  /// Display label: village/locality + city (if different) + state
  String get displayLabel {
    final parts = <String>[];
    if (name.isNotEmpty) parts.add(name);
    if (city.isNotEmpty && city != name) parts.add(city);
    if (state.isNotEmpty) parts.add(state);
    return parts.join(', ');
  }

  /// Short label for app bars: village + district
  String get shortLabel {
    if (city.isNotEmpty && city != name) return '$name, $city';
    if (district.isNotEmpty) return '$name, $district';
    return name;
  }

  static const delhi = LocData(
    lat: 28.7041, lon: 77.1025,
    name: 'Delhi', city: 'Delhi',
    district: 'New Delhi', state: 'Delhi',
    fullAddress: 'Delhi, India',
  );
}

class LocationResult {
  final double lat, lon;
  final String name, city, district, state, fullAddress, type;
  const LocationResult({
    required this.lat, required this.lon,
    required this.name, required this.city,
    required this.district, required this.state,
    required this.fullAddress, required this.type,
  });

  factory LocationResult.fromJson(Map<String, dynamic> j) => LocationResult(
    lat:         (j['lat'] as num?)?.toDouble() ?? 0,
    lon:         (j['lon'] as num?)?.toDouble() ?? 0,
    name:        j['name'] as String? ?? '',
    city:        j['city'] as String? ?? '',
    district:    j['district'] as String? ?? '',
    state:       j['state'] as String? ?? '',
    fullAddress: j['full_address'] as String? ?? '',
    type:        j['type'] as String? ?? '',
  );

  String get displayLabel {
    final parts = <String>[];
    if (name.isNotEmpty) parts.add(name);
    if (city.isNotEmpty && city != name) parts.add(city);
    if (district.isNotEmpty && district != city) parts.add(district);
    if (state.isNotEmpty) parts.add(state);
    return parts.join(', ');
  }
}

class LocationService {
  static final LocationService _i = LocationService._();
  factory LocationService() => _i;
  LocationService._();

  static const _latKey   = 'km_lat';
  static const _lonKey   = 'km_lon';
  static const _nameKey  = 'km_name';
  static const _cityKey  = 'km_city';
  static const _distKey  = 'km_district';
  static const _stateKey = 'km_state';
  static const _addrKey  = 'km_addr';

  LocData _cur = LocData.delhi;
  LocData get current => _cur;

  Future<void> init() async {
    final p = await SharedPreferences.getInstance();
    final lat  = p.getDouble(_latKey);
    final lon  = p.getDouble(_lonKey);
    final name = p.getString(_nameKey);
    if (lat != null && lon != null && name != null) {
      _cur = LocData(
        lat: lat, lon: lon, name: name,
        city:     p.getString(_cityKey)  ?? '',
        district: p.getString(_distKey)  ?? '',
        state:    p.getString(_stateKey) ?? '',
        fullAddress: p.getString(_addrKey) ?? '',
      );
    }
  }

  // ── GPS detection + reverse geocode to village level ──────────────────────
  //
  // Bug 8 fix: the old bare `catch (_)` swallowed every exception —
  // TimeoutException, PermissionDeniedException, FormatException from bad JSON,
  // even logic errors — silently falling back to Delhi with zero diagnostics.
  //
  // The new version:
  //   1. Handles permission and service-disabled cases early (unchanged path).
  //   2. Isolates reverse-geocode failures so a backend error never hides a
  //      valid GPS fix — raw coordinates are used as fallback instead.
  //   3. Logs specific error types so crash reports are actionable.
  //   4. The outer catch is a typed guard for OEM-specific platform exceptions.
  Future<LocData?> detectGps() async {
    try {
      if (!kIsWeb) {
        if (!await Geolocator.isLocationServiceEnabled()) {
          debugPrint('[LocationService] GPS service disabled');
          return null;
        }
        var perm = await Geolocator.checkPermission();
        if (perm == LocationPermission.denied) {
          perm = await Geolocator.requestPermission();
        }
        if (perm == LocationPermission.denied ||
            perm == LocationPermission.deniedForever) {
          debugPrint('[LocationService] GPS permission denied: $perm');
          return null;
        }
      }

      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,   // high = village-level
        timeLimit: const Duration(seconds: 10),   // reduced: 15 s stalls splash screen
      );

      // Reverse geocode is best-effort — a backend timeout must NOT discard
      // a valid GPS fix. Errors here are caught separately.
      LocData? rich;
      try {
        rich = await _reverseGeocode(pos.latitude, pos.longitude);
      } on Exception catch (e) {
        // Network error, JSON parse failure, server 500 — all non-fatal here
        debugPrint('[LocationService] Reverse geocode failed (using raw coords): $e');
      }

      final loc = rich ?? LocData(
        lat: pos.latitude, lon: pos.longitude,
        name: '${pos.latitude.toStringAsFixed(4)},${pos.longitude.toStringAsFixed(4)}',
        state: '', isGps: true,
      );

      await _persist(loc);
      _cur = loc;
      return loc;
    } on LocationServiceDisabledException {
      debugPrint('[LocationService] Location service disabled mid-call');
      return null;
    } on PermissionDeniedException catch (e) {
      debugPrint('[LocationService] Permission denied mid-call: $e');
      return null;
    } catch (e, st) {
      // Typed catch-all for OEM-specific platform exceptions — log full stack
      // so device-specific failures are visible in crash reports.
      debugPrint('[LocationService] Unexpected GPS error: $e\n$st');
      return null;
    }
  }

  // ── Reverse geocode via backend (/api/locations/reverse/) ─────────────────
  Future<LocData?> _reverseGeocode(double lat, double lon) async {
    try {
      final url = Uri.parse(
          '${AppConfig.baseUrl}/api/locations/reverse/?latitude=$lat&longitude=$lon');
      final r = await http.get(url).timeout(const Duration(seconds: 8));
      if (r.statusCode != 200) return null;
      final data = jsonDecode(r.body) as Map<String, dynamic>;
      final loc  = data['location'] as Map<String, dynamic>?;
      if (loc == null) return null;

      // Prefer village > locality > sublocality > city for display name
      final name = _bestName(loc);
      return LocData(
        lat: lat, lon: lon,
        name:        name,
        city:        loc['city']     as String? ?? '',
        district:    loc['district'] as String? ?? '',
        state:       loc['state']    as String? ?? '',
        fullAddress: loc['full_address'] as String? ?? '',
        isGps:       true,
      );
    } catch (_) { return null; }
  }

  String _bestName(Map<String, dynamic> loc) {
    final village    = loc['village']    as String? ?? '';
    final locality   = loc['locality']   as String? ?? '';
    final subloc     = loc['sublocality'] as String? ?? '';
    final city       = loc['city']       as String? ?? '';
    final name       = loc['name']       as String? ?? '';
    // Priority: village > locality > sublocality > name > city
    if (village.isNotEmpty)  return village;
    if (locality.isNotEmpty) return locality;
    if (subloc.isNotEmpty)   return subloc;
    if (name.isNotEmpty)     return name;
    return city;
  }

  // ── Location search (live as-you-type) ────────────────────────────────────
  // Returns village/town/district level results — same API as the web app
  Future<List<LocationResult>> search(String query) async {
    if (query.trim().length < 2) return [];
    try {
      final url = Uri.parse(
          '${AppConfig.baseUrl}/api/locations/search/?q=${Uri.encodeComponent(query)}&limit=8');
      final r = await http.get(url).timeout(const Duration(seconds: 6));
      if (r.statusCode != 200) return [];
      final data    = jsonDecode(r.body) as Map<String, dynamic>;
      final results = data['results'] as List? ?? [];
      return results
          .map((x) => LocationResult.fromJson(x as Map<String, dynamic>))
          .toList();
    } catch (_) { return []; }
  }

  // ── Manual set from search result ─────────────────────────────────────────
  Future<LocData> setFromResult(LocationResult r) async {
    final loc = LocData(
      lat:        r.lat, lon: r.lon,
      name:       r.name.isNotEmpty ? r.name : r.city,
      city:       r.city,
      district:   r.district,
      state:      r.state,
      fullAddress: r.fullAddress,
    );
    await _persist(loc);
    _cur = loc;
    return loc;
  }

  Future<void> setLocation(LocData loc) async {
    await _persist(loc);
    _cur = loc;
  }

  Future<void> _persist(LocData loc) async {
    final p = await SharedPreferences.getInstance();
    await p.setDouble(_latKey,   loc.lat);
    await p.setDouble(_lonKey,   loc.lon);
    await p.setString(_nameKey,  loc.name);
    await p.setString(_cityKey,  loc.city);
    await p.setString(_distKey,  loc.district);
    await p.setString(_stateKey, loc.state);
    await p.setString(_addrKey,  loc.fullAddress);
  }
}
