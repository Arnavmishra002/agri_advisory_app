"""
KrishiMitra — WhatsApp, SMS/IVR, TTS, User, Forum viewsets
============================================================

WhatsApp integration uses Meta Cloud API (free up to 1000 conversations/month).
Flow: Farmer sends WhatsApp → Meta webhook → /api/sms-ivr/whatsapp/ → chatbot → reply

TTS uses Edge TTS (no API key needed) to convert advisory text to speech
so IVR callers can hear the advice.

Setup (5 min):
  1. Create a Meta Developer app at developers.facebook.com
  2. Add WhatsApp Business product
  3. Set webhook URL to: https://your-domain.com/api/sms-ivr/whatsapp/
  4. Set verify token in .env: WHATSAPP_VERIFY_TOKEN=any-random-string
  5. Add .env: WHATSAPP_TOKEN=your-access-token, WHATSAPP_PHONE_ID=your-phone-id

For Twilio SMS (alternative):
  TWILIO_ACCOUNT_SID=...
  TWILIO_AUTH_TOKEN=...
  TWILIO_FROM_NUMBER=+1...
"""

import hashlib
import hmac
import html
import io
import json
import logging
import os
import base64
import urllib.request

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..errors import safe_error_message
from advisory.services.api_keys import env_key
from ..serializers import (
    AdvisoryAudioInputSerializer,
    EmptyInputSerializer,
    TextToSpeechInputSerializer,
    TwilioWebhookInputSerializer,
    WhatsAppVerificationQuerySerializer,
    WhatsAppWebhookInputSerializer,
)
logger = logging.getLogger(__name__)

# ── Environment config ────────────────────────────────────────────────────────
WHATSAPP_TOKEN        = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID     = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_APP_SECRET   = os.getenv("WHATSAPP_APP_SECRET", "")
TWILIO_SID            = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN          = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM           = os.getenv("TWILIO_FROM_NUMBER", "")
GROQ_API_KEY          = env_key("GROQ_API_KEY")   # for Whisper STT (free tier)


def _owned_advisory_audio_session(request) -> str:
    """Return a server-owned TTS history key; never trust a client session id."""
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"user:{user.pk}"
    return ""


def _twilio_signature_valid(request) -> bool:
    """Validate Twilio webhooks; only local DEBUG may run without a token."""
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if not auth_token:
        return bool(settings.DEBUG)
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False
    params = request.POST or getattr(request, "data", {}) or {}
    signed = request.build_absolute_uri()
    for key in sorted(params):
        values = params.getlist(key) if hasattr(params, "getlist") else [params[key]]
        signed += key + "".join(str(value) for value in values)
    expected = base64.b64encode(
        hmac.new(auth_token.encode(), signed.encode(), hashlib.sha1).digest()
    ).decode()
    return hmac.compare_digest(signature, expected)


def _reject_invalid_twilio(request):
    if _twilio_signature_valid(request):
        return None
    logger.warning("Rejected unsigned or invalid Twilio webhook")
    return Response(
        {"error": "Webhook signature validation failed", "error_code": "INVALID_WEBHOOK_SIGNATURE"},
        status=status.HTTP_401_UNAUTHORIZED,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  WhatsApp / SMS IVR ViewSet
# ─────────────────────────────────────────────────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class SMSIVRViewSet(viewsets.ViewSet):
    """
    Handles WhatsApp Business webhook and Twilio SMS.
    URL prefix: /api/sms-ivr/
    """
    permission_classes = [AllowAny]

    def list(self, request):
        serializer = EmptyInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"error": "This endpoint does not accept query parameters", "error_code": "UNEXPECTED_INPUT"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            "service":  "KrishiMitra WhatsApp/SMS Gateway",
            "status":   "active" if WHATSAPP_TOKEN else "needs WHATSAPP_TOKEN in .env",
            "webhook":  "/api/sms-ivr/whatsapp/",
            "twilio":   "/api/sms-ivr/sms/",
            "docs":     "Set WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_VERIFY_TOKEN in .env",
        })

    # ── WhatsApp webhook — GET (Meta verification) ────────────────────────────
    @action(detail=False, methods=["get", "post"], url_path="whatsapp")
    def whatsapp(self, request):
        if request.method == "GET":
            return self._verify_webhook(request)
        return self._handle_whatsapp_message(request)

    def _verify_webhook(self, request):
        """Meta sends a GET with hub.verify_token to confirm the webhook."""
        serializer = WhatsAppVerificationQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid WhatsApp verification request", "error_code": "INVALID_WEBHOOK_VERIFICATION"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        mode = serializer.validated_data["mode"]
        token = serializer.validated_data["verify_token"]
        challenge = serializer.validated_data["challenge"]
        if not WHATSAPP_VERIFY_TOKEN and not settings.DEBUG:
            return Response({"error": "WhatsApp verification is not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            logger.info("WhatsApp webhook verified successfully")
            from django.http import HttpResponse
            return HttpResponse(challenge, content_type="text/plain")
        return Response({"error": "Verification failed"}, status=status.HTTP_403_FORBIDDEN)

    def _handle_whatsapp_message(self, request):
        """Process incoming WhatsApp messages and reply via the AI chatbot."""
        try:
            if not WHATSAPP_APP_SECRET and not settings.DEBUG:
                logger.error("WhatsApp webhook rejected: WHATSAPP_APP_SECRET is not configured")
                return Response({"error": "WhatsApp webhook is not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            if len(request.body) > 1_048_576:
                return Response({"error": "Webhook payload is too large"}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
            # Optional signature verification
            if WHATSAPP_APP_SECRET:
                # FIX 2a: guard against None header (some load balancers omit it)
                sig = request.headers.get("X-Hub-Signature-256") or ""
                expected = "sha256=" + hmac.new(
                    WHATSAPP_APP_SECRET.encode(),
                    request.body,
                    hashlib.sha256,
                ).hexdigest()
                # FIX 2b: zero-byte body = Meta health-check ping → accept silently
                if request.body and not hmac.compare_digest(sig, expected):
                    logger.warning("WhatsApp webhook signature mismatch — rejecting")
                    return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

            serializer = WhatsAppWebhookInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Invalid webhook payload", "error_code": "INVALID_WEBHOOK_PAYLOAD", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            body = serializer.validated_data
            entry = (body.get("entry") or [{}])[0]
            changes = (entry.get("changes") or [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return Response({"status": "no_message"})

            msg      = messages[0]
            wa_id    = msg.get("from")          # farmer's WhatsApp number
            msg_type = msg.get("type", "text")

            # ── Resolve message text ──────────────────────────────────────────
            if msg_type == "text":
                text = msg.get("text", {}).get("body", "").strip()

            elif msg_type == "audio":
                # Voice message — attempt Groq Whisper STT (free: 7200 sec/day)
                audio_id = msg.get("audio", {}).get("id", "")
                text = self._transcribe_whatsapp_audio(audio_id)
                if text:
                    logger.info("Voice transcribed: %s", text[:60])
                else:
                    # Friendly prompt to type instead
                    text = "मेरी बात सुनी नहीं गई। कृपया अपना सवाल टाइप करें।"

            elif msg_type == "image":
                # Image with caption — treat caption as question
                text = (msg.get("image", {}).get("caption") or "").strip()
                if not text:
                    text = "मेरी फसल की फोटो देखिए — क्या बीमारी है?"

            else:
                text = msg.get("caption") or msg.get("body") or ""

            if not text or not wa_id:
                return Response({"status": "ignored"})

            logger.info("WhatsApp %s from %s: %s", msg_type, wa_id[:6] + "****", text[:60])

            # ── Auto-create FarmerProfile on first message ────────────────────
            # Ensures every WhatsApp farmer is tracked from message 1.
            # Uses get_or_create so subsequent messages are a no-op.
            language = self._get_or_create_profile_language(wa_id)

            # ── Get AI response via chatbot ───────────────────────────────────
            reply = self._get_ai_reply(query=text, phone=wa_id, language=language)

            # ── Send reply back via WhatsApp Cloud API ────────────────────────
            if WHATSAPP_TOKEN and WHATSAPP_PHONE_ID:
                self._send_whatsapp_reply(wa_id, reply)
            else:
                logger.warning("WHATSAPP_TOKEN not set — reply not sent (set in .env)")

            return Response({"status": "replied", "to": wa_id})

        except Exception as exc:
            logger.error("WhatsApp handler error: %s", exc)
            return Response({"status": "error"}, status=status.HTTP_200_OK)   # always 200 to Meta

    def _get_or_create_profile_language(self, phone: str) -> str:
        """
        Get preferred language from FarmerProfile.
        Creates the profile automatically on first contact so every
        WhatsApp farmer is tracked from their first message.
        """
        try:
            from ...models import FarmerProfile
            profile, created = FarmerProfile.objects.get_or_create(
                phone_number=phone,
                defaults={
                    "whatsapp_opt_in": True,
                    "preferred_language": "hi",
                },
            )
            if created:
                logger.info("Auto-created FarmerProfile for WhatsApp user %s****", phone[:4])
            return profile.preferred_language or "hi"
        except Exception as exc:
            logger.warning("Could not get/create FarmerProfile: %s", exc)
            return "hi"

    def _transcribe_whatsapp_audio(self, audio_id: str) -> str:
        """
        Download a WhatsApp audio message and transcribe it via Groq Whisper.
        Returns transcribed text or empty string on failure.

        Groq Whisper (whisper-large-v3) is free:
          - 7,200 seconds/day audio
          - No credit card needed
          - Supports Hindi, Bhojpuri, Marathi, Tamil, Telugu, Gujarati etc.

        To enable: set GROQ_API_KEY in .env
        To get key: https://console.groq.com → Sign up → API Keys
        """
        if not GROQ_API_KEY or not WHATSAPP_TOKEN:
            return ""
        if not audio_id:
            return ""

        try:
            import tempfile

            # Step 1: Get the audio download URL from Meta Graph API
            meta_url = f"https://graph.facebook.com/v18.0/{audio_id}"
            req = urllib.request.Request(
                meta_url,
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                meta = json.loads(resp.read())
            audio_url = meta.get("url", "")
            if not audio_url:
                return ""

            # Step 2: Download the audio bytes
            dl_req = urllib.request.Request(
                audio_url,
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            )
            with urllib.request.urlopen(dl_req, timeout=20) as resp:
                audio_bytes = resp.read()

            # Step 3: Transcribe via Groq Whisper API
            import http.client
            import mimetypes
            # Build multipart/form-data manually (no external libs needed)
            boundary = "---KrishiMitraAudioBoundary"
            body_parts = [
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="model"\r\n\r\n'
                f"whisper-large-v3\r\n",
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="language"\r\n\r\n'
                f"hi\r\n",    # hint: Hindi — Whisper auto-corrects if different
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="voice.ogg"\r\n'
                f"Content-Type: audio/ogg\r\n\r\n",
            ]
            body = ("".join(body_parts)).encode() + audio_bytes + f"\r\n--{boundary}--\r\n".encode()

            conn = http.client.HTTPSConnection("api.groq.com", timeout=30)
            conn.request(
                "POST",
                "/openai/v1/audio/transcriptions",
                body=body,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
            )
            groq_resp = conn.getresponse()
            groq_data = json.loads(groq_resp.read())
            conn.close()

            text = groq_data.get("text", "").strip()
            logger.info("Groq Whisper transcribed %d chars", len(text))
            return text

        except Exception as exc:
            logger.warning("Audio transcription failed (non-fatal): %s", exc)
            return ""

    def _get_ai_reply(self, query: str, phone: str, language: str) -> str:
        """Route through the main chatbot pipeline."""
        try:
            from ...services.chat_intelligence_service import chat_intelligence_service
            from ...services.session_memory_service import session_memory

            # Use phone as session_id so memory persists per farmer
            session_id = f"wa_{phone}"
            history    = session_memory.load_history(session_id, limit=8)

            # Resolve rough location from profile
            ctx = self._build_location_context(phone)

            result = chat_intelligence_service.answer(
                query=query,
                ctx=ctx,
                language=language,
                history=history,
            )
            response_text = result.get("response", "")

            # Persist turn + update profile language if the AI detected something different
            session_memory.save_turn(
                session_id=session_id,
                user_id=phone,
                user_query=query,
                ai_response=response_text,
                intent=result.get("intent", "general"),
                language=result.get("language", language),
                data_source=result.get("data_source", ""),
            )

            # Update profile: last_seen + detected language
            try:
                from ...models import FarmerProfile
                from django.utils import timezone
                detected_lang = result.get("language", language)
                FarmerProfile.objects.filter(phone_number=phone).update(
                    last_seen_at=timezone.now(),
                    preferred_language=detected_lang,
                )
            except Exception:
                pass

            return response_text or "माफ़ करें, कृपया फिर से पूछें। Kisan Helpline: 1800-180-1551"

        except Exception as exc:
            logger.error("AI reply error for WhatsApp: %s", exc)
            return (
                "माफ़ करें, AI सेवा अभी व्यस्त है। "
                "Kisan Helpline: 1800-180-1551 (Free, 24x7)"
            )

    def _build_location_context(self, phone: str):
        """Build a LocationContext from the farmer profile without substitution."""
        try:
            from ...models import FarmerProfile
            from ...services.location_context import LocationContext
            p = FarmerProfile.objects.filter(phone_number=phone).first()
            if p and p.latitude and p.longitude:
                return LocationContext(
                    latitude=p.latitude,
                    longitude=p.longitude,
                    display_name=p.location_name or p.district or p.state or "India",
                    state=p.state or "",
                    source="farmer_profile",
                    confidence=1.0,
                )
        except Exception:
            pass
        from ...services.location_context import LocationContext
        return LocationContext(
            latitude=None,
            longitude=None,
            display_name="",
            source="unconfirmed",
            confidence=0.0,
        )

    def _send_whatsapp_reply(self, to: str, text: str) -> None:
        """Send a WhatsApp text message via Meta Cloud API."""
        # WhatsApp has a 4096-char limit — split if needed
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks[:3]:   # max 3 messages per reply
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "to":   to,
                "type": "text",
                "text": {"body": chunk},
            }).encode("utf-8")
            req = urllib.request.Request(
                f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages",
                data=payload,
                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    logger.debug("WhatsApp reply sent: %s", resp.status)
            except Exception as exc:
                logger.error("WhatsApp send failed: %s", exc)

    # ── Twilio SMS webhook ────────────────────────────────────────────────────
    @action(detail=False, methods=["post"], url_path="sms")
    def sms(self, request):
        """
        Twilio SMS webhook — POST /api/sms-ivr/sms/
        Twilio sends: From, Body, etc. as form data.
        """
        rejected = _reject_invalid_twilio(request)
        if rejected:
            return rejected
        serializer = TwilioWebhookInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response("<Response/>", content_type="text/xml", status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        from_number = data.get("From", "")
        raw_body    = data.get("Body", "")
        if not isinstance(from_number, str) or len(from_number) > 32 or not isinstance(raw_body, str):
            return Response("<Response/>", content_type="text/xml", status=status.HTTP_400_BAD_REQUEST)
        body = raw_body.strip()[:4000]
        if not from_number or not body:
            return Response("<Response/>", content_type="text/xml")

        language = self._get_or_create_profile_language(from_number)
        reply    = self._get_ai_reply(body, from_number, language)

        # FIX 1: escape reply before XML injection — bare & breaks TwiML parser
        safe_reply = html.escape(reply[:1600])
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"<Message>{safe_reply}</Message>"
            "</Response>"
        )
        from django.http import HttpResponse
        return HttpResponse(twiml, content_type="text/xml")

    # ── Twilio Voice webhook (IVR Entry) ──────────────────────────────────────
    @action(detail=False, methods=["post"], url_path="voice")
    def voice(self, request):
        """
        Twilio Voice webhook — POST /api/sms-ivr/voice/
        Incoming phone call: play welcome greeting and gather speech input.
        """
        rejected = _reject_invalid_twilio(request)
        if rejected:
            return rejected
        from django.http import HttpResponse
        
        serializer = TwilioWebhookInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response("<Response/>", content_type="text/xml", status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        from_number = data.get("From", "")
        if not isinstance(from_number, str) or len(from_number) > 32:
            return Response("<Response/>", content_type="text/xml", status=status.HTTP_400_BAD_REQUEST)
        lang_code = self._get_or_create_profile_language(from_number)
        
        # Map simple language codes to Twilio voice locales
        twilio_locale_map = {
            "hi": "hi-IN",
            "en": "en-IN",
            "ta": "ta-IN",
            "te": "te-IN",
            "mr": "mr-IN",
            "gu": "gu-IN",
            "kn": "kn-IN",
            "ml": "ml-IN",
            "bn": "bn-IN",
            "pa": "pa-IN",
        }
        locale = twilio_locale_map.get(lang_code, "hi-IN")
        
        # Welcome message in user's language
        greetings = {
            "hi-IN": "नमस्ते किसान भाई! कृषिमित्रा एआई सहायता केंद्र में आपका स्वागत है। कृपया अपनी समस्या या प्रश्न बोलें।",
            "en-IN": "Welcome to KrishiMitra AI advisory. Please speak your agricultural question after the beep.",
            "ta-IN": "கிருஷிமித்ரா ஏஐ உதவி மையத்திற்கு வரவேற்கிறோம். தயவுசெய்து உங்கள் கேள்வியைக் கூறுங்கள்.",
            "te-IN": "కృషిమిత్ర ఏఐ సహాయ కేంద్రానికి స్వాగతం. దయచేసి మీ ప్రశ్నను మాట్లాడండి.",
            "mr-IN": "कृषिमित्र एआय मदत केंद्रात आपले स्वागत आहे. कृपया आपला प्रश्न बोला.",
            "gu-IN": "કૃષિમિત્ર એઆઈ સહાયતા કેન્દ્રમાં આપનું સ્વાગત છે. કૃપા કરીને તમારો પ્રશ્ન બોલો.",
            "kn-IN": "ಕೃಷಿಮಿತ್ರ ಏಐ ಸಹಾಯ ಕೇಂದ್ರಕ್ಕೆ ಸ್ವಾಗತ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ತಿಳಿಸಿ.",
            "ml-IN": "കൃഷിമിತ್ರ എഐ സഹായ കേന്ദ്രത്തിലേക്ക് സ്വാഗതം. ദയവായി നിങ്ങളുടെ ചോദ്യം പറയുക.",
            "bn-IN": "কৃষি মিত্র এআই সহায়তা কেন্দ্রে আপনাকে স্বাগত। অনুগ্রহ করে আপনার প্রশ্নটি বলুন।",
            "pa-IN": "ਕ੍ਰਿਸ਼ੀਮਿੱਤਰਾ ਏਆਈ ਸਹਾਇਤਾ ਕੇਂਦਰ ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ। ਕਿਰਪา ਕਰਕੇ ਆਪਣਾ ਸਵਾਲ ਬੋਲੋ।"
        }
        greet_text = greetings.get(locale, greetings["hi-IN"])

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{locale}">{greet_text}</Say>
    <Gather input="speech" language="{locale}" action="/api/sms-ivr/voice-callback/" timeout="5" speechTimeout="auto">
        <!-- Re-prompt if they don't say anything -->
    </Gather>
    <Say language="{locale}">कोई आवाज़ नहीं सुनी गई। कृपया दोबारा कॉल करें। धन्यवाद।</Say>
</Response>"""
        return HttpResponse(twiml, content_type="text/xml")

    # ── Twilio Voice webhook (IVR Callback) ───────────────────────────────────
    @action(detail=False, methods=["post"], url_path="voice-callback")
    def voice_callback(self, request):
        """
        Twilio Voice speech gathering callback — POST /api/sms-ivr/voice-callback/
        """
        rejected = _reject_invalid_twilio(request)
        if rejected:
            return rejected
        from django.http import HttpResponse
        
        serializer = TwilioWebhookInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response("<Response/>", content_type="text/xml", status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        from_number   = data.get("From", "")
        raw_speech    = data.get("SpeechResult", "")
        if not isinstance(from_number, str) or not isinstance(raw_speech, str) or len(from_number) > 32:
            return Response("<Response/>", content_type="text/xml", status=status.HTTP_400_BAD_REQUEST)
        speech_result = raw_speech.strip()[:4000]
        
        lang_code = self._get_or_create_profile_language(from_number)
        
        twilio_locale_map = {
            "hi": "hi-IN",
            "en": "en-IN",
            "ta": "ta-IN",
            "te": "te-IN",
            "mr": "mr-IN",
            "gu": "gu-IN",
            "kn": "kn-IN",
            "ml": "ml-IN",
            "bn": "bn-IN",
            "pa": "pa-IN",
        }
        locale = twilio_locale_map.get(lang_code, "hi-IN")
        
        if not speech_result:
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response>"
                f'<Say language="{locale}">माफ़ करें, हम आपकी आवाज़ नहीं सुन पाए। कृपया दोबारा कोशिश करें।</Say>'
                "</Response>"
            )
            return HttpResponse(twiml, content_type="text/xml")

        reply = self._get_ai_reply(speech_result, from_number, lang_code)

        # FIX 1: escape AI reply & static strings before injecting into XML
        safe_reply     = html.escape(reply[:800])
        safe_thank_you = html.escape("कृषिमित्रा एआई सहायता केंद्र में कॉल करने के लिए धन्यवाद।")
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Say language="{locale}">{safe_reply}</Say>'
            f'<Say language="{locale}">{safe_thank_you}</Say>'
            "</Response>"
        )
        return HttpResponse(twiml, content_type="text/xml")


# ─────────────────────────────────────────────────────────────────────────────
#  Text-to-Speech ViewSet
# ─────────────────────────────────────────────────────────────────────────────
class TextToSpeechViewSet(viewsets.ViewSet):
    """
    Convert advisory text to speech using Edge TTS (no API key needed).

    POST /api/tts/generate/
    Body: {"text": "...", "language": "hi"}
    Returns: audio/mpeg binary

    GET /api/tts/generate/?text=...&language=hi
    Returns: audio/mpeg binary (for quick testing in browser)
    """
    permission_classes = [AllowAny]

    def list(self, request):
        serializer = EmptyInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"error": "This endpoint does not accept query parameters", "error_code": "UNEXPECTED_INPUT"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            "service":   "KrishiMitra Text-to-Speech",
            "engine":    "Edge TTS (online, no API key needed)",
            "languages": ["hi", "en", "mr", "ta", "te", "gu", "pa", "bn", "kn", "ml"],
            "endpoint":  "POST /api/tts/generate/ — {text, language}",
        })

    @action(detail=False, methods=["get", "post"], url_path="generate")
    def generate(self, request):
        """Generate MP3 from text. Safe to call without API keys."""
        if request.method == "GET":
            serializer = TextToSpeechInputSerializer(data=request.query_params)
        else:
            serializer = TextToSpeechInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "error_code": "INVALID_TTS_REQUEST"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        text = serializer.validated_data["text"]
        language = serializer.validated_data["language"]

        if not text:
            return Response({"error": "text is required"}, status=status.HTTP_400_BAD_REQUEST)

        return self._render_tts(text[:500], language)

    @action(detail=False, methods=["post"], url_path="advisory-audio")
    def advisory_audio(self, request):
        """
        Get AI advice AND return it as audio in one call.
        POST /api/tts/advisory-audio/
        Body: {"query": "सरसों में माहू", "language": "hi", "session_id": "sess_..."}
        Returns: audio/mpeg
        """
        serializer = AdvisoryAudioInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "error_code": "INVALID_ADVISORY_AUDIO_REQUEST"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        query = serializer.validated_data["query"]
        language = serializer.validated_data["language"]
        # The request field remains accepted for client compatibility, but it
        # is never used as a database lookup key. Anonymous audio requests do
        # not load conversation history; authenticated users use their own key.
        session_id = _owned_advisory_audio_session(request)

        if not query:
            return Response({"error": "query required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get AI text response
        try:
            from ...services.chat_intelligence_service import chat_intelligence_service
            from ...services.session_memory_service import session_memory
            from ...services.location_context import LocationContext

            history = session_memory.load_history(session_id, limit=6) if session_id else []
            ctx = LocationContext(
                latitude=None,
                longitude=None,
                display_name="",
                source="unconfirmed",
                confidence=0.0,
            )
            result      = chat_intelligence_service.answer(query, ctx, language=language, history=history)
            advice_text = result.get("response", "")
        except Exception as exc:
            logger.warning("advisory_audio AI call failed: %s", exc)
            advice_text = "Kisan Helpline: 1800-180-1551"

        # Convert to speech — call the shared helper directly (avoids fake-request anti-pattern)
        return self._render_tts(advice_text[:500], language)

    # ── Internal TTS helper ───────────────────────────────────────────────────
    def _render_tts(self, text: str, language: str):
        """Render `text` as audio/mpeg via Edge TTS."""
        try:
            import edge_tts
        except ImportError:
            return Response(
                {"error": "Text-to-speech engine is not installed"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            voice_map = {
                "hi": "hi-IN-SwaraNeural",
                "en": "en-IN-NeerjaNeural",
                "mr": "mr-IN-AarohiNeural",
                "ta": "ta-IN-PallaviNeural",
                "te": "te-IN-ShrutiNeural",
                "gu": "gu-IN-DhwaniNeural",
                "pa": "pa-IN-VaaniNeural",
                "bn": "bn-IN-TanishaaNeural",
                "kn": "kn-IN-SapnaNeural",
                "ml": "ml-IN-SobhanaNeural",
                "or": "or-IN-SubhasiniNeural",
                "as": "as-IN-YashicaNeural",
            }
            voice = voice_map.get(language, voice_map["hi"])
            communicate = edge_tts.Communicate(text=text, voice=voice)
            buf = io.BytesIO()
            for chunk in communicate.stream_sync():
                if chunk.get("type") == "audio":
                    buf.write(chunk.get("data", b""))
                    if buf.tell() > 5 * 1024 * 1024:
                        raise ValueError("Generated audio exceeded the 5 MB safety limit")
            if not buf.tell():
                raise ValueError("Text-to-speech provider returned no audio")
            buf.seek(0)
            from django.http import FileResponse
            return FileResponse(buf, content_type="audio/mpeg", as_attachment=False, filename="advisory.mp3")
        except Exception as exc:
            logger.error("TTS render failed: %s", exc)
            return Response(
                {"error": safe_error_message(exc, context="tts")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─────────────────────────────────────────────────────────────────────────────
#  Forum stub
# ─────────────────────────────────────────────────────────────────────────────
class ForumPostViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    def list(self, request):
        serializer = EmptyInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"error": "This endpoint does not accept query parameters", "error_code": "UNEXPECTED_INPUT"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Forum service — coming soon"})
