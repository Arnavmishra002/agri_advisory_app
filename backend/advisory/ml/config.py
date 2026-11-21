"""Training and inference configuration."""

from __future__ import annotations

import os
from pathlib import Path

# Monorepo paths: backend/ app + repo-root data/ and models/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "datasets"
DEFAULT_MODEL_DIR = REPO_ROOT / "models" / "crop_disease"

# Image
IMG_SIZE = (224, 224)
IMG_CHANNELS = 3

# Model
BACKBONE = "efficientnetb3"
DROPOUT = 0.35
WARMUP_EPOCHS = int(os.getenv("ML_WARMUP_EPOCHS", "3"))
FINE_TUNE_LAYERS = int(os.getenv("ML_FINE_TUNE_LAYERS", "30"))
FINE_TUNE_LR_FACTOR = float(os.getenv("ML_FINE_TUNE_LR_FACTOR", "0.01"))

# Training
BATCH_SIZE = int(os.getenv("ML_BATCH_SIZE", "32"))
EPOCHS = int(os.getenv("ML_EPOCHS", "40"))
LEARNING_RATE = float(os.getenv("ML_LEARNING_RATE", "1e-3"))
VALIDATION_SPLIT = 0.15
TEST_SPLIT = 0.10
SEED = 42

# Inference
CONFIDENCE_THRESHOLD = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.75"))
# Out-of-scope gate (theta): the largest unknown-class probability a released
# label may have. 5.11e-6 is the 99th percentile on validation plant images, so
# 99% of in-scope leaves pass while field photos and leaves of crops the model
# was never trained on (e.g. rice) are mostly refused.
UNKNOWN_PROB_THRESHOLD = float(os.getenv("ML_UNKNOWN_PROB_THRESHOLD", "5.11e-6"))
OUT_OF_SCOPE_MESSAGE = (
    "This leaf does not match the crops and diseases the model knows well enough "
    "to give a label. Please answer a few symptom questions or show it to your KVK."
)
TOP_K = 3
UNKNOWN_LABEL = "unknown__unknown"
UNKNOWN_DISPLAY = "Unknown"
LOW_CONFIDENCE_MESSAGE = (
    "Disease not confidently identified. Please upload a clearer leaf image."
)
NOT_PLANT_MESSAGE = (
    "This does not look like a crop or leaf photo. Please upload a clear plant leaf image "
    "(not a laptop, person, or indoor object)."
)

# Supported dataset folder names (under data/datasets/raw/)
DATASET_SOURCES = (
    "plantvillage",
    "PlantVillage",
    "plant_doc",
    "PlantDoc",
    "crop_pest_disease",
    "Crop_Pest_and_Disease_Detection",
    "new_plant_diseases",
    "New_Plant_Diseases_Dataset",
)

# Class imbalance
USE_CLASS_WEIGHTS = os.getenv("ML_USE_CLASS_WEIGHTS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Checkpoint filenames
MODEL_FILENAME = "efficientnetb3_crop_disease.keras"
# Low-memory serving artifact. Free-tier hosts cannot fit TensorFlow
# (~2 GB) in RAM, so production serves this float16 TFLite export via
# tflite-runtime (~150-250 MB resident) instead.
TFLITE_FILENAME = "efficientnetb3_crop_disease.tflite"
LABELS_FILENAME = "class_labels.json"
METRICS_FILENAME = "metrics.json"
HISTORY_FILENAME = "training_history.json"
