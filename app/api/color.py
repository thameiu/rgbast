from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status

from app.controllers.color import ColorController
from app.schemas.color import ColorContrastCheckResponse, ColorInfoResponse, PaletteGenerateRequest, PaletteGenerateResponse

router = APIRouter()


@router.post("/palette/generate", response_model=PaletteGenerateResponse, status_code=200)
def generate_palette_handler(request: PaletteGenerateRequest):
    return ColorController.generate_palette_control(request)


@router.post("/color/palette/from-image", response_model=PaletteGenerateResponse, status_code=200)
async def generate_palette_from_image_handler(
    image: UploadFile = File(...),
    count: int = Form(5, ge=1, le=8),
):
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image.",
        )
    image_bytes = await image.read()
    return ColorController.generate_palette_from_image_control(image_bytes=image_bytes, count=count)


@router.get("/color/{hex}/contrast/{hex2}", response_model=ColorContrastCheckResponse, status_code=200)
def get_contrast_check_handler(hex: str, hex2: str):
    return ColorController.get_contrast_check_control(hex, hex2)


@router.get("/color/{hex}", response_model=ColorInfoResponse, status_code=200)
def get_color_info_handler(hex: str):
    return ColorController.get_color_info_control(hex)
