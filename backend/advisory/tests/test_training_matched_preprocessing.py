"""Inference must prepare images exactly as training did.

Training used ``tf.image.resize(img, [224, 224])`` (bilinear, half-pixel
centres, no antialiasing, float output) and never blurred the background. The
served pipeline used OpenCV's area resize after a green-mask blur, which blurs
brown and grey lesions and changes the model's output on real photographs.
"""
import importlib.util
import unittest

import numpy as np
from django.test import SimpleTestCase

from advisory.ml.preprocess import prepare_for_model, resize_like_training

HAS_TF = importlib.util.find_spec("tensorflow") is not None


class TrainingMatchedResizeTests(SimpleTestCase):
    def test_upscaling_matches_half_pixel_bilinear_by_hand(self):
        # 1x2 -> 1x4: sample positions -0.25, 0.25, 0.75, 1.25 clamp to the edges.
        image = np.array([[[0, 0, 0], [100, 100, 100]]], dtype=np.uint8)
        out = resize_like_training(image, (4, 1))
        np.testing.assert_allclose(out[0, :, 0], [0.0, 25.0, 75.0, 100.0], atol=1e-5)

    def test_output_is_unrounded_float32(self):
        image = np.array([[[0, 0, 0], [1, 1, 1]]], dtype=np.uint8)
        out = resize_like_training(image, (4, 1))
        self.assertEqual(out.dtype, np.float32)
        self.assertAlmostEqual(float(out[0, 1, 0]), 0.25, places=6)

    def test_identity_size_is_unchanged(self):
        rng = np.random.default_rng(0)
        image = rng.integers(0, 256, size=(8, 8, 3), dtype=np.uint8)
        np.testing.assert_allclose(resize_like_training(image, (8, 8)), image.astype(np.float32))

    def test_inference_does_not_blur_the_background_by_default(self):
        # A brown lesion on a grey background lies outside the green mask the
        # old pipeline used; it must reach the model unchanged.
        image = np.full((224, 224, 3), 128, dtype=np.uint8)
        image[100:124, 100:124] = (120, 70, 30)
        batch = prepare_for_model(image)
        np.testing.assert_allclose(batch[0], image.astype(np.float32))

    @unittest.skipUnless(HAS_TF, "TensorFlow not installed")
    def test_matches_tensorflow_resize_on_photo_sized_input(self):
        import tensorflow as tf

        rng = np.random.default_rng(1)
        for shape in ((256, 256), (897, 3081), (480, 640), (100, 75)):
            image = rng.integers(0, 256, size=(*shape, 3), dtype=np.uint8)
            expected = tf.image.resize(image, [224, 224]).numpy()
            actual = resize_like_training(image, (224, 224))
            # TensorFlow's kernel rounds each fused multiply-add once; the
            # NumPy version reproduces that, so the output is bit-identical.
            self.assertEqual(float(np.max(np.abs(expected - actual))), 0.0, shape)
