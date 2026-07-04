import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/app_models.dart';

class StorageService {
  static final StorageService _i = StorageService._();
  factory StorageService() => _i;
  StorageService._();

  static const _lang    = 'km_lang';
  static const _session = 'km_session';
  static const _chat    = 'km_chat';
  static const _mandi   = 'km_mandi';

  Future<String> getLanguage() async =>
      (await SharedPreferences.getInstance()).getString(_lang) ?? 'hi';

  Future<void> setLanguage(String code) async =>
      (await SharedPreferences.getInstance()).setString(_lang, code);

  Future<String> getOrCreateSession() async {
    final p = await SharedPreferences.getInstance();
    var id = p.getString(_session);
    if (id == null || id.isEmpty) {
      id = 'sess_${DateTime.now().millisecondsSinceEpoch}';
      await p.setString(_session, id);
    }
    return id;
  }

  Future<String?> getSelectedMandi() async =>
      (await SharedPreferences.getInstance()).getString(_mandi);

  Future<void> setSelectedMandi(String name) async =>
      (await SharedPreferences.getInstance()).setString(_mandi, name);

  Future<List<ChatMessage>> loadHistory() async {
    final p = await SharedPreferences.getInstance();
    return (p.getStringList(_chat) ?? []).map((s) {
      try { return ChatMessage.fromJson(jsonDecode(s) as Map<String, dynamic>); }
      catch (_) { return null; }
    }).whereType<ChatMessage>().toList();
  }

  Future<void> saveHistory(List<ChatMessage> msgs) async {
    final p = await SharedPreferences.getInstance();
    final recent = msgs.length > 50 ? msgs.sublist(msgs.length - 50) : msgs;
    await p.setStringList(_chat, recent.map((m) => jsonEncode(m.toJson())).toList());
  }

  Future<void> clearHistory() async =>
      (await SharedPreferences.getInstance()).remove(_chat);
}
