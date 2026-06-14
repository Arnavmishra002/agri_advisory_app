/// KrishiMitra Disease Detection (KrishiRaksha) Screen
library;

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../services/storage_service.dart';
import '../utils/constants.dart';

class DiseaseDetectionScreen extends StatefulWidget {
  final String language;
  const DiseaseDetectionScreen({super.key, required this.language});
  @override
  State<DiseaseDetectionScreen> createState() => _DiseaseDetectionScreenState();
}

class _DiseaseDetectionScreenState extends State<DiseaseDetectionScreen> {
  final _api      = ApiService();
  final _locSvc   = LocationService();
  final _storage  = StorageService();
  final _picker   = ImagePicker();

  File?                  _image;
  Map<String, dynamic>?  _result;
  bool                   _loading = false;
  String?                _error;
  String                 _cropName = '';

  static const List<String> _commonCrops = [
    'wheat', 'rice', 'maize', 'cotton', 'soybean',
    'tomato', 'potato', 'mustard', 'onion', 'gram',
  ];

  Future<void> _pickImage(ImageSource source) async {
    final picked = await _picker.pickImage(
      source:   source,
      maxWidth: 1024,
      imageQuality: 80,
    );
    if (picked != null) {
      setState(() { _image = File(picked.path); _result = null; _error = null; });
    }
  }

  Future<void> _diagnose() async {
    if (_image == null) return;
    setState(() { _loading = true; _error = null; });
    try {
      final sessionId = await _storage.getOrCreateSessionId();
      final result    = await _api.diagnoseCropDisease(
        imageFile: _image!,
        cropName:  _cropName.isEmpty ? 'unknown' : _cropName,
        sessionId: sessionId,
        language:  widget.language,
      );
      setState(() { _result = result; _loading = false; });
    } catch (e) {
      setState(() { _loading = false; _error = e.toString(); });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: AppBar(
        backgroundColor: const Color(AppColors.primary),
        title: const Text('🔬 KrishiRaksha',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          // Info banner
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(AppColors.chipAmber),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(AppColors.accent)),
            ),
            child: const Text(
              '📸 फसल की पत्ती/फल की तस्वीर अपलोड करें।\n'
              'AI 150+ रोगों की पहचान करेगा।',
              style: TextStyle(fontSize: 13, height: 1.5),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 16),
          // Crop selector
          DropdownButtonFormField<String>(
            value: _cropName.isEmpty ? null : _cropName,
            decoration: InputDecoration(
              labelText: 'फसल चुनें (वैकल्पिक)',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
              filled: true,
              fillColor: Colors.white,
            ),
            items: _commonCrops.map((c) => DropdownMenuItem(
              value: c,
              child: Text(c),
            )).toList(),
            onChanged: (v) => setState(() => _cropName = v ?? ''),
          ),
          const SizedBox(height: 16),
          // Image area
          GestureDetector(
            onTap: () => _showImageSourceDialog(),
            child: Container(
              height: 220,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                    color: const Color(AppColors.primary), width: 2,
                    style: BorderStyle.solid),
              ),
              child: _image != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: Image.file(_image!, fit: BoxFit.cover),
                    )
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.add_a_photo,
                            size: 48, color: Color(AppColors.primary)),
                        const SizedBox(height: 8),
                        const Text('तस्वीर अपलोड करें',
                            style: TextStyle(color: Color(AppColors.primary))),
                      ],
                    ),
            ),
          ),
          const SizedBox(height: 16),
          // Action buttons
          Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                icon: const Icon(Icons.photo_library),
                label: const Text('Gallery'),
                onPressed: () => _pickImage(ImageSource.gallery),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                icon: const Icon(Icons.camera_alt),
                label: const Text('Camera'),
                onPressed: () => _pickImage(ImageSource.camera),
              ),
            ),
          ]),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(AppColors.primary),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: _image == null || _loading ? null : _diagnose,
              child: _loading
                  ? const SizedBox(
                      height: 20, width: 20,
                      child: CircularProgressIndicator(
                          color: Colors.white, strokeWidth: 2))
                  : const Text('🔍 रोग पहचानें',
                      style: TextStyle(color: Colors.white, fontSize: 16)),
            ),
          ),
          const SizedBox(height: 16),
          // Results
          if (_error != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text('⚠️ $_error',
                  style: TextStyle(color: Colors.red.shade700)),
            ),
          if (_result != null) _buildResult(_result!),
        ]),
      ),
    );
  }

  Widget _buildResult(Map<String, dynamic> r) {
    final disease    = r['disease']    as String? ?? 'Unknown';
    final confidence = ((r['confidence'] as num?)?.toDouble() ?? 0) * 100;
    final response   = r['response']   as String? ?? '';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(AppColors.primary).withOpacity(0.3)),
        boxShadow: const [BoxShadow(color: Colors.black08, blurRadius: 6)],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.bug_report, color: Color(AppColors.warning)),
          const SizedBox(width: 8),
          Expanded(
            child: Text('रोग: $disease',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: confidence > 75
                  ? Colors.green.shade50
                  : Colors.orange.shade50,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text('${confidence.toStringAsFixed(0)}%',
                style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: confidence > 75 ? Colors.green : Colors.orange)),
          ),
        ]),
        const Divider(height: 20),
        Text(response,
            style: const TextStyle(fontSize: 14, height: 1.6)),
        const SizedBox(height: 12),
        const Text('📞 KVK/ICAR: 1800-180-1551',
            style: TextStyle(fontSize: 12, color: Colors.grey)),
      ]),
    );
  }

  void _showImageSourceDialog() {
    showModalBottomSheet(
      context: context,
      builder: (_) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(
            leading: const Icon(Icons.camera_alt),
            title: const Text('Camera'),
            onTap: () {
              Navigator.pop(context);
              _pickImage(ImageSource.camera);
            },
          ),
          ListTile(
            leading: const Icon(Icons.photo_library),
            title: const Text('Gallery'),
            onTap: () {
              Navigator.pop(context);
              _pickImage(ImageSource.gallery);
            },
          ),
        ]),
      ),
    );
  }
}
