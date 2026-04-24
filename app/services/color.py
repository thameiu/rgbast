import colorsys
import math
import re

try:
    import colornames as _cn
    _CN_AVAILABLE = True
except ImportError:
    _cn = None  # type: ignore
    _CN_AVAILABLE = False

from app.schemas.color import (
    ColorAccessibility,
    ColorBlindnessPreview,
    ColorBlindVariant,
    ColorCMYK,
    ColorContrast,
    ColorHSL,
    ColorHSB,
    ColorHWB,
    ColorInfoResponse,
    ColorLAB,
    ColorLCH,
    ColorLUV,
    ColorRGB,
    ColorXYZ,
)


class ColorService:
    _HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")

    _PURE_RGB = [
        (255, 255, 255),
        (0, 0, 0),
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (0, 255, 255),
        (255, 0, 255),
    ]

    @staticmethod
    def get_color_info(hex_value: str) -> ColorInfoResponse:
        normalized_hex = ColorService._normalize_hex(hex_value)
        r, g, b = ColorService._hex_to_rgb(normalized_hex)

        hsl = ColorService._to_hsl(r, g, b)
        hsb = ColorService._to_hsb(r, g, b)
        hwb = ColorService._to_hwb(r, g, b)
        cmyk = ColorService._to_cmyk(r, g, b)
        xyz = ColorService._to_xyz(r, g, b)
        lab = ColorService._xyz_to_lab(xyz)
        lch = ColorService._lab_to_lch(lab)
        luv = ColorService._xyz_to_luv(xyz)

        contrast = ColorService._contrast_info(r, g, b)
        cb = ColorService._color_blindness_previews(r, g, b)
        bast_score = ColorService._bast_score(r, g, b)

        closest_name = ColorService._closest_name(normalized_hex, r, g, b)
        label_is_approximate = False
        if closest_name and _CN_AVAILABLE:
            try:
                nr, ng, nb = _cn._colors[closest_name]
                label_is_approximate = not (nr == r and ng == g and nb == b)
            except Exception:
                label_is_approximate = True

        return ColorInfoResponse(
            input_hex=hex_value,
            normalized_hex=normalized_hex,
            closest_name=closest_name,
            label_is_approximate=label_is_approximate,
            rgb=ColorRGB(r=r, g=g, b=b),
            hsl=hsl,
            cmyk=cmyk,
            hsb=hsb,
            lab=lab,
            xyz=xyz,
            lch=lch,
            luv=luv,
            hwb=hwb,
            accessibility=ColorAccessibility(
                color_blindness=cb,
                contrast=contrast,
            ),
            bast_score=round(bast_score, 2),
        )

    @staticmethod
    def _normalize_hex(hex_value: str) -> str:
        if not ColorService._HEX_RE.match(hex_value):
            raise ValueError("Invalid hex format. Expected 6-characters hex, with or without '#'.")
        return hex_value.lstrip("#").upper()

    @staticmethod
    def _hex_to_rgb(hex_value: str) -> tuple[int, int, int]:
        return tuple(int(hex_value[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _to_hsl(r: int, g: int, b: int) -> ColorHSL:
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        h, l, s = colorsys.rgb_to_hls(rf, gf, bf)
        return ColorHSL(h=round(h * 360, 2), s=round(s * 100, 2), l=round(l * 100, 2))

    @staticmethod
    def _to_hsb(r: int, g: int, b: int) -> ColorHSB:
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
        return ColorHSB(h=round(h * 360, 2), s=round(s * 100, 2), b=round(v * 100, 2))

    @staticmethod
    def _to_hwb(r: int, g: int, b: int) -> ColorHWB:
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        h, _s, _v = colorsys.rgb_to_hsv(rf, gf, bf)
        w = min(rf, gf, bf)
        blk = 1.0 - max(rf, gf, bf)
        return ColorHWB(h=round(h * 360, 2), w=round(w * 100, 2), b=round(blk * 100, 2))

    @staticmethod
    def _to_cmyk(r: int, g: int, b: int) -> ColorCMYK:
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        k = 1 - max(rf, gf, bf)
        if k >= 1.0:
            return ColorCMYK(c=0.0, m=0.0, y=0.0, k=100.0)

        c = (1 - rf - k) / (1 - k)
        m = (1 - gf - k) / (1 - k)
        y = (1 - bf - k) / (1 - k)
        return ColorCMYK(
            c=round(c * 100, 2),
            m=round(m * 100, 2),
            y=round(y * 100, 2),
            k=round(k * 100, 2),
        )

    @staticmethod
    def _srgb_to_linear(c: float) -> float:
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    @staticmethod
    def _to_xyz(r: int, g: int, b: int) -> ColorXYZ:
        rf = ColorService._srgb_to_linear(r / 255.0)
        gf = ColorService._srgb_to_linear(g / 255.0)
        bf = ColorService._srgb_to_linear(b / 255.0)

        x = (rf * 0.4124564 + gf * 0.3575761 + bf * 0.1804375) * 100
        y = (rf * 0.2126729 + gf * 0.7151522 + bf * 0.0721750) * 100
        z = (rf * 0.0193339 + gf * 0.1191920 + bf * 0.9503041) * 100
        return ColorXYZ(x=round(x, 4), y=round(y, 4), z=round(z, 4))

    @staticmethod
    def _f_lab(t: float) -> float:
        delta = 6 / 29
        if t > delta**3:
            return t ** (1 / 3)
        return (t / (3 * delta * delta)) + (4 / 29)

    @staticmethod
    def _xyz_to_lab(xyz: ColorXYZ) -> ColorLAB:
        xn, yn, zn = 95.047, 100.0, 108.883
        fx = ColorService._f_lab(xyz.x / xn)
        fy = ColorService._f_lab(xyz.y / yn)
        fz = ColorService._f_lab(xyz.z / zn)

        l = (116 * fy) - 16
        a = 500 * (fx - fy)
        b = 200 * (fy - fz)
        return ColorLAB(l=round(l, 4), a=round(a, 4), b=round(b, 4))

    @staticmethod
    def _lab_to_lch(lab: ColorLAB) -> ColorLCH:
        c = math.sqrt(lab.a * lab.a + lab.b * lab.b)
        h = math.degrees(math.atan2(lab.b, lab.a))
        if h < 0:
            h += 360
        return ColorLCH(l=lab.l, c=round(c, 4), h=round(h, 4))

    @staticmethod
    def _xyz_to_luv(xyz: ColorXYZ) -> ColorLUV:
        xn, yn, zn = 95.047, 100.0, 108.883

        def uv_prime(x: float, y: float, z: float) -> tuple[float, float]:
            denom = x + 15 * y + 3 * z
            if denom == 0:
                return 0.0, 0.0
            return (4 * x) / denom, (9 * y) / denom

        un, vn = uv_prime(xn, yn, zn)
        u, v = uv_prime(xyz.x, xyz.y, xyz.z)

        yr = xyz.y / yn
        if yr > (6 / 29) ** 3:
            l = (116 * (yr ** (1 / 3))) - 16
        else:
            l = (903.3 * yr)

        uu = 13 * l * (u - un)
        vv = 13 * l * (v - vn)

        return ColorLUV(l=round(l, 4), u=round(uu, 4), v=round(vv, 4))

    @staticmethod
    def _relative_luminance(r: int, g: int, b: int) -> float:
        rf = ColorService._srgb_to_linear(r / 255.0)
        gf = ColorService._srgb_to_linear(g / 255.0)
        bf = ColorService._srgb_to_linear(b / 255.0)
        return 0.2126 * rf + 0.7152 * gf + 0.0722 * bf

    @staticmethod
    def _contrast_ratio(l1: float, l2: float) -> float:
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def _contrast_info(r: int, g: int, b: int) -> ColorContrast:
        lum = ColorService._relative_luminance(r, g, b)
        white_lum = 1.0
        black_lum = 0.0

        on_white = ColorService._contrast_ratio(lum, white_lum)
        on_black = ColorService._contrast_ratio(lum, black_lum)

        return ColorContrast(
            on_white=round(on_white, 3),
            on_black=round(on_black, 3),
            aa_on_white_normal_text=on_white >= 4.5,
            aa_on_black_normal_text=on_black >= 4.5,
            aaa_on_white_normal_text=on_white >= 7.0,
            aaa_on_black_normal_text=on_black >= 7.0,
        )

    @staticmethod
    def _clamp_u8(v: float) -> int:
        return max(0, min(255, int(round(v))))

    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        return f"{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def _apply_matrix(r: int, g: int, b: int, matrix: tuple[tuple[float, float, float], ...]) -> tuple[int, int, int]:
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        r2 = matrix[0][0] * rf + matrix[0][1] * gf + matrix[0][2] * bf
        g2 = matrix[1][0] * rf + matrix[1][1] * gf + matrix[1][2] * bf
        b2 = matrix[2][0] * rf + matrix[2][1] * gf + matrix[2][2] * bf
        return (
            ColorService._clamp_u8(r2 * 255),
            ColorService._clamp_u8(g2 * 255),
            ColorService._clamp_u8(b2 * 255),
        )

    @staticmethod
    def _color_blindness_previews(r: int, g: int, b: int) -> ColorBlindnessPreview:
        protanopia_m = (
            (0.56667, 0.43333, 0.0),
            (0.55833, 0.44167, 0.0),
            (0.0, 0.24167, 0.75833),
        )
        deuteranopia_m = (
            (0.625, 0.375, 0.0),
            (0.7, 0.3, 0.0),
            (0.0, 0.3, 0.7),
        )
        tritanopia_m = (
            (0.95, 0.05, 0.0),
            (0.0, 0.43333, 0.56667),
            (0.0, 0.475, 0.525),
        )

        p = ColorService._apply_matrix(r, g, b, protanopia_m)
        d = ColorService._apply_matrix(r, g, b, deuteranopia_m)
        t = ColorService._apply_matrix(r, g, b, tritanopia_m)

        return ColorBlindnessPreview(
            protanopia=ColorBlindVariant(
                rgb=ColorRGB(r=p[0], g=p[1], b=p[2]),
                hex=ColorService._rgb_to_hex(*p),
            ),
            deuteranopia=ColorBlindVariant(
                rgb=ColorRGB(r=d[0], g=d[1], b=d[2]),
                hex=ColorService._rgb_to_hex(*d),
            ),
            tritanopia=ColorBlindVariant(
                rgb=ColorRGB(r=t[0], g=t[1], b=t[2]),
                hex=ColorService._rgb_to_hex(*t),
            ),
        )

    @staticmethod
    def _closest_name(_hex_value: str, r: int, g: int, b: int) -> str | None:
        if not _CN_AVAILABLE:
            return None
        try:
            return _cn.find(r, g, b)
        except Exception:
            return None

    @staticmethod
    def _bast_score(r: int, g: int, b: int) -> float:
        """How 'bastard' (undescribable) a colour is, 0–100.

        Three additive components, all derived from HSV:

        • vivid-between  — saturated colour whose hue falls between the six
          primary/secondary archetypes (red/yellow/green/cyan/blue/magenta).
          Example: orange, chartreuse, violet. Dampened at extreme lightness
          because "dark orange" and "bright orange" are still nameable.

        • muddy  — medium saturation AND medium lightness: the zone that
          produces browns, olives, mauves, khakis, dusty everythings.

        • achromatic ambiguity  — near-grey at mid-lightness; pure black and
          pure white score 0 because they have unambiguous names.

        Calibration: the analytical maximum of the weighted sum (≈ 0.702) is
        used as the normalisation divisor so the scale fills 0–100.
        """
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
        h_deg = h * 360.0

        # Distance to nearest primary/secondary hue archetype, [0, 1]
        # 0 = on an archetype, 1 = midpoint between two (e.g. h=30° for orange)
        archetypes = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]
        hue_dist = min(min(abs(h_deg - a), 360.0 - abs(h_deg - a)) for a in archetypes)
        hue_between = min(hue_dist / 30.0, 1.0)

        # Mid-zone functions (each peaks at 0.5, zero at the extremes)
        val_mid  = 1.0 - abs(2.0 * v - 1.0)   # 1 at v=0.5, 0 at v=0 or v=1
        sat_dome = 4.0 * s * (1.0 - s)         # 1 at s=0.5, 0 at s=0 or s=1

        # Component 1: vivid colour with ambiguous hue, dampened at lightness extremes
        vivid_between = s * hue_between * (1.0 - 0.5 * abs(2.0 * v - 1.0))

        # Component 2: the muddy middle — medium sat + medium value
        muddy = sat_dome * val_mid

        # Component 3: achromatic ambiguity — near-grey at mid-lightness
        achromatic = (1.0 - s) ** 2 * val_mid

        # Extra penalty: far from all 8 pure-colour anchors (white, black, RGBYCM)
        min_pure_dist = min(
            math.sqrt((r - rp) ** 2 + (g - gp) ** 2 + (b - bp) ** 2)
            for rp, gp, bp in ColorService._PURE_RGB
        )
        pure_dist_norm = min_pure_dist / 441.67  # max RGB Euclidean distance

        raw = (
            0.42 * vivid_between
            + 0.33 * muddy
            + 0.15 * pure_dist_norm
            + 0.10 * achromatic
        )

        # Calibrated normalisation: max raw ≈ 0.6391 (numerically verified at rgb≈(48,88,128))
        return max(0.0, min(100.0, raw / 0.6391 * 100.0))
