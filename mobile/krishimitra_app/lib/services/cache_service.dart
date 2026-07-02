/// KrishiMitra Offline Cache Service (Task 10 / RAG-7)
///
/// Wraps Hive for fast local key-value caching of API responses.
/// Every entry is stored with a UTC timestamp; callers pass a TTL and
/// this service returns null for expired entries.
///
/// Cache keys are namespaced by (screen, locationName, lang) so a user
/// who switches location never sees stale data from the old location.
///
/// TTLs (from spec requirement 6):
///   weather  : 3 hours
///   mandi    : 6 hours
///   crop_rec : 24 hours

import 'package:hive_flutter/hive_flutter.dart';

class CacheService {
  static final CacheService _i = CacheService._();
  factory CacheService() => _i;
  CacheService._();

  static const _boxName = 'km_offline_cache';

  // TTL constants
  static const Duration weatherTtl  = Duration(hours: 3);
  static const Duration mandiTtl    = Duration(hours: 6);
  static const Duration cropRecTtl  = Duration(hours: 24);

  Box? _box;

  /// Must be called once from main() after Hive.initFlutter()
  Future<void> init() async {
    _box = await Hive.openBox(_boxName);
  }

  /// Build a cache key scoped to location + language so stale entries
  /// from a different location are never returned for the new one.
  static String key(String screen, String locationName, String lang) {
    final safeLocation = locationName.replaceAll(RegExp(r'[^a-zA-Z0-9_\u0900-\u097F]'), '_');
    return '${screen}_${safeLocation}_$lang';
  }

  // ── Write ──────────────────────────────────────────────────────────────────

  Future<void> set(String cacheKey, dynamic data) async {
    final box = _box;
    if (box == null) return;
    await box.put(cacheKey, {
      'data':      data,
      'cached_at': DateTime.now().toUtc().toIso8601String(),
    });
  }

  // ── Read ───────────────────────────────────────────────────────────────────

  /// Returns the cached data if the entry exists and is younger than [ttl].
  /// Returns null if cache miss or expired.
  dynamic get(String cacheKey, Duration ttl) {
    final box = _box;
    if (box == null) return null;

    final entry = box.get(cacheKey) as Map?;
    if (entry == null) return null;

    final cachedAtStr = entry['cached_at'] as String?;
    if (cachedAtStr == null) return null;

    final cachedAt = DateTime.tryParse(cachedAtStr);
    if (cachedAt == null) return null;

    if (DateTime.now().toUtc().difference(cachedAt) > ttl) {
      // Expired — delete proactively
      box.delete(cacheKey);
      return null;
    }
    return entry['data'];
  }

  /// Returns the age of a cache entry rounded to the nearest hour.
  /// Returns null if no entry exists.
  int? ageHours(String cacheKey) {
    final box = _box;
    if (box == null) return null;
    final entry = box.get(cacheKey) as Map?;
    if (entry == null) return null;
    final cachedAtStr = entry['cached_at'] as String?;
    if (cachedAtStr == null) return null;
    final cachedAt = DateTime.tryParse(cachedAtStr);
    if (cachedAt == null) return null;
    final diff = DateTime.now().toUtc().difference(cachedAt);
    return (diff.inMinutes / 60).round().clamp(0, 999);
  }

  // ── Clear ──────────────────────────────────────────────────────────────────

  Future<void> clear() async => _box?.clear();

  Future<void> delete(String cacheKey) async => _box?.delete(cacheKey);
}
