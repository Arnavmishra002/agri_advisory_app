import logging
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

from .clean_weather_api import CleanWeatherAPI
from .crop_catalog import crop_catalog
from ..ml.config import LOW_CONFIDENCE_MESSAGE, NOT_PLANT_MESSAGE
from .crop_disease_ml_service import crop_disease_ml_service
from .ultra_dynamic_government_api import UltraDynamicGovernmentAPI

try:
    from ..models import DiagnosticSession
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Specialist models for high-traffic crops
_EXPERT_CROPS = frozenset({"tomato", "rice", "potato", "banana", "chilli"})

# Category-based guidance when no specialist model exists
_CATEGORY_DIAGNOSES: Dict[str, List[Dict[str, Any]]] = {
    "cereal": [
        {
            "name": "Rust / Smut (Suspected)",
            "confidence": 0.72,
            "requires_humidity": True,
            "symptoms": ["Orange/brown pustules on leaves", "Black spore masses on grains"],
            "treatment": ["Propiconazole spray", "Resistant varieties", "Balanced nitrogen"],
            "explanation": "Common cereal fungal complex in humid seasons — verify with local KVK.",
        },
        {
            "name": "Stem Borer",
            "confidence": 0.68,
            "symptoms": ["Dead hearts in young plants", "Holes in stems"],
            "treatment": ["Pheromone traps", "Cartap hydrochloride as per label", "Early sowing"],
            "explanation": "Typical lepidopteran pest pressure on cereals in your region.",
        },
    ],
    "pulse": [
        {
            "name": "Pod Borer / Helicoverpa",
            "confidence": 0.7,
            "symptoms": ["Holed pods", "Grain damage"],
            "treatment": ["NPV spray", "Pheromone traps", "Inter-cropping with marigold"],
            "explanation": "Frequent pulse pest — confirm with pheromone trap counts.",
        },
        {
            "name": "Powdery Mildew",
            "confidence": 0.65,
            "requires_humidity": False,
            "symptoms": ["White powder on leaves", "Yellowing"],
            "treatment": ["Sulphur dusting", "Trichoderma seed treatment"],
            "explanation": "Often appears in moderate humidity on legumes.",
        },
    ],
    "oilseed": [
        {
            "name": "Alternaria Blight",
            "confidence": 0.7,
            "requires_humidity": True,
            "symptoms": ["Dark concentric leaf spots", "Pod shattering"],
            "treatment": ["Mancozeb + Carbendazim (label dose)", "Crop rotation"],
            "explanation": "Typical oilseed foliar disease in post-flowering stage.",
        },
    ],
    "vegetable": [
        {
            "name": "Leaf Spot / Blight Complex",
            "confidence": 0.74,
            "requires_humidity": True,
            "symptoms": ["Brown spots with yellow halo", "Defoliation"],
            "treatment": ["Copper fungicide", "Remove infected debris", "Drip irrigation"],
            "explanation": "Vegetable foliar disease pattern — upload close-up leaf photo for precision.",
        },
        {
            "name": "Aphid / Whitefly Infestation",
            "confidence": 0.7,
            "symptoms": ["Sticky honeydew", "Curling leaves", "Sooty mould"],
            "treatment": ["Neem oil 1%", "Yellow sticky traps", "Imidacloprid only if severe"],
            "explanation": "Vector pests common on vegetables — check underside of leaves.",
        },
    ],
    "fruit": [
        {
            "name": "Fruit Fly / Borer",
            "confidence": 0.71,
            "symptoms": ["Puncture marks on fruit", "Premature drop"],
            "treatment": ["Methyl eugenol traps", "Bagging of fruits", "Protein bait sprays"],
            "explanation": "Orchard pest pressure increases near harvest.",
        },
    ],
    "general": [
        {
            "name": "Nutrient Deficiency (N/P/K)",
            "confidence": 0.6,
            "symptoms": ["Inter-veinal chlorosis", "Stunted growth", "Poor flowering"],
            "treatment": ["Soil test at soil health card lab", "Split NPK as per crop stage"],
            "explanation": "Non-specific stress — soil test recommended for your GPS location.",
        },
    ],
}


class KrishiRakshaPestService:
    """
    KrishiRaksha 2.0: Advanced Pest Detection System
    Supports any catalog crop with location-aware weather verification.
    """

    def __init__(self):
        self.weather_api = CleanWeatherAPI()
        self.gov_api = UltraDynamicGovernmentAPI()

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
        except Exception as e:
            logger.error(f"Error in KrishiRaksha pipeline: {e}")
            return {
                "status": "error",
                "message": str(e),
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
        if raw_diagnosis is None:
            raw_diagnosis = self._ml_unavailable_diagnosis(crop_name)

        detected_crop = self._classify_crop(
            crop_name, images, catalog_entry, ml_result=ml_result
        )
        verified = self._verify_region_context(
            raw_diagnosis, location, latitude=latitude, longitude=longitude
        )
        final_result = self._analyze_severity(verified, from_image=True)

        status = "success"
        if ml_result and ml_result.get("status") in (
            "low_confidence",
            "not_plant",
            "model_unavailable",
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
            "message": (ml_result or {}).get("message"),
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

    def _run_specialist_model(
        self,
        crop: str,
        images: Dict,
        catalog_entry: Optional[Dict] = None,
        ml_result: Optional[Dict] = None,
    ) -> List[Dict]:
        if ml_result:
            ml_diag = self._diagnosis_from_ml(ml_result)
            if ml_diag is not None:
                return ml_diag
        experts = {
            "tomato": self._tomato_expert_logic,
            "rice": self._rice_expert_logic,
            "potato": self._potato_expert_logic,
            "banana": self._banana_expert_logic,
            "chilli": self._chilli_expert_logic,
        }
        if crop in experts:
            return experts[crop]()
        return self._catalog_expert_logic(crop, catalog_entry)

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

    def _diagnosis_from_ml(self, ml_result: Optional[Dict[str, Any]]) -> Optional[List[Dict]]:
        if not ml_result:
            return None
        status = ml_result.get("status")
        if status in ("model_unavailable", "tensorflow_missing", "error"):
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

    def _catalog_expert_logic(
        self, crop: str, catalog_entry: Optional[Dict] = None
    ) -> List[Dict]:
        entry = catalog_entry or crop_catalog.get(crop)
        category = entry["category"] if entry else "general"
        raw = list(_CATEGORY_DIAGNOSES.get(category, []))
        if category != "general":
            raw.extend(_CATEGORY_DIAGNOSES.get("general", []))
        crop_label = entry["name"] if entry else crop.title()
        if not raw:
            return self._generalist_logic(crop)
        out = []
        for d in raw[:3]:
            copy = dict(d)
            copy["explanation"] = (
                f"{d.get('explanation', '')} "
                f"Tailored for {crop_label} ({category}) at your GPS location."
            ).strip()
            out.append(copy)
        return out

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

    def _tomato_expert_logic(self):
        return [
            {
                "name": "Early Blight",
                "confidence": 0.95,
                "requires_humidity": True,
                "symptoms": ["Target-like spots", "Yellowing leaves"],
                "treatment": ["Copper fungicides", "Trim infected leaves", "Mulching"],
                "explanation": "Identified by characteristic concentric rings on lower leaves.",
            },
            {
                "name": "Late Blight",
                "confidence": 0.85,
                "max_temp": 30,
                "symptoms": ["Dark water-soaked lesions", "White mold on underside"],
                "treatment": ["Mancozeb", "Improve air circulation", "Avoid overhead irrigation"],
                "explanation": "Detected dark lesions typical of phytophthora infestans.",
            },
        ]

    def _rice_expert_logic(self):
        return [
            {
                "name": "Rice Blast",
                "confidence": 0.92,
                "requires_humidity": True,
                "symptoms": ["Diamond shaped lesions", "Gray center spots"],
                "treatment": ["Tricyclazole", "Reduce Nitrogen dosage", "Keep water level constant"],
                "explanation": "Diamond-shaped lesions on leaves confirm Pyricularia oryzae.",
            },
            {
                "name": "Bacterial Leaf Blight",
                "confidence": 0.75,
                "requires_humidity": True,
                "symptoms": ["Water-soaked streaks", "Milky ooze"],
                "treatment": ["Copper oxychloride", "Drain field", "Potash application"],
                "explanation": "Yellowish streaks starting from leaf tips.",
            },
        ]

    def _potato_expert_logic(self):
        return [
            {
                "name": "Early Blight",
                "confidence": 0.88,
                "symptoms": ["Brown spots with rings", "Yellow halo"],
                "treatment": ["Chlorothalonil", "Crop rotation", "Drip irrigation"],
                "explanation": "Concentric rings (target board effect) visible.",
            }
        ]

    def _banana_expert_logic(self):
        return [
            {
                "name": "Panama Wilt",
                "confidence": 0.90,
                "symptoms": ["Yellowing of older leaves", "Splitting stem"],
                "treatment": ["Soil drenching with Carbendazim", "Remove infected plants"],
                "explanation": "Yellowing starting from older leaves indicates vascular wilt.",
            }
        ]

    def _chilli_expert_logic(self):
        return [
            {
                "name": "Leaf Curl Virus",
                "confidence": 0.94,
                "symptoms": ["Curled leaves", "Stunted growth"],
                "treatment": ["Control whitefly vector", "Imidacloprid", "Remove infected plants"],
                "explanation": "Upward curling of leaves is a classic sign of Geminivirus.",
            }
        ]

    def _generalist_logic(self, crop):
        return [{
            "name": "General Stress / Unknown",
            "confidence": 0.5,
            "symptoms": ["Leaf discoloration", "Wilting"],
            "treatment": ["Ensure proper watering", "Check for pests", "Consult local agronomist"],
            "explanation": f"Upload clear photos of {crop} for a sharper diagnosis.",
        }]
