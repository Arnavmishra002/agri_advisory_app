# Disease Model Readiness

Last checked: 2026-07-18

## Farmer-Facing Status

Disease image classification remains disabled. The API returns an honest
`advisory_fallback` with symptom questions and escalation guidance instead of a
predicted disease label. Keep `ML_ALLOW_UNVERIFIED_MODEL=false` in farmer
environments.

The old artifact under `models/crop_disease/` is not production-ready. It was
trained for two epochs through a decoder bug that silently replaced every image
with black pixels, and its reported validation accuracy was 2.63%. Do not mount
or promote it.

## Repaired Pipeline

The training and evaluation pipeline now:

- Deduplicates physical images before splitting. The local PlantVillage mirror
  contains 54,305 unique images across 38 populated classes.
- Creates the full deterministic train/validation/test split before applying a
  local sample cap, preventing train-to-test leakage during later evaluation.
- Fails on corrupt image decoding instead of silently training on black images.
- Starts with a frozen ImageNet EfficientNet-B3 backbone, then fine-tunes only
  the requested top non-BatchNorm layers at a lower learning rate.
- Evaluates labels in the persisted model order and fails on label drift.
- Records top-1/top-3 accuracy, per-class precision/recall/F1, false-negative
  rates, non-plant support, manifest approval, and whether evaluation was
  bounded.
- Recomputes the model quality label from evidence; a stale value in
  `metrics.json` cannot promote a model.

## Bounded Candidate Evidence

A leakage-free CPU candidate was trained with 100 images per class, three
frozen-backbone warm-up epochs, and one limited fine-tuning epoch:

- 38 classes; train 2,850; validation 570; capped test 380.
- Best validation accuracy: 77.72%.
- Best validation top-3 accuracy: 92.98%.
- Deterministic 760-image evaluation accuracy: 79.87%.
- Evaluation top-3 accuracy: 94.34%.
- Weighted F1: 79.30%.
- Quality verdict: `needs_validation`.

These numbers prove the repaired pipeline learns. They do not approve the model
for farmers because evaluation was bounded, no non-plant negatives were
available, and the current source manifest is not approved for production use.
The candidate was intentionally kept outside `models/crop_disease/`.

## Coverage And License Gaps

The current PlantVillage-shaped labels cover apple, blueberry, cherry,
corn/maize, grape, orange, peach, bell pepper, potato, raspberry, soybean,
squash, strawberry, and tomato. They do not provide broad Indian field coverage
for wheat, rice, millets, pulses, mustard, groundnut, cotton, sugarcane, chilli,
onion, okra, brinjal, banana, or mango.

The local dataset is the [Kaggle PlantVillage mirror](https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset),
which declares CC BY-NC-SA 4.0. The checked-in example manifest therefore keeps
`usage_approved: false`; legal/product approval is required before production
training. Dataset mirrors must not be treated as licensed merely because files
are available.

## Production Go/No-Go

All of the following are required before enabling classification:

1. Every dataset source has a reviewed manifest and `usage_approved: true`.
2. Indian crop coverage and representative phone-camera field images are added.
3. Unknown/non-plant negatives are present in train, validation, and test data.
4. Full held-out evaluation runs without `--max-test-samples`.
5. Every model label has held-out support and no unsupported dataset label exists.
6. Validation and held-out top-1 accuracy are at least 75% and top-3 accuracy is
   at least 90%, with reviewed per-class false-negative rates.
7. The resulting metadata verdict is `production_candidate`.

Safe candidate run:

```bash
python3 scripts/train_crop_disease.py --skip-setup \
  --max-per-class 100 --epochs 4 --warmup-epochs 3 \
  --fine-tune-layers 20 --max-test-samples 760
```

Production-candidate gate after approved data and negatives are available:

```bash
python3 scripts/train_crop_disease.py --skip-setup --production \
  --max-per-class 0 --epochs 20 --max-test-samples 0 \
  --dataset-manifest data/datasets/dataset_manifest.json \
  --output-dir models/crop_disease_candidate
```

Promotion into `models/crop_disease/` is a separate reviewed release step.
