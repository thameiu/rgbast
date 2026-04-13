from sqlmodel import Field, SQLModel


class Palette_Color(SQLModel, table=True):
    id: int = (Field(primary_key=True, nullable=False),)
