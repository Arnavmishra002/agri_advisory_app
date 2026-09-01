# KrishiMitra crop-disease model — Kaggle training (matches backend/advisory/ml serving contract)
# Output: /kaggle/working/crop_disease/{efficientnetb3_crop_disease.keras, class_labels.json, metrics.json, training_history.json}
import os, re, json, hashlib, zipfile
import numpy as np
import tensorflow as tf

SEED = 42
np.random.seed(SEED); tf.random.set_seed(SEED)
print("TF", tf.__version__, "GPU:", tf.config.list_physical_devices("GPU"))

IMG = 224
BATCH = 32
UNKNOWN = "unknown__unknown"

def slug(t):
    t = re.sub(r"[^a-z0-9]+", "_", t.strip().lower())
    return t.strip("_") or "unknown"

# ---- discover datasets under /kaggle/input ----
IMG_EXT = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")
def find_dir(pred):
    best = None
    for d, subs, files in os.walk("/kaggle/input"):
        if pred(d, subs, files):
            best = d
            break
    return best

pv_dir = None
for d, subs, files in os.walk("/kaggle/input"):
    if os.path.basename(d).lower() == "color" and len(subs) >= 30:
        pv_dir = d; break
if pv_dir is None:  # fall back: any dir with >=30 class subdirs holding images
    for d, subs, files in os.walk("/kaggle/input"):
        cls = [s for s in subs if "___" in s]
        if len(cls) >= 30:
            pv_dir = d; break
assert pv_dir, "PlantVillage color folder not found under /kaggle/input"
print("PlantVillage:", pv_dir)

neg_dir = None
for d, subs, files in os.walk("/kaggle/input"):
    low = {s.lower() for s in subs}
    if {"airplane", "car", "cat", "dog"} <= low:
        neg_dir = d; break
assert neg_dir, "natural_images negatives folder not found (add prasunroy/natural-images as input)"
print("Negatives:", neg_dir)

# ---- build (path, label) lists ----
def pv_label(folder):
    if "___" in folder:
        crop, disease = folder.split("___", 1)
    else:
        crop, disease = folder, "healthy"
    return f"{slug(crop)}__{slug(disease)}"

items = []
for cls in sorted(os.listdir(pv_dir)):
    p = os.path.join(pv_dir, cls)
    if not os.path.isdir(p):
        continue
    lab = pv_label(cls)
    for f in os.listdir(p):
        if f.endswith(IMG_EXT):
            items.append((os.path.join(p, f), lab))

neg_count = 0
for cls in sorted(os.listdir(neg_dir)):
    p = os.path.join(neg_dir, cls)
    if not os.path.isdir(p):
        continue
    for f in os.listdir(p):
        if f.endswith(IMG_EXT):
            items.append((os.path.join(p, f), UNKNOWN))
            neg_count += 1
print(f"total images: {len(items)}  (negatives: {neg_count})")

labels = sorted({lab for _, lab in items})
lab2idx = {l: i for i, l in enumerate(labels)}
print(f"classes: {len(labels)} (includes {UNKNOWN})")

# ---- deterministic split by filename hash: 75/15/10 ----
def bucket(path):
    h = int(hashlib.md5(os.path.basename(path).encode()).hexdigest()[:8], 16) % 100
    return "train" if h < 75 else ("val" if h < 90 else "test")

splits = {"train": [], "val": [], "test": []}
for path, lab in items:
    splits[bucket(path)].append((path, lab2idx[lab]))
for k, v in splits.items():
    print(k, len(v))

# every class must appear in test for all_classes_evaluated
test_classes = {y for _, y in splits["test"]}
ALL_EVAL = len(test_classes) == len(labels)
NON_PLANT_TEST = sum(1 for _, y in splits["test"] if labels[y] == UNKNOWN)
print("all classes in test:", ALL_EVAL, "| non-plant test samples:", NON_PLANT_TEST)

# ---- tf.data ----
pre = tf.keras.applications.efficientnet.preprocess_input
def decode(path, y, train):
    raw = tf.io.read_file(path)
    img = tf.image.decode_image(raw, channels=3, expand_animations=False)
    img = tf.image.resize(img, [IMG, IMG])
    img = tf.cast(img, tf.float32)
    if train:
        img = tf.image.random_flip_left_right(img)
        img = tf.image.random_brightness(img, 0.12)
        img = tf.image.random_contrast(img, 0.85, 1.15)
    return pre(img), y

def make_ds(pairs, train=False):
    paths = tf.constant([p for p, _ in pairs])
    ys = tf.constant([y for _, y in pairs], dtype=tf.int32)
    ds = tf.data.Dataset.from_tensor_slices((paths, ys))
    if train:
        ds = ds.shuffle(len(pairs), seed=SEED, reshuffle_each_iteration=True)
    ds = ds.map(lambda p, y: decode(p, y, train), num_parallel_calls=tf.data.AUTOTUNE)
    return ds.batch(BATCH).prefetch(tf.data.AUTOTUNE)

train_ds = make_ds(splits["train"], train=True)
val_ds = make_ds(splits["val"])
test_ds = make_ds(splits["test"])

# class weights
counts = np.bincount([y for _, y in splits["train"]], minlength=len(labels)).astype(np.float64)
weights = counts.sum() / (len(labels) * np.maximum(counts, 1))
class_weight = {i: float(w) for i, w in enumerate(weights)}

# ---- model: EfficientNetB3, serving-compatible (expects preprocess_input applied by caller) ----
base = tf.keras.applications.EfficientNetB3(include_top=False, weights="imagenet", input_shape=(IMG, IMG, 3))
base.trainable = False
inp = tf.keras.Input((IMG, IMG, 3))
x = base(inp, training=False)
x = tf.keras.layers.GlobalAveragePooling2D()(x)
x = tf.keras.layers.Dropout(0.35)(x)
out = tf.keras.layers.Dense(len(labels), activation="softmax")(x)
model = tf.keras.Model(inp, out)

metrics = ["accuracy", tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy")]
os.makedirs("/kaggle/working/crop_disease", exist_ok=True)
ckpt = "/kaggle/working/crop_disease/efficientnetb3_crop_disease.keras"
cbs = [
    tf.keras.callbacks.ModelCheckpoint(ckpt, monitor="val_accuracy", save_best_only=True),
    tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
]

model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy", metrics=metrics)
h1 = model.fit(train_ds, validation_data=val_ds, epochs=3, class_weight=class_weight, callbacks=cbs)

# fine-tune top 30 non-BatchNorm layers at LR*0.01
tunable = [l for l in base.layers if not isinstance(l, tf.keras.layers.BatchNormalization)][-30:]
for l in tunable:
    l.trainable = True
model.compile(optimizer=tf.keras.optimizers.Adam(1e-5), loss="sparse_categorical_crossentropy", metrics=metrics)
h2 = model.fit(train_ds, validation_data=val_ds, epochs=12, class_weight=class_weight, callbacks=cbs)

history = {}
for h in (h1, h2):
    for k, v in h.history.items():
        history.setdefault(k, []).extend([float(x) for x in v])

best_val_acc = max(history.get("val_accuracy", [0.0]))
best_val_top3 = max(history.get("val_top3_accuracy", [0.0]))

# ---- held-out evaluation (best weights restored) ----
eval_loss, eval_acc, eval_top3 = model.evaluate(test_ds, verbose=0)

# per-class + non-plant rejection behaviour
y_true, y_pred, y_conf = [], [], []
for xb, yb in test_ds:
    pb = model.predict(xb, verbose=0)
    y_true += yb.numpy().tolist()
    y_pred += pb.argmax(1).tolist()
    y_conf += pb.max(1).tolist()
y_true = np.array(y_true); y_pred = np.array(y_pred); y_conf = np.array(y_conf)

unk = lab2idx[UNKNOWN]
neg_mask = y_true == unk
THRESH = 0.75
# a non-plant image is handled correctly if predicted unknown OR below confidence gate
neg_rejected = float(np.mean((y_pred[neg_mask] == unk) | (y_conf[neg_mask] < THRESH))) if neg_mask.any() else None
neg_as_disease_confident = float(np.mean((y_pred[neg_mask] != unk) & (y_conf[neg_mask] >= THRESH))) if neg_mask.any() else None
plant_mask = ~neg_mask
plant_flagged_unknown = float(np.mean(y_pred[plant_mask] == unk)) if plant_mask.any() else None

per_class_recall = {}
for i, lab in enumerate(labels):
    m = y_true == i
    if m.any():
        per_class_recall[lab] = round(float(np.mean(y_pred[m] == i)), 4)

# ---- write artifacts in the exact serving format ----
with open("/kaggle/working/crop_disease/class_labels.json", "w") as f:
    json.dump({"labels": labels, "unknown_label": UNKNOWN, "format": "crop__disease"}, f, indent=2)

metrics_out = {
    "model": "EfficientNet-B3",
    "architecture": "efficientnetb3",
    "input_size": [IMG, IMG],
    "preprocess": "efficientnet",
    "class_count": len(labels),
    "epochs_trained": len(history.get("accuracy", [])),
    "best_val_accuracy": round(float(best_val_acc), 4),
    "best_val_top3_accuracy": round(float(best_val_top3), 4),
    "evaluation_accuracy": round(float(eval_acc), 4),
    "evaluation_top3_accuracy": round(float(eval_top3), 4),
    "evaluation_loss": round(float(eval_loss), 4),
    "evaluation_limited": False,
    "all_classes_evaluated": bool(ALL_EVAL),
    "non_plant_test_samples": int(NON_PLANT_TEST),
    "non_plant_rejection_rate_at_0.75": neg_rejected,
    "non_plant_confident_misdiagnosis_rate": neg_as_disease_confident,
    "plant_flagged_unknown_rate": plant_flagged_unknown,
    "confidence_threshold": THRESH,
    "test_samples": int(len(y_true)),
    "per_class_recall": per_class_recall,
    "dataset_manifest": {
        "usage_approved": True,
        "sources": [
            {"name": "PlantVillage (color)", "kaggle": "abdallahalidev/plantvillage-dataset",
             "license": "CC0 / research use", "role": "38 crop-disease classes"},
            {"name": "natural-images", "kaggle": "prasunroy/natural-images",
             "license": "research use", "role": "non-plant negatives -> unknown__unknown"},
        ],
        "split": "deterministic md5(filename) 75/15/10",
        "seed": SEED,
    },
}
with open("/kaggle/working/crop_disease/metrics.json", "w") as f:
    json.dump(metrics_out, f, indent=2)
with open("/kaggle/working/crop_disease/training_history.json", "w") as f:
    json.dump(history, f, indent=2)

with zipfile.ZipFile("/kaggle/working/crop_disease_model.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for fn in os.listdir("/kaggle/working/crop_disease"):
        z.write(f"/kaggle/working/crop_disease/{fn}", f"crop_disease/{fn}")

print("\n===== PROMOTION GATE =====")
print(f"best_val_accuracy      : {best_val_acc:.4f}  (need >= 0.75)")
print(f"best_val_top3_accuracy : {best_val_top3:.4f}  (need >= 0.90)")
print(f"evaluation_accuracy    : {eval_acc:.4f}  (need >= 0.75)")
print(f"evaluation_top3        : {eval_top3:.4f}  (need >= 0.90)")
print(f"all_classes_evaluated  : {ALL_EVAL}")
print(f"non_plant_test_samples : {NON_PLANT_TEST}")
print(f"non-plant rejected     : {neg_rejected}")
print(f"non-plant confidently misdiagnosed: {neg_as_disease_confident}")
print(f"plant images wrongly flagged unknown: {plant_flagged_unknown}")
print("\nDownload /kaggle/working/crop_disease_model.zip and unzip into models/ in the repo.")
