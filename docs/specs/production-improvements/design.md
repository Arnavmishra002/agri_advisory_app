# KrishiMitra Production Improvements — Design

## Overview

Six targeted production improvements to the KrishiMitra app that address perceived latency,
field-usability, backend efficiency, observability, database performance, and offline resilience.
Each improvement is self-contained with a minimal blast radius; no existing behaviour is removed.

The improvements touch three layers:
- **Backend** (Django/DRF): SSE streaming endpoint, Celery async writes, Sentry span, DB index
- **Mobile** (Flutter): SSE client, voice input + TTS, Sentry Flutter SDK, Hive offline cache
- **Config/infra**: new pubspec deps, new migration, new health endpoint

---

## Glossary

- **SSE**: Server-Sent Events — HTTP/1.1 chunked streaming with `Content-Type: text/event-stream`
- **STT**: Speech-to-Text — converting microphone audio to a text transcript
- **TTS**: Text-to-Speech — converting a text string to audio playback
- **`_handle_query`**: the central method in `ChatbotViewSet` (`chatbot.py`) that runs the full chatbot pipeline
- **`chat_intelligence_service`**: the singleton in `services/chat_intelligence_service.py` whose `.answer()` calls Gemini
- **`session_memory`**: singleton in `services/session_memory_service.py` — `save_turn` and `update_session_context`
- **`FarmerInteractionLog`**: Django model in `models.py` that records every Q&A for ML training
- **`IoTSensorReading`**: Django model storing field sensor readings; queried in `_handle_query` with a lat/lon bounding-box filter
- **Hive**: Flutter key-value store (`hive` + `hive_flutter`) used for offline caching
- **`CacheService`**: new Flutter class in `lib/services/cache_service.dart` that wraps Hive reads/writes
- **Bug_Condition (C)**: inputs that trigger the defect under investigation (applicable to each sub-improvement)
- **Preservation**: all behaviour outside the change scope that must remain identical

---

## Improvement 1 — SSE Response Streaming

### Bug Details / Problem Statement

#### Current State

`POST /api/chatbot/query/` waits for `chat_intelligence_service.answer()` to return the
complete Gemini response before sending any bytes. Gemini token generation for a long
agricultural answer (100–300 tokens in Hindi) can take 3–8 seconds. The Flutter client
shows a static typing indicator for that entire window with no incremental content.

#### Bug Condition

```
FUNCTION isStreamingNeeded(request)
  INPUT: request — an HTTP chatbot request
  OUTPUT: boolean

  RETURN request.path == '/api/chatbot/stream/'
         AND request.method == 'POST'
         AND 'query' in request.data
END FUNCTION
```

**Examples:**
- `POST /api/chatbot/stream/ {"query": "गेहूँ में पानी कब दें?"}` → must stream tokens
- `POST /api/chatbot/query/ {"query": "..."}` → existing endpoint, no change (preservation)
- Gemini returns 250 tokens → client should see first token within ~200 ms

### Expected Behavior

#### Preservation Requirements

**Unchanged Behaviours:**
- `POST /api/chatbot/query/` returns the same JSON envelope, status codes, and latency
- `session_memory.save_turn`, `update_session_context`, and `FarmerInteractionLog.create`
  all execute on the stream path (after the stream completes)
- Rate-limiting middleware applies equally to `/api/chatbot/stream/`
- All existing `ChatbotViewSet` tests pass without modification

**Scope:** every request that does NOT go to `/api/chatbot/stream/` is completely unaffected.

### Hypothesized Root Cause

The existing endpoint architecture has no streaming path. `chat_intelligence_service.answer()`
returns a complete string. To stream we must:

1. Have Gemini emit a generator of token chunks rather than a completed string
2. Wrap it in Django's `StreamingHttpResponse` with `Content-Type: text/event-stream`
3. Add a new URL route without touching the existing router entry

Potential issues:
- `chat_intelligence_service.answer()` currently returns `dict`, not a generator —
  a new `answer_stream()` method (or `stream=True` kwarg) is needed
- `StreamingHttpResponse` does not play well with DRF's response pipeline;
  the streaming view must be a plain Django view, not a `ViewSet` action
- Gunicorn in sync mode buffers responses; `--timeout 120` and nginx
  `proxy_buffering off` must be set (documented, not enforced in code)

### Correctness Properties

Property 1: Bug Condition — SSE Frame Format and Ordering

_For any_ valid chatbot POST to `/api/chatbot/stream/`, the response SHALL have
`Content-Type: text/event-stream`, and every intermediate frame SHALL match
`data: {"token": "<chunk>"}\n\n`, and the final frame SHALL match
`data: {"done": true, "intent": "...", "data_source": "...", "language": "..."}\n\n`.

**Validates: Requirements 1.1, 1.2, 1.3**

Property 2: Preservation — Existing Endpoint Unchanged

_For any_ request to `POST /api/chatbot/query/` (the non-streaming path), the fixed
codebase SHALL produce a response byte-for-byte identical in shape to the response
produced before this improvement was applied.

**Validates: Requirements 1.4, C.1**

### Fix Implementation

#### Changes Required

**File:** `backend/advisory/services/chat_intelligence_service.py`

1. **Add `answer_stream()` method**: accepts the same arguments as `answer()`;
   calls `gemini_model.generate_content(..., stream=True)` and yields each
   `chunk.text` string. Final yield is a sentinel dict
   `{"__done__": True, "intent": ..., "language": ..., "data_source": ...}`.

**File:** `backend/advisory/api/viewsets/chatbot.py`

2. **Add `stream_chat` plain Django view function** (not a `ViewSet` action):
   - Reads request body identically to `_handle_query`
   - Calls `chat_intelligence_service.answer_stream()`
   - Wraps in `StreamingHttpResponse` with `content_type="text/event-stream"`
   - After the generator exhausts, fires `session_memory.save_turn`,
     `update_session_context`, and `FarmerInteractionLog.create` synchronously
     (or via Celery if Improvement 3 is applied first)

**File:** `backend/core/urls.py`

3. **Add route:** `path("api/chatbot/stream/", stream_chat, name="chatbot-stream")`
   — alongside the existing DRF router, not replacing it.

**File:** `mobile/krishimitra_app/lib/services/api_service.dart`

4. **Add `chatStream()` method**:
   - Opens `http.Request('POST', Uri.parse('$baseUrl/api/chatbot/stream/'))`
   - Calls `client.send(request)` to get `StreamedResponse`
   - Reads `response.stream` line by line, parses `data: {...}` frames
   - Yields parsed maps via a `Stream<Map<String, dynamic>>`

**File:** `mobile/krishimitra_app/lib/screens/chat_screen.dart`

5. **Replace `_api.chat()` call with streaming path**:
   - Add a `String _streamingContent` state variable
   - Listen to `_api.chatStream()`, appending each `token` to `_streamingContent`
     and calling `setState` to re-render the bubble
   - On `done` frame, promote `_streamingContent` to a full `ChatMessage` and save history
   - On stream error, fall back to `_api.chat()` for resilience

---

## Improvement 2 — Voice Input and TTS

### Bug Details / Problem Statement

#### Current State

`_inputBar()` in `chat_screen.dart` renders a `TextField` and a send `GestureDetector`.
There is no microphone affordance. Farmers working in the field cannot type in Hindi/regional
scripts on a mobile keyboard while handling tools. There is no TTS playback of AI responses.

#### Bug Condition

```
FUNCTION isVoiceInputNeeded(event)
  INPUT: event — a user interaction event in ChatScreen
  OUTPUT: boolean

  RETURN micButtonTapped(event)
         AND speechToTextAvailable()
         AND NOT alreadyListening()
END FUNCTION
```

**Examples:**
- User taps mic → app starts listening in `hi-IN` → recognized text fills TextField → auto-send
- STT fails → snack bar "माइक उपलब्ध नहीं" → text input still works
- AI responds after voice query → TTS reads response aloud in `hi-IN`
- User types query manually → TTS does NOT auto-play

### Expected Behavior

#### Preservation Requirements

**Unchanged Behaviours:**
- Text-only send flow (`_send(text)`) remains completely unchanged
- Existing `_inputBar()` layout and send button behaviour are preserved
- No additional dependencies are pulled in beyond `speech_to_text: ^6.x` and `flutter_tts: ^4.x`
- Screen disposal still calls `_ctrl.dispose()` and `_scroll.dispose()`

**Scope:** every interaction that does NOT involve the mic button is unaffected.

### Hypothesized Root Cause

The missing feature requires:
1. `speech_to_text` plugin — provides `SpeechToText` which wraps platform STT APIs
2. `flutter_tts` plugin — provides `FlutterTts` which wraps platform TTS engines
3. Platform permission handling — `RECORD_AUDIO` on Android, `NSMicrophoneUsageDescription` on iOS
4. State tracking — `_isListening` bool, `_lastInputWasVoice` bool

Potential issues:
- Language locale mapping: `widget.lang` is a 2-char code (`hi`, `te`) but STT/TTS expect
  BCP-47 tags (`hi-IN`, `te-IN`); a conversion helper is needed
- iOS simulator does not support STT — must guard with `stt.isAvailable` check
- `flutter_tts` on Android requires the `INTERNET` permission for cloud TTS engines;
  offline engines should be preferred via `setSharedInstance(false)` on iOS

### Correctness Properties

Property 1: Bug Condition — Voice Input Submits Recognised Transcript

_For any_ mic-button tap event where STT is available and the app is not already listening,
the fixed `_ChatScreenState` SHALL start recognition, fill the `TextField` with the
transcript, and invoke `_send()` automatically when silence is detected.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation — Text Input Behaviour Unchanged

_For any_ user interaction that does NOT involve the mic button (typing, pasting, tapping send),
the fixed `chat_screen.dart` SHALL behave identically to the original, and TTS SHALL NOT
auto-play.

**Validates: Requirements 2.6, C.1**

### Fix Implementation

#### Changes Required

**File:** `mobile/krishimitra_app/pubspec.yaml`

1. **Add deps:**
   ```yaml
   speech_to_text: ^6.6.0
   flutter_tts: ^4.0.2
   ```

**File:** `mobile/krishimitra_app/android/app/src/main/AndroidManifest.xml`

2. **Add permission** (already present for geolocator, add alongside it):
   `<uses-permission android:name="android.permission.RECORD_AUDIO"/>`

**File:** `mobile/krishimitra_app/ios/Runner/Info.plist`

3. **Add key:** `NSMicrophoneUsageDescription` → `"Voice input for farming queries"`

**File:** `mobile/krishimitra_app/lib/screens/chat_screen.dart`

4. **Add state variables:**
   ```dart
   final _stt = SpeechToText();
   final _tts = FlutterTts();
   bool _isListening = false;
   bool _lastInputWasVoice = false;
   ```

5. **Add `_initVoice()` call in `initState`** — calls `_stt.initialize()` and
   configures `_tts` language/speech rate.

6. **Add `_toggleListen()` method** — starts/stops STT, sets `_isListening`,
   calls `_send()` on final result, handles `onError` with snack bar.

7. **Modify `_send()`** — after calling existing logic, if `_lastInputWasVoice`,
   call `_tts.speak(bot.content)`; always reset `_lastInputWasVoice = false`.

8. **Modify `_inputBar()`** — insert mic `IconButton` between the TextField container
   and the send button. Mic shows `Icons.mic` (idle) or pulsing red `Icons.mic` (listening).

9. **Add `_langToLocale()` helper** — maps `'hi'→'hi-IN'`, `'te'→'te-IN'`, etc.
   for both STT and TTS locale strings.

10. **Modify `dispose()`** — add `_tts.stop()` and `_stt.stop()`.

---

## Improvement 3 — Celery Async Post-Response Writes

### Bug Details / Problem Statement

#### Current State

After `chat_intelligence_service.answer()` returns, `_handle_query` performs three
synchronous blocking DB writes before `return Response(...)`:

```python
# ~5–30 ms each on PostgreSQL
session_memory.save_turn(...)           # ChatHistory INSERT + ChatSession UPDATE
session_memory.update_session_context(...) # ChatSession UPDATE
FarmerInteractionLog.objects.create(...)   # INSERT
```

These writes add 15–90 ms to every response and hold a Gunicorn worker thread during
that time, reducing the effective concurrency of the server.

#### Bug Condition

```
FUNCTION isBlockingWrite(operation)
  INPUT: operation — a database write in _handle_query
  OUTPUT: boolean

  RETURN operation IN [save_turn, update_session_context, FarmerInteractionLog.create]
         AND CELERY_BROKER_URL IS SET IN ENVIRONMENT
         AND operation EXECUTES BEFORE return Response(...)
END FUNCTION
```

**Examples:**
- `REDIS_URL` set → all three writes dispatched via `.delay()` → `Response` returned immediately
- `REDIS_URL` absent (local dev) → writes execute synchronously inline → same result as today
- Celery worker crashes mid-task → error logged at WARNING, farmer never sees it

### Expected Behavior

#### Preservation Requirements

**Unchanged Behaviours:**
- JSON response body and status code from `/api/chatbot/query/` unchanged
- When Redis is absent, behaviour is byte-for-byte identical to current code
- `FarmerInteractionLog` rows still reach the DB (just slightly later when async)
- `ChatHistory` rows still persist (async delay of < 1 s typical)

**Scope:** only `_handle_query`'s post-answer write block changes; everything else is untouched.

### Hypothesized Root Cause

The writes are not deferred because:
1. No Celery task wrappers exist for `save_turn`, `update_session_context`, or
   `FarmerInteractionLog.create`
2. No conditional dispatch logic exists to check `CELERY_BROKER_URL`

### Correctness Properties

Property 1: Bug Condition — Writes Dispatched Asynchronously When Redis Present

_For any_ chatbot request where `CELERY_BROKER_URL` is set, the fixed `_handle_query`
SHALL dispatch all three write operations via `.delay()` and execute `return Response(...)`
before those writes complete.

**Validates: Requirements 3.1, 3.2**

Property 2: Preservation — Synchronous Fallback When Redis Absent

_For any_ chatbot request where `CELERY_BROKER_URL` is not set, the fixed `_handle_query`
SHALL execute the three write operations synchronously and produce the same JSON response
as the original code.

**Validates: Requirements 3.3, 3.6**

### Fix Implementation

#### Changes Required

**File:** `backend/advisory/tasks.py`

1. **Add `log_interaction` task** — accepts all `FarmerInteractionLog` field values as kwargs,
   calls `FarmerInteractionLog.objects.create(...)` inside, wrapped in try/except with
   `logger.warning` on failure.

2. **Add `persist_turn` task** — accepts `session_id`, `user_id`, and all `save_turn` kwargs;
   calls `session_memory.save_turn(...)` and `session_memory.update_session_context(...)`.
   Both are grouped in one task to avoid two round-trips to the broker for a single request.

**File:** `backend/advisory/api/viewsets/chatbot.py`

3. **Add dispatch helper `_dispatch_writes(use_celery, ...)` function** at module level:
   ```python
   import os as _os
   _USE_CELERY = bool(_os.getenv('CELERY_BROKER_URL'))

   def _dispatch_writes(session_id, ...):
       if _USE_CELERY:
           persist_turn.delay(session_id, ...)
           log_interaction.delay(...)
       else:
           # inline synchronous path (identical to current code)
           session_memory.save_turn(...)
           session_memory.update_session_context(...)
           FarmerInteractionLog.objects.create(...)
   ```

4. **Replace the three inline write blocks** in `_handle_query` with a single call to
   `_dispatch_writes(...)` immediately before `return Response(...)`.

---

## Improvement 4 — Sentry Error Tracking

### Bug Details / Problem Statement

#### Current State

`settings.py` already calls `sentry_sdk.init(dsn=SENTRY_DSN, ...)` when `SENTRY_DSN` is
set, but:
- The Flutter app has no Sentry SDK — mobile crashes are invisible
- The expensive Gemini call in `_handle_query` is not wrapped in a Sentry span —
  no per-request AI latency in the Performance dashboard
- There is no way to verify that the DSN is correctly configured in a deployed environment
  without manually forcing a crash

#### Bug Condition

```
FUNCTION isSentryGap(context)
  INPUT: context — an execution context in the app
  OUTPUT: boolean

  RETURN (context == FLUTTER_APP AND sentryFlutterSDK NOT initialised)
         OR (context == GEMINI_CALL AND sentry_span NOT active)
         OR (context == HEALTH_CHECK AND sentry_test_endpoint NOT exists)
END FUNCTION
```

**Examples:**
- Flutter widget throws `NullPointerException` → crash goes untracked (gap)
- Gemini takes 7 s → no Sentry span for AI latency (gap)
- DevOps deploys new `SENTRY_DSN` → no way to confirm it works (gap)

### Expected Behavior

#### Preservation Requirements

**Unchanged Behaviours:**
- `settings.py` `sentry_sdk.init()` call — `traces_sample_rate=0.1`, `DjangoIntegration()`
  both preserved
- Existing health endpoints (`/api/health/`, `/api/health/simple/`) unchanged
- App startup sequence in `main.dart` still calls `LocationService().init()` and
  `SystemChrome.setPreferredOrientations(...)` in the same order

**Scope:** only additive changes — new SDK init, new span, new endpoint.

### Hypothesized Root Cause

1. `sentry_flutter` was never added to `pubspec.yaml`
2. `_handle_query` has no instrumentation wrapper around the `answer()` call
3. No test endpoint was written to smoke-test the DSN post-deploy

### Correctness Properties

Property 1: Bug Condition — Sentry Flutter Initialised Before runApp

_For any_ app launch where `SENTRY_DSN` is compiled in via `--dart-define`, the fixed
`main.dart` SHALL call `SentryFlutter.init(...)` before `runApp(...)` and register
`FlutterError.onError` so widget errors are captured automatically.

**Validates: Requirements 4.1, 4.2**

Property 2: Preservation — Backend Sentry Config Unchanged

_For any_ backend request, the fixed `settings.py` SHALL continue to initialise Sentry
with `traces_sample_rate=0.1` and `DjangoIntegration()`, and the existing health endpoints
SHALL continue to return their current responses.

**Validates: Requirements 4.6, C.3**

### Fix Implementation

#### Changes Required

**File:** `mobile/krishimitra_app/pubspec.yaml`

1. **Add dep:** `sentry_flutter: ^7.19.0`

**File:** `mobile/krishimitra_app/lib/main.dart`

2. **Wrap `main()` body in `SentryFlutter.init(...)`**:
   ```dart
   const _sentryDsn = String.fromEnvironment('SENTRY_DSN', defaultValue: '');
   await SentryFlutter.init(
     (options) {
       if (_sentryDsn.isNotEmpty) options.dsn = _sentryDsn;
       options.tracesSampleRate = 0.1;
     },
     appRunner: () async {
       await SystemChrome.setPreferredOrientations([...]);
       await LocationService().init();
       runApp(const KrishiMitraApp());
     },
   );
   ```
   When `_sentryDsn` is empty, Sentry initialises with no DSN and is a no-op.

**File:** `backend/advisory/api/viewsets/chatbot.py`

3. **Wrap `chat_intelligence_service.answer()` call in a Sentry span**:
   ```python
   import sentry_sdk
   with sentry_sdk.start_span(op="ai.gemini", description="chatbot_query"):
       result = chat_intelligence_service.answer(...)
   ```
   The `with` block is a no-op when `SENTRY_DSN` is not configured.

**File:** `backend/advisory/api/monitoring_views.py` (or `misc.py` viewset)

4. **Add `sentry_test` endpoint** at `GET /api/health/sentry-test/`:
   ```python
   if settings.SENTRY_DSN:
       sentry_sdk.capture_message("Sentry DSN test", level="info")
       return Response({"status": "ok", "sentry": "event_sent"})
   return Response({"status": "ok", "sentry": "not_configured"})
   ```

**File:** `backend/core/urls.py`

5. **Register the new endpoint** — add URL pattern alongside existing health routes.

---
