import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../models/app_models.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../services/location_service.dart';
import '../utils/constants.dart';

/// Maps 2-char language code → BCP-47 locale for STT/TTS
String _toLangLocale(String lang) {
  const map = {
    'hi': 'hi-IN', 'en': 'en-IN', 'bn': 'bn-IN', 'te': 'te-IN',
    'mr': 'mr-IN', 'ta': 'ta-IN', 'gu': 'gu-IN', 'kn': 'kn-IN',
    'ml': 'ml-IN', 'pa': 'pa-IN', 'or': 'or-IN', 'as': 'as-IN',
    'ur': 'ur-IN',
  };
  return map[lang] ?? 'hi-IN';
}

class ChatScreen extends StatefulWidget {
  final String lang, sessId;
  const ChatScreen({super.key, required this.lang, required this.sessId});
  @override State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen>
    with SingleTickerProviderStateMixin {
  final _ctrl   = TextEditingController();
  final _scroll = ScrollController();
  final _api    = ApiService();
  final _store  = StorageService();
  final _loc    = LocationService();

  // ── Voice ─────────────────────────────────────────────────────
  final _stt = SpeechToText();
  final _tts = FlutterTts();
  bool _sttAvailable     = false;
  bool _isListening      = false;
  bool _lastInputWasVoice = false;

  // ── Chat state ────────────────────────────────────────────────
  List<ChatMessage> _msgs     = [];
  bool              _typing   = false;
  String            _streamBuf = '';      // accumulates SSE tokens
  StreamSubscription<Map<String, dynamic>>? _streamSub;

  // ── Mic button pulse animation ────────────────────────────────
  late final AnimationController _micAnim;
  late final Animation<double>   _micScale;

  static const _suggestHi = [
    '🌾 गेहूँ में पानी कब दें?',
    '💰 आज का मंडी भाव',
    '🏛️ PM-Kisan स्थिति',
    '🐛 धान में कीट',
    '🌱 कौन सी फसल लगाऊं?',
    '🌦️ इस हफ्ते बारिश?',
  ];
  static const _suggestEn = [
    '🌾 When to water wheat?',
    '💰 Today\'s mandi price',
    '🏛️ Check PM-Kisan status',
    '🐛 Paddy pest control',
    '🌱 Best crop this season?',
    '🌦️ Rain this week?',
  ];

  @override
  void initState() {
    super.initState();
    _micAnim = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 600));
    _micScale = Tween<double>(begin: 1.0, end: 1.3)
        .animate(CurvedAnimation(parent: _micAnim, curve: Curves.easeInOut));
    _micAnim.addStatusListener((s) {
      if (s == AnimationStatus.completed) _micAnim.reverse();
      else if (s == AnimationStatus.dismissed && _isListening) _micAnim.forward();
    });
    _initVoice();
    _store.loadHistory().then((h) {
      if (mounted) setState(() => _msgs = h);
      _scrollBottom();
    });
  }

  @override
  void dispose() {
    _micAnim.dispose();
    _ctrl.dispose();
    _scroll.dispose();
    _streamSub?.cancel();
    _tts.stop();
    _stt.stop();
    super.dispose();
  }

  // ── Voice init ────────────────────────────────────────────────
  Future<void> _initVoice() async {
    _sttAvailable = await _stt.initialize(
      onError: (e) => _showSnack(
        widget.lang == 'hi' ? 'माइक उपलब्ध नहीं: ${e.errorMsg}' : 'Mic error: ${e.errorMsg}',
      ),
    );
    await _tts.setLanguage(_toLangLocale(widget.lang));
    await _tts.setSpeechRate(0.45);
    await _tts.setVolume(1.0);
    if (mounted) setState(() {});
  }

  Future<void> _toggleListen() async {
    if (!_sttAvailable) {
      _showSnack(widget.lang == 'hi' ? 'माइक उपलब्ध नहीं' : 'Microphone unavailable');
      return;
    }
    if (_isListening) {
      await _stt.stop();
      _micAnim.stop();
      if (mounted) setState(() => _isListening = false);
    } else {
      final locale = _toLangLocale(widget.lang);
      final started = await _stt.listen(
        localeId: locale,
        onResult: (result) {
          if (result.finalResult && result.recognizedWords.isNotEmpty) {
            _ctrl.text = result.recognizedWords;
            _micAnim.stop();
            if (mounted) setState(() => _isListening = false);
            _lastInputWasVoice = true;
            _send(result.recognizedWords);
          } else {
            if (mounted) setState(() => _ctrl.text = result.recognizedWords);
          }
        },
        listenFor: const Duration(seconds: 20),
        pauseFor: const Duration(seconds: 3),
        listenOptions: SpeechListenOptions(
          partialResults: true,
          autoPunctuation: true,
        ),
      );
      if (started) {
        _micAnim.forward();
        if (mounted) setState(() => _isListening = true);
      }
    }
  }

  void _scrollBottom() => WidgetsBinding.instance.addPostFrameCallback((_) {
    if (_scroll.hasClients) {
      _scroll.animateTo(_scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
    }
  });

  void _showSnack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), duration: const Duration(seconds: 2)));
  }

  // ── Send message (with SSE streaming) ────────────────────────
  Future<void> _send(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || _typing) return;
    _ctrl.clear();
    final voiceMode = _lastInputWasVoice;
    _lastInputWasVoice = false;

    final user = ChatMessage.user(trimmed);
    setState(() {
      _msgs.add(user);
      _typing   = true;
      _streamBuf = '';
    });
    _scrollBottom();
    HapticFeedback.lightImpact();

    final loc     = _loc.current;
    final history = _msgs
        .where((m) => m.isUser)
        .take(8)
        .map((m) => <String, String>{'role': 'user', 'content': m.content})
        .toList();

    // Optimistically add a streaming bot message placeholder
    final botId    = DateTime.now().millisecondsSinceEpoch.toString();
    final botPlaceholder = ChatMessage(
      id: botId, role: 'assistant', content: '', timestamp: DateTime.now());
    setState(() => _msgs.add(botPlaceholder));

    try {
      _streamSub = _api.chatStream(
        query: trimmed, sessionId: widget.sessId, language: widget.lang,
        location: loc.name, lat: loc.lat, lon: loc.lon,
        history: history,
      ).listen(
        (frame) {
          if (frame['error'] != null) {
            _finalizeStream(
              botId,
              widget.lang == 'hi'
                  ? '⚠️ नेटवर्क त्रुटि। कृपया दोबारा प्रयास करें।'
                  : '⚠️ Network error. Please try again.',
              voiceMode: false,
            );
            return;
          }
          if (frame['token'] != null) {
            if (mounted) setState(() {
              _streamBuf += frame['token'] as String;
              // Update the placeholder message's content in-place
              final idx = _msgs.indexWhere((m) => m.id == botId);
              if (idx != -1) {
                _msgs[idx] = ChatMessage(
                  id: botId, role: 'assistant',
                  content: _streamBuf, timestamp: DateTime.now(),
                  dataSource: 'streaming…',
                );
              }
            });
            _scrollBottom();
          }
          if (frame['done'] == true) {
            _finalizeStream(
              botId, _streamBuf,
              dataSource: frame['data_source'] as String?,
              intent:     frame['intent']      as String?,
              voiceMode:  voiceMode,
            );
          }
        },
        onError: (_) => _finalizeStream(
          botId,
          widget.lang == 'hi'
              ? '⚠️ नेटवर्क त्रुटि। कृपया दोबारा प्रयास करें।'
              : '⚠️ Network error. Please try again.',
          voiceMode: false,
        ),
        onDone: () {
          // Guard: if stream closed without done frame
          if (_typing) _finalizeStream(botId, _streamBuf, voiceMode: voiceMode);
        },
      );
    } catch (e) {
      _finalizeStream(
        botId,
        widget.lang == 'hi'
            ? '⚠️ नेटवर्क त्रुटि। कृपया दोबारा प्रयास करें।'
            : '⚠️ Network error. Please try again.',
        voiceMode: false,
      );
    }
  }

  void _finalizeStream(
    String botId, String content, {
    String? dataSource, String? intent, required bool voiceMode,
  }) {
    if (!mounted) return;
    _streamSub?.cancel();
    _streamSub = null;
    final idx = _msgs.indexWhere((m) => m.id == botId);
    final finalMsg = ChatMessage(
      id: botId, role: 'assistant',
      content: content.trim().isEmpty
          ? (widget.lang == 'hi' ? '⚠️ कोई जवाब नहीं। दोबारा कोशिश करें।'
                                  : '⚠️ No response. Try again.')
          : content,
      timestamp: DateTime.now(),
      dataSource: dataSource, intent: intent,
    );
    setState(() {
      if (idx != -1) _msgs[idx] = finalMsg; else _msgs.add(finalMsg);
      _typing    = false;
      _streamBuf = '';
    });
    _store.saveHistory(_msgs);
    _scrollBottom();

    // TTS playback if query was voice-initiated
    if (voiceMode && finalMsg.content.isNotEmpty &&
        !finalMsg.content.startsWith('⚠️')) {
      _tts.speak(finalMsg.content);
    }
  }

  // ── Build ─────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF0F4F0),
      appBar: _buildAppBar(),
      body: Column(children: [
        Expanded(
          child: _msgs.isEmpty
              ? _suggestions()
              : ListView.builder(
                  controller: _scroll,
                  padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
                  itemCount: _msgs.length,
                  itemBuilder: (_, i) => _bubble(_msgs[i]),
                ),
        ),
        _inputBar(),
      ]),
    );
  }

  PreferredSizeWidget _buildAppBar() => AppBar(
    flexibleSpace: Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF1B5E20), Color(0xFF2E7D32), Color(0xFF43A047)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
      ),
    ),
    backgroundColor: Colors.transparent,
    elevation: 0,
    title: const Row(children: [
      Text('🌾 ', style: TextStyle(fontSize: 24)),
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('KrishiMitra AI',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 17)),
        Text('स्मार्ट कृषि सहायक',
            style: TextStyle(color: Colors.white70, fontSize: 10)),
      ]),
    ]),
    actions: [
      // Live indicator
      Container(
        margin: const EdgeInsets.only(right: 4),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(10),
        ),
        child: const Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.circle, size: 7, color: Colors.greenAccent),
          SizedBox(width: 4),
          Text('Live', style: TextStyle(color: Colors.white70, fontSize: 10)),
        ]),
      ),
      IconButton(
        icon: const Icon(Icons.delete_outline_rounded, color: Colors.white60, size: 22),
        tooltip: 'Clear chat',
        onPressed: () async {
          await _store.clearHistory();
          if (mounted) setState(() => _msgs.clear());
        },
      ),
    ],
  );

  // ── Suggestion cards ──────────────────────────────────────────
  Widget _suggestions() {
    final s = widget.lang == 'hi' ? _suggestHi : _suggestEn;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(18),
      child: Column(children: [
        const SizedBox(height: 8),
        // Hero card
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF1B5E20), Color(0xFF2E7D32)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [BoxShadow(
              color: const Color(0xFF1B5E20).withValues(alpha: 0.3),
              blurRadius: 16, offset: const Offset(0, 6),
            )],
          ),
          child: Column(children: [
            const Text('🌾', style: TextStyle(fontSize: 52)),
            const SizedBox(height: 10),
            const Text('KrishiMitra AI',
                style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold,
                    color: Colors.white)),
            const SizedBox(height: 4),
            Text(
              widget.lang == 'hi'
                  ? '50,000+ किसान सवालों पर प्रशिक्षित'
                  : 'Trained on 50,000+ farmer queries',
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 16),
            // Feature badges
            Wrap(spacing: 8, runSpacing: 8, children: [
              _badge('🎤 Voice', Colors.white24),
              _badge('📡 Live Data', Colors.white24),
              _badge('🔒 Offline', Colors.white24),
              _badge('🌐 22 भाषाएं', Colors.white24),
            ]),
          ]),
        ),
        const SizedBox(height: 20),
        Align(
          alignment: Alignment.centerLeft,
          child: Text(
            widget.lang == 'hi' ? 'जल्दी पूछें:' : 'Quick questions:',
            style: TextStyle(fontWeight: FontWeight.w600,
                color: Colors.grey[700], fontSize: 13),
          ),
        ),
        const SizedBox(height: 10),
        GridView.count(
          crossAxisCount: 2, shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 10, mainAxisSpacing: 10,
          childAspectRatio: 2.6,
          children: s.map((q) => GestureDetector(
            onTap: () => _send(q.replaceAll(RegExp(r'^[^\s]+ '), '')),
            child: Container(
              alignment: Alignment.centerLeft,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                    color: const Color(AppColors.primary).withValues(alpha: 0.25)),
                boxShadow: [BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 4, offset: const Offset(0, 2))],
              ),
              child: Text(q, style: const TextStyle(fontSize: 12.5,
                  color: Color(AppColors.textPrimary)), maxLines: 2),
            ),
          )).toList(),
        ),
        const SizedBox(height: 18),
        // Helpline card
        Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
          decoration: BoxDecoration(
            color: const Color(AppColors.chipGreen),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
                color: const Color(AppColors.primary).withValues(alpha: 0.2)),
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            const Text('📞 ', style: TextStyle(fontSize: 18)),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Kisan Helpline: 1800-180-1551',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              Text(
                widget.lang == 'hi' ? 'निःशुल्क · 24 घंटे · 7 दिन'
                                    : 'Free · 24x7',
                style: const TextStyle(color: Colors.grey, fontSize: 11),
              ),
            ]),
          ]),
        ),
        const SizedBox(height: 80),  // padding for input bar
      ]),
    );
  }

  Widget _badge(String label, Color bg) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
    child: Text(label, style: const TextStyle(color: Colors.white, fontSize: 11)),
  );

  // ── Chat bubble ───────────────────────────────────────────────
  Widget _bubble(ChatMessage m) {
    final isUser = m.isUser;
    final isEmpty = m.content.isEmpty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            Container(
              width: 32, height: 32,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF1B5E20), Color(0xFF43A047)],
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Center(child: Text('🌾', style: TextStyle(fontSize: 16))),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              constraints: BoxConstraints(
                  maxWidth: MediaQuery.of(context).size.width * 0.8),
              decoration: BoxDecoration(
                gradient: isUser
                    ? const LinearGradient(
                        colors: [Color(0xFF1B5E20), Color(0xFF2E7D32)],
                        begin: Alignment.topLeft, end: Alignment.bottomRight,
                      )
                    : null,
                color: isUser ? null : Colors.white,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(18),
                  topRight: const Radius.circular(18),
                  bottomLeft: Radius.circular(isUser ? 18 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 18),
                ),
                boxShadow: [BoxShadow(
                    color: Colors.black.withValues(alpha: 0.07),
                    blurRadius: 8, offset: const Offset(0, 2))],
              ),
              child: isEmpty
                  ? _streamingIndicator()
                  : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(
                        m.content,
                        style: TextStyle(
                          color: isUser ? Colors.white : const Color(AppColors.textPrimary),
                          fontSize: 14, height: 1.55,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                        if (!isUser && m.dataSource != null &&
                            m.dataSource!.isNotEmpty && m.dataSource != 'streaming…')
                          Expanded(child: Row(children: [
                            const Icon(Icons.sensors, size: 9, color: Colors.grey),
                            const SizedBox(width: 3),
                            Flexible(child: Text(m.dataSource!,
                                style: const TextStyle(fontSize: 9, color: Colors.grey),
                                overflow: TextOverflow.ellipsis)),
                          ])),
                        Text(_fmtTime(m.timestamp),
                            style: TextStyle(
                              fontSize: 10,
                              color: isUser ? Colors.white60 : Colors.grey[400],
                            )),
                      ]),
                    ]),
            ),
          ),
          if (isUser) const SizedBox(width: 8),
        ],
      ),
    );
  }

  Widget _streamingIndicator() => Row(mainAxisSize: MainAxisSize.min, children: [
    _dot(0), const SizedBox(width: 4),
    _dot(1), const SizedBox(width: 4),
    _dot(2),
    const SizedBox(width: 8),
    Text(_streamBuf.isEmpty ? '' : '${_streamBuf.length} chars…',
        style: const TextStyle(fontSize: 10, color: Colors.grey)),
  ]);

  Widget _dot(int i) => TweenAnimationBuilder<double>(
    tween: Tween(begin: 0.3, end: 1.0),
    duration: Duration(milliseconds: 500 + i * 150),
    builder: (_, v, __) => Opacity(
      opacity: v,
      child: Container(
        width: 8, height: 8,
        decoration: const BoxDecoration(
            color: Color(AppColors.primary), shape: BoxShape.circle),
      ),
    ),
  );

  // ── Input bar ─────────────────────────────────────────────────
  Widget _inputBar() => Container(
    padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
    decoration: BoxDecoration(
      color: Colors.white,
      boxShadow: [BoxShadow(
          color: Colors.black.withValues(alpha: 0.08),
          blurRadius: 12, offset: const Offset(0, -3))],
    ),
    child: SafeArea(
      top: false,
      child: Row(children: [
        Expanded(
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFFF0F4F0),
              borderRadius: BorderRadius.circular(28),
            ),
            child: TextField(
              controller: _ctrl,
              maxLines: 4, minLines: 1,
              textCapitalization: TextCapitalization.sentences,
              decoration: InputDecoration(
                hintText: widget.lang == 'hi'
                    ? 'कोई भी कृषि सवाल पूछें...'
                    : 'Ask any farming question...',
                hintStyle: TextStyle(color: Colors.grey[500], fontSize: 14),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(
                    horizontal: 18, vertical: 12),
              ),
              onSubmitted: _typing ? null : _send,
            ),
          ),
        ),
        const SizedBox(width: 8),
        // ── Mic button ────────────────────────────────────────
        if (_sttAvailable)
          AnimatedBuilder(
            animation: _micScale,
            builder: (_, child) => Transform.scale(
              scale: _micScale.value,
              child: child,
            ),
            child: GestureDetector(
              onTap: _typing ? null : _toggleListen,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: 46, height: 46,
                decoration: BoxDecoration(
                  color: _isListening
                      ? const Color(0xFFE53935)
                      : const Color(AppColors.primary).withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                  border: _isListening
                      ? Border.all(color: const Color(0xFFE53935).withValues(alpha: 0.4), width: 2)
                      : null,
                ),
                child: Icon(
                  _isListening ? Icons.mic : Icons.mic_none_rounded,
                  color: _isListening ? Colors.white : const Color(AppColors.primary),
                  size: 22,
                ),
              ),
            ),
          ),
        if (_sttAvailable) const SizedBox(width: 8),
        // ── Send button ───────────────────────────────────────
        GestureDetector(
          onTap: _typing ? null : () => _send(_ctrl.text),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: 48, height: 48,
            decoration: BoxDecoration(
              gradient: _typing
                  ? null
                  : const LinearGradient(
                      colors: [Color(0xFF2E7D32), Color(0xFF43A047)],
                      begin: Alignment.topLeft, end: Alignment.bottomRight,
                    ),
              color: _typing ? Colors.grey[300] : null,
              shape: BoxShape.circle,
              boxShadow: _typing
                  ? []
                  : [BoxShadow(
                      color: const Color(AppColors.primary).withValues(alpha: 0.4),
                      blurRadius: 10, offset: const Offset(0, 4))],
            ),
            child: Icon(
              _typing ? Icons.hourglass_empty_rounded : Icons.send_rounded,
              color: Colors.white, size: 22,
            ),
          ),
        ),
      ]),
    ),
  );

  String _fmtTime(DateTime dt) =>
      '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
}
