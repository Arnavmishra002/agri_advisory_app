/// KrishiMitra Location Service — GPS + persistent storage
library;

import 'package:geolocator/geolocator.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LocationData {
  final double latitude;
  final double longitude;
  final String displayName;
  final String state;
  final bool isGps;

  const LocationData({
    required this.latitude,
    required this.longitude,
    required this.displayName,
    required this.state,
    this.isGps = false,
  });

  static const LocationData defaultDelhi = LocationData(
    latitude:    28.7041,
    longitude:   77.1025,
    displayName: 'Delhi',
    state:       'Delhi',
  );
}

class LocationService {
  static final LocationService _instance = LocationService._internal();
  factory LocationService() => _instance;
  LocationService._internal();

  static const String _latKey  = 'km_lat';
  static const String _lonKey  = 'km_lon';
  static const String _nameKey = 'km_location_name';
  static const String _stateKey= 'km_state';

  LocationData _current = LocationData.defaultDelhi;
  LocationData get current => _current;

  // ── Load from storage ─────────────────────────────────────────────────────

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final lat   = prefs.getDouble(_latKey);
    final lon   = prefs.getDouble(_lonKey);
    final name  = prefs.getString(_nameKey);
    final state = prefs.getString(_stateKey);
    if (lat != null && lon != null && name != null) {
      _current = LocationData(
        latitude:    lat,
        longitude:   lon,
        displayName: name,
        state:       state ?? '',
      );
    }
  }

  // ── GPS detection ─────────────────────────────────────────────────────────

  Future<LocationData?> detectGps() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return null;

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return null;
    }
    if (permission == LocationPermission.deniedForever) return null;

    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.medium,
        timeLimit:       const Duration(seconds: 10),
      );
      // We'll update displayName via reverse geocode in the provider
      final loc = LocationData(
        latitude:    pos.latitude,
        longitude:   pos.longitude,
        displayName: '${pos.latitude.toStringAsFixed(2)}, ${pos.longitude.toStringAsFixed(2)}',
        state:       '',
        isGps:       true,
      );
      await _persist(loc);
      _current = loc;
      return loc;
    } catch (_) {
      return null;
    }
  }

  // ── Manual set ────────────────────────────────────────────────────────────

  Future<void> setLocation(LocationData loc) async {
    await _persist(loc);
    _current = loc;
  }

  Future<void> _persist(LocationData loc) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_latKey,   loc.latitude);
    await prefs.setDouble(_lonKey,   loc.longitude);
    await prefs.setString(_nameKey,  loc.displayName);
    await prefs.setString(_stateKey, loc.state);
  }

  // ── Well-known cities for manual selection ────────────────────────────────

  static const List<LocationData> popularCities = [
    LocationData(latitude: 28.7041, longitude: 77.1025, displayName: 'Delhi',        state: 'Delhi'),
    LocationData(latitude: 26.8467, longitude: 80.9462, displayName: 'Lucknow',       state: 'Uttar Pradesh'),
    LocationData(latitude: 25.5941, longitude: 85.1376, displayName: 'Patna',         state: 'Bihar'),
    LocationData(latitude: 26.9124, longitude: 75.7873, displayName: 'Jaipur',        state: 'Rajasthan'),
    LocationData(latitude: 23.2599, longitude: 77.4126, displayName: 'Bhopal',        state: 'Madhya Pradesh'),
    LocationData(latitude: 19.0760, longitude: 72.8777, displayName: 'Mumbai',        state: 'Maharashtra'),
    LocationData(latitude: 18.5204, longitude: 73.8567, displayName: 'Pune',          state: 'Maharashtra'),
    LocationData(latitude: 23.0225, longitude: 72.5714, displayName: 'Ahmedabad',     state: 'Gujarat'),
    LocationData(latitude: 12.9716, longitude: 77.5946, displayName: 'Bangalore',     state: 'Karnataka'),
    LocationData(latitude: 13.0827, longitude: 80.2707, displayName: 'Chennai',       state: 'Tamil Nadu'),
    LocationData(latitude: 17.3850, longitude: 78.4867, displayName: 'Hyderabad',     state: 'Telangana'),
    LocationData(latitude: 22.5726, longitude: 88.3639, displayName: 'Kolkata',       state: 'West Bengal'),
    LocationData(latitude: 30.7333, longitude: 76.7794, displayName: 'Chandigarh',    state: 'Punjab'),
    LocationData(latitude: 26.1445, longitude: 91.7362, displayName: 'Guwahati',      state: 'Assam'),
    LocationData(latitude: 20.2961, longitude: 85.8245, displayName: 'Bhubaneswar',   state: 'Odisha'),
  ];
}
