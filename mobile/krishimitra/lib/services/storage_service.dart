/// KrishiMitra Storage Service — local persistence via SharedPreferences
library;

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/app_models.dart';

class StorageService {
  static final StorageService _instance = StorageService._internal();
  factory StorageService() => _instance;
  StorageService._internal();

  static const String _langKey    = 'km_language';
  static const String _sessionKey = 'km_session_id';
  static const String _chatKey    = 'km_chat_history';
  static const String _mandiKey   = 'km_selected_mandi';

  // ── Language ──────────────────────────────────────────────────────────────

  Future<String> getLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_langKey) ?? 'hi';
  }

  Future<void> setLanguage(String code) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_langKey, code);
  }

  // ── Session ───────────────────────────────────────────────────────────────

  Future<String> getOrCreateSessionId() async {
    final prefs = await SharedPreferences.getInstance();
    var id = prefs.getString(_sessionKey);
    if (id == null || id.isEmpty) {
      id = 'sess_${DateTime.now().millisecondsSinceEpoch}';
      await prefs.setString(_sessionKey, id);
    }
    return id;
  }

  // ── Selected mandi ────────────────────────────────────────────────────────

  Future<String?> getSelectedMandi() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_mandiKey);
  }

  Future<void> setSelectedMandi(String mandiName) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_mandiKey, mandiName);
  }

  // ── Chat history (last 50 messages, JSON encoded) ─────────────────────────

  Future<List<ChatMessage>> loadChatHistory() async {
    final prefs  = await SharedPreferences.getInstance();
    final stored = prefs.getStringList(_chatKey) ?? [];
    return stored.map((s) {
      try {
        final decoded = jsonDecode(s);
        return ChatMessage.fromJson(decoded as Map<String, dynamic>);
      } catch (_) {
        return null;
      }
    }).whereType<ChatMessage>().toList();
  }

  Future<void> saveChatHistory(List<ChatMessage> messages) async {
    final prefs  = await SharedPreferences.getInstance();
    // Keep last 50 messages only
    final recent = messages.length > 50
        ? messages.sublist(messages.length - 50)
        : messages;
    await prefs.setStringList(
      _chatKey,
      recent.map((m) => jsonEncode(m.toJson())).toList(),
    );
  }

  Future<void> clearChatHistory() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_chatKey);
  }
}
