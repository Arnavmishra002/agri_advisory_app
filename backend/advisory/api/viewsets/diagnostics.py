import logging
import uuid
from datetime import datetime, timezone

from django.db import IntegrityError, OperationalError, ProgrammingError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ..errors import safe_error_message
from ..location_utils import attach_location_metadata, resolve_request_location
from ..validation import (
    MAX_DIAGNOSTIC_CROP_LENGTH,
    read_upload_with_limit,
    query_too_long,
)
from ...models import DiagnosticSession
from ...services.crop_catalog import crop_catalog
from ...services.crop_disease_ml_service import crop_disease_ml_service
from ...services.disease_chat_bridge import disease_chat_bridge
from ...services.krishi_raksha_pest_service import KrishiRakshaPestService

logger = logging.getLogger(__name__)

class DiagnosticViewSet(viewsets.ViewSet):
    """
    API for KrishiRaksha 2.0: Advanced Pest Detection
    """
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pest_service = KrishiRakshaPestService()

    @staticmethod
    def _predict_label(result):
        status_code = result.get("status", "error")
        if result.get("disease_name"):
            return result["disease_name"]
        return {
            "model_unavailable": "AI model not trained",
            "tensorflow_missing": "AI model dependencies missing",
            "not_plant": "Not a crop leaf photo",
            "low_confidence": "Disease not confidently identified",
            "error": "Diagnosis unavailable",
        }.get(status_code, "Diagnosis unavailable")

    @staticmethod
    def _prediction_response_text(result):
        status_code = result.get("status", "error")
        if status_code == "success":
            disease = result.get("disease_name") or "the detected issue"
            crop = result.get("crop_name") or "the crop"
            conf = result.get("confidence_percent")
            conf_txt = f" ({conf}% confidence)" if conf is not None else ""
            return (
                f"AI detected {disease} in {crop}{conf_txt}. "
                "Confirm with your local KVK/agriculture officer before spraying, "
                "and follow the label dose."
            )
        if status_code == "model_unavailable":
            return (
                "Image received, but the trained crop disease model is not installed on this server. "
                "Use KrishiRaksha full diagnosis for crop/weather-based advisory, or ask admin to train: "
                "python -m advisory.ml.train --data-dir data/datasets"
            )
        if status_code == "advisory_fallback":
            return (
                result.get("message")
                or "Image received. The trained ML model is unavailable, so this is a crop/weather advisory fallback."
            )
        if status_code == "tensorflow_missing":
            return "Image received, but ML dependencies are missing. Install backend/requirements-ml.txt on the server."
        if status_code == "not_plant":
            return result.get("message") or "Please upload a clear photo of a crop leaf in daylight."
        if status_code == "low_confidence":
            return result.get("message") or "Please upload a clearer close-up of the affected leaf."
        return result.get("message") or "Diagnosis is temporarily unavailable. Please try again with a clear leaf image."

    @action(detail=False, methods=["get"], url_path="crop-search")
    def crop_search(self, request):
        """Crop autocomplete for disease detection (any Indian crop)."""
        query = request.query_params.get("q", "").strip()
        too_long = query_too_long(query, MAX_DIAGNOSTIC_CROP_LENGTH, field="q")
        if too_long:
            return too_long
        try:
            limit = min(int(request.query_params.get("limit", 10)), 20)
        except (ValueError, TypeError):
            limit = 10
        results = crop_catalog.search(query, limit=limit) if query else crop_catalog.popular(limit)
        return Response({
            "query": query,
            "results": results,
            "total": len(results),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })

    @action(detail=False, methods=['post'])
    def detect(self, request):
        """
        Run the full diagnostic pipeline.
        Payload: {
            "crop": "tomato",
            "location": "Delhi",
            "images": {"whole": "...", "close_up": "..."},
            "session_id": "optional-uuid"
        }
        """
        try:
            data = request.data
            crop_raw = data.get('crop')
            if crop_raw:
                too_long = query_too_long(str(crop_raw).strip(), MAX_DIAGNOSTIC_CROP_LENGTH, field="crop")
                if too_long:
                    return too_long
            norm = crop_catalog.normalize(crop_raw) if crop_raw else None
            crop = norm["id"] if norm else crop_raw
            ctx = resolve_request_location(request)
            images = data.get('images', {})
            session_id = data.get('session_id') # Can be generated if missing
            
            # Start Diagnostic Pipeline
            result = self.pest_service.diagnose_crop(
                session_id=session_id,
                crop_name=crop,
                location=ctx.query_label,
                images=images,
                latitude=ctx.latitude,
                longitude=ctx.longitude,
                state=ctx.state,
            )
            
            # Persist Session — audit trail for active learning and analytics
            # Bug 5 fix: infrastructure failures (DB down, connection error) are
            # re-raised so the caller gets a 500 instead of a silent data loss.
            # Only IntegrityError (duplicate session_id) is safe to swallow.
            try:
                if result['status'] in ('success', 'advisory_fallback'):
                    DiagnosticSession.objects.create(
                        session_id=session_id or str(uuid.uuid4()),
                        user_id=str(request.user.id) if request.user.is_authenticated else 'anonymous',
                        crop_detected=result['crop_detected'],
                        final_diagnosis=result['diagnosis'][0]['name'] if result['diagnosis'] else 'Unknown',
                        confidence_score=result['diagnosis'][0].get('confidence', 0.0) if result['diagnosis'] else 0.0,
                        severity_level=result['diagnosis'][0].get('severity_label', 'Low') if result['diagnosis'] else 'Low'
                    )
            except IntegrityError:
                # Duplicate session_id — safe to ignore (idempotent re-submit)
                logger.info("DiagnosticSession already exists for session_id=%s — skipping", session_id)
            except (OperationalError, ProgrammingError) as db_err:
                # Infrastructure failure — surface it so on-call is alerted
                logger.error("CRITICAL: DiagnosticSession.create failed for session_id=%s: %s", session_id, db_err)
                raise   # will be caught by outer except → 500 response
            
            treatment_advice = disease_chat_bridge.format_for_api(
                result, ctx, language=request.data.get("language", "hi")
            )
            top = (result.get("diagnosis") or [{}])[0]
            response_text = (
                treatment_advice.get("response")
                or treatment_advice.get("advice")
                or result.get("message")
                or "Diagnosis advisory generated."
            )
            return Response(attach_location_metadata({
                **result,
                "crop": result.get("crop_detected") or crop,
                "disease": top.get("name") or self._predict_label(result),
                "response": response_text,
                "recommendation": response_text,
                "treatment_advice": treatment_advice,
            }, ctx))
            
        except Exception as e:
            return Response(
                {'status': 'error', 'message': safe_error_message(e, context="diagnostics")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="predict")
    def predict(self, request):
        """
        ML-only crop/disease prediction (EfficientNet-B3).

        Payload: {"images": {"close_up": "<base64>"}} or multipart file field "image".
        Returns: crop_name, disease_name, confidence, top_predictions
        """
        try:
            upload = request.FILES.get("image")
            if upload:
                image_bytes, size_err = read_upload_with_limit(upload)
                if size_err:
                    return size_err
                result = crop_disease_ml_service.predict_image(
                    image_bytes=image_bytes
                )
            else:
                data = request.data
                images = data.get("images", {})
                if images:
                    result = crop_disease_ml_service.predict_from_upload_dict(images)
                elif data.get("image") or data.get("image_base64"):
                    b64 = data.get("image") or data.get("image_base64")
                    result = crop_disease_ml_service.predict_image(image_data=b64)
                else:
                    return Response(
                        {"status": "error", "message": "Provide image or images.close_up"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            requested_crop = (
                request.data.get("crop")
                or request.data.get("crop_name")
                or request.data.get("commodity")
            )
            payload = {
                "status": result.get("status", "error"),
                "crop_name": result.get("crop_name"),
                "disease_name": result.get("disease_name"),
                "crop": result.get("crop_name") or requested_crop,
                "disease": self._predict_label(result),
                "confidence": result.get("confidence", 0.0),
                "confidence_percent": result.get("confidence_percent"),
                "top_predictions": result.get("top_predictions", []),
                "message": result.get("message"),
                "response": self._prediction_response_text(result),
                "recommendation": self._prediction_response_text(result),
                "model": result.get("model"),
                "threshold": result.get("threshold"),
            }
            return Response(payload)
        except Exception as e:
            return Response(
                {"status": "error", "message": safe_error_message(e, context="diagnostics_predict")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'])
    def feedback(self, request):
        """
        Active Learning Loop: User provides correct diagnosis.
        Payload: {"session_id": "...", "is_correct": false, "correct_diagnosis": "Late Blight"}
        """
        try:
            data = request.data
            session_id = data.get('session_id')
            is_correct = data.get('is_correct')
            correct_diagnosis = data.get('correct_diagnosis', '')

            if not session_id:
                return Response(
                    {'status': 'error', 'message': 'session_id is required'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Persist feedback to ExpertVerification for Active Learning
            try:
                diagnostic = DiagnosticSession.objects.filter(session_id=session_id).first()
                if diagnostic:
                    from ...models import ExpertVerification
                    from django.utils import timezone
                    ExpertVerification.objects.update_or_create(
                        diagnostic_session=diagnostic,
                        defaults={
                            'is_verified': True,
                            'expert_diagnosis': correct_diagnosis if not is_correct else diagnostic.final_diagnosis,
                            'expert_notes': f"User feedback: is_correct={is_correct}",
                            'verified_at': timezone.now(),
                        }
                    )
                    logger.info(
                        "Feedback recorded for session %s — is_correct=%s correction='%s'",
                        session_id, is_correct, correct_diagnosis,
                    )
                else:
                    logger.warning("Feedback: no DiagnosticSession found for session_id=%s", session_id)
            except Exception as db_err:
                logger.warning("Failed to persist feedback: %s", db_err)

            return Response({
                'status': 'success',
                'message': 'Feedback recorded for Active Learning',
                'session_id': session_id,
                'is_correct': is_correct,
            })
        except Exception as e:
            logger.exception("Feedback processing error: %s", e)
            return Response({'status': 'error', 'message': 'Unable to process feedback'}, status=status.HTTP_400_BAD_REQUEST)
