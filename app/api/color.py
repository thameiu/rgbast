from fastapi import APIRouter

from app.controllers.color import ColorController
from app.schemas.color import ColorInfoResponse

router = APIRouter()


@router.get("/color/{hex}", response_model=ColorInfoResponse, status_code=200)
def get_color_info_handler(hex: str):
    return ColorController.get_color_info_control(hex)
