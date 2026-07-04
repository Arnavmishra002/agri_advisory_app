from django.test import SimpleTestCase

from advisory.ml.evaluate import _limit_test_samples


class DiseaseEvaluationTests(SimpleTestCase):
    def test_limit_test_samples_is_deterministic_and_bounded(self):
        paths = [f"img-{i}.jpg" for i in range(20)]
        labels = [i % 4 for i in range(20)]

        first_paths, first_labels = _limit_test_samples(paths, labels, max_samples=8)
        second_paths, second_labels = _limit_test_samples(paths, labels, max_samples=8)

        self.assertEqual(first_paths, second_paths)
        self.assertEqual(first_labels, second_labels)
        self.assertEqual(len(first_paths), 8)
        self.assertEqual(len(first_labels), 8)
        self.assertEqual(set(first_labels), {0, 1, 2, 3})

    def test_limit_test_samples_keeps_full_set_when_unbounded(self):
        paths = ["a.jpg", "b.jpg"]
        labels = [1, 2]

        limited_paths, limited_labels = _limit_test_samples(
            paths,
            labels,
            max_samples=None,
        )

        self.assertEqual(limited_paths, paths)
        self.assertEqual(limited_labels, labels)
