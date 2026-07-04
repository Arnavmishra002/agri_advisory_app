# Disease Model Readiness

Last checked: 2026-07-04

## Current Local Artifact

Local files exist under `models/crop_disease/`, but they are intentionally ignored
by git and are not part of the repository:

- `efficientnetb3_crop_disease.keras` exists locally.
- `class_labels.json` has 39 labels across 15 crop buckets.
- `training_history.json` records only 2 training epochs.
- Best recorded validation accuracy is 2.63%.
- Best recorded validation top-3 accuracy is 7.89%.
- Bounded smoke evaluation on 390 deterministic test images produced 3.08%
  accuracy and 2.58% weighted F1.

This model is **not farmer-ready**. The backend now blocks it by default because
its metadata quality is `needs_retraining`. The API returns
`model_unverified`/`advisory_fallback` with zero confidence instead of emitting a
farmer-facing disease prediction.

## Coverage Gap

The installed label set is PlantVillage-shaped and covers:

`apple`, `blueberry`, `cherry`, `corn/maize`, `grape`, `orange`, `peach`,
`pepper_bell`, `potato`, `raspberry`, `soybean`, `squash`, `strawberry`,
`tomato`, and `unknown`.

It does not cover several high-priority Indian farmer crops and diseases:

- Cereals: wheat, rice, bajra, jowar, ragi.
- Pulses: arhar/tur, moong, urad, chana, masoor.
- Oilseeds: mustard, groundnut, sunflower, sesame.
- Cash crops: cotton, sugarcane, jute.
- Horticulture/spices: chilli, onion, okra, brinjal, banana, mango.

Do not market this as broad Indian crop disease detection until those classes are
represented in training and held-out evaluation data.

## Dataset And License Notes

- PlantVillage/PlantVillage-derived data is common and large, but official
  challenge documentation describes it as CC BY-SA 3.0 and states that trained
  algorithms fall under the same license. Treat this as a share-alike licensing
  obligation, not a permissive production default, until legal review confirms
  the release plan.
- PlantDoc is listed by its official repository as CC BY 4.0. It is more
  permissive for commercial use with attribution, but it is much smaller and
  should be used mainly for real-world-photo robustness, not as the only source.
- Kaggle mirrors vary by uploader. Do not train production models from a Kaggle
  mirror unless the original source and license are recorded in model metadata.

## Required Go/No-Go Evidence

Before enabling farmer-facing disease predictions:

1. Add a dataset manifest with source URL, license, crop/disease classes, sample
   counts, and source date.
2. Train with Indian-crop coverage and unknown/non-plant negatives.
3. Run full held-out evaluation, not only `--max-test-samples`.
4. Record per-class precision/recall/F1 and false-negative rate for serious
   diseases.
5. Mark the model `production_candidate` only when validation accuracy >= 75% and
   top-3 accuracy >= 90%, or update the thresholds with a documented safety
   rationale.
6. Keep `ML_ALLOW_UNVERIFIED_MODEL=false` in farmer production.

Useful commands:

```bash
PYTHONPATH=backend python -m advisory.ml.evaluate \
  --model-dir models/crop_disease \
  --data-dir data/datasets

PYTHONPATH=backend python -m advisory.ml.evaluate \
  --model-dir models/crop_disease \
  --data-dir data/datasets \
  --max-test-samples 390
```
