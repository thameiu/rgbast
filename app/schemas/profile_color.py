import re
from typing import Annotated

from pydantic import BeforeValidator


def validate_profile_color(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError("Profile color must be a six-digit hex code.")
    return value.upper()


ProfileColor = Annotated[str, BeforeValidator(validate_profile_color)]
