/// KrishiMitra Government Schemes Screen
library;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../utils/constants.dart';

class SchemesScreen extends StatefulWidget {
  final String language;
  const SchemesScreen({super.key, required this.language});
  @override
  State<SchemesScreen> createState() => _SchemesScreenState();
}

class _SchemesScreenState extends State<SchemesScreen> {
  final _api    = ApiService();
  final _locSvc = LocationService();

  List<GovScheme> _schemes = [];
  bool  _loading = true;

  // Static fallback schemes always shown
  static const List<Map<String, String>> _staticSchemes = [
    {'name': 'PM-Kisan Samman Nidhi', 'hindi': 'पीएम-किसान सम्मान निधि',
     'desc': '₹6,000/वर्ष (3 किस्त ₹2,000)', 'url': 'https://pmkisan.gov.in',
     'helpline': '155261', 'category': 'income'},
    {'name': 'PMFBY', 'hindi': 'प्रधानमंत्री फसल बीमा योजना',
     'desc': 'खरीफ 2% · रबी 1.5% प्रीमियम', 'url': 'https://pmfby.gov.in',
     'helpline': '14447', 'category': 'insurance'},
    {'name': 'Kisan Credit Card', 'hindi': 'किसान क्रेडिट कार्ड',
     'desc': '₹3 लाख तक ऋण @ 4% ब्याज', 'url': 'https://www.nabard.org',
     'helpline': '1800-180-1551', 'category': 'credit'},
    {'name': 'PM-KUSUM', 'hindi': 'पीएम-कुसुम सोलर पंप',
     'desc': '90% सब्सिडी (30%+30%+30%)', 'url': 'https://pmkusum.mnre.gov.in',
     'helpline': '1800-180-3333', 'category': 'solar'},
    {'name': 'Soil Health Card', 'hindi': 'मृदा स्वास्थ्य कार्ड',
     'desc': 'निःशुल्क मिट्टी जांच + सुझाव', 'url': 'https://soilhealth.dac.gov.in',
     'helpline': '1800-180-1551', 'category': 'soil'},
    {'name': 'eNAM', 'hindi': 'राष्ट्रीय कृषि बाजार',
     'desc': 'ऑनलाइन मंडी व्यापार', 'url': 'https://enam.gov.in',
     'helpline': '1800-270-0224', 'category': 'market'},
  ];

  static const Map<String, IconData> _catIcons = {
    'income':    Icons.currency_rupee,
    'insurance': Icons.shield,
    'credit':    Icons.credit_card,
    'solar':     Icons.solar_power,
    'soil':      Icons.eco,
    'market':    Icons.store,
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final loc = _locSvc.current;
      final s   = await _api.getSchemes(state: loc.state, language: widget.language);
      setState(() { _schemes = s; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _launchUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: AppBar(
        backgroundColor: const Color(AppColors.primary),
        title: const Text('🏛️ सरकारी योजनाएं',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white70),
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(12),
              children: [
                // Helpline banner
                Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(AppColors.chipGreen),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(AppColors.primary), width: 0.5),
                  ),
                  child: InkWell(
                    onTap: () => _launchUrl('tel:18001801551'),
                    child: const Row(children: [
                      Icon(Icons.phone, color: Color(AppColors.primary)),
                      SizedBox(width: 8),
                      Text('Kisan Call Centre: 1800-180-1551 (Free, 24x7)',
                          style: TextStyle(fontWeight: FontWeight.w600)),
                    ]),
                  ),
                ),
                // Static schemes (always visible, instant)
                ..._staticSchemes.map((s) => _schemeCard(
                  name:     s['name']!,
                  hindi:    s['hindi']!,
                  desc:     s['desc']!,
                  url:      s['url']!,
                  helpline: s['helpline']!,
                  icon:     _catIcons[s['category']] ?? Icons.agriculture,
                )),
                // Live schemes from API (if any extra)
                if (_schemes.isNotEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Text('📡 राज्य-विशिष्ट योजनाएं',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                  ),
                ..._schemes.map((s) => _schemeCard(
                  name:     s.name,
                  hindi:    s.nameHindi,
                  desc:     s.description,
                  url:      s.applyUrl,
                  helpline: s.helpline,
                  icon:     Icons.account_balance,
                )),
              ],
            ),
    );
  }

  Widget _schemeCard({
    required String name,
    required String hindi,
    required String desc,
    required String url,
    required String helpline,
    required IconData icon,
  }) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 5),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: ExpansionTile(
        leading: CircleAvatar(
          backgroundColor: const Color(AppColors.chipGreen),
          child: Icon(icon, color: const Color(AppColors.primary), size: 20),
        ),
        title: Text(hindi.isNotEmpty ? hindi : name,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
        subtitle: Text(name, style: const TextStyle(fontSize: 11, color: Colors.grey)),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(desc, style: const TextStyle(fontSize: 13, height: 1.5)),
              const SizedBox(height: 10),
              Row(children: [
                if (helpline.isNotEmpty)
                  Expanded(
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.phone, size: 16),
                      label: Text(helpline, style: const TextStyle(fontSize: 12)),
                      onPressed: () => _launchUrl('tel:$helpline'),
                    ),
                  ),
                const SizedBox(width: 8),
                if (url.isNotEmpty)
                  Expanded(
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(AppColors.primary)),
                      icon: const Icon(Icons.open_in_new, size: 16, color: Colors.white),
                      label: const Text('आवेदन करें',
                          style: TextStyle(color: Colors.white, fontSize: 12)),
                      onPressed: () => _launchUrl(url),
                    ),
                  ),
              ]),
            ]),
          ),
        ],
      ),
    );
  }
}
