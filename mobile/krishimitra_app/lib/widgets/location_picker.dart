import 'dart:async';
import 'package:flutter/material.dart';
import '../services/location_service.dart';
import '../utils/constants.dart';

/// Zepto/Swiggy-style bottom sheet for location picking.
/// Features: GPS auto-detect, live search as-you-type, village level results.
class LocationPickerSheet extends StatefulWidget {
  final void Function(LocData) onSelected;

  const LocationPickerSheet({super.key, required this.onSelected});

  static Future<LocData?> show(BuildContext ctx,
      {required void Function(LocData) onSelected}) {
    return showModalBottomSheet<LocData>(
      context: ctx,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => LocationPickerSheet(onSelected: onSelected),
    );
  }

  @override
  State<LocationPickerSheet> createState() => _LocationPickerSheetState();
}

class _LocationPickerSheetState extends State<LocationPickerSheet> {
  final _ctrl    = TextEditingController();
  final _focusN  = FocusNode();
  final _svc     = LocationService();

  List<LocationResult> _results = [];
  bool  _searching  = false;
  bool  _gpsLoading = false;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _focusN.requestFocus();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _focusN.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onQueryChanged(String q) {
    _debounce?.cancel();
    if (q.trim().length < 2) {
      setState(() { _results = []; _searching = false; });
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 350), () async {
      setState(() => _searching = true);
      final r = await _svc.search(q);
      if (mounted) setState(() { _results = r; _searching = false; });
    });
  }

  Future<void> _detectGps() async {
    setState(() => _gpsLoading = true);
    final loc = await _svc.detectGps();
    if (mounted) {
      setState(() => _gpsLoading = false);
      if (loc != null) {
        widget.onSelected(loc);
        Navigator.pop(context);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('GPS location नहीं मिली। कृपया मैन्युअल खोजें।')),
        );
      }
    }
  }

  void _selectResult(LocationResult r) async {
    final loc = await _svc.setFromResult(r);
    widget.onSelected(loc);
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    return Container(
      height: mq.size.height * 0.88,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(children: [
        // Handle bar
        Container(
          width: 44, height: 4,
          margin: const EdgeInsets.only(top: 12, bottom: 8),
          decoration: BoxDecoration(
            color: Colors.grey[300],
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        // Header
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('अपना गाँव/शहर चुनें',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text('Village / Town / District खोजें',
                style: TextStyle(fontSize: 13, color: Colors.grey[600])),
          ]),
        ),
        const SizedBox(height: 16),
        // Search bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFFF5F5F5),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                  color: const Color(AppColors.primary).withValues(alpha: 0.3)),
            ),
            child: TextField(
              controller: _ctrl,
              focusNode: _focusN,
              onChanged: _onQueryChanged,
              textCapitalization: TextCapitalization.words,
              decoration: InputDecoration(
                hintText: 'गाँव / कस्बा / जिला टाइप करें...',
                hintStyle: TextStyle(color: Colors.grey[500], fontSize: 14),
                prefixIcon: const Icon(Icons.search_rounded,
                    color: Color(AppColors.primary)),
                suffixIcon: _searching
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: SizedBox(width: 20, height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2)))
                    : _ctrl.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 18),
                            onPressed: () {
                              _ctrl.clear();
                              setState(() => _results = []);
                            })
                        : null,
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(
                    vertical: 14, horizontal: 4),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        // GPS button
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: GestureDetector(
            onTap: _gpsLoading ? null : _detectGps,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(AppColors.primary).withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                    color: const Color(AppColors.primary).withValues(alpha: 0.2)),
              ),
              child: Row(children: [
                if (_gpsLoading)
                  const SizedBox(width: 22, height: 22,
                      child: CircularProgressIndicator(
                          color: Color(AppColors.primary), strokeWidth: 2.5))
                else
                  const Icon(Icons.my_location_rounded,
                      color: Color(AppColors.primary), size: 22),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('अपना GPS स्थान उपयोग करें',
                        style: TextStyle(
                            fontWeight: FontWeight.w600,
                            color: Color(AppColors.primary), fontSize: 14)),
                    Text('गाँव/मोहल्ला स्तर तक सटीक',
                        style: TextStyle(fontSize: 11, color: Colors.grey[600])),
                  ]),
                ),
                const Icon(Icons.arrow_forward_ios,
                    size: 14, color: Color(AppColors.primary)),
              ]),
            ),
          ),
        ),
        const SizedBox(height: 8),
        // Results
        Expanded(child: _buildResults()),
        SizedBox(height: mq.viewInsets.bottom),
      ]),
    );
  }

  Widget _buildResults() {
    if (_ctrl.text.trim().length < 2 && _results.isEmpty) {
      return _quickPicks();
    }
    if (_results.isEmpty && !_searching) {
      return Center(child: Column(
        mainAxisAlignment: MainAxisAlignment.center, children: [
        const Text('🔍', style: TextStyle(fontSize: 40)),
        const SizedBox(height: 12),
        Text('कोई स्थान नहीं मिला',
            style: TextStyle(color: Colors.grey[600])),
        const SizedBox(height: 6),
        Text('"${_ctrl.text}" के लिए',
            style: TextStyle(color: Colors.grey[400], fontSize: 12)),
      ]));
    }
    return ListView.separated(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      itemCount: _results.length,
      separatorBuilder: (_, __) => const Divider(height: 1, indent: 52),
      itemBuilder: (_, i) {
        final r = _results[i];
        return ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
          leading: Container(
            width: 40, height: 40,
            decoration: BoxDecoration(
              color: _typeColor(r.type).withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Center(child: Text(_typeEmoji(r.type),
                style: const TextStyle(fontSize: 18))),
          ),
          title: Text(r.name.isNotEmpty ? r.name : r.city,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
          subtitle: Text(
            [if (r.city.isNotEmpty && r.city != r.name) r.city,
             if (r.district.isNotEmpty && r.district != r.city) r.district,
             r.state].where((s) => s.isNotEmpty).join(', '),
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
          ),
          trailing: const Icon(Icons.arrow_forward_ios,
              size: 13, color: Colors.grey),
          onTap: () => _selectResult(r),
        );
      },
    );
  }

  Widget _quickPicks() {
    // Show common agri areas for quick selection
    const quick = [
      ('🌾', 'Barabanki', 'Uttar Pradesh', 26.9421, 81.3856),
      ('🌾', 'Ludhiana', 'Punjab', 30.9010, 75.8573),
      ('🌾', 'Nashik', 'Maharashtra', 19.9975, 73.7898),
      ('🌾', 'Guntur', 'Andhra Pradesh', 16.2992, 80.4575),
      ('🌾', 'Anand', 'Gujarat', 22.5645, 72.9289),
      ('🌾', 'Coimbatore', 'Tamil Nadu', 11.0168, 76.9558),
      ('🌾', 'Warangal', 'Telangana', 17.9784, 79.5941),
      ('🌾', 'Hoshiarpur', 'Punjab', 31.5317, 75.9114),
    ];
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      children: [
        Text('  लोकप्रिय कृषि क्षेत्र',
            style: TextStyle(fontWeight: FontWeight.bold,
                color: Colors.grey[600], fontSize: 12)),
        const SizedBox(height: 8),
        ...quick.map((q) => ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
          dense: true,
          leading: Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: const Color(AppColors.chipGreen),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(child: Text(q.$1,
                style: const TextStyle(fontSize: 16))),
          ),
          title: Text(q.$2, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(q.$3, style: TextStyle(
              fontSize: 11, color: Colors.grey[500])),
          trailing: const Icon(Icons.arrow_forward_ios, size: 12, color: Colors.grey),
          onTap: () async {
            final loc = LocData(
              lat: q.$4, lon: q.$5,
              name: q.$2, state: q.$3,
            );
            await _svc.setLocation(loc);
            widget.onSelected(loc);
            if (mounted) Navigator.pop(context);
          },
        )),
      ],
    );
  }

  Color _typeColor(String type) {
    switch (type) {
      case 'village': return const Color(AppColors.success);
      case 'city': return const Color(AppColors.primary);
      case 'district': return Colors.orange;
      default: return Colors.blue;
    }
  }

  String _typeEmoji(String type) {
    switch (type) {
      case 'village': return '🏘️';
      case 'city':    return '🏙️';
      case 'district': return '📍';
      default:         return '📌';
    }
  }
}
