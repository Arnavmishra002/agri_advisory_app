# Requirements: KrishiMitra Production Improvements

> Canonical beta policy: `.kiro/specs/farmer-ready-beta/requirements.md`
> defines the production launch gate and farmer-safe degradation policy. This
> document remains authoritative for non-conflicting implementation details.

## Introduction

Six production improvements to the KrishiMitra agricultural AI app. The app consists of a Django 5.2 + DRF backend with a Gemini AI chatbot, a Flutter mobile client, and 22-language support. All improvements must preserve existing behaviour for paths that are not being changed.

---

## 1. SSE Response Streaming (chatbot)

### 1.1 Overview

The current `POST /api/chatbot/query/` endpoint blocks until Gemini finishes generating the full response, then returns it in a single JSON body. This creates a perceived latency of several seconds with no visible progress in the mobile chat bubble. The improvement adds a parallel streaming endpoint while keeping the existing one unchanged.

### Acceptance Criteria

**1.1** WHEN a client sends `POST /api/chatbot/stream/` with the same request body accepted by `/api/chatbot/query/`, THEN the server SHALL respond with `Content-Type: text/event-stream` and begin emitting Server-Sent Events before the Gemini response is complete.

**1.2** WHEN the backend streams a token chunk, THEN each SSE frame SHALL follow the format `data: {"token": "<chunk>"}\n\n` so the client can append it incrementally to the message bubble.

**1.3** WHEN the Gemini response is complete, THEN the final SSE frame SHALL be `data: {"done": true, "intent": "...", "data_source": "...", "language": "..."}\n\n` followed by the SSE termination sequence, providing the same metadata that `/api/chatbot/query/` returns in its JSON envelope.

**1.4** WHEN `POST /api/chatbot/query/` is called, THEN it SHALL continue to return a complete JSON response identical to its current behaviour — no change to the existing endpoint.

**1.5** WHEN the mobile client connects to `/api/chatbot/stream/`, THEN the Flutter `ApiService` SHALL open an `http.Request` with chunked-transfer reading and append each received token to the active `ChatMessage` via `setState`, producing a real-time token-by-token rendering effect in the chat bubble.

**1.6** WHEN the streaming connection is interrupted before the `done` frame arrives, THEN the mobile client SHALL surface the partially received text in the bubble and show the existing network-error localised message.

**1.7** WHEN the streaming endpoint is called, THEN it SHALL apply the same rate-limiting middleware, session memory (`session_memory.save_turn`), and `FarmerInteractionLog` write as the non-streaming endpoint — these writes happen after the stream completes.

---

## 2. Voice Input and TTS (mobile only)

### 2.1 Overview

Farmers using the app while working in the field cannot type queries. The improvement adds a microphone button to the chat input bar for speech-to-text input and auto-reads AI responses aloud using text-to-speech when a voice query was used.

### Acceptance Criteria

**2.1** WHEN the mic button in the chat input bar is tapped while the app is not already listening, THEN the app SHALL begin STT recognition using the `speech_to_text` package with the language set to `widget.lang` (e.g. `hi-IN`, `te-IN`).

**2.2** WHEN the user stops speaking (silence timeout) or taps the mic button a second time while listening, THEN the recognised transcript SHALL be placed in the `TextField` and submitted as a chat query automatically.

**2.3** WHEN the mic button is in the listening state, THEN it SHALL display a pulsing red recording indicator to give the user unambiguous visual feedback.

**2.4** WHEN speech recognition fails or the device microphone is unavailable, THEN the app SHALL show a localised snack bar error (Hindi: "माइक उपलब्ध नहीं", English: "Microphone unavailable") and fall back to text input without crashing.

**2.5** WHEN an AI response arrives and the preceding query was submitted via voice, THEN the app SHALL read the response aloud using `flutter_tts` with the voice locale matching `widget.lang`.

**2.6** WHEN a text-only query is submitted (user typed directly), THEN TTS SHALL NOT auto-play — TTS is opt-in via voice flow only.

**2.7** WHEN the screen is disposed or the user navigates away, THEN the TTS player and STT session SHALL both be stopped and released to avoid audio leaking into other screens.

**2.8** WHEN microphone permission is not yet granted, THEN the app SHALL request it on first mic-button tap using the platform permission dialog; if denied, the app SHALL show the localised error from 2.4.

---

## 3. Celery Async Post-Response Writes

### 3.1 Overview

Currently `_handle_query` in `chatbot.py` blocks the HTTP response thread to perform three synchronous DB operations after the AI result is ready: `FarmerInteractionLog.objects.create(...)`, `session_memory.save_turn(...)`, and `session_memory.update_session_context(...)`. Moving these off the request thread returns the response to the farmer faster and frees Gunicorn workers sooner.

### Acceptance Criteria

**3.1** WHEN `_handle_query` builds the response and `session_id` is set, THEN `session_memory.save_turn(...)` and `session_memory.update_session_context(...)` SHALL be dispatched as Celery tasks via `.delay()` before `return Response(...)` is executed, so the HTTP response is sent first.

**3.2** WHEN `_handle_query` builds the response, THEN `FarmerInteractionLog.objects.create(...)` SHALL be dispatched as a Celery task via `.delay()` before `return Response(...)` is executed.

**3.3** WHEN `REDIS_URL` is not set in the environment (development or CI without Redis), THEN the tasks SHALL execute synchronously inline, preserving the existing behaviour so no `celery worker` is required in local dev.

**3.4** WHEN the Celery task for `save_turn` or `update_session_context` fails (e.g. DB down after the response was already sent), THEN the failure SHALL be logged at `WARNING` level and SHALL NOT surface an error to the farmer — the HTTP response was already delivered.

**3.5** WHEN the new tasks are added, THEN they SHALL be placed in `backend/advisory/tasks.py` using the `@shared_task` decorator, alongside the existing `refresh_location_cache` placeholder.

**3.6** WHEN the existing `/api/chatbot/query/` response is observed by the mobile client, THEN its shape (fields, status codes, latency from the client's perspective) SHALL be unchanged or improved — async writes must not add observable delay.

---

## 4. Sentry Error Tracking

### 4.1 Overview

`sentry-sdk[django]>=2.0.0` is present in `requirements.txt` and `settings.py` initialises Sentry when `SENTRY_DSN` is set, but three gaps remain: the Flutter mobile app has no Sentry integration, the Gemini API call inside the chatbot is not wrapped in a performance transaction span, and there is no test endpoint to verify the DSN is active in a deployed environment.

### Acceptance Criteria

**4.1** WHEN `sentry_flutter: ^7.x` is added to `pubspec.yaml`, THEN `main.dart` SHALL call `SentryFlutter.init(...)` before `runApp(...)`, reading the DSN from a compile-time constant (`SENTRY_DSN`) or falling back silently if not set.

**4.2** WHEN the Flutter app catches an unhandled exception or a widget error, THEN Sentry SHALL capture it automatically via the Flutter error handler integration.

**4.3** WHEN the backend's `chat_intelligence_service.answer(...)` call is executed inside `_handle_query`, THEN it SHALL be wrapped in a Sentry performance transaction span with `op="ai.gemini"` and `description="chatbot_query"` so latency is tracked per request in the Sentry Performance dashboard.

**4.4** WHEN `GET /api/health/sentry-test/` is called and `SENTRY_DSN` is configured, THEN the endpoint SHALL deliberately capture a test event to Sentry and return `{"status": "ok", "sentry": "event_sent"}`.

**4.5** WHEN `GET /api/health/sentry-test/` is called and `SENTRY_DSN` is not configured, THEN the endpoint SHALL return `{"status": "ok", "sentry": "not_configured"}` without raising an error.

**4.6** WHEN the existing Sentry `init()` call in `settings.py` is modified, THEN the `traces_sample_rate=0.1` and `DjangoIntegration()` SHALL be preserved — no regression to the existing partial configuration.

---

## 5. DB Composite Index on IoTSensorReading

### 5.1 Overview

`IoTSensorReading` in `models.py` currently has two separate indexes: `("field_id", "created_at")` and `("latitude", "longitude")`. The chatbot's bounding-box query in `_handle_query` filters by `latitude__gte`, `latitude__lte`, `longitude__gte`, `longitude__lte` and then orders by `-created_at`. Because the two predicates span separate indexes, PostgreSQL performs a bitmap index merge followed by a filesort on `created_at`, causing degraded query time at scale.

### Acceptance Criteria

**5.1** WHEN a new Django migration is applied, THEN `IoTSensorReading` SHALL have a composite index on `(latitude, longitude, created_at)` stored in `Meta.indexes`.

**5.2** WHEN the migration is applied, THEN the two existing separate indexes — `("field_id", "created_at")` and `("latitude", "longitude")` — SHALL remain in place; the new index is additive, not a replacement.

**5.3** WHEN no model field definitions are changed, THEN the migration SHALL contain only `AddIndex` operations and no `AlterField` or `CreateModel` operations.

**5.4** WHEN the migration is run on a database that already has the existing schema, THEN it SHALL complete without error, and `django.db.migrations.executor.MigrationExecutor` SHALL mark it as applied.

---

## 6. Offline Cache in Flutter (weather, mandi, crop recommendations)

### 6.1 Overview

When the device is offline or the backend is unreachable, `WeatherScreen`, `MandiScreen`, and `CropRecScreen` currently show a generic error view with no data. The improvement caches the last successful API response using `hive` local storage and shows it with an "Offline — showing data from X hours ago" banner when the network is unavailable.

### Acceptance Criteria

**6.1** WHEN `hive` and `hive_flutter` packages are added to `pubspec.yaml`, THEN `Hive.initFlutter()` SHALL be called in `main.dart` before `runApp(...)` so the box is ready before any screen opens.

**6.2** WHEN `WeatherScreen._load()` receives a successful API response, THEN the response SHALL be written to the Hive cache with a key of `"weather_<locationName>_<lang>"` and a timestamp, expiring after 3 hours.

**6.3** WHEN `MandiScreen._loadMandis()` and `_loadPrices()` receive a successful API response, THEN each response SHALL be written to the Hive cache with a key of `"mandi_<locationName>"` and a timestamp, expiring after 6 hours.

**6.4** WHEN `CropRecScreen._load()` receives a successful API response, THEN the response SHALL be written to the Hive cache with a key of `"croprec_<locationName>_<lang>"` and a timestamp, expiring after 24 hours.

**6.5** WHEN a screen's `_load()` throws a network error AND a non-expired cache entry exists for the current `(location, language)` key, THEN the screen SHALL render the cached data and display a banner reading `"📶 Offline — showing data from X hours ago"` (localised: Hindi `"📶 ऑफ़लाइन — X घंटे पहले का डेटा"`) where X is the age of the cached data rounded to the nearest hour.

**6.6** WHEN a screen's `_load()` throws a network error AND no cache entry exists or the cache entry is expired, THEN the existing `ErrorView` widget SHALL be shown — no change to the current error path.

**6.7** WHEN `connectivity_plus` detects that the device is offline before a network call is attempted, THEN `_load()` SHALL skip the HTTP request, read the cache directly, and display the offline banner — avoiding an unnecessary connection timeout.

**6.8** WHEN the user changes location in the location picker, THEN the cache lookup key SHALL change to reflect the new location so stale data from the previous location is never shown for the new one.

**6.9** WHEN the existing `connectivity_plus: ^6.0.3` dependency in `pubspec.yaml` is referenced for offline detection, THEN it SHALL NOT be removed or downgraded — it is already present and must continue to work.

---

## Cross-Cutting Constraints

**C.1** WHEN any of the 6 improvements are applied, THEN `backend/advisory/api/viewsets/chatbot.py`'s existing `_handle_query` method signature and its current JSON response shape SHALL remain unchanged for the `/api/chatbot/query/` path.

**C.2** WHEN any of the 6 improvements are applied, THEN `mobile/krishimitra_app/pubspec.yaml`'s existing dependencies SHALL NOT be removed or have their version constraints lowered.

**C.3** WHEN any of the 6 improvements are applied, THEN all existing passing tests SHALL continue to pass.
