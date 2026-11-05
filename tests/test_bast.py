import unittest

from app.services.bast import CATEGORY_REFERENCES, CENTROIDS, bast_index, naming_entropy, rgb_to_oklab


class BastIndexTests(unittest.TestCase):
    def test_oklab_endpoints(self):
        self.assertEqual(rgb_to_oklab(0, 0, 0), (0, 0, 0))
        for actual, expected in zip(rgb_to_oklab(255, 255, 255), (1, 0, 0)):
            self.assertAlmostEqual(actual, expected, places=7)

    def test_reference_colors_have_low_ambiguity(self):
        self.assertEqual(len(CENTROIDS), 13)
        for focal in CENTROIDS:
            self.assertLess(naming_entropy(focal), 0.2)

    def test_revision_2_1_reference_counts(self):
        self.assertEqual([len(refs) for refs in CATEGORY_REFERENCES],
                         [1, 1, 1, 3, 3, 1, 3, 1, 3, 3, 3, 1, 1])
        self.assertEqual(CATEGORY_REFERENCES[-1], (CENTROIDS[-1],))

    def test_revision_2_1_pdf_examples(self):
        for hex_color, expected in {
            '00FF19': 8.09, 'EB00FF': 16.45, 'F97306': 18.09,
            'FF8C00': 12.73, '808080': 13.72, 'A0522D': 70.70,
        }.items():
            with self.subTest(hex_color=hex_color):
                rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
                self.assertAlmostEqual(bast_index(*rgb), expected, delta=0.005)

    def test_vivid_green_and_magenta_are_recognized(self):
        self.assertLess(bast_index(0, 255, 25), 20)
        self.assertLess(bast_index(235, 0, 255), 25)

    def test_orphan_tends_to_maximum_not_zero(self):
        self.assertAlmostEqual(naming_entropy((10, 10, 10)), 1)

    def test_rgb_grid_is_finite_and_bounded(self):
        for r in range(0, 256, 17):
            for g in range(0, 256, 17):
                for b in range(0, 256, 17):
                    self.assertTrue(0 <= bast_index(r, g, b) <= 100)

    def test_local_continuity(self):
        self.assertLess(abs(bast_index(48, 88, 128) - bast_index(49, 88, 128)), 2)


if __name__ == '__main__':
    unittest.main()
