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
FINE_TUNE_AT = 120  # Unfreeze top layers from this block onward

# Training
BATCH_SIZE = int(os.getenv("ML_BATCH_SIZE", "32"))
EPOCHS = int(os.getenv("ML_EPOCHS", "40"))
LEARNING_RATE = float(os.getenv("ML_LEARNING_RATE", "1e-4"))
VALIDATION_SPLIT = 0.15
TEST_SPLIT = 0.10
SEED = 42

# Inference
CONFIDENCE_THRESHOLD = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.75"))
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
USE_CLASS_WEIGHTS = True

# Checkpoint filenames
MODEL_FILENAME = "efficientnetb3_crop_disease.keras"
LABELS_FILENAME = "class_labels.json"
METRICS_FILENAME = "metrics.json"
HISTORY_FILENAME = "training_history.json"
