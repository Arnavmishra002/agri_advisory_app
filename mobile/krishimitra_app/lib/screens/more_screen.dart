import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../services/storage_service.dart';
import '../utils/constants.dart';
import '../widgets/location_picker.dart';

// ── More / Settings Screen ────────────────────────────────────────────────────
class MoreScreen extends StatelessWidget {
  final String lang;
  final void Function(String) onLangChange;

  const MoreScreen({super.key, required this.lang, required this.onLangChange});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: AppBar(
        title: const Text('More', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: ListView(children: [
        // Language
        _tile(context, Icons.language, 'भाषा / Language',
            AppStrings.languages[lang] ?? lang, () => _pickLang(context)),
        const Divider(height: 1),
        // Disease detection — hide on web
        if (!kIsWeb) ...[
          _tile(context, Icons.biotech, 'KrishiRaksha — रोग पहचान',
              'फोटो से AI रोग पहचान', () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => DiseaseScreen(lang: lang)))),
          const Divider(height: 1),
        ],
        // Schemes
        _tile(context, Icons.account_balance, 'सरकारी योजनाएं',
            'PM-Kisan, PMFBY, KCC, PM-KUSUM',
            () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => SchemesScreen(lang: lang)))),
        const Divider(height: 1),
        // Location
        _tile(context, Icons.location_on, 'लोकेशन बदलें',
            LocationService().current.name, () => _pickLocation(context)),
        const Divider(height: 1),
        // Kisan helpline
        _tile(context, Icons.phone, 'Kisan Helpline',
            '1800-180-1551 (निःशुल्क, 24x7)',
            () => _launch('tel:18001801551')),
        const Divider(height: 1),
        const AboutListTile(
          icon: Icon(Icons.info_outline),
          applicationName: 'KrishiMitra AI',
          applicationVersion: AppConfig.appVersion,
          applicationLegalese: '© 2026 KrishiMitra AI',
          child: Text('About'),
        ),
      ]),
    );
  }

  ListTile _tile(BuildContext ctx, IconData icon, String title,
      String sub, VoidCallback onTap) =>
      ListTile(
        leading: CircleAvatar(
          backgroundColor: const Color(AppColors.chipGreen),
          child: Icon(icon, color: const Color(AppColors.primary), size: 20),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(sub, style: const TextStyle(fontSize: 12)),
        trailing: const Icon(Icons.chevron_right, color: Colors.grey),
        onTap: onTap,
      );

  Future<void> _launch(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) launchUrl(uri);
  }

  void _pickLang(BuildContext ctx) => showModalBottomSheet(
    context: ctx,
    shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
    builder: (_) => ListView(
      shrinkWrap: true,
      padding: const EdgeInsets.all(16),
      children: [
        const Text('भाषा / Language',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 12),
        ...AppStrings.languages.entries.map((e) => ListTile(
          title: Text(e.value),
          trailing: lang == e.key
              ? const Icon(Icons.check, color: Color(AppColors.primary))
              : null,
          onTap: () { onLangChange(e.key); Navigator.pop(ctx); },
        )),
      ],
    ),
  );

  void _pickLocation(BuildContext ctx) {
    LocationPickerSheet.show(ctx, onSelected: (_) {
      // Location stored in service — screens reload on next navigation
      if (ctx.mounted) Navigator.pop(ctx);
    });
  }
}

// ── Disease Detection Screen ──────────────────────────────────────────────────
class DiseaseScreen extends StatefulWidget {
  final String lang;
  const DiseaseScreen({super.key, required this.lang});
  @override State<DiseaseScreen> createState() => _DiseaseScreenState();
}

class _DiseaseScreenState extends State<DiseaseScreen> {
  final _api    = ApiService();
  final _store  = StorageService();
  final _picker = ImagePicker();
  final _cropController = TextEditingController();

  File?                 _img;
  Map<String, dynamic>? _result;
  List<Map<String, dynamic>> _cropSuggestions = [];
  Timer? _cropDebounce;
  bool   _loading  = false;
  bool   _cropSearching = false;
  String _cropName = '';
  String? _err;

  @override
  void dispose() {
    _cropDebounce?.cancel();
    _cropController.dispose();
    super.dispose();
  }

  void _scheduleCropSearch(String value) {
    _cropDebounce?.cancel();
    final query = value.trim();
    setState(() {
      _cropName = query;
      if (query.isEmpty) _cropSuggestions = [];
    });
    if (query.isEmpty) return;
    _cropDebounce = Timer(const Duration(milliseconds: 280), () async {
      if (!mounted) return;
      setState(() => _cropSearching = true);
      try {
        final rows = await _api.searchDiagnosticCrops(query: query, limit: 8);
        if (!mounted) return;
        setState(() => _cropSuggestions = rows);
      } catch (_) {
        if (!mounted) return;
        setState(() => _cropSuggestions = []);
      } finally {
        if (mounted) setState(() => _cropSearching = false);
      }
    });
  }

  void _selectCropSuggestion(Map<String, dynamic> crop) {
    final id = (crop['id'] ?? crop['name'] ?? '').toString();
    final label = (crop['label'] ?? crop['name'] ?? id).toString();
    setState(() {
      _cropName = id;
      _cropController.text = label;
      _cropSuggestions = [];
    });
    FocusScope.of(context).unfocus();
  }

  Future<void> _pick(ImageSource src) async {
    final p = await _picker.pickImage(
        source: src, maxWidth: 1024, imageQuality: 80);
    if (p != null) setState(() { _img = File(p.path); _result = null; _err = null; });
  }

  Future<void> _diagnose() async {
    if (_img == null) return;
    setState(() { _loading = true; _err = null; });
    try {
      final sess = await _store.getOrCreateSession();
      final r    = await _api.diagnose(
          image: _img!, crop: _cropName.isEmpty ? 'unknown' : _cropName,
          sessionId: sess, lang: widget.lang);
      setState(() { _result = r; _loading = false; });
    } catch (e) {
      setState(() { _loading = false; _err = e.toString(); });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(AppColors.background),
    appBar: AppBar(
      title: const Text('🔬 KrishiRaksha',
          style: TextStyle(fontWeight: FontWeight.bold)),
    ),
    body: SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(children: [
        // Info
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(AppColors.chipAmber),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Text(
            '📸 फसल की पत्ती / फल की तस्वीर अपलोड करें\n'
            'Model ready होने पर AI पहचान; model missing हो तो सुरक्षित advisory fallback।',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, height: 1.5),
          ),
        ),
        const SizedBox(height: 16),
        // Crop search
        TextFormField(
          controller: _cropController,
          decoration: InputDecoration(
            labelText: 'फसल खोजें या नाम लिखें',
            hintText: 'Wheat, धान, Makhana...',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _cropSearching
                ? const Padding(
                    padding: EdgeInsets.all(12),
                    child: SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                : null,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
            filled: true, fillColor: Colors.white,
          ),
          textInputAction: TextInputAction.done,
          autocorrect: false,
          onChanged: _scheduleCropSearch,
        ),
        if (_cropSuggestions.isNotEmpty) ...[
          const SizedBox(height: 8),
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.black12),
            ),
            child: Column(
              children: _cropSuggestions.map((crop) {
                final label = (crop['label'] ?? crop['name'] ?? '').toString();
                final category = (crop['category'] ?? 'crop').toString();
                return ListTile(
                  dense: true,
                  leading: const Icon(Icons.grass, color: Color(AppColors.primary)),
                  title: Text(label),
                  subtitle: Text(category),
                  onTap: () => _selectCropSuggestion(crop),
                );
              }).toList(),
            ),
          ),
        ],
        const SizedBox(height: 16),
        // Image picker area
        GestureDetector(
          onTap: () => _showPicker(),
          child: Container(
            height: 200, width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(AppColors.primary), width: 2),
            ),
            child: _img != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(14),
                    child: Image.file(_img!, fit: BoxFit.cover))
                : const Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.add_a_photo, size: 48, color: Color(AppColors.primary)),
                      SizedBox(height: 8),
                      Text('तस्वीर अपलोड करें',
                          style: TextStyle(color: Color(AppColors.primary))),
                    ]),
          ),
        ),
        const SizedBox(height: 12),
        // Action buttons
        Row(children: [
          Expanded(child: OutlinedButton.icon(
            icon: const Icon(Icons.photo_library),
            label: const Text('Gallery'),
            onPressed: () => _pick(ImageSource.gallery),
          )),
          const SizedBox(width: 12),
          Expanded(child: OutlinedButton.icon(
            icon: const Icon(Icons.camera_alt),
            label: const Text('Camera'),
            onPressed: () => _pick(ImageSource.camera),
          )),
        ]),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _img == null || _loading ? null : _diagnose,
            child: _loading
                ? const SizedBox(height: 20, width: 20,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : const Text('🔍 रोग पहचानें',
                    style: TextStyle(fontSize: 16)),
          ),
        ),
        if (_err != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.red.shade50,
              borderRadius: BorderRadius.circular(10)),
            child: Text('⚠️ $_err',
                style: TextStyle(color: Colors.red.shade700)),
          ),
        ],
        if (_result != null) ...[
          const SizedBox(height: 16),
          _resultCard(_result!),
        ],
      ]),
    ),
  );

  Widget _resultCard(Map<String, dynamic> r) {
    final disease    = (r['disease'] ?? r['disease_name'] ?? 'Unknown').toString();
    final confidence = ((r['confidence'] as num?)?.toDouble() ?? 0) * 100;
    final response   = (r['response'] ?? r['recommendation'] ?? r['message'] ?? '').toString();
    final status     = (r['status'] ?? '').toString();
    final isFallback = status == 'advisory_fallback' ||
        status == 'model_unavailable' ||
        status == 'tensorflow_missing';
    final statusText = status == 'advisory_fallback'
        ? 'Advisory fallback'
        : status == 'model_unavailable'
            ? 'Model unavailable'
            : status == 'tensorflow_missing'
                ? 'ML dependencies missing'
                : status == 'low_confidence'
                    ? 'Low confidence'
                    : status == 'not_plant'
                        ? 'Photo not recognized as plant'
                        : 'AI result';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6)],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.bug_report, color: Color(AppColors.warning)),
          const SizedBox(width: 8),
          Expanded(child: Text('रोग: $disease',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16))),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: isFallback
                  ? Colors.blueGrey.shade50
                  : confidence > 75 ? Colors.green.shade50 : Colors.orange.shade50,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(isFallback ? 'fallback' : '${confidence.toStringAsFixed(0)}%',
                style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: isFallback
                        ? Colors.blueGrey
                        : confidence > 75 ? Colors.green : Colors.orange)),
          ),
        ]),
        const SizedBox(height: 8),
        Text(statusText,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: isFallback ? Colors.blueGrey : const Color(AppColors.primary),
            )),
        const Divider(height: 20),
        Text(response, style: const TextStyle(fontSize: 14, height: 1.6)),
        const SizedBox(height: 12),
        const Text('📞 KVK/ICAR: 1800-180-1551',
            style: TextStyle(fontSize: 12, color: Colors.grey)),
      ]),
    );
  }

  void _showPicker() => showModalBottomSheet(
    context: context,
    builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
      ListTile(leading: const Icon(Icons.camera_alt), title: const Text('Camera'),
          onTap: () { Navigator.pop(context); _pick(ImageSource.camera); }),
      ListTile(leading: const Icon(Icons.photo_library), title: const Text('Gallery'),
          onTap: () { Navigator.pop(context); _pick(ImageSource.gallery); }),
    ])),
  );
}

// ── Government Schemes Screen ─────────────────────────────────────────────────
class SchemesScreen extends StatelessWidget {
  final String lang;
  const SchemesScreen({super.key, required this.lang});

  static const _schemes = [
    {'name': 'PM-Kisan Samman Nidhi', 'h': 'पीएम-किसान',
     'desc': '₹6,000/वर्ष — 3 किस्त ₹2,000', 'url': 'https://pmkisan.gov.in',
     'phone': '155261'},
    {'name': 'PMFBY Crop Insurance',  'h': 'प्रधानमंत्री फसल बीमा',
     'desc': 'खरीफ 2% · रबी 1.5% प्रीमियम',  'url': 'https://pmfby.gov.in',
     'phone': '14447'},
    {'name': 'Kisan Credit Card',     'h': 'किसान क्रेडिट कार्ड',
     'desc': '₹3 लाख @4% ब्याज',              'url': 'https://www.nabard.org',
     'phone': '1800-180-1551'},
    {'name': 'PM-KUSUM Solar Pump',   'h': 'पीएम-कुसुम',
     'desc': '90% सब्सिडी',                    'url': 'https://pmkusum.mnre.gov.in',
     'phone': '1800-180-3333'},
    {'name': 'Soil Health Card',      'h': 'मृदा स्वास्थ्य कार्ड',
     'desc': 'निःशुल्क मिट्टी जांच',           'url': 'https://soilhealth.dac.gov.in',
     'phone': '1800-180-1551'},
    {'name': 'eNAM',                  'h': 'राष्ट्रीय कृषि बाजार',
     'desc': 'ऑनलाइन मंडी व्यापार',           'url': 'https://enam.gov.in',
     'phone': '1800-270-0224'},
  ];

  Future<void> _open(String url) async {
    final u = Uri.tryParse(url);
    if (u != null && await canLaunchUrl(u)) launchUrl(u, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(AppColors.background),
    appBar: AppBar(
      title: const Text('🏛️ सरकारी योजनाएं',
          style: TextStyle(fontWeight: FontWeight.bold)),
    ),
    body: ListView(padding: const EdgeInsets.all(12), children: [
      // Kisan helpline banner
      Card(
        color: const Color(AppColors.chipGreen),
        child: ListTile(
          leading: const Icon(Icons.phone, color: Color(AppColors.primary)),
          title: const Text('Kisan Call Centre: 1800-180-1551',
              style: TextStyle(fontWeight: FontWeight.w600)),
          subtitle: const Text('निःशुल्क · 24x7'),
          onTap: () => _open('tel:18001801551'),
        ),
      ),
      const SizedBox(height: 8),
      ..._schemes.map((s) => Card(
        margin: const EdgeInsets.symmetric(vertical: 4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: ExpansionTile(
          leading: const CircleAvatar(
            backgroundColor: Color(AppColors.chipGreen),
            child: Icon(Icons.agriculture, color: Color(AppColors.primary), size: 18),
          ),
          title: Text(s['h']!,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
          subtitle: Text(s['name']!,
              style: const TextStyle(fontSize: 11, color: Colors.grey)),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(s['desc']!,
                    style: const TextStyle(fontSize: 13, height: 1.5)),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(child: OutlinedButton.icon(
                    icon: const Icon(Icons.phone, size: 14),
                    label: Text(s['phone']!,
                        style: const TextStyle(fontSize: 12)),
                    onPressed: () => _open('tel:${s['phone']}'),
                  )),
                  const SizedBox(width: 8),
                  Expanded(child: ElevatedButton.icon(
                    icon: const Icon(Icons.open_in_new, size: 14, color: Colors.white),
                    label: const Text('आवेदन करें',
                        style: TextStyle(color: Colors.white, fontSize: 12)),
                    onPressed: () => _open(s['url']!),
                  )),
                ]),
              ]),
            ),
          ],
        ),
      )),
    ]),
  );
}
