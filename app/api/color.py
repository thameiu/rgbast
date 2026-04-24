from fastapi import APIRouter

from app.controllers.color import ColorController
from app.schemas.color import ColorContrastCheckResponse, ColorInfoResponse

router = APIRouter()


@router.get("/color/{hex}/contrast/{hex2}", response_model=ColorContrastCheckResponse, status_code=200)
def get_contrast_check_handler(hex: str, hex2: str):
    return ColorController.get_contrast_check_control(hex, hex2)


@router.get("/color/{hex}", response_model=ColorInfoResponse, status_code=200)
def get_color_info_handler(hex: str):
    return ColorController.get_color_info_control(hex)
