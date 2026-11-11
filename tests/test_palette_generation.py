import unittest

from app.schemas.color import PaletteGenerateRequest
from app.services.color import PaletteGeneratorService


class PaletteGenerationTests(unittest.TestCase):
    def test_maximum_count_with_and_without_shades(self):
        for shades in (True, False):
            for harmony in ("analogous", "complementary", "triadic", "split_complementary", "tetradic"):
                with self.subTest(shades=shades, harmony=harmony):
                    result = PaletteGeneratorService.generate(PaletteGenerateRequest(
                        count=15, harmony=harmony, include_shades=shades,
                    ))
                    self.assertEqual(len(result.colors), 15)
                    self.assertEqual(len({color.hex for color in result.colors}), 15)

    def test_maximum_count_with_base_colors(self):
        request = PaletteGenerateRequest(
            count=15,
            base_colors=["#112233", "#445566", "#778899", "#AABBCC", "#DDEEFF"],
        )
        result = PaletteGeneratorService.generate(request)
        self.assertEqual(len(result.colors), 15)
        self.assertEqual([c.hex for c in result.colors[:5]], ["112233", "445566", "778899", "AABBCC", "DDEEFF"])
        self.assertEqual(len({color.hex for color in result.colors}), 15)
