/// KrishiMitra Mandi Screen — nearby mandi prices with GPS-based filtering
library;

import 'package:flutter/material.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../services/storage_service.dart';
import '../utils/constants.dart';

class MandiScreen extends StatefulWidget {
  final String language;
  const MandiScreen({super.key, required this.language});

  @override
  State<MandiScreen> createState() => _MandiScreenState();
}

class _MandiScreenState extends State<MandiScreen>
    with SingleTickerProviderStateMixin {
  final _api      = ApiService();
  final _locSvc   = LocationService();
  final _storage  = StorageService();
  late TabController _tabCtrl;

  List<MandiInfo> _mandis     = [];
  List<CropPrice> _prices     = [];
  MandiInfo?      _selected;
  bool _loadingMandis = true;
  bool _loadingPrices = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 2, vsync: this);
    _loadMandis();
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadMandis() async {
    setState(() { _loadingMandis = true; _error = null; });
    try {
      final loc   = _locSvc.current;
      final saved = await _storage.getSelectedMandi();
      final list  = await _api.getNearbyMandis(
        location:  loc.displayName,
        lat:       loc.latitude,
        lon:       loc.longitude,
        state:     loc.state,
        radiusKm:  AppConfig.mandiRadiusKm,
      );
      MandiInfo? sel;
      if (saved != null) {
        try { sel = list.firstWhere((m) => m.name == saved); } catch (_) {}
      }
      sel ??= list.isNotEmpty ? list.first : null;
      setState(() {
        _mandis          = list;
        _selected        = sel;
        _loadingMandis   = false;
      });
      if (sel != null) _loadPrices(sel.name);
    } catch (e) {
      setState(() { _loadingMandis = false; _error = e.toString(); });
    }
  }

  Future<void> _loadPrices(String mandiName) async {
    setState(() { _loadingPrices = true; });
    try {
      final loc  = _locSvc.current;
      final data = await _api.getMarketPrices(
        location: loc.displayName,
        lat:      loc.latitude,
        lon:      loc.longitude,
        state:    loc.state,
        mandi:    mandiName,
      );
      final crops = (data['top_crops'] as List? ?? [])
          .map((c) => CropPrice.fromJson(c as Map<String, dynamic>))
          .toList();
      setState(() { _prices = crops; _loadingPrices = false; });
    } catch (_) {
      setState(() => _loadingPrices = false);
    }
  }

  void _selectMandi(MandiInfo mandi) {
    setState(() => _selected = mandi);
    _storage.setSelectedMandi(mandi.name);
    _loadPrices(mandi.name);
    _tabCtrl.animateTo(1);  // switch to prices tab
  }

  @override
  Widget build(BuildContext context) {
    final loc = _locSvc.current;
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: AppBar(
        backgroundColor: const Color(AppColors.primary),
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('💰 मंडी भाव',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          Text(loc.displayName,
              style: const TextStyle(color: Colors.white70, fontSize: 12)),
        ]),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white70),
            onPressed: _loadMandis,
          ),
        ],
        bottom: TabBar(
          controller: _tabCtrl,
          indicatorColor: const Color(AppColors.accent),
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white60,
          tabs: const [
            Tab(text: '🏪 नज़दीकी मंडियां'),
            Tab(text: '📊 भाव'),
          ],
        ),
      ),
      body: _loadingMandis
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError()
              : TabBarView(
                  controller: _tabCtrl,
                  children: [
                    _buildMandiList(),
                    _buildPricesTab(),
                  ],
                ),
    );
  }

  Widget _buildMandiList() {
    if (_mandis.isEmpty) {
      return const Center(
        child: Text('नज़दीक कोई मंडी नहीं मिली।\nGPS चालू करें।',
            textAlign: TextAlign.center),
      );
    }
    // Group by proximity
    final veryNear = _mandis.where((m) => m.proximity == 'very_near').toList();
    final near     = _mandis.where((m) => m.proximity == 'near').toList();
    final regional = _mandis.where((m) =>
        m.proximity == 'regional' || m.proximity == 'unknown').toList();

    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        if (veryNear.isNotEmpty) ...[
          _sectionHeader('📍 बहुत नज़दीक (< 30 km)'),
          ...veryNear.map(_mandiCard),
        ],
        if (near.isNotEmpty) ...[
          _sectionHeader('🗺️ नज़दीक (30–150 km)'),
          ...near.map(_mandiCard),
        ],
        if (regional.isNotEmpty) ...[
          _sectionHeader('📋 क्षेत्रीय मंडियां'),
          ...regional.map(_mandiCard),
        ],
      ],
    );
  }

  Widget _sectionHeader(String label) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 12, 4, 6),
    child: Text(label,
        style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 13,
            color: Color(AppColors.textSecondary))),
  );

  Widget _mandiCard(MandiInfo m) {
    final isSelected = _selected?.name == m.name;
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      color: isSelected ? const Color(AppColors.chipGreen) : Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: isSelected
            ? const BorderSide(color: Color(AppColors.primary), width: 1.5)
            : BorderSide.none,
      ),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: m.isLive
              ? const Color(AppColors.success)
              : const Color(AppColors.divider),
          radius: 18,
          child: Text(m.name.substring(0, 1).toUpperCase(),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        ),
        title: Text(m.name,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text(
          [if (m.district.isNotEmpty) m.district, if (m.state.isNotEmpty) m.state]
              .join(', '),
          style: const TextStyle(fontSize: 12),
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            if (m.distanceKm != null)
              Text('${m.distanceKm!.toStringAsFixed(0)} km',
                  style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                      color: Color(AppColors.primary))),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: m.isLive ? Colors.green.shade50 : Colors.grey.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(m.isLive ? '🟢 Live' : '⚪ Ref',
                  style: TextStyle(
                      fontSize: 10,
                      color: m.isLive ? Colors.green.shade800 : Colors.grey)),
            ),
          ],
        ),
        onTap: () => _selectMandi(m),
      ),
    );
  }

  Widget _buildPricesTab() {
    if (_selected == null) {
      return const Center(child: Text('पहले एक मंडी चुनें।'));
    }
    return Column(children: [
      // Selected mandi banner
      Container(
        color: const Color(AppColors.chipGreen),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(children: [
          const Icon(Icons.location_on, color: Color(AppColors.primary), size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text('${_selected!.name} · ${_selected!.displayDistance}',
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          ),
          TextButton(
            onPressed: () => _tabCtrl.animateTo(0),
            child: const Text('बदलें', style: TextStyle(fontSize: 12)),
          ),
        ]),
      ),
      if (_loadingPrices)
        const Expanded(child: Center(child: CircularProgressIndicator()))
      else if (_prices.isEmpty)
        const Expanded(child: Center(
          child: Text('इस मंडी के लिए भाव उपलब्ध नहीं।',
              textAlign: TextAlign.center)))
      else
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: _prices.length,
            itemBuilder: (_, i) => _priceCard(_prices[i]),
          ),
        ),
    ]);
  }

  Widget _priceCard(CropPrice c) {
    final aboveMsp   = c.aboveMsp;
    final trendColor = c.trend == 'up'
        ? Colors.green
        : c.trend == 'down' ? Colors.red : Colors.grey;
    final trendIcon  = c.trend == 'up' ? '📈' : c.trend == 'down' ? '📉' : '➡️';

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 5),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text(c.cropNameHindi.isNotEmpty ? c.cropNameHindi : c.cropName,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(width: 6),
                Text(trendIcon, style: const TextStyle(fontSize: 14)),
              ]),
              if (c.cropNameHindi.isNotEmpty && c.cropName.isNotEmpty)
                Text(c.cropName,
                    style: const TextStyle(fontSize: 11, color: Colors.grey)),
              if (c.msp != null)
                Text('MSP: ₹${c.msp!.toStringAsFixed(0)}/q',
                    style: TextStyle(
                        fontSize: 11,
                        color: aboveMsp ? Colors.green.shade700 : Colors.red)),
            ]),
          ),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('₹${c.modalPrice?.toStringAsFixed(0) ?? '—'}/q',
                style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                    color: Color(AppColors.primary))),
            if (c.profitVsMsp != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: aboveMsp ? Colors.green.shade50 : Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '${aboveMsp ? '+' : ''}${c.profitVsMsp!.toStringAsFixed(1)}% vs MSP',
                  style: TextStyle(
                      fontSize: 10,
                      color: aboveMsp ? Colors.green.shade800 : Colors.red),
                ),
              ),
          ]),
        ]),
      ),
    );
  }

  Widget _buildError() => Center(
    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      const Icon(Icons.wifi_off, size: 48, color: Colors.grey),
      const SizedBox(height: 12),
      const Text('डेटा लोड नहीं हो सका।', style: TextStyle(fontSize: 16)),
      const SizedBox(height: 8),
      ElevatedButton(
        onPressed: _loadMandis,
        child: const Text('दोबारा कोशिश करें'),
      ),
    ]),
  );
}
