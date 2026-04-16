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
# Positions are managed using lexicographic ranking (string-based ordering),
# instead of numeric fractional indexing.
# Each color has a 'position_key' (e.g. "a", "am", "b") which determines its order
# when sorted lexicographically (ORDER BY position_key).
# 
# This allows inserting new colors between any two existing ones by generating
# a new key that falls between their keys (e.g. between "a" and "b" → "am"),
# without needing to generate more changes or rebalance positions.
# Despite this, A balance may be necessary when approaching a extreme case, like 100 characters.
# 
# This approach avoids precision issues from numeric division and makes insertions
# stable and scalable, even with many consecutive inserts between the same elements.
class Palette_Color(SQLModel, table=True):
    id: int = Field(primary_key=True, nullable=False)
    palette_snapshot_id: int = Field(
        index=True, default=None, foreign_key="palette_snapshot.id", nullable=False
    )

    # Only stores what comes after the "#".
    hex: str = Field(default=None, max_length=6, nullable=False)
    label: str | None = Field(default=None, nullable=True)
    position_key: str = Field(index=True, nullable=False)


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
