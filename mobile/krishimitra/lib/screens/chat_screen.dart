/// KrishiMitra Chat Screen — AI agricultural chatbot with voice input
library;

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../services/location_service.dart';
import '../utils/constants.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/suggested_queries.dart';

class ChatScreen extends StatefulWidget {
  final String language;
  final String sessionId;
  const ChatScreen({super.key, required this.language, required this.sessionId});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller   = TextEditingController();
  final _scrollCtrl   = ScrollController();
  final _api          = ApiService();
  final _storage      = StorageService();
  final _locationSvc  = LocationService();

  List<ChatMessage> _messages = [];
  bool _isTyping = false;
  String _currentLang = 'hi';

  // Suggested queries shown when chat is empty
  static const List<String> _suggestionsHi = [
    'गेहूँ की बुवाई कब करें?',
    'आज का मंडी भाव',
    'PM-Kisan आवेदन कैसे करें?',
    'कीटनाशक की जानकारी',
    'धान में सिंचाई कब करें?',
  ];
  static const List<String> _suggestionsEn = [
    'When to sow wheat?',
    'Today\'s mandi price',
    'Apply for PM-Kisan',
    'Pest control tips',
    'Rice irrigation schedule',
  ];

  @override
  void initState() {
    super.initState();
    _currentLang = widget.language;
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    final history = await _storage.loadChatHistory();
    if (mounted) setState(() => _messages = history);
    _scrollToBottom();
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    _controller.clear();

    final userMsg = ChatMessage(
      id:        DateTime.now().toIso8601String(),
      role:      'user',
      content:   text.trim(),
      timestamp: DateTime.now(),
      language:  _currentLang,
    );

    setState(() {
      _messages.add(userMsg);
      _isTyping = true;
    });
    _scrollToBottom();

    try {
      final loc = _locationSvc.current;
      final history = _messages
          .where((m) => m.role == 'user')
          .map((m) => {'role': m.role, 'content': m.content})
          .toList();

      final result = await _api.sendChatMessage(
        query:     text.trim(),
        sessionId: widget.sessionId,
        language:  _currentLang,
        location:  loc.displayName,
        latitude:  loc.latitude,
        longitude: loc.longitude,
        history:   history.cast<Map<String, String>>(),
      );

      final botMsg = ChatMessage(
        id:         DateTime.now().toIso8601String(),
        role:       'assistant',
        content:    result['answer'] as String? ?? result['response'] as String? ?? 'कोई उत्तर नहीं मिला',
        timestamp:  DateTime.now(),
        intent:     result['intent']      as String?,
        language:   result['language']    as String? ?? _currentLang,
        dataSource: result['data_source'] as String?,
        sources: (result['sources'] as List?)?.cast<String>() ?? [],
      );

      setState(() => _messages.add(botMsg));
      await _storage.saveChatHistory(_messages);
    } catch (e) {
      setState(() => _messages.add(ChatMessage(
        id:        DateTime.now().toIso8601String(),
        role:      'assistant',
        content:   _currentLang == 'hi'
            ? '⚠️ नेटवर्क त्रुटि — कृपया दोबारा प्रयास करें।'
            : '⚠️ Network error. Please try again.',
        timestamp: DateTime.now(),
      )));
    } finally {
      if (mounted) setState(() => _isTyping = false);
      _scrollToBottom();
    }
  }

  @override
  Widget build(BuildContext context) {
    final suggestions = _currentLang == 'hi' ? _suggestionsHi : _suggestionsEn;
    return Scaffold(
      backgroundColor: const Color(AppColors.background),
      appBar: AppBar(
        backgroundColor: const Color(AppColors.primary),
        title: const Row(children: [
          Text('🌾 ', style: TextStyle(fontSize: 20)),
          Text('KrishiMitra AI', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        ]),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline, color: Colors.white70),
            tooltip: 'Clear chat',
            onPressed: () async {
              await _storage.clearChatHistory();
              if (mounted) setState(() => _messages.clear());
            },
          ),
        ],
      ),
      body: Column(children: [
        // ── Messages list ──────────────────────────────────────────
        Expanded(
          child: _messages.isEmpty
              ? SuggestedQueries(
                  suggestions: suggestions,
                  onTap: _sendMessage,
                )
              : ListView.builder(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                  itemCount: _messages.length + (_isTyping ? 1 : 0),
                  itemBuilder: (ctx, i) {
                    if (i == _messages.length) {
                      return const TypingIndicator();
                    }
                    return ChatBubble(message: _messages[i]);
                  },
                ),
        ),
        // ── Input bar ──────────────────────────────────────────────
        _buildInputBar(),
      ]),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: const BoxDecoration(
        color: Colors.white,
        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 4)],
      ),
      child: SafeArea(
        top: false,
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: _controller,
              textCapitalization: TextCapitalization.sentences,
              maxLines: 4,
              minLines: 1,
              decoration: InputDecoration(
                hintText: _currentLang == 'hi'
                    ? 'कोई भी कृषि सवाल पूछें...'
                    : 'Ask any farming question...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: const Color(0xFFF0F4F0),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
              onSubmitted: _sendMessage,
            ),
          ),
          const SizedBox(width: 6),
          FloatingActionButton.small(
            heroTag: 'send_btn',
            backgroundColor: const Color(AppColors.primary),
            onPressed: _isTyping ? null : () => _sendMessage(_controller.text),
            child: const Icon(Icons.send, color: Colors.white, size: 20),
          ),
        ]),
      ),
    );
  }
}
