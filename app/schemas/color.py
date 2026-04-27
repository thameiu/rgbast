from sqlmodel import SQLModel, Field
from pydantic import field_validator

HARMONY_MODES = {"random", "analogous", "complementary", "triadic", "split_complementary", "tetradic"}


class ColorRGB(SQLModel):
    r: int
    g: int
    b: int


class ColorHSL(SQLModel):
    h: float
    s: float
    l: float


class ColorCMYK(SQLModel):
    c: float
    m: float
    y: float
    k: float


class ColorHSB(SQLModel):
    h: float
    s: float
    b: float


class ColorLAB(SQLModel):
    l: float
    a: float
    b: float


class ColorXYZ(SQLModel):
    x: float
    y: float
    z: float


class ColorLCH(SQLModel):
    l: float
    c: float
    h: float


class ColorLUV(SQLModel):
    l: float
    u: float
    v: float


class ColorHWB(SQLModel):
    h: float
    w: float
    b: float


class ColorContrast(SQLModel):
    on_white: float
    on_black: float
    aa_on_white_normal_text: bool
    aa_on_black_normal_text: bool
    aaa_on_white_normal_text: bool
    aaa_on_black_normal_text: bool


class ColorBlindVariant(SQLModel):
    rgb: ColorRGB
    hex: str


class ColorBlindnessPreview(SQLModel):
    protanopia: ColorBlindVariant
    deuteranopia: ColorBlindVariant
    tritanopia: ColorBlindVariant


class ColorAccessibility(SQLModel):
    color_blindness: ColorBlindnessPreview
    contrast: ColorContrast


class ColorContrastCheckResponse(SQLModel):
    hex1: str
    hex2: str
    ratio: float
    aa_normal: bool
    aa_large: bool
    aaa_normal: bool
    aaa_large: bool


class ColorInfoResponse(SQLModel):
    input_hex: str
    normalized_hex: str
    closest_name: str | None
    rgb: ColorRGB
    hsl: ColorHSL
    cmyk: ColorCMYK
    hsb: ColorHSB
    lab: ColorLAB
    xyz: ColorXYZ
    lch: ColorLCH
    luv: ColorLUV
    hwb: ColorHWB
    accessibility: ColorAccessibility
    bast_score: float
    label_is_approximate: bool


class PaletteGenerateRequest(SQLModel):
    count: int = Field(default=5, ge=2, le=8)
    base_colors: list[str] = Field(default_factory=list)
    contrast: int = Field(default=5, ge=1, le=10)
    include_shades: bool = True
    harmony: str = "random"

    @field_validator("base_colors")
    @classmethod
    def validate_base_colors(cls, v: list[str]) -> list[str]:
        return v[:3]

    @field_validator("harmony")
    @classmethod
    def validate_harmony(cls, v: str) -> str:
        if v not in HARMONY_MODES:
            raise ValueError(f"harmony must be one of: {', '.join(sorted(HARMONY_MODES))}")
        return v


class GeneratedColor(SQLModel):
    hex: str


class PaletteGenerateResponse(SQLModel):
    colors: list[GeneratedColor]
