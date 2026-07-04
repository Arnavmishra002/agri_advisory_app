/// Suggested queries shown on empty chat screen
library;

import 'package:flutter/material.dart';
import '../utils/constants.dart';

class SuggestedQueries extends StatelessWidget {
  final List<String> suggestions;
  final void Function(String) onTap;

  const SuggestedQueries({
    super.key,
    required this.suggestions,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 20),
          const Text('🌾', style: TextStyle(fontSize: 64)),
          const SizedBox(height: 12),
          const Text(
            'KrishiMitra AI',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Color(AppColors.primary),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'आपका स्मार्ट कृषि सहायक',
            style: TextStyle(
              fontSize: 15,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 32),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: suggestions.map((q) => _SuggestionChip(
              label: q,
              onTap: () => onTap(q),
            )).toList(),
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(AppColors.chipGreen),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(AppColors.primary), width: 0.5),
            ),
            child: const Column(
              children: [
                Text('📞 Kisan Helpline: 1800-180-1551',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                SizedBox(height: 4),
                Text('निःशुल्क · 24x7 · सभी भाषाएं',
                  style: TextStyle(fontSize: 12, color: Colors.grey)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SuggestionChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  const _SuggestionChip({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(AppColors.primary), width: 1),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 3)],
        ),
        child: Text(
          label,
          style: const TextStyle(
            fontSize: 13,
            color: Color(AppColors.primary),
          ),
        ),
      ),
    );
  }
}
