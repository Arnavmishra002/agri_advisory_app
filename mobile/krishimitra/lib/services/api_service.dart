/// KrishiMitra API Service — wraps all backend REST calls
library;

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import '../models/app_models.dart';
import '../utils/constants.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  final http.Client _client = http.Client();
  static const Duration _timeout = Duration(seconds: 30);

  // ── Location helpers ──────────────────────────────────────────────────────

  String _locationQuery({
    required String location,
    double? lat,
    double? lon,
    String? state,
  }) {
    final params = <String, String>{'location': location};
    if (lat  != null) params['latitude']  = lat.toStringAsFixed(6);
    if (lon  != null) params['longitude'] = lon.toStringAsFixed(6);
    if (state != null && state.isNotEmpty) params['state'] = state;
    return Uri(queryParameters: params).query;
  }

  // ── Chat ──────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> sendChatMessage({
    required String query,
    required String sessionId,
    required String language,
    String location = '',
    double? latitude,
    double? longitude,
    List<Map<String, String>> history = const [],
  }) async {
    final body = json.encode({
      'query':     query,
      'session_id': sessionId,
      'language':  language,
      'location':  location,
      if (latitude  != null) 'latitude':  latitude,
      if (longitude != null) 'longitude': longitude,
      'history': history.take(10).toList(),
    });

    final response = await _client
        .post(
          Uri.parse(AppConfig.chatEndpoint),
          headers: {'Content-Type': 'application/json'},
          body: body,
        )
        .timeout(_timeout);

    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    }
    throw ApiException('Chat failed: ${response.statusCode}');
  }

  // ── Weather ───────────────────────────────────────────────────────────────

  Future<WeatherData> getWeather({
    required String location,
    double? lat,
    double? lon,
    String language = 'hi',
  }) async {
    final q = _locationQuery(location: location, lat: lat, lon: lon);
    final url = '${AppConfig.weatherEndpoint}?$q&language=$language';

    final response = await _client
        .get(Uri.parse(url))
        .timeout(_timeout);

    if (response.statusCode == 200) {
      final data = json.decode(response.body) as Map<String, dynamic>;
      return WeatherData.fromJson(data);
    }
    throw ApiException('Weather failed: ${response.statusCode}');
  }

  // ── Market / Mandi ────────────────────────────────────────────────────────

  Future<List<MandiInfo>> getNearbyMandis({
    required String location,
    double? lat,
    double? lon,
    String? state,
    int radiusKm = 150,
  }) async {
    final q = _locationQuery(location: location, lat: lat, lon: lon, state: state);
    final url = '${AppConfig.mandisEndpoint}?$q&radius_km=$radiusKm';

    final response = await _client
        .get(Uri.parse(url))
        .timeout(_timeout);

    if (response.statusCode == 200) {
      final data = json.decode(response.body) as Map<String, dynamic>;
      final mandis = (data['mandis'] as List? ?? [])
          .map((m) => MandiInfo.fromJson(m as Map<String, dynamic>))
          .toList();
      return mandis;
    }
    throw ApiException('Mandis failed: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> getMarketPrices({
    required String location,
    double? lat,
    double? lon,
    String? state,
    String? mandi,
    String? crop,
  }) async {
    final params = <String, String>{'location': location};
    if (lat   != null) params['latitude']   = lat.toString();
    if (lon   != null) params['longitude']  = lon.toString();
    if (state != null) params['state']      = state;
    if (mandi != null) params['mandi']      = mandi;
    if (crop  != null) params['crop']       = crop;

    final uri = Uri.parse(AppConfig.marketEndpoint)
        .replace(queryParameters: params);

    final response = await _client
        .get(uri)
        .timeout(_timeout);

    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    }
    throw ApiException('Market failed: ${response.statusCode}');
  }

  // ── Crop Recommendation ───────────────────────────────────────────────────

  Future<List<CropRecommendation>> getCropRecommendations({
    required String location,
    double? lat,
    double? lon,
    String? state,
    String language = 'hi',
  }) async {
    final q = _locationQuery(location: location, lat: lat, lon: lon, state: state);
    final url = '${AppConfig.cropRecEndpoint}?$q&language=$language';

    final response = await _client
        .get(Uri.parse(url))
        .timeout(_timeout);

    if (response.statusCode == 200) {
      final data = json.decode(response.body) as Map<String, dynamic>;
      final recs = data['recommendations'] as List? ?? [];
      return recs
          .map((r) => CropRecommendation.fromJson(r as Map<String, dynamic>))
          .toList();
    }
    throw ApiException('Crop rec failed: ${response.statusCode}');
  }

  // ── Government Schemes ────────────────────────────────────────────────────

  Future<List<GovScheme>> getSchemes({
    String? state,
    String language = 'hi',
  }) async {
    final params = <String, String>{'language': language};
    if (state != null) params['state'] = state;
    final uri = Uri.parse(AppConfig.schemesEndpoint)
        .replace(queryParameters: params);

    final response = await _client
        .get(uri)
        .timeout(_timeout);

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final schemeList = (data is List)
          ? data
          : (data['results'] ?? data['schemes'] ?? []) as List;
      return schemeList
          .map((s) => GovScheme.fromJson(s as Map<String, dynamic>))
          .toList();
    }
    throw ApiException('Schemes failed: ${response.statusCode}');
  }

  // ── Disease Diagnosis ─────────────────────────────────────────────────────

  Future<Map<String, dynamic>> diagnoseCropDisease({
    required File imageFile,
    required String cropName,
    required String sessionId,
    String language = 'hi',
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse(AppConfig.diagnosticsEndpoint),
    );
    request.fields['crop_name']  = cropName;
    request.fields['session_id'] = sessionId;
    request.fields['language']   = language;
    request.files.add(
      await http.MultipartFile.fromPath('image', imageFile.path),
    );

    final streamed = await request.send().timeout(_timeout);
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    }
    throw ApiException('Diagnosis failed: ${response.statusCode}');
  }

  // ── Farmer Profile ────────────────────────────────────────────────────────

  Future<void> upsertFarmerProfile(FarmerProfile profile) async {
    final response = await _client
        .post(
          Uri.parse(AppConfig.farmerProfileEndpoint),
          headers: {'Content-Type': 'application/json'},
          body: json.encode(profile.toJson()),
        )
        .timeout(_timeout);

    if (response.statusCode >= 400) {
      throw ApiException('Profile save failed: ${response.statusCode}');
    }
  }
}

class ApiException implements Exception {
  final String message;
  const ApiException(this.message);
  @override
  String toString() => 'ApiException: $message';
}
