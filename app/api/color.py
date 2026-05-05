from fastapi import APIRouter, HTTPException, Request, status
from starlette.datastructures import UploadFile

from app.controllers.color import ColorController
from app.schemas.color import ColorContrastCheckResponse, ColorInfoResponse, PaletteGenerateRequest, PaletteGenerateResponse

router = APIRouter()
IMAGE_PALETTE_MAX_BYTES = 10 * 1024 * 1024
IMAGE_PALETTE_MAX_PART_BYTES = IMAGE_PALETTE_MAX_BYTES + (256 * 1024)


@router.post("/palette/generate", response_model=PaletteGenerateResponse, status_code=200)
def generate_palette_handler(request: PaletteGenerateRequest):
    return ColorController.generate_palette_control(request)


@router.post("/color/palette/from-image", response_model=PaletteGenerateResponse, status_code=200)
async def generate_palette_from_image_handler(
    request: Request,
):
    form = await request.form(
        max_files=4,
        max_fields=32,
        max_part_size=IMAGE_PALETTE_MAX_PART_BYTES,
    )

    image = form.get("image")
    if not isinstance(image, UploadFile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is required.",
        )

    raw_count = form.get("count", 5)
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="count must be between 1 and 8.",
        )
    if count < 1 or count > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="count must be between 1 and 8.",
        )

    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image.",
        )
    image_bytes = await image.read()
    if len(image_bytes) > IMAGE_PALETTE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large. Maximum size is 10MB.",
        )
    return ColorController.generate_palette_from_image_control(image_bytes=image_bytes, count=count)


@router.get("/color/{hex}/contrast/{hex2}", response_model=ColorContrastCheckResponse, status_code=200)
def get_contrast_check_handler(hex: str, hex2: str):
    return ColorController.get_contrast_check_control(hex, hex2)


@router.get("/color/{hex}", response_model=ColorInfoResponse, status_code=200)
def get_color_info_handler(hex: str):
    return ColorController.get_color_info_control(hex)
