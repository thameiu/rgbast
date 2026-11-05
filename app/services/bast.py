"""Bast index revision 2.1: see bast_index_2_1.pdf and bast_index.md."""

import math

TAU = 0.08
ORPHAN_RADIUS = 0.15
# Reference hex values from the specification; convert at full precision.
CENTROID_HEX = (
    'FFFFFF', '000000', '929591', 'E50000', 'F97306', 'FFFF14',
    '15B01A', '00FFFF', '0343DF', '7E1E9C', 'C20078', 'FF81C0', '653700',
)


def rgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    def linear(channel: float) -> float:
        x = channel / 255.0
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = linear(r), linear(g), linear(b)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


CENTROIDS = tuple(rgb_to_oklab(*(int(h[i:i + 2], 16) for i in (0, 2, 4))) for h in CENTROID_HEX)


def category_references(hex_color: str) -> tuple[tuple[float, float, float], ...]:
    rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    base = rgb_to_oklab(*rgb)
    # Achromatic anchors stay fixed; brightening brown would invade orange.
    if hex_color in (*CENTROID_HEX[:3], '653700'):
        return (base,)
    peak = max(rgb)
    vivid = rgb_to_oklab(*(channel * 255.0 / peak for channel in rgb))
    midpoint = tuple((a + b) / 2 for a, b in zip(base, vivid))
    return tuple(dict.fromkeys((base, midpoint, vivid)))


CATEGORY_REFERENCES = tuple(category_references(h) for h in CENTROID_HEX)
ORPHAN_WEIGHT = math.exp(-(ORPHAN_RADIUS / TAU) ** 2)


def naming_entropy(color: tuple[float, float, float]) -> float:
    """Normalized entropy in [0, 1]; unknown votes are shared uniformly.

    The reference points and provisional parameters define a naming model,
    not measured probabilities of human responses.
    """
    # One vote per name: extra references extend coverage, not voting strength.
    weights = [math.exp(-min(
        sum((a - b) ** 2 for a, b in zip(color, focal))
        for focal in references
    ) / TAU ** 2) for references in CATEGORY_REFERENCES]
    total = sum(weights) + ORPHAN_WEIGHT
    probabilities = [(w + ORPHAN_WEIGHT / len(CENTROIDS)) / total for w in weights]
    entropy = -sum(p * math.log(p) for p in probabilities) / math.log(len(CENTROIDS))
    return max(0.0, min(1.0, entropy))


def bast_index(r: int, g: int, b: int) -> float:
    """Return the Bast index on the API's 0-100 scale, without rounding."""
    return 100.0 * naming_entropy(rgb_to_oklab(r, g, b))
