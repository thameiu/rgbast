from decimal import Decimal
from sqlmodel import TIMESTAMP, Field, Numeric, SQLModel, text
from datetime import datetime


# Color palette of an user.
class Palette(SQLModel, table=True):
    id: int = Field(primary_key=True, nullable=False)
    user_id: int = Field(
        index=True, default=None, foreign_key="user.id", nullable=False
    )
    title: str = Field(index=True, default=None, nullable=False)
    description: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )


# Snapshot of a palette, defining a saved state in its history.
# A palette's full history can be browsed by finding the latest snapshot and getting its parent.
class Palette_Snapshot(SQLModel, table=True):
    id: int = Field(primary_key=True, nullable=False)
    palette_id: int = Field(
        index=True, default=None, foreign_key="palette.id", nullable=False
    )
    parent_snapshot_id: int | None = Field(
        default=None, foreign_key="palette_snapshot.id", nullable=True
    )
    comment: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )


# Color in a palette, linked to a snapshot (not the main palette).
# Positions are calculated in thousands (1000 - 2000 - 3000...) in order to make insertions easier,
# by making the inserted color's position the median between the previous and next colors (1000 - 2000 -> 1500).
# But eventually, they might be recalculated if the median becomes too complex (1007.8125 for example).
class Palette_Color(SQLModel, table=True):
    id: int = Field(primary_key=True, nullable=False)
    palette_snapshot_id: int = Field(
        index=True, default=None, foreign_key="palette_snapshot.id", nullable=False
    )

    # Only stores what comes after the "#".
    hex: str = Field(default=None, max_length=6, nullable=False)
    label: str | None = Field(default=None, nullable=True)
    position: Decimal = Field(default=None, sa_type=Numeric(10, 4), nullable=False)


# Change between two palette snapshots.
# Only the changes are stored, to avoid duplicating an entire palette with each save.
# The difference is checked between the two colors.
# The snapshots id are required in case of an addition or deletion of a color,
# as only checking the colors snapshots ids wouldn't be possible, in this case scenario.
# The 1st save of a palette, creating the 1st snapshot, does not generate a change.
class Palette_Change(SQLModel, table=True):
    id: int = Field(primary_key=True, nullable=False)
    previous_snapshot_id: int = Field(
        index=True, default=None, foreign_key="palette_snapshot.id", nullable=False
    )
    new_snapshot_id: int = Field(
        index=True, default=None, foreign_key="palette_snapshot.id", nullable=False
    )

    # Previous color is None if the new color is added.
    previous_color_id: int | None = Field(
        default=None, foreign_key="palette_color.id", nullable=True
    )

    # New color is None if the previous color is deleted.
    new_color_id: int | None = Field(
        default=None, foreign_key="palette_color.id", nullable=True
    )
