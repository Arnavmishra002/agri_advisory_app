"""TensorFlow data augmentation pipeline."""

from __future__ import annotations

import tensorflow as tf

from .model_builder import get_preprocess_fn


def _load_image_with_pillow(path_value, label_value, image_size):
    """Decode the scalar values supplied by ``tf.py_function``."""
    import os

    import numpy as np
    from PIL import Image

    if hasattr(path_value, "numpy"):
        path_value = path_value.numpy()
    if isinstance(path_value, np.ndarray):
        path_value = path_value.item()
    if hasattr(label_value, "numpy"):
        label_value = label_value.numpy()
    if isinstance(label_value, np.ndarray):
        label_value = label_value.item()

    path = os.fsdecode(path_value)
    height, width = (int(value) for value in image_size)
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image = image.resize((width, height), Image.Resampling.BILINEAR)
            pixels = np.asarray(image, dtype=np.float32)
    except Exception as exc:
        raise ValueError(f"Unable to decode training image {path}: {exc}") from exc
    return pixels, np.int32(label_value)


def decode_and_resize(path: tf.Tensor, label: tf.Tensor, image_size=(224, 224)) -> tuple:
    img, lbl = tf.py_function(
        lambda path_value, label_value: _load_image_with_pillow(
            path_value,
            label_value,
            image_size,
        ),
        [path, label],
        [tf.float32, tf.int32],
    )
    img.set_shape((image_size[0], image_size[1], 3))
    lbl.set_shape(())
    return img, lbl


def _apply_preprocess(image: tf.Tensor, preprocess_mode: str) -> tf.Tensor:
    if preprocess_mode == "rescale_1_255":
        return image / 255.0
    if preprocess_mode == "none":
        return image
    preprocess = get_preprocess_fn()
    return preprocess(image)


def augment_train(
    image: tf.Tensor,
    label: tf.Tensor,
    image_size=(224, 224),
    preprocess_mode: str = "efficientnet",
) -> tuple:
    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_flip_up_down(image)
    # Images are still in the 0-255 range here, so the brightness delta must be
    # expressed on that scale. A 0.25 delta was effectively a no-op.
    image = tf.image.random_brightness(image, max_delta=20.0)
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
    image = tf.image.resize_with_crop_or_pad(image, image_size[1], image_size[0])

    # Gaussian noise
    noise = tf.random.normal(tf.shape(image), mean=0.0, stddev=8.0)
    image = tf.clip_by_value(image + noise, 0, 255)

    image = _apply_preprocess(image, preprocess_mode)
    return image, label


def preprocess_val(
    image: tf.Tensor,
    label: tf.Tensor,
    preprocess_mode: str = "efficientnet",
) -> tuple:
    image = _apply_preprocess(image, preprocess_mode)
    return image, label


def make_datasets(
    train_paths,
    train_labels,
    val_paths,
    val_labels,
    batch_size: int,
    image_size=(224, 224),
    preprocess_mode: str = "efficientnet",
    augment: bool = True,
):
    train_ds = tf.data.Dataset.from_tensor_slices((train_paths, train_labels))
    train_ds = train_ds.shuffle(min(len(train_paths), 5000), seed=42)
    train_ds = train_ds.map(
        lambda path, label: decode_and_resize(path, label, image_size),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    if augment:
        train_ds = train_ds.map(
            lambda image, label: augment_train(image, label, image_size, preprocess_mode),
            num_parallel_calls=tf.data.AUTOTUNE,
        )
    else:
        train_ds = train_ds.map(
            lambda image, label: preprocess_val(image, label, preprocess_mode),
            num_parallel_calls=tf.data.AUTOTUNE,
        )
    train_ds = train_ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)

    val_ds = tf.data.Dataset.from_tensor_slices((val_paths, val_labels))
    val_ds = val_ds.map(
        lambda path, label: decode_and_resize(path, label, image_size),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    val_ds = val_ds.map(
        lambda image, label: preprocess_val(image, label, preprocess_mode),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    val_ds = val_ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)

    return train_ds, val_ds
