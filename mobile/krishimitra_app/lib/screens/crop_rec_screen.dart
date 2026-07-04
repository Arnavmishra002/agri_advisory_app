import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/cache_service.dart';
import '../services/location_service.dart';
import '../utils/constants.dart';
import '../widgets/error_view.dart';

class CropRecScreen extends StatefulWidget {
  final String lang;
  const CropRecScreen({super.key, required this.lang});
  @override State<CropRecScreen> createState() => _CropRecScreenState();
}

class _CropRecScreenState extends State<CropRecScreen>
    with AutomaticKeepAliveClientMixin {
  final _api   = ApiService();
  final _loc   = LocationService();
  final _cache = CacheService();

  List<CropRec> _recs         = [];
  bool          _loading       = true;
  String?       _err;
  String?       _locationName;
  bool          _fromCache     = false;
  int?          _cacheAge;

  @override bool get wantKeepAlive => true;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _err = null; _fromCache = false; });
    final l        = _loc.current;
    _locationName  = l.name;
    final cacheKey = CacheService.key('croprec', l.name, widget.lang);

    final conn    = await Connectivity().checkConnectivity();
    final offline = conn.contains(ConnectivityResult.none);

    if (offline) {
      final cached = _cache.get(cacheKey, CacheService.cropRecTtl);
      if (cached != null) {
        _applyCache(cached, cacheKey);
        return;
      }
      setState(() { _loading = false; _err = 'offline'; });
      return;
    }

    try {
      final recs = await _api.getCropRecs(
        location: l.name, lat: l.lat, lon: l.lon,
        state: l.state, lang: widget.lang,
      );
      // Cache the raw list as JSON
      await _cache.set(cacheKey,
          recs.map((r) => _recToJson(r)).toList());
      setState(() { _recs = recs; _loading = false; });
    } catch (_) {
      final cached = _cache.get(cacheKey, const Duration(hours: 48));
      if (cached != null) {
        _applyCache(cached, cacheKey);
      } else {
        setState(() { _loading = false; _err = 'network'; });
      }
    }
  }

  void _applyCache(dynamic cached, String cacheKey) {
    try {
      final list = (cached as List)
          .map((r) => CropRec.fromJson(Map<String, dynamic>.from(r as Map)))
          .toList();
      setState(() {
        _recs      = list;
        _fromCache = true;
        _cacheAge  = _cache.ageHours(cacheKey);
        _loading   = false;
      });
    } catch (_) {
      setState(() { _loading = false; _err = 'cache_parse'; });
    }
  }

  static Map<String, dynamic> _recToJson(CropRec r) => {
    'crop_name':       r.cropName,
    'crop_name_hindi': r.cropNameHindi,
    'suitability_score': r.score,
    'profit_per_hectare': r.profit,
    'msp_per_quintal': r.mspPerQuintal,
    'season': r.season,
    'reason': r.reason,
  };

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: _buildAppBar(),
      body: _loading
          ? _loadingView()
          : _err != null && _recs.isEmpty
              ? ErrorView(error: _err!, onRetry: _load,
                          title: 'फसल सुझाव उपलब्ध नहीं')
              : _recs.isEmpty
                  ? _emptyView()
                  : _recsList(),
    );
  }

  PreferredSizeWidget _buildAppBar() => AppBar(
    flexibleSpace: Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF1B5E20), Color(0xFF2E7D32), Color(0xFF43A047)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
      ),
    ),
    title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Row(children: [
        Text('🌾 ', style: TextStyle(fontSize: 20)),
        Text('फसल सुझाव', style: TextStyle(
            color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
      ]),
      Text(_locationName ?? '...', style: const TextStyle(
          color: Colors.white70, fontSize: 12)),
    ]),
    backgroundColor: Colors.transparent, elevation: 0,
    actions: [
      if (_fromCache)
        Padding(
          padding: const EdgeInsets.only(right: 4),
          child: Center(child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.orange.withValues(alpha: 0.25),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text('📶 ${_cacheAge ?? 0}h',
                style: const TextStyle(color: Colors.orange, fontSize: 10)),
          )),
        ),
      IconButton(
        icon: const Icon(Icons.refresh_rounded, color: Colors.white),
        onPressed: _load,
      ),
    ],
  );

  Widget _loadingView() => Center(child: Column(
    mainAxisAlignment: MainAxisAlignment.center, children: [
    const CircularProgressIndicator(color: Color(AppColors.primary)),
    const SizedBox(height: 16),
    Text('आपके स्थान के लिए फसल विश्लेषण हो रहा है...',
        style: TextStyle(color: Colors.grey[600], fontSize: 14),
        textAlign: TextAlign.center),
  ]));

  Widget _emptyView() => Center(child: Column(
    mainAxisAlignment: MainAxisAlignment.center, children: [
    const Text('🌱', style: TextStyle(fontSize: 56)),
    const SizedBox(height: 12),
    const Text('कोई सुझाव उपलब्ध नहीं',
        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
    const SizedBox(height: 8),
    Text('GPS चालू करें या लोकेशन बदलें',
        style: TextStyle(color: Colors.grey[600])),
    const SizedBox(height: 16),
    ElevatedButton.icon(
      icon: const Icon(Icons.refresh),
      label: const Text('दोबारा'),
      onPressed: _load,
    ),
  ]));

  Widget _recsList() => CustomScrollView(
    slivers: [
      SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Column(children: [
            // Offline banner
            if (_fromCache) _offlineBanner(),
            if (_fromCache) const SizedBox(height: 10),
            // Summary header card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF1B5E20), Color(0xFF2E7D32)],
                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(18),
                boxShadow: [BoxShadow(
                    color: const Color(0xFF1B5E20).withValues(alpha: 0.25),
                    blurRadius: 12, offset: const Offset(0, 4))],
              ),
              child: Row(children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text('📊', style: TextStyle(fontSize: 26)),
                ),
                const SizedBox(width: 14),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_recs.length} फसल विश्लेषण',
                      style: const TextStyle(fontWeight: FontWeight.bold,
                          fontSize: 16, color: Colors.white)),
                  const SizedBox(height: 4),
                  Text(
                    widget.lang == 'hi'
                        ? 'मिट्टी · मौसम · बाज़ार के आधार पर'
                        : 'Based on soil, weather & market',
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ])),
              ]),
            ),
          ]),
        ),
      ),
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        sliver: SliverList(
          delegate: SliverChildBuilderDelegate(
            (_, i) => _cropCard(_recs[i], i + 1),
            childCount: _recs.length,
          ),
        ),
      ),
    ],
  );

  Widget _offlineBanner() => Container(
    padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
    decoration: BoxDecoration(
      color: Colors.orange.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: Colors.orange.withValues(alpha: 0.3)),
    ),
    child: Row(children: [
      const Icon(Icons.wifi_off_rounded, color: Colors.orange, size: 16),
      const SizedBox(width: 8),
      Text(
        '📶 ऑफ़लाइन — ${_cacheAge ?? 0} घंटे पहले का डेटा',
        style: const TextStyle(color: Colors.orange, fontSize: 12),
      ),
    ]),
  );

  Widget _cropCard(CropRec r, int rank) {
    final scoreColor = r.score >= 85
        ? const Color(0xFF2E7D32)
        : r.score >= 65 ? const Color(0xFFF57F17) : const Color(0xFFC62828);
    final scoreBg = r.score >= 85
        ? const Color(0xFFE8F5E9)
        : r.score >= 65 ? const Color(0xFFFFF8E1) : const Color(0xFFFFEBEE);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10, offset: const Offset(0, 4))],
        border: rank == 1
            ? Border.all(color: const Color(AppColors.primary), width: 1.5)
            : null,
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(children: [
          // Rank + Score column
          Column(children: [
            Container(
              width: 46, height: 46,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: rank <= 3
                      ? [const Color(0xFF1B5E20), const Color(0xFF43A047)]
                      : [const Color(AppColors.chipGreen), const Color(0xFFE8F5E9)],
                ),
                borderRadius: BorderRadius.circular(13),
              ),
              child: Center(child: Text('$rank',
                  style: TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 18,
                      color: rank <= 3 ? Colors.white : const Color(AppColors.primary)))),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
              decoration: BoxDecoration(
                  color: scoreBg, borderRadius: BorderRadius.circular(8)),
              child: Text('${r.score}%',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                      color: scoreColor)),
            ),
          ]),
          const SizedBox(width: 14),
          // Crop info
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text(r.badge, style: const TextStyle(fontSize: 18)),
              const SizedBox(width: 6),
              Expanded(child: Text(r.displayName,
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 16))),
            ]),
            if (r.cropNameHindi.isNotEmpty && r.cropName.isNotEmpty &&
                r.cropNameHindi != r.cropName)
              Text(r.cropName,
                  style: TextStyle(fontSize: 12, color: Colors.grey[600])),
            const SizedBox(height: 6),
            Wrap(spacing: 6, runSpacing: 4, children: [
              _tag(r.season, Icons.calendar_today,
                  const Color(0xFF1565C0), const Color(0xFFE3F2FD)),
              if (r.mspPerQuintal > 0)
                _tag('MSP ₹${r.mspPerQuintal}', Icons.currency_rupee,
                    const Color(0xFF2E7D32), const Color(0xFFE8F5E9)),
            ]),
            if (r.reason.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(r.reason,
                  style: TextStyle(fontSize: 12,
                      color: Colors.blueGrey[600], height: 1.4),
                  maxLines: 2, overflow: TextOverflow.ellipsis),
            ],
          ])),
          // Profit
          if (r.profit > 0)
            Column(children: [
              Text('₹${(r.profit / 1000).toStringAsFixed(0)}K',
                  style: const TextStyle(fontWeight: FontWeight.bold,
                      fontSize: 15, color: Color(AppColors.success))),
              Text('/हे.', style: TextStyle(fontSize: 10, color: Colors.grey[500])),
            ]),
        ]),
      ),
    );
  }

  Widget _tag(String label, IconData icon, Color color, Color bg) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
    decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(7)),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, size: 10, color: color),
      const SizedBox(width: 3),
      Text(label, style: TextStyle(
          fontSize: 10, color: color, fontWeight: FontWeight.w600)),
    ]),
  );
}
