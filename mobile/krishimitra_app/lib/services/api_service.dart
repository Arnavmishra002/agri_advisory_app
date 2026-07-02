import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart' show kIsWeb, debugPrint;
import 'package:http/http.dart' as http;
import '../models/app_models.dart';
import '../utils/constants.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  const ApiException(this.message, {this.statusCode});
  @override String toString() => 'ApiException($statusCode): $message';

  String get displayMessage {
    if (statusCode == null) return 'नेटवर्क त्रुटि — सर्वर से संपर्क नहीं हो सका।';
    if ((statusCode ?? 0) >= 500) return 'सर्वर में समस्या। थोड़ी देर बाद कोशिश करें।';
    return 'डेटा लोड नहीं हो सका। (${statusCode})';
  }
}

class ApiService {
  static final ApiService _i = ApiService._();
  factory ApiService() => _i;
  ApiService._();

  static const _timeout = Duration(seconds: 30);
  final _client = http.Client();

  String _locQ({required String loc, double? lat, double? lon, String? state}) {
    final p = <String, String>{'location': loc};
    if (lat   != null) p['latitude']  = lat.toStringAsFixed(6);
    if (lon   != null) p['longitude'] = lon.toStringAsFixed(6);
    if (state != null && state.isNotEmpty) p['state'] = state;
    return Uri(queryParameters: p).query;
  }

  Future<Map<String, dynamic>> _get(String url) async {
    debugPrint('GET $url');
    try {
      final r = await _client.get(Uri.parse(url)).timeout(_timeout);
      if (r.statusCode == 200) return jsonDecode(r.body) as Map<String, dynamic>;
      throw ApiException('GET $url → ${r.statusCode}', statusCode: r.statusCode);
    } on SocketException catch (e) {
      throw ApiException('Cannot connect: $e');
    } on http.ClientException catch (e) {
      throw ApiException('HTTP error: $e');
    }
  }

  Future<Map<String, dynamic>> _post(String url, Map<String, dynamic> body) async {
    debugPrint('POST $url');
    try {
      final r = await _client.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      ).timeout(_timeout);
      if (r.statusCode == 200 || r.statusCode == 201) {
        return jsonDecode(r.body) as Map<String, dynamic>;
      }
      throw ApiException('POST $url → ${r.statusCode}', statusCode: r.statusCode);
    } on SocketException catch (e) {
      throw ApiException('Cannot connect: $e');
    }
  }

  // ── Health ───────────────────────────────────────────────────────────────
  Future<bool> isReachable() async {
    try {
      final r = await _client
          .get(Uri.parse('${AppConfig.baseUrl}/api/health/'))
          .timeout(const Duration(seconds: 5));
      return r.statusCode == 200;
    } catch (_) { return false; }
  }

  // ── Chat (non-streaming, kept for backwards compat) ───────────────────────
  Future<Map<String, dynamic>> chat({
    required String query,
    required String sessionId,
    required String language,
    required String location,
    double? lat,
    double? lon,
    List<Map<String, String>> history = const [],
  }) => _post('${AppConfig.baseUrl}/api/chatbot/query/', {
    'query': query, 'session_id': sessionId, 'language': language,
    'location': location,
    if (lat != null) 'latitude': lat,
    if (lon != null) 'longitude': lon,
    'history': history.take(8).toList(),
    'fast_mode': false,
  });

  // ── Chat streaming (SSE — Task 11 / RAG-7) ────────────────────────────────
  /// Opens an SSE connection to /api/chatbot/stream/ and yields parsed frames.
  ///
  /// Each frame is one of:
  ///   {"token": "..."}          — partial response token, append to bubble
  ///   {"done": true, ...}       — stream complete, contains intent/language/etc.
  ///   {"error": "...", ...}     — server-side stream error
  ///
  /// Usage:
  ///   await for (final frame in _api.chatStream(...)) {
  ///     if (frame['token'] != null) setState(() => _buf += frame['token']);
  ///     if (frame['done'] == true) _finalize(frame);
  ///   }
  Stream<Map<String, dynamic>> chatStream({
    required String query,
    required String sessionId,
    required String language,
    required String location,
    double? lat,
    double? lon,
    List<Map<String, String>> history = const [],
  }) async* {
    final body = jsonEncode({
      'query': query, 'session_id': sessionId, 'language': language,
      'location': location,
      if (lat != null) 'latitude': lat,
      if (lon != null) 'longitude': lon,
      'history': history.take(8).toList(),
      'fast_mode': false,
    });

    debugPrint('SSE POST ${AppConfig.baseUrl}/api/chatbot/stream/');

    try {
      final request = http.Request(
        'POST',
        Uri.parse('${AppConfig.baseUrl}/api/chatbot/stream/'),
      )
        ..headers['Content-Type'] = 'application/json'
        ..headers['Accept']       = 'text/event-stream'
        ..body = body;

      final streamed = await _client.send(request).timeout(_timeout);

      if (streamed.statusCode != 200) {
        yield {'error': 'HTTP ${streamed.statusCode}'};
        return;
      }

      // SSE frames are: "data: {...}\n\n"
      // We accumulate bytes into lines and parse each complete frame.
      final buffer = StringBuffer();
      await for (final chunk in streamed.stream.transform(utf8.decoder)) {
        buffer.write(chunk);
        final raw = buffer.toString();
        // Split on double-newline (SSE frame separator)
        final frames = raw.split('\n\n');
        // Keep any incomplete trailing frame in the buffer
        buffer.clear();
        if (!raw.endsWith('\n\n') && frames.isNotEmpty) {
          buffer.write(frames.removeLast());
        }
        for (final frame in frames) {
          final trimmed = frame.trim();
          if (trimmed.isEmpty) continue;
          // Each line inside a frame: "data: {...}"
          for (final line in trimmed.split('\n')) {
            if (line.startsWith('data: ')) {
              final jsonStr = line.substring(6).trim();
              if (jsonStr.isEmpty) continue;
              try {
                final parsed = jsonDecode(jsonStr) as Map<String, dynamic>;
                yield parsed;
                if (parsed['done'] == true) return;
              } catch (_) {
                // Malformed frame — skip
              }
            }
          }
        }
      }
    } on TimeoutException {
      yield {'error': 'Connection timed out', 'timeout': true};
    } on SocketException catch (e) {
      yield {'error': 'Cannot connect: $e'};
    } catch (e) {
      yield {'error': 'Stream error: $e'};
    }
  }

  // ── Weather ──────────────────────────────────────────────────────────────
  Future<WeatherData> getWeather({
    required String location, double? lat, double? lon, String lang = 'hi',
  }) async {
    final q = _locQ(loc: location, lat: lat, lon: lon);
    return WeatherData.fromJson(
      await _get('${AppConfig.baseUrl}/api/weather/?$q&language=$lang'),
    );
  }

  /// Force-bypasses the server-side cache by hitting /api/weather/refresh/.
  /// Use when the user explicitly pulls to refresh on the weather screen.
  Future<WeatherData> getWeatherFresh({
    required String location, double? lat, double? lon, String lang = 'hi',
  }) async {
    final q = _locQ(loc: location, lat: lat, lon: lon);
    try {
      return WeatherData.fromJson(
        await _get('${AppConfig.baseUrl}/api/weather/refresh/?$q&language=$lang'),
      );
    } catch (_) {
      // Refresh endpoint not available (older server) — fall back to normal fetch
      return getWeather(location: location, lat: lat, lon: lon, lang: lang);
    }
  }

  // ── Nearby mandis ────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getMandis({
    required String location, double? lat, double? lon, String? state,
    int radiusKm = 150,
  }) async {
    final q = _locQ(loc: location, lat: lat, lon: lon, state: state);
    return _get('${AppConfig.baseUrl}/api/market-prices/mandis/?$q&radius_km=$radiusKm');
  }

  // ── Market prices ────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getPrices({
    required String location, double? lat, double? lon,
    String? state, String? mandi, String? crop,
  }) async {
    final p = <String, String>{'location': location};
    if (lat   != null) p['latitude']  = lat.toString();
    if (lon   != null) p['longitude'] = lon.toString();
    if (state != null) p['state']     = state;
    if (mandi != null) p['mandi']     = mandi;
    if (crop  != null) p['crop']      = crop;
    final uri = Uri.parse('${AppConfig.baseUrl}/api/market-prices/')
        .replace(queryParameters: p);
    return _get(uri.toString());
  }

  // ── Crop recommendations ─────────────────────────────────────────────────
  Future<List<CropRec>> getCropRecs({
    required String location, double? lat, double? lon,
    String? state, String lang = 'hi',
  }) async {
    final q = _locQ(loc: location, lat: lat, lon: lon, state: state);
    final data = await _get('${AppConfig.baseUrl}/api/advisories/?$q&language=$lang');
    final recs = (data['recommendations'] ?? data['top_4_recommendations'] ?? []) as List;
    return recs.map((r) => CropRec.fromJson(r as Map<String, dynamic>)).toList();
  }

  // ── Schemes ──────────────────────────────────────────────────────────────
  Future<List<dynamic>> getSchemes({String? state, String lang = 'hi'}) async {
    final p = <String, String>{'language': lang};
    if (state != null) p['state'] = state;
    final uri = Uri.parse('${AppConfig.baseUrl}/api/schemes/')
        .replace(queryParameters: p);
    final raw = await _get(uri.toString());
    if (raw['schemes'] is List && (raw['schemes'] as List).isNotEmpty)
      return raw['schemes'] as List;
    if (raw['catalog'] is List && (raw['catalog'] as List).isNotEmpty)
      return raw['catalog'] as List;
    if (raw['results'] is List) return raw['results'] as List;
    return [];
  }

  // ── Disease diagnosis ────────────────────────────────────────────────────
  Future<List<Map<String, dynamic>>> searchDiagnosticCrops({
    required String query,
    int limit = 8,
  }) async {
    final uri = Uri.parse('${AppConfig.baseUrl}/api/diagnostics/crop-search/')
        .replace(queryParameters: {
      'q': query,
      'limit': limit.toString(),
    });
    final raw = await _get(uri.toString());
    final rows = (raw['results'] as List?) ?? const [];
    return rows
        .whereType<Map>()
        .map((row) => Map<String, dynamic>.from(row))
        .toList();
  }

  Future<Map<String, dynamic>> diagnose({
    required File image, required String crop,
    required String sessionId, String lang = 'hi',
  }) async {
    if (kIsWeb) throw const ApiException('Camera upload not supported on web browser');
    final req = http.MultipartRequest(
        'POST', Uri.parse('${AppConfig.baseUrl}/api/diagnostics/predict/'));
    req.fields['crop']       = crop;
    req.fields['session_id'] = sessionId;
    req.fields['language']   = lang;
    req.files.add(await http.MultipartFile.fromPath('image', image.path));
    try {
      final streamed = await req.send().timeout(_timeout);
      final r = await http.Response.fromStream(streamed);
      if (r.statusCode == 200) return jsonDecode(r.body) as Map<String, dynamic>;
      throw ApiException('Diagnose failed', statusCode: r.statusCode);
    } on SocketException catch (e) {
      throw ApiException('Cannot connect: $e');
    }
  }
}
