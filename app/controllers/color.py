from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.color import ColorInfoResponse
from app.services.color import ColorService


class ColorController:
    @staticmethod
    def get_color_info_control(hex_value: str) -> ColorInfoResponse:
        try:
            return ColorService.get_color_info(hex_value)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )
