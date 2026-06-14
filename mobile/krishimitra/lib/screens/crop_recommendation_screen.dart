/// KrishiMitra Crop Recommendation Screen
library;

import 'package:flutter/material.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../utils/constants.dart';

class CropRecommendationScreen extends StatefulWidget {
  final String language;
  const CropRecommendationScreen({super.key, required this.language});
  @override
  State<CropRecommendationScreen> createState() => _CropRecommendationScreenState();
}

class _CropRecommendationScreenState extends State<CropRecommendationScreen> {
  final _api    = ApiService();
  final _locSvc = LocationService();

  List<CropRecommendation> _recs = [];
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
      final recs = await _api.getCropRecommendations(
        location: loc.displayName,
        lat:      loc.latitude,
        lon:      loc.longitude,
        state:    loc.state,
        language: widget.language,
      );
      setState(() { _recs = recs; _loading = false; });
    } catch (e) {
      setState(() { _loading = false; _error = e.toString(); });
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = _locSvc.current;
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: AppBar(
        backgroundColor: const Color(AppColors.primary),
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('🌾 फसल सुझाव',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          Text(loc.displayName,
              style: const TextStyle(color: Colors.white70, fontSize: 12)),
        ]),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white70),
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text('डेटा लोड नहीं हो सका।'),
                    const SizedBox(height: 8),
                    ElevatedButton(onPressed: _load, child: const Text('दोबारा')),
                  ]))
              : _recs.isEmpty
                  ? const Center(child: Text('कोई सुझाव उपलब्ध नहीं।'))
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: _recs.length,
                      itemBuilder: (_, i) => _cropCard(_recs[i], i + 1),
                    ),
    );
  }

  Widget _cropCard(CropRecommendation r, int rank) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(children: [
          // Rank badge
          Container(
            width: 40, height: 40,
            decoration: BoxDecoration(
              color: rank == 1
                  ? const Color(AppColors.accent)
                  : const Color(AppColors.chipGreen),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text('$rank',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            ),
          ),
          const SizedBox(width: 14),
          // Crop info
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text(r.scoreLabel, style: const TextStyle(fontSize: 16)),
                const SizedBox(width: 6),
                Text(r.cropNameHindi.isNotEmpty ? r.cropNameHindi : r.cropName,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ]),
              if (r.cropNameHindi.isNotEmpty)
                Text(r.cropName,
                    style: const TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 4),
              Text('${r.suitabilityScore}% उपयुक्त · ${r.season}',
                  style: const TextStyle(fontSize: 12, color: Color(AppColors.textSecondary))),
              if (r.reason.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(r.reason,
                      style: const TextStyle(fontSize: 12, color: Colors.blueGrey)),
                ),
            ]),
          ),
          // Profit / MSP
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            if (r.profitPerHectare > 0)
              Text('₹${(r.profitPerHectare / 1000).toStringAsFixed(0)}K/हे.',
                  style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                      color: Color(AppColors.success))),
            if (r.mspPerQuintal > 0)
              Text('MSP ₹${r.mspPerQuintal}/q',
                  style: const TextStyle(fontSize: 11, color: Colors.grey)),
          ]),
        ]),
      ),
    );
  }
}
