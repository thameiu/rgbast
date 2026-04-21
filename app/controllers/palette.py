from fastapi import HTTPException, status
from pydantic import ValidationError
from app.core.database import SessionDep
from app.schemas.palette import (
    PaletteBranchMergeResponse,
    PaletteCreate,
    PaletteCreateResponse,
    PaletteHistoryGraphResponse,
    PaletteSnapshotSave,
    PaletteSnapshotSaveResponse,
)
from app.services.palette import PaletteService


class PaletteController:
    # Handles the creation of a new palette and returns the formatted response.
    def create_palette_control(
        paletteSchema: PaletteCreate, user_id: int, session: SessionDep
    ) -> PaletteCreateResponse:
        try:
            palette = PaletteService.create_palette(paletteSchema, user_id, session)
            return PaletteCreateResponse(**palette.model_dump())

        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
            )

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )

    # Handles saving a new snapshot to a palette and returns the snapshot details along with diff metrics.
    def save_palette_control(
        palette_id: int,
        saveSchema: PaletteSnapshotSave,
        current_user_id: int,
        session: SessionDep,
    ) -> PaletteSnapshotSaveResponse:
        try:
            new_snapshot, recorded_changes = PaletteService.save_palette(
                palette_id, saveSchema, current_user_id, session
            )

            colors = PaletteService.get_snapshot_state(new_snapshot, session)

            added, deleted, modified = 0, 0, 0
            for c in recorded_changes:
                if c.previous_color_id and c.new_color_id:
                    modified += 1
                elif c.new_color_id:
                    added += 1
                elif c.previous_color_id:
                    deleted += 1

            return PaletteSnapshotSaveResponse(
                palette_id=new_snapshot.palette_id,
                palette_snapshot_id=new_snapshot.id,
                parent_snapshot_id=new_snapshot.parent_snapshot_id,
                branch_id=new_snapshot.branch_id,
                comment=new_snapshot.comment,
                created_at=new_snapshot.created_at,
                palette_colors=[{"hex": c.hex, "label": c.label} for c in colors],
                colors_added=added,
                colors_deleted=deleted,
                colors_modified=modified,
            )
        except PermissionError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

        except ValueError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
            )

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    # Retrieves and formats the full Git-style history graph of a palette, organized by main and branches.
    def get_palette_history_control(
        palette_id: int, session: SessionDep
    ) -> PaletteHistoryGraphResponse:
        try:
            palette = PaletteService.get_palette(palette_id, session)
            if not palette:
                raise HTTPException(status_code=404, detail="Palette not found.")

            history_data = PaletteService.get_palette_history(palette_id, session)

            return PaletteHistoryGraphResponse(**history_data)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    # Merges a branch into the main branch by materializing the latest branch state in main.
    def merge_branch_control(
        palette_id: int,
        branch_id: int,
        current_user_id: int,
        session: SessionDep,
    ) -> PaletteBranchMergeResponse:
        try:
            branch, merged_snapshot, recorded_changes = PaletteService.merge_branch(
                palette_id, branch_id, current_user_id, session
            )
            colors = PaletteService.get_snapshot_state(merged_snapshot, session)

            added, deleted, modified = 0, 0, 0
            for c in recorded_changes:
                if c.previous_color_id and c.new_color_id:
                    modified += 1
                elif c.new_color_id:
                    added += 1
                elif c.previous_color_id:
                    deleted += 1

            return PaletteBranchMergeResponse(
                palette_id=palette_id,
                branch_id=branch.id,
                merged_at=branch.merged_at,
                palette_snapshot_id=merged_snapshot.id,
                parent_snapshot_id=merged_snapshot.parent_snapshot_id,
                comment=merged_snapshot.comment,
                created_at=merged_snapshot.created_at,
                palette_colors=[{"hex": c.hex, "label": c.label} for c in colors],
                colors_added=added,
                colors_deleted=deleted,
                colors_modified=modified,
            )
        except PermissionError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
