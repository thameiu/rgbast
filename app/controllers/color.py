from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.color import ColorContrastCheckResponse, ColorInfoResponse, PaletteGenerateRequest, PaletteGenerateResponse
from app.services.color import ColorService, PaletteGeneratorService


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

    @staticmethod
    def get_contrast_check_control(hex1: str, hex2: str) -> ColorContrastCheckResponse:
        try:
            return ColorService.get_contrast_check(hex1, hex2)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )

    @staticmethod
    def generate_palette_control(request: PaletteGenerateRequest) -> PaletteGenerateResponse:
        try:
            return PaletteGeneratorService.generate(request)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )
