"""Regenerate every vision number the paper reports, from the shipped model.

Run this on Kaggle with the same two datasets attached as the training run
(abdallahalidev/plantvillage-dataset and prasunroy/natural-images) and the
trained model uploaded, or straight after training in the same notebook.

It reproduces the deterministic md5(filename) 75/15/10 split used in training,
so the test partition here is exactly the one the model never saw, and prints
the figures the paper needs:

    top-1, top-3, macro F1, weighted F1        -> Table 7
    ECE before and after temperature scaling   -> Table 8, Section 3.2
    fitted temperature T                       -> Section 3.2
    coverage and selective accuracy at tau     -> Table 8, Table 9
    risk-coverage curve and AURC               -> Section 3.1 (new)
    non-plant rejection / confident misdiagnosis
                                               -> Table 8, abstract

Why this exists: the paper currently reports ECE, coverage and selective
accuracy that were produced before the shipped model was trained, so they
describe a different artefact. These are the three numbers that cannot be
recovered from metrics.json and must be measured again before submission.

Usage on Kaggle:
    !python eval_selective_metrics.py --model /kaggle/working/crop_disease
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os

import numpy as np
import tensorflow as tf

IMG = 224
UNKNOWN = "unknown__unknown"
SEED = 42


def bucket(path: str) -> str:
    """The exact split rule used in training -- do not change."""
    h = int(hashlib.md5(os.path.basename(path).encode()).hexdigest()[:8], 16) % 100
    return "train" if h < 75 else ("val" if h < 90 else "test")


def slug(t: str) -> str:
    import re
    t = re.sub(r"[^a-z0-9]+", "_", t.strip().lower())
    return t.strip("_") or "unknown"


def discover(root="/kaggle/input"):
    IMG_EXT = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")
    pv = neg = None
    for d, subs, _ in os.walk(root):
        if pv is None and os.path.basename(d).lower() == "color" and len(subs) >= 30:
            pv = d
        low = {s.lower() for s in subs}
        if neg is None and {"airplane", "car", "cat", "dog"} <= low:
            neg = d
    assert pv and neg, "PlantVillage colour dir or natural-images dir not found"
    items = []
    for cls in sorted(os.listdir(pv)):
        p = os.path.join(pv, cls)
        if not os.path.isdir(p):
            continue
        crop, _, disease = cls.partition("___")
        lab = f"{slug(crop)}__{slug(disease or 'healthy')}"
        items += [(os.path.join(p, f), lab) for f in os.listdir(p) if f.endswith(IMG_EXT)]
    for cls in sorted(os.listdir(neg)):
        p = os.path.join(neg, cls)
        if not os.path.isdir(p):
            continue
        items += [(os.path.join(p, f), UNKNOWN) for f in os.listdir(p) if f.endswith(IMG_EXT)]
    return items


def ece(conf: np.ndarray, correct: np.ndarray, bins: int = 15) -> float:
    """Expected calibration error, equal-width bins (Guo et al. 2017)."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.sum() == 0:
            continue
        total += (m.sum() / len(conf)) * abs(correct[m].mean() - conf[m].mean())
    return float(total)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """Single-parameter temperature scaling on held-out logits."""
    lg = tf.constant(logits, tf.float32)
    y = tf.constant(labels, tf.int32)
    log_t = tf.Variable(0.0, dtype=tf.float32)      # T = exp(log_t) keeps T > 0
    opt = tf.keras.optimizers.Adam(0.01)
    for _ in range(500):
        with tf.GradientTape() as tape:
            loss = tf.reduce_mean(
                tf.nn.sparse_softmax_cross_entropy_with_logits(y, lg / tf.exp(log_t))
            )
        opt.apply_gradients(zip(tape.gradient(loss, [log_t]), [log_t]))
    return float(np.exp(log_t.numpy()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="/kaggle/working/crop_disease")
    ap.add_argument("--tau", type=float, default=0.75)
    args = ap.parse_args()

    labels = json.load(open(f"{args.model}/class_labels.json"))["labels"]
    lab2idx = {l: i for i, l in enumerate(labels)}
    model = tf.keras.models.load_model(f"{args.model}/efficientnetb3_crop_disease.keras")

    items = discover()
    splits = {"val": [], "test": []}
    for path, lab in items:
        b = bucket(path)
        if b in splits:
            splits[b].append((path, lab2idx[lab]))

    pre = tf.keras.applications.efficientnet.preprocess_input

    def logits_for(pairs):
        """Softmax is stripped so temperature can be fitted on real logits."""
        base = tf.keras.Model(model.input, model.layers[-1].input)
        dense = model.layers[-1]
        W, b = dense.get_weights()
        out, ys = [], []
        ds = tf.data.Dataset.from_tensor_slices(
            (tf.constant([p for p, _ in pairs]), tf.constant([y for _, y in pairs]))
        )
        def dec(p, y):
            img = tf.image.decode_image(tf.io.read_file(p), channels=3, expand_animations=False)
            return pre(tf.cast(tf.image.resize(img, [IMG, IMG]), tf.float32)), y
        for xb, yb in ds.map(dec, num_parallel_calls=tf.data.AUTOTUNE).batch(64):
            out.append(base.predict(xb, verbose=0) @ W + b)
            ys.append(yb.numpy())
        return np.concatenate(out), np.concatenate(ys)

    val_logits, val_y = logits_for(splits["val"])
    T = fit_temperature(val_logits, val_y)

    test_logits, y_true = logits_for(splits["test"])

    def softmax(z):
        z = z - z.max(1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(1, keepdims=True)

    p_raw = softmax(test_logits)
    p_cal = softmax(test_logits / T)
    y_pred = p_cal.argmax(1)
    conf = p_cal.max(1)
    correct = (y_pred == y_true).astype(float)

    top3 = np.mean([y in np.argsort(r)[-3:] for y, r in zip(y_true, p_cal)])

    # F1
    f1s, support = [], []
    for i in range(len(labels)):
        tp = ((y_pred == i) & (y_true == i)).sum()
        fp = ((y_pred == i) & (y_true != i)).sum()
        fn = ((y_pred != i) & (y_true == i)).sum()
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
        support.append((y_true == i).sum())
    f1s, support = np.array(f1s), np.array(support)

    # selective classification
    emitted = conf >= args.tau
    coverage = emitted.mean()
    selective_acc = correct[emitted].mean() if emitted.any() else float("nan")

    order = np.argsort(-conf)
    risks, covs = [], []
    for k in range(1, len(order) + 1):
        idx = order[:k]
        covs.append(k / len(order))
        risks.append(1.0 - correct[idx].mean())
    aurc = float(np.trapz(risks, covs))

    unk = lab2idx[UNKNOWN]
    neg = y_true == unk
    print("\n" + "=" * 64)
    print("VISION NUMBERS FOR THE PAPER")
    print("=" * 64)
    print(f"  test images                    {len(y_true)} ({neg.sum()} non-plant)")
    print(f"  classes                        {len(labels)}")
    print(f"  top-1                          {correct.mean()*100:.2f}%")
    print(f"  top-3                          {top3*100:.2f}%")
    print(f"  macro F1                       {f1s.mean()*100:.2f}%")
    print(f"  weighted F1                    {np.average(f1s, weights=support)*100:.2f}%")
    print(f"  fitted temperature T           {T:.3f}")
    print(f"  ECE before scaling             {ece(p_raw.max(1), (p_raw.argmax(1)==y_true).astype(float))*100:.2f}%")
    print(f"  ECE after scaling              {ece(conf, correct)*100:.2f}%")
    print(f"  coverage at tau={args.tau}          {coverage*100:.2f}%")
    print(f"  selective accuracy at tau      {selective_acc*100:.2f}%")
    print(f"  delivered error at tau         {(1-selective_acc)*100:.2f}%")
    print(f"  AURC                           {aurc:.4f}")
    if neg.any():
        rej = np.mean((y_pred[neg] == unk) | (conf[neg] < args.tau))
        bad = np.mean((y_pred[neg] != unk) & (conf[neg] >= args.tau))
        print(f"  non-plant rejected             {rej*100:.2f}%")
        print(f"  non-plant confidently wrong    {bad*100:.2f}%")
        print(f"  plants wrongly refused         {np.mean(y_pred[~neg]==unk)*100:.2f}%")
    print("=" * 64)


if __name__ == "__main__":
    main()
