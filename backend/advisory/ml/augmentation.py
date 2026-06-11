"""TensorFlow data augmentation pipeline."""

from __future__ import annotations

import tensorflow as tf

from .model_builder import get_preprocess_fn


def decode_and_resize(path: tf.Tensor, label: tf.Tensor) -> tuple:
    def _load(path_str: bytes, label_val: int):
        import numpy as np
        from PIL import Image
        import io

        try:
            raw = open(path_str.decode("utf-8"), "rb").read()
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            im = im.resize((224, 224), Image.Resampling.BILINEAR)
            arr = np.array(im, dtype=np.float32)
            return arr, np.int32(label_val)
        except Exception:
            return np.zeros((224, 224, 3), np.float32), np.int32(label_val)

    img, lbl = tf.py_function(
        _load, [path, label], [tf.float32, tf.int32]
    )
    img.set_shape((224, 224, 3))
    lbl.set_shape(())
    return img, lbl


def augment_train(image: tf.Tensor, label: tf.Tensor) -> tuple:
    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_flip_up_down(image)
    image = tf.image.random_brightness(image, max_delta=0.25)
    image = tf.image.random_contrast(image, 0.75, 1.35)
    image = tf.image.random_saturation(image, 0.8, 1.25)
    image = tf.clip_by_value(image, 0, 255)

    # Random rotation via contrib or manual — use projective transform approximation
    # Rotation (90° increments + small affine via resize crop simulates zoom/rotate)
    k = tf.random.uniform([], 0, 4, dtype=tf.int32)
    image = tf.image.rot90(image, k=k)

    # Zoom: central crop + resize
    scale = tf.random.uniform([], 0.85, 1.0)
    h, w = tf.shape(image)[0], tf.shape(image)[1]
    nh = tf.cast(tf.round(tf.cast(h, tf.float32) * scale), tf.int32)
    nw = tf.cast(tf.round(tf.cast(w, tf.float32) * scale), tf.int32)
    image = tf.image.resize(image, [nh, nw])
    image = tf.image.resize_with_crop_or_pad(image, 224, 224)

    # Gaussian noise
    noise = tf.random.normal(tf.shape(image), mean=0.0, stddev=8.0)
    image = tf.clip_by_value(image + noise, 0, 255)

    preprocess = get_preprocess_fn()
    image = preprocess(image)
    return image, label


def preprocess_val(image: tf.Tensor, label: tf.Tensor) -> tuple:
    preprocess = get_preprocess_fn()
    image = preprocess(image)
    return image, label


def make_datasets(train_paths, train_labels, val_paths, val_labels, batch_size: int):
    train_ds = tf.data.Dataset.from_tensor_slices((train_paths, train_labels))
    train_ds = train_ds.shuffle(min(len(train_paths), 5000), seed=42)
    train_ds = train_ds.map(decode_and_resize, num_parallel_calls=tf.data.AUTOTUNE)
    train_ds = train_ds.map(augment_train, num_parallel_calls=tf.data.AUTOTUNE)
    train_ds = train_ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)

    val_ds = tf.data.Dataset.from_tensor_slices((val_paths, val_labels))
    val_ds = val_ds.map(decode_and_resize, num_parallel_calls=tf.data.AUTOTUNE)
    val_ds = val_ds.map(preprocess_val, num_parallel_calls=tf.data.AUTOTUNE)
    val_ds = val_ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)

    return train_ds, val_ds
