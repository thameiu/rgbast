from fastapi import APIRouter, Depends, Query
from app.core.database import SessionDep
from app.middlewares.auth import verify_token
from app.controllers.palette import PaletteController
from app.schemas.palette import (
    PaletteBranchDeleteResponse,
    PaletteByUsernameResponse,
    PaletteBranchMergeResponse,
    PaletteBranchRevertResponse,
    PaletteCreate,
    PaletteCreateResponse,
    PaletteDeleteResponse,
    PaletteHistoryGraphResponse,
    PaletteMainRevertResponse,
    PaletteSnapshotSave,
    PaletteSnapshotSaveResponse,
    PaletteUpdate,
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


@router.get(
    "/users/{username}/palettes",
    response_model=PaletteByUsernameResponse,
    status_code=200,
)
def get_palettes_by_username_handler(username: str, session: SessionDep):
    return PaletteController.get_palettes_by_username_control(username, session)


@router.get(
    "/users/{username}/palettes/history",
    response_model=PaletteHistoryGraphResponse,
    status_code=200,
)
def get_palette_history_by_path_handler(
    username: str,
    session: SessionDep,
    path: str = Query(..., description="folder/subfolder/palette"),
):
    return PaletteController.get_palette_history_by_path_control(username, path, session)


@router.put(
    "/palettes/{palette_id}",
    response_model=PaletteCreateResponse,
    status_code=200,
)
def update_palette_handler(
    palette_id: int,
    updateSchema: PaletteUpdate,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return PaletteController.update_palette_control(
        palette_id, updateSchema, current_user.id, session
    )


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


@router.delete(
    "/palettes/{palette_id}",
    response_model=PaletteDeleteResponse,
    status_code=200,
)
def delete_palette_handler(
    palette_id: int,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return PaletteController.delete_palette_control(palette_id, current_user.id, session)


@router.delete(
    "/palettes/{palette_id}/branches/{branch_id}",
    response_model=PaletteBranchDeleteResponse,
    status_code=200,
)
def delete_branch_handler(
    palette_id: int,
    branch_id: int,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return PaletteController.delete_branch_control(
        palette_id, branch_id, current_user.id, session
    )


@router.post(
    "/palettes/{palette_id}/main/revert/{snapshot_id}",
    response_model=PaletteMainRevertResponse,
    status_code=200,
)
def revert_main_handler(
    palette_id: int,
    snapshot_id: int,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return PaletteController.revert_main_control(
        palette_id, snapshot_id, current_user.id, session
    )


@router.post(
    "/palettes/{palette_id}/branches/{branch_id}/revert/{snapshot_id}",
    response_model=PaletteBranchRevertResponse,
    status_code=200,
)
def revert_branch_handler(
    palette_id: int,
    branch_id: int,
    snapshot_id: int,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return PaletteController.revert_branch_control(
        palette_id, branch_id, snapshot_id, current_user.id, session
    )
