from fastapi import APIRouter, Depends
from app.core.database import SessionDep
from app.middlewares.auth import verify_token
from app.controllers.palette import PaletteController
from app.schemas.palette import (
    PaletteBranchMergeResponse,
    PaletteCreate,
    PaletteCreateResponse,
    PaletteHistoryGraphResponse,
    PaletteSnapshotSave,
    PaletteSnapshotSaveResponse,
)
from app.models.user import User

router = APIRouter()


@router.post("/palettes", response_model=PaletteCreateResponse, status_code=201)
def create_palette_handler(
    paletteSchema: PaletteCreate,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return PaletteController.create_palette_control(
        paletteSchema, current_user.id, session
    )


@router.put(
    "/palettes/{palette_id}/snapshots",
    response_model=PaletteSnapshotSaveResponse,
    status_code=201,
)
def save_palette_snapshot_handler(
    palette_id: int,
    saveSchema: PaletteSnapshotSave,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return PaletteController.save_palette_control(
        palette_id, saveSchema, current_user.id, session
    )


@router.get(
    "/palettes/{palette_id}/history",
    response_model=PaletteHistoryGraphResponse,
    status_code=200,
)
def get_palette_history_handler(palette_id: int, session: SessionDep):
    return PaletteController.get_palette_history_control(palette_id, session)


@router.post(
    "/palettes/{palette_id}/branches/{branch_id}/merge",
    response_model=PaletteBranchMergeResponse,
    status_code=201,
)
def merge_branch_handler(
    palette_id: int,
    branch_id: int,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return PaletteController.merge_branch_control(
        palette_id, branch_id, current_user.id, session
    )
