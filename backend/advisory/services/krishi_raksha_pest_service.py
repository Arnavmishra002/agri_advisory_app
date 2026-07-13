import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .clean_weather_api import CleanWeatherAPI
from .crop_catalog import crop_catalog
from ..ml.config import LOW_CONFIDENCE_MESSAGE, NOT_PLANT_MESSAGE
from .crop_disease_ml_service import crop_disease_ml_service
from .ultra_dynamic_government_api import _gov_api_singleton as _udg_api_singleton

try:
    from ..models import DiagnosticSession
except ImportError:
    pass

logger = logging.getLogger(__name__)


class KrishiRakshaPestService:
    """
    KrishiRaksha 2.0: Advanced Pest Detection System
    Supports any catalog crop with location-aware weather verification.
    """

    def __init__(self):
        self.weather_api = CleanWeatherAPI()
        # Use the shared singleton to avoid creating a redundant requests.Session
        self.gov_api = _udg_api_singleton

    def diagnose_crop(
        self,
        session_id: str,
        crop_name: str,
        location: str,
        images: Dict[str, str] = None,
        latitude: float = None,
        longitude: float = None,
        state: str = None,
    ) -> Dict[str, Any]:
        try:
            catalog_entry = crop_catalog.normalize(crop_name) if crop_name else None
            has_images = self._has_uploaded_images(images)

            if has_images:
                return self._diagnose_from_images(
                    images,
                    crop_name,
                    catalog_entry,
                    location,
                    latitude,
                    longitude,
                    state,
                )

            return self._diagnose_text_only(
                crop_name,
                catalog_entry,
                location,
                latitude,
                longitude,
                state,
            )
        except Exception:
            logger.exception("Error in KrishiRaksha pipeline")
            return {
                "status": "error",
                "message": "Diagnosis is temporarily unavailable. Please try again with a clear leaf photo.",
                "error_code": "DIAGNOSIS_UNAVAILABLE",
                "diagnosis": self._photo_required_diagnosis(crop_name or "crop"),
            }

    @staticmethod
    def _has_uploaded_images(images: Optional[Dict[str, str]]) -> bool:
        if not images:
            return False
        return any(bool(v and str(v).strip()) for v in images.values())

    def _diagnose_from_images(
        self,
        images: Dict[str, str],
        crop_name: str,
        catalog_entry: Optional[Dict],
        location: str,
        latitude: float,
        longitude: float,
        state: str,
    ) -> Dict[str, Any]:
        """Image-based path only — never invent diseases from crop name alone."""
        ml_result = self._run_ml_inference(images)
        raw_diagnosis = self._diagnosis_from_ml(ml_result)
        advisory_fallback = False
        if raw_diagnosis is None:
            ml_status = (ml_result or {}).get("status")
            if ml_status in (
                "model_unavailable",
                "model_unverified",
                "tensorflow_missing",
            ) or ml_result is None:
                raw_diagnosis = self._model_unavailable_rule_diagnosis(
                    crop_name, catalog_entry
                )
                advisory_fallback = True
            else:
                raw_diagnosis = self._ml_unavailable_diagnosis(crop_name)

        detected_crop = self._classify_crop(
            crop_name, images, catalog_entry, ml_result=ml_result
        )
        verified = self._verify_region_context(
            raw_diagnosis, location, latitude=latitude, longitude=longitude
        )
        final_result = self._analyze_severity(verified, from_image=True)

        status = "advisory_fallback" if advisory_fallback else "success"
        if not advisory_fallback and ml_result and ml_result.get("status") in (
            "low_confidence",
            "not_plant",
            "model_unavailable",
            "model_unverified",
            "tensorflow_missing",
            "error",
        ):
            status = ml_result["status"]

        display = catalog_entry["name"] if catalog_entry else detected_crop.title()
        if ml_result and ml_result.get("crop_name") and ml_result.get("status") == "success":
            display = ml_result["crop_name"]

        return {
            "status": status,
            "crop_detected": detected_crop,
            "crop_display": display,
            "crop_hindi": catalog_entry.get("hindi") if catalog_entry else "",
            "diagnosis": final_result,
            "pipeline_stages": {
                "classification": "EfficientNet-B3 + plant validation",
                "specialist_model": (
                    "ML active"
                    if ml_result and ml_result.get("status") == "success"
                    else "ML unavailable: safety advisory only"
                    if advisory_fallback
                    else "Blocked (no fake expert fallback)"
                ),
                "region_verification": "GPS weather at your location",
                "severity_analysis": (
                    "From model confidence"
                    if ml_result and ml_result.get("status") == "success"
                    else "N/A"
                ),
            },
            "location": location,
            "state": state,
            "coordinates": (
                {"lat": latitude, "lon": longitude}
                if latitude is not None and longitude is not None
                else None
            ),
            "timestamp": datetime.now().isoformat(),
            "ml_prediction": ml_result,
            "message": (
                "Image received. The trained leaf-disease ML model is not available "
                "on this server, so this is a crop/weather-based advisory, not image classification."
                if advisory_fallback
                else (ml_result or {}).get("message")
            ),
        }

    def _diagnose_text_only(
        self,
        crop_name: str,
        catalog_entry: Optional[Dict],
        location: str,
        latitude: float,
        longitude: float,
        state: str,
    ) -> Dict[str, Any]:
        """No photos — do not claim specific diseases."""
        crop_id = (
            catalog_entry["id"]
            if catalog_entry
            else (crop_name.lower().strip() if crop_name else "unknown")
        )
        diagnosis = self._photo_required_diagnosis(
            catalog_entry["name"] if catalog_entry else (crop_name or "your crop")
        )
        return {
            "status": "photo_required",
            "crop_detected": crop_id,
            "crop_display": catalog_entry["name"] if catalog_entry else crop_id.title(),
            "crop_hindi": catalog_entry.get("hindi") if catalog_entry else "",
            "diagnosis": diagnosis,
            "pipeline_stages": {
                "classification": "Crop name only (no image)",
                "specialist_model": "Disabled until photo uploaded",
                "region_verification": "Skipped",
                "severity_analysis": "Skipped",
            },
            "location": location,
            "state": state,
            "coordinates": (
                {"lat": latitude, "lon": longitude}
                if latitude is not None and longitude is not None
                else None
            ),
            "timestamp": datetime.now().isoformat(),
            "ml_prediction": None,
            "message": "Upload at least one leaf photo to run AI disease detection.",
        }

    def _run_ml_inference(self, images: Dict) -> Optional[Dict[str, Any]]:
        if not images:
            return None
        try:
            return crop_disease_ml_service.predict_from_upload_dict(images)
        except Exception as exc:
            logger.warning("ML inference skipped: %s", exc)
            return None

    def _classify_crop(
        self,
        crop_input: str,
        images: Dict,
        catalog_entry: Optional[Dict] = None,
        ml_result: Optional[Dict] = None,
    ) -> str:
        if ml_result and ml_result.get("crop_name") and ml_result.get("status") == "success":
            slug = crop_catalog.normalize(ml_result["crop_name"])
            if slug:
                return slug["id"]
            return ml_result["crop_name"].lower().replace(" ", "_")
        if catalog_entry:
            return catalog_entry["id"]
        if crop_input:
            normalized = crop_catalog.normalize(crop_input)
            if normalized:
                return normalized["id"]
            return crop_input.lower().strip()
        return "unknown"

    def _photo_required_diagnosis(self, crop_label: str) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Upload leaf photo to detect disease",
                "confidence": 0.0,
                "symptoms": [],
                "treatment": [
                    "Upload close-up of affected leaf (Step 2)",
                    f"Selected crop ({crop_label}) is used as hint only",
                ],
                "explanation": (
                    "KrishiRaksha does not guess diseases without a plant image. "
                    "Random expert rules are disabled."
                ),
                "source": "safety",
            }
        ]

    def _ml_unavailable_diagnosis(self, crop_name: str) -> List[Dict[str, Any]]:
        return [
            {
                "name": "AI model not available on server",
                "confidence": 0.0,
                "symptoms": [],
                "treatment": [
                    "Admin: python -m advisory.ml.train --data-dir data/datasets",
                    "Upload a clear leaf image after model is trained",
                ],
                "explanation": (
                    "Plant validation ran, but no trained EfficientNet model was found. "
                    f"Crop hint '{crop_name or 'none'}' was not used to invent a disease."
                ),
                "source": "safety",
            }
        ]

    def _model_unavailable_rule_diagnosis(
        self, crop_name: str, catalog_entry: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Neutral fallback when a plant image is present but ML is unavailable."""
        crop_id = catalog_entry["id"] if catalog_entry else (crop_name or "crop")
        crop_label = catalog_entry["name"] if catalog_entry else str(crop_id).title()
        return [
            {
                "name": "Disease model unavailable",
                "confidence": 0.0,
                "symptoms": [],
                "treatment": [
                    "Do not treat this response as a disease diagnosis",
                    "Take one close-up affected-leaf photo and one whole-plant photo",
                    "Share the photos with a local KVK or agriculture officer for confirmation",
                    f"Selected crop ({crop_label}) is used only as context, not as proof of disease",
                ],
                "explanation": (
                    "A plant image was uploaded, but the trained ML classifier is not installed. "
                    "This is a safety advisory only, not image classification, and no disease "
                    "confidence is available."
                ),
                "source": "safety",
                "crop_hint": crop_label,
            }
        ]

    def _diagnosis_from_ml(self, ml_result: Optional[Dict[str, Any]]) -> Optional[List[Dict]]:
        if not ml_result:
            return None
        status = ml_result.get("status")
        if status in ("model_unavailable", "model_unverified", "tensorflow_missing", "error"):
            return None
        if status == "not_plant":
            return [
                {
                    "name": ml_result.get("message", NOT_PLANT_MESSAGE),
                    "confidence": 0.0,
                    "symptoms": ["Image appears to be a non-plant object (e.g. laptop, desk)"],
                    "treatment": [
                        "Photograph an actual crop leaf in daylight",
                        "Fill the frame with green leaf tissue",
                    ],
                    "explanation": "Rejected before disease classification (plant validation).",
                    "top_predictions": ml_result.get("top_predictions", []),
                    "source": "plant_validation",
                }
            ]
        if status == "low_confidence":
            return [
                {
                    "name": ml_result.get("message", "Low confidence"),
                    "confidence": ml_result.get("confidence", 0.0),
                    "symptoms": ["Upload a clear, well-lit close-up of a single leaf"],
                    "treatment": [
                        "Ensure leaf fills the frame",
                        "Avoid soil/sky background",
                        "Use daylight without flash glare",
                    ],
                    "explanation": LOW_CONFIDENCE_MESSAGE,
                    "top_predictions": ml_result.get("top_predictions", []),
                    "source": "EfficientNet-B3",
                }
            ]
        if status != "success":
            return None
        disease = ml_result.get("disease_name") or "Unknown"
        return [
            {
                "name": disease,
                "confidence": ml_result.get("confidence", 0.0),
                "symptoms": ["Detected from uploaded leaf image"],
                "treatment": [
                    "Confirm with local KVK / agriculture officer",
                    "Follow label doses for recommended fungicide/pesticide",
                ],
                "explanation": (
                    f"EfficientNet-B3 classification ({ml_result.get('confidence_percent', 0)}% confidence)."
                ),
                "top_predictions": ml_result.get("top_predictions", []),
                "source": "EfficientNet-B3",
            }
        ]

    def _verify_region_context(
        self,
        diseases: List[Dict],
        location: str,
        latitude: float = None,
        longitude: float = None,
    ) -> List[Dict]:
        try:
            weather = self.weather_api.get_current_weather(
                location, latitude=latitude, longitude=longitude
            )
            temp = float(weather.get("temperature", 25))
            hum_str = str(weather.get("humidity", "50")).replace("%", "")
            humidity = float(hum_str) if hum_str.replace(".", "").isdigit() else 50

            verified = []
            for d in diseases:
                confidence = d.get("confidence", 0.5)
                if d.get("requires_humidity") and humidity < 30:
                    confidence -= 0.4
                    d["verification_note"] = (
                        f"Unlikely at current humidity ({humidity}%) near {location}"
                    )
                if d.get("max_temp") and temp > d["max_temp"]:
                    confidence -= 0.5
                    d["verification_note"] = (
                        f"Unlikely at current temperature ({temp}°C)"
                    )
                d["confidence"] = round(max(0.0, min(1.0, confidence)), 2)
                # Keep safety / validation messages even at 0% confidence
                if d["confidence"] > 0.3 or d.get("source") in (
                    "plant_validation",
                    "safety",
                    "EfficientNet-B3",
                ):
                    verified.append(d)
            return sorted(verified, key=lambda x: x["confidence"], reverse=True)
        except Exception as e:
            logger.warning(f"Region verification skipped: {e}")
            return diseases

    def _analyze_severity(
        self, diseases: List[Dict], from_image: bool = False
    ) -> List[Dict]:
        for d in diseases:
            conf = float(d.get("confidence", 0.0))
            if from_image and conf > 0:
                d["severity_score"] = int(round(conf * 100))
            else:
                d["severity_score"] = int(round(conf * 100)) if conf else 0
            if d["severity_score"] > 70:
                d["severity_label"] = "High"
            elif d["severity_score"] > 40:
                d["severity_label"] = "Medium"
            else:
                d["severity_label"] = "Low"
        return diseases
