import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/cache_service.dart';
import '../services/location_service.dart';
import '../services/storage_service.dart';
import '../utils/constants.dart';
import '../widgets/error_view.dart';

class MandiScreen extends StatefulWidget {
  final String lang;
  const MandiScreen({super.key, required this.lang});
  @override State<MandiScreen> createState() => _MandiScreenState();
}

class _MandiScreenState extends State<MandiScreen>
    with SingleTickerProviderStateMixin, AutomaticKeepAliveClientMixin {
  final _api   = ApiService();
  final _loc   = LocationService();
  final _store = StorageService();
  final _cache = CacheService();
  late TabController _tab;

  List<MandiInfo> _mandis       = [];
  List<CropPrice> _prices       = [];
  MandiInfo?      _sel;
  bool            _loadingMandis = true;
  bool            _loadingPrices = false;
  String?         _err;
  String?         _nearestMsg;
  bool            _fromCache = false;
  int?            _cacheAge;

  @override bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
    _loadMandis();
  }

  @override void dispose() { _tab.dispose(); super.dispose(); }

  Future<void> _loadMandis() async {
    setState(() { _loadingMandis = true; _err = null; _fromCache = false; });
    final l        = _loc.current;
    final cacheKey = CacheService.key('mandi', l.name, 'all');

    final conn    = await Connectivity().checkConnectivity();
    final offline = conn.contains(ConnectivityResult.none);

    if (offline) {
      final cached = _cache.get(cacheKey, CacheService.mandiTtl);
      if (cached != null) {
        _applyMandiCache(cached, cacheKey);
        return;
      }
      setState(() { _loadingMandis = false; _err = 'offline'; });
      return;
    }

    try {
      final saved = await _store.getSelectedMandi();
      final data  = await _api.getMandis(
        location: l.name, lat: l.lat, lon: l.lon, state: l.state,
      );
      await _cache.set(cacheKey, data);

      final list = (data['mandis'] as List? ?? [])
          .map((m) => MandiInfo.fromJson(m as Map<String, dynamic>))
          .toList();

      final nearest = data['nearest_mandi'] as Map<String, dynamic>?;
      if (nearest != null && nearest['name'] != null) {
        final d = nearest['distance_km'];
        _nearestMsg = '📍 नज़दीकी: ${nearest['name']}'
            + (d != null ? ' (${(d as num).toStringAsFixed(0)} km)' : '');
      }

      MandiInfo? sel;
      if (saved != null) {
        try { sel = list.firstWhere((m) => m.name == saved); } catch (_) {}
      }
      sel ??= list.isNotEmpty ? list.first : null;
      setState(() { _mandis = list; _sel = sel; _loadingMandis = false; });
      if (sel != null) _loadPrices(sel.name);
    } catch (_) {
      final cached = _cache.get(cacheKey, const Duration(hours: 12));
      if (cached != null) {
        _applyMandiCache(cached, cacheKey);
      } else {
        setState(() { _loadingMandis = false; _err = 'network'; });
      }
    }
  }

  void _applyMandiCache(dynamic cached, String cacheKey) {
    try {
      final data = Map<String, dynamic>.from(cached as Map);
      final list = (data['mandis'] as List? ?? [])
          .map((m) => MandiInfo.fromJson(m as Map<String, dynamic>))
          .toList();
      final sel = list.isNotEmpty ? list.first : null;
      setState(() {
        _mandis    = list; _sel = sel;
        _fromCache = true; _cacheAge = _cache.ageHours(cacheKey);
        _loadingMandis = false;
      });
      if (sel != null) _loadPrices(sel.name);
    } catch (_) {
      setState(() { _loadingMandis = false; _err = 'cache_parse'; });
    }
  }

  Future<void> _loadPrices(String mandi) async {
    setState(() => _loadingPrices = true);
    final l        = _loc.current;
    final cacheKey = CacheService.key('prices', '${l.name}_$mandi', 'all');

    final conn    = await Connectivity().checkConnectivity();
    final offline = conn.contains(ConnectivityResult.none);

    if (!offline) {
      try {
        final d = await _api.getPrices(
          location: l.name, lat: l.lat, lon: l.lon,
          state: l.state, mandi: mandi,
        );
        await _cache.set(cacheKey, d);
        setState(() {
          _prices = ((d['top_crops'] as List?) ?? [])
              .map((c) => CropPrice.fromJson(c as Map<String, dynamic>))
              .toList();
          _loadingPrices = false;
        });
        return;
      } catch (_) {}
    }

    // Fallback to cache
    final cached = _cache.get(cacheKey, const Duration(hours: 12));
    if (cached != null) {
      try {
        final d = Map<String, dynamic>.from(cached as Map);
        setState(() {
          _prices = ((d['top_crops'] as List?) ?? [])
              .map((c) => CropPrice.fromJson(c as Map<String, dynamic>))
              .toList();
          _loadingPrices = false;
        });
        return;
      } catch (_) {}
    }
    setState(() => _loadingPrices = false);
  }

  void _selectMandi(MandiInfo m) {
    setState(() => _sel = m);
    _store.setSelectedMandi(m.name);
    _loadPrices(m.name);
    _tab.animateTo(1);
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final l = _loc.current;
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: AppBar(
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF1A237E), Color(0xFF283593), Color(0xFF3949AB)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
          ),
        ),
        backgroundColor: Colors.transparent, elevation: 0,
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Text('💰 ', style: TextStyle(fontSize: 18)),
            Text('मंडी भाव', style: TextStyle(
                color: Colors.white, fontWeight: FontWeight.bold, fontSize: 17)),
          ]),
          Text(l.name, style: const TextStyle(color: Colors.white60, fontSize: 11)),
        ]),
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
            icon: const Icon(Icons.refresh_rounded, color: Colors.white60),
            onPressed: _loadMandis,
          ),
        ],
        bottom: TabBar(
          controller: _tab,
          indicatorColor: const Color(AppColors.accent),
          indicatorWeight: 3,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white54,
          tabs: const [
            Tab(icon: Icon(Icons.storefront_outlined, size: 18), text: 'नज़दीकी मंडी'),
            Tab(icon: Icon(Icons.bar_chart_rounded, size: 18), text: 'भाव'),
          ],
        ),
      ),
      body: _loadingMandis
          ? _loadingView()
          : _err != null && _mandis.isEmpty
              ? ErrorView(error: _err!, onRetry: _loadMandis,
                          title: 'मंडी डेटा उपलब्ध नहीं')
              : TabBarView(
                  controller: _tab,
                  children: [_mandiList(), _pricesTab()],
                ),
    );
  }

  Widget _loadingView() => const Center(child: Column(
    mainAxisAlignment: MainAxisAlignment.center, children: [
    CircularProgressIndicator(color: Color(AppColors.primary)),
    SizedBox(height: 12),
    Text('नज़दीकी मंडियां खोज रहे हैं...'),
  ]));

  Widget _mandiList() {
    if (_mandis.isEmpty) return Center(child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Text('🏪', style: TextStyle(fontSize: 56)),
        const SizedBox(height: 12),
        const Text('नज़दीक कोई मंडी नहीं मिली',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Text('GPS चालू करें या लोकेशन बदलें',
            style: TextStyle(color: Colors.grey[600])),
        const SizedBox(height: 20),
        ElevatedButton.icon(
          icon: const Icon(Icons.refresh),
          label: const Text('दोबारा खोजें'),
          onPressed: _loadMandis,
        ),
      ]),
    ));

    final veryNear = _mandis.where((m) => m.proximity == 'very_near').toList();
    final near     = _mandis.where((m) => m.proximity == 'near').toList();
    final other    = _mandis.where((m) =>
        m.proximity != 'very_near' && m.proximity != 'near').toList();

    return RefreshIndicator(
      onRefresh: _loadMandis,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_fromCache) _offlineBanner(),
          if (_nearestMsg != null) _nearestBanner(),
          if (veryNear.isNotEmpty) ...[
            _sectionHeader('📍 बहुत नज़दीक (< 30 km)', veryNear.length),
            ...veryNear.map(_mandiCard),
          ],
          if (near.isNotEmpty) ...[
            _sectionHeader('🗺️ नज़दीक (30–150 km)', near.length),
            ...near.map(_mandiCard),
          ],
          if (other.isNotEmpty) ...[
            _sectionHeader('📋 अन्य मंडियां', other.length),
            ...other.take(10).map(_mandiCard),
          ],
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _offlineBanner() => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
    decoration: BoxDecoration(
      color: Colors.orange.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: Colors.orange.withValues(alpha: 0.3)),
    ),
    child: Row(children: [
      const Icon(Icons.wifi_off_rounded, color: Colors.orange, size: 16),
      const SizedBox(width: 8),
      Text('📶 ऑफ़लाइन — ${_cacheAge ?? 0} घंटे पहले का डेटा',
          style: const TextStyle(color: Colors.orange, fontSize: 12)),
    ]),
  );

  Widget _nearestBanner() => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    decoration: BoxDecoration(
      gradient: const LinearGradient(
          colors: [Color(0xFF1A237E), Color(0xFF283593)]),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Row(children: [
      const Icon(Icons.near_me, color: Colors.white70, size: 16),
      const SizedBox(width: 8),
      Text(_nearestMsg!, style: const TextStyle(
          color: Colors.white, fontWeight: FontWeight.w600)),
    ]),
  );

  Widget _sectionHeader(String title, int count) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 12, 4, 6),
    child: Row(children: [
      Text(title, style: const TextStyle(
          fontWeight: FontWeight.bold, fontSize: 13,
          color: Color(AppColors.textSecondary))),
      const SizedBox(width: 6),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(
          color: const Color(AppColors.primary).withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text('$count', style: const TextStyle(
            fontSize: 11, color: Color(AppColors.primary),
            fontWeight: FontWeight.bold)),
      ),
    ]),
  );

  Widget _mandiCard(MandiInfo m) {
    final isSel = _sel?.name == m.name;
    return GestureDetector(
      onTap: () => _selectMandi(m),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isSel ? const Color(AppColors.chipGreen) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSel ? const Color(AppColors.primary) : Colors.transparent,
            width: isSel ? 1.5 : 0,
          ),
          boxShadow: [BoxShadow(
              color: Colors.black.withValues(alpha: isSel ? 0.1 : 0.05),
              blurRadius: 8, offset: const Offset(0, 3))],
        ),
        child: Row(children: [
          Container(
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: m.isLive
                  ? const Color(AppColors.success).withValues(alpha: 0.12)
                  : Colors.grey.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(child: Text(
              m.name.isNotEmpty ? m.name[0].toUpperCase() : '?',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18,
                  color: m.isLive ? const Color(AppColors.success) : Colors.grey),
            )),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(m.name, style: const TextStyle(
                fontWeight: FontWeight.w700, fontSize: 14)),
            const SizedBox(height: 2),
            Text(
              [if (m.district.isNotEmpty) m.district,
               if (m.state.isNotEmpty) m.state].join(', '),
              style: TextStyle(fontSize: 11, color: Colors.grey[600]),
            ),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            if (m.distanceKm != null)
              Text('${m.distanceKm!.toStringAsFixed(0)} km',
                  style: const TextStyle(fontWeight: FontWeight.bold,
                      fontSize: 14, color: Color(AppColors.primary))),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: m.isLive
                    ? Colors.green.withValues(alpha: 0.1)
                    : Colors.grey.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.circle, size: 7,
                    color: m.isLive ? Colors.green : Colors.grey),
                const SizedBox(width: 3),
                Text(m.isLive ? 'Live' : 'Ref',
                    style: TextStyle(fontSize: 10,
                        color: m.isLive ? Colors.green[800] : Colors.grey)),
              ]),
            ),
          ]),
        ]),
      ),
    );
  }

  Widget _pricesTab() {
    if (_sel == null) return Center(child: Column(
      mainAxisAlignment: MainAxisAlignment.center, children: [
      const Text('🏪', style: TextStyle(fontSize: 48)),
      const SizedBox(height: 12),
      const Text('पहले एक मंडी चुनें', style: TextStyle(fontSize: 16)),
      const SizedBox(height: 8),
      TextButton(onPressed: () => _tab.animateTo(0),
          child: const Text('मंडी चुनें →')),
    ]));

    return Column(children: [
      // Selected mandi header
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
              colors: [Color(0xFFE8F5E9), Color(0xFFF1F8E9)]),
        ),
        child: Row(children: [
          const Icon(Icons.location_on, color: Color(AppColors.primary), size: 16),
          const SizedBox(width: 6),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_sel!.name, style: const TextStyle(
                fontWeight: FontWeight.bold, fontSize: 14)),
            if (_sel!.distanceKm != null)
              Text('${_sel!.distanceKm!.toStringAsFixed(0)} km दूर',
                  style: const TextStyle(fontSize: 11, color: Colors.grey)),
          ])),
          TextButton.icon(
            icon: const Icon(Icons.swap_horiz, size: 14),
            label: const Text('बदलें', style: TextStyle(fontSize: 12)),
            onPressed: () => _tab.animateTo(0),
          ),
        ]),
      ),
      if (_loadingPrices)
        const Expanded(child: Center(child: Column(
          mainAxisAlignment: MainAxisAlignment.center, children: [
          CircularProgressIndicator(color: Color(AppColors.primary)),
          SizedBox(height: 12),
          Text('भाव लोड हो रहे हैं...'),
        ])))
      else if (_prices.isEmpty)
        const Expanded(child: Center(child: Column(
          mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('📊', style: TextStyle(fontSize: 48)),
          SizedBox(height: 12),
          Text('इस मंडी के लिए भाव उपलब्ध नहीं',
              textAlign: TextAlign.center),
          SizedBox(height: 8),
          Text('अन्य मंडी चुनें या बाद में देखें',
              style: TextStyle(color: Colors.grey, fontSize: 12)),
        ])))
      else
        Expanded(child: ListView.builder(
          padding: const EdgeInsets.all(12),
          itemCount: _prices.length,
          itemBuilder: (_, i) => _priceCard(_prices[i]),
        )),
    ]);
  }

  Widget _priceCard(CropPrice c) {
    final above    = c.aboveMsp;
    final trendIcon = c.trend == 'up' ? '📈' : c.trend == 'down' ? '📉' : '➡️';
    final pnlColor  = above ? const Color(0xFF2E7D32) : const Color(0xFFC62828);
    final pnlBg     = above ? const Color(0xFFE8F5E9) : const Color(0xFFFFEBEE);

    // One-day price change for real-time trend context
    final hasYday = c.oneDayPrice != null && c.oneDayPrice! > 0 && c.modalPrice != null;
    final ydayDiff = hasYday ? c.modalPrice! - c.oneDayPrice! : 0.0;
    final ydayPct  = hasYday && c.oneDayPrice! > 0
        ? (ydayDiff / c.oneDayPrice! * 100) : 0.0;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 6, offset: const Offset(0, 2))],
        border: Border(left: BorderSide(
          color: above ? const Color(AppColors.success) : const Color(0xFFEF5350),
          width: 4,
        )),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text(trendIcon, style: const TextStyle(fontSize: 16)),
              const SizedBox(width: 6),
              Text(
                c.cropNameHindi.isNotEmpty ? c.cropNameHindi : c.cropName,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
              ),
              if (c.isLive) ...[
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.green.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Text('Live', style: TextStyle(
                      fontSize: 9, color: Colors.green, fontWeight: FontWeight.bold)),
                ),
              ],
            ]),
            if (c.cropNameHindi.isNotEmpty && c.cropName.isNotEmpty)
              Text(c.cropName, style: TextStyle(fontSize: 11, color: Colors.grey[600])),
            const SizedBox(height: 4),
            // Data age label — honest freshness
            if (c.reportedDate.isNotEmpty)
              Row(children: [
                Icon(Icons.access_time_rounded, size: 11, color: Colors.grey[400]),
                const SizedBox(width: 3),
                Text(c.ageLabel(hindi: widget.lang == 'hi'),
                    style: TextStyle(fontSize: 10, color: Colors.grey[500])),
              ]),
            if (c.msp != null) ...[
              const SizedBox(height: 2),
              Text('MSP: ₹${c.msp!.toStringAsFixed(0)}/q',
                  style: TextStyle(fontSize: 11, color: Colors.grey[600])),
            ],
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('₹${c.modalPrice?.toStringAsFixed(0) ?? '—'}',
                style: const TextStyle(fontWeight: FontWeight.bold,
                    fontSize: 22, color: Color(AppColors.primary))),
            const Text('/क्विंटल',
                style: TextStyle(fontSize: 10, color: Colors.grey)),
            if (c.profitVsMsp != null) ...[
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                    color: pnlBg, borderRadius: BorderRadius.circular(8)),
                child: Text(
                  '${above ? '+' : ''}${c.profitVsMsp!.toStringAsFixed(1)}%',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                      color: pnlColor),
                ),
              ),
            ],
          ]),
        ]),
        // Yesterday vs today comparison bar
        if (hasYday) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(AppColors.background),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(children: [
              Text(
                widget.lang == 'hi' ? 'कल: ₹${c.oneDayPrice!.toStringAsFixed(0)}' : 'Yday: ₹${c.oneDayPrice!.toStringAsFixed(0)}',
                style: const TextStyle(fontSize: 11, color: Colors.grey),
              ),
              const SizedBox(width: 6),
              Icon(
                ydayDiff >= 0 ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
                size: 12,
                color: ydayDiff >= 0 ? Colors.green : Colors.red,
              ),
              Text(
                '${ydayDiff >= 0 ? '+' : ''}₹${ydayDiff.toStringAsFixed(0)} (${ydayPct.toStringAsFixed(1)}%)',
                style: TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w600,
                  color: ydayDiff >= 0 ? Colors.green[700] : Colors.red[700],
                ),
              ),
            ]),
          ),
        ],
      ]),
    );
  }
}
