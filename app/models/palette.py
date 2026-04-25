from sqlalchemy import BigInteger
from sqlmodel import TIMESTAMP, Field, SQLModel, text
from datetime import datetime


class Palette(SQLModel, table=True):
    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    user_id: int = Field(
        index=True, default=None, foreign_key="user.id",
        nullable=False, sa_type=BigInteger(),
    )
    title: str = Field(index=True, default=None, nullable=False)
    description: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )


class Palette_Branch(SQLModel, table=True):
    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    palette_id: int = Field(
        index=True, default=None, foreign_key="palette.id",
        nullable=False, sa_type=BigInteger(),
    )
    title: str = Field(max_length=100, nullable=False)
    merged_at: datetime | None = Field(
        sa_type=TIMESTAMP(timezone=True),
        default=None,
        nullable=True,
    )
    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )


class Palette_Snapshot(SQLModel, table=True):
    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    palette_id: int = Field(
        index=True, default=None, foreign_key="palette.id",
        nullable=False, sa_type=BigInteger(),
    )
    parent_snapshot_id: int | None = Field(
        default=None, foreign_key="palette_snapshot.id",
        nullable=True, sa_type=BigInteger(),
    )
    branch_id: int | None = Field(
        default=None, foreign_key="palette_branch.id",
        sa_type=BigInteger(),
    )
    comment: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )


class Palette_Color(SQLModel, table=True):
    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    palette_snapshot_id: int = Field(
        index=True, default=None, foreign_key="palette_snapshot.id",
        nullable=False, sa_type=BigInteger(),
    )

    hex: str = Field(default=None, max_length=6, nullable=False)
    label: str | None = Field(default=None, nullable=True)
    position_key: str = Field(index=True, nullable=False)


class Palette_Change(SQLModel, table=True):
    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    previous_snapshot_id: int = Field(
        index=True, default=None, foreign_key="palette_snapshot.id",
        nullable=False, sa_type=BigInteger(),
    )
    new_snapshot_id: int = Field(
        index=True, default=None, foreign_key="palette_snapshot.id",
        nullable=False, sa_type=BigInteger(),
    )

    previous_color_id: int | None = Field(
        default=None, foreign_key="palette_color.id",
        nullable=True, sa_type=BigInteger(),
    )

    new_color_id: int | None = Field(
        default=None, foreign_key="palette_color.id",
        nullable=True, sa_type=BigInteger(),
    )
