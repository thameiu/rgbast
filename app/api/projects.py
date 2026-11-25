from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import delete, select

from app.core.database import SessionDep
from app.middlewares.auth import optional_user, verify_token
from app.models.project import Project, ProjectAccess, ProjectInvitation
from app.models.color_bookmark import Color_Bookmark
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectDelete, ProjectMemberInput, ProjectUpdate
from app.schemas.project import ProjectPaletteAdd
from app.services.project import ProjectService as Service
from app.services.project_content import ProjectContentService as Content
from app.services.palette import PaletteService
from app.schemas.palette import PaletteCreate, PaletteUpdate, PaletteHistoryGraphResponse
from app.schemas.folder import FolderCreate, FolderUpdate
from typing import Literal

router = APIRouter()


@router.get("/projects/me")
def mine(session: SessionDep, user=Depends(verify_token)):
    return Service.list_visible(session, user.id, mine=True)


@router.get("/projects/invitations")
def invitations(session: SessionDep, user=Depends(verify_token)):
    return Service.invitations(user.id, session)


@router.post("/projects/invitations/{invitation_id}/accept", status_code=204)
def accept_invitation(invitation_id: int, session: SessionDep, user=Depends(verify_token)):
    Service.respond(invitation_id, user.id, True, session)


@router.delete("/projects/invitations/{invitation_id}", status_code=204)
def decline_invitation(invitation_id: int, session: SessionDep, user=Depends(verify_token)):
    Service.respond(invitation_id, user.id, False, session)


@router.get("/users/{username}/projects")
def by_user(username: str, session: SessionDep, user=Depends(optional_user)):
    owner = session.exec(select(User).where(User.username == username)).first()
    if not owner:
        raise HTTPException(404, "User not found.")
    return Service.list_visible(session, user.id if user else None, owner.id)


@router.post("/projects", status_code=201)
def create(data: ProjectCreate, session: SessionDep, user=Depends(verify_token)):
    return Service.create(data, user.id, session)


@router.get("/projects/by-path/{username}/{slug}")
def by_path(username: str, slug: str, session: SessionDep, user=Depends(optional_user)):
    project = session.exec(select(Project).join(User, User.id == Project.creator_id).where(
        User.username == username, Project.slug == slug)).first()
    if not project:
        raise HTTPException(404, "Project not found.")
    return get(project.id, session, user)


@router.get("/projects/{project_id}")
def get(project_id: int, session: SessionDep, user=Depends(optional_user)):
    return Service.serialize(Service.require(project_id, user.id if user else None, session),
                             user.id if user else None, session)


@router.put("/projects/{project_id}")
def update(project_id: int, data: ProjectUpdate, session: SessionDep, user=Depends(verify_token)):
    project = Service.require(project_id, user.id, session, "edit_project", lock=True)
    slug = data.slug or project.slug
    if session.exec(select(Project.id).where(Project.creator_id == project.creator_id,
                                             Project.slug == slug, Project.id != project.id)).first():
        raise HTTPException(409, "Project slug already exists.")
    for key, value in data.model_dump(exclude={"slug"}).items():
        setattr(project, key, value)
    project.slug = slug
    session.add(project)
    session.commit()
    return Service.serialize(project, user.id, session)


@router.delete("/projects/{project_id}", status_code=204)
def remove(project_id: int, data: ProjectDelete, session: SessionDep, user=Depends(verify_token)):
    project = Service.require(project_id, user.id, session, lock=True)
    if project.creator_id != user.id:
        raise HTTPException(403, "Only the creator can delete this project.")
    if data.confirm_title != project.title:
        raise HTTPException(400, "Project title confirmation does not match.")
    Content.delete_contents(project_id, session)
    session.exec(delete(Color_Bookmark).where(Color_Bookmark.project_id == project_id))
    session.exec(delete(ProjectAccess).where(ProjectAccess.project_id == project_id))
    session.exec(delete(ProjectInvitation).where(ProjectInvitation.project_id == project_id))
    session.delete(project)
    session.commit()


def content_result(fn, *args):
    try:
        return fn(*args)
    except (ValueError, PermissionError) as error:
        raise HTTPException(403 if isinstance(error, PermissionError) else 400, str(error))


@router.post('/projects/{project_id}/add-palette', status_code=201)
def add_palette_to_project(project_id: int, data: ProjectPaletteAdd, session: SessionDep, user=Depends(verify_token)):
    palette = content_result(Content.add_palette, project_id, user.id, data, session)
    return {**palette.model_dump(), 'folder_path': PaletteService._get_folder_path(palette.folder_id, session)}


@router.get("/projects/{project_id}/folders")
def project_folders(project_id: int, session: SessionDep, user=Depends(optional_user)):
    return Content.folders(project_id, user.id if user else None, session)


@router.post("/projects/{project_id}/folders", status_code=201)
def create_project_folder(project_id: int, data: FolderCreate, session: SessionDep, user=Depends(verify_token)):
    return Content.create_folder(project_id, user.id, data, session)


@router.put("/projects/{project_id}/folders/{folder_id}")
def update_project_folder(project_id: int, folder_id: int, data: FolderUpdate, session: SessionDep, user=Depends(verify_token)):
    return content_result(Content.update_folder, project_id, folder_id, user.id, data, session)


@router.delete("/projects/{project_id}/folders/{folder_id}")
def delete_project_folder(project_id: int, folder_id: int, session: SessionDep,
                          palette_strategy: Literal['move_root', 'delete'] = 'move_root', user=Depends(verify_token)):
    return content_result(Content.delete_folder, project_id, folder_id, user.id, palette_strategy, session)


@router.get("/projects/{project_id}/palettes")
def project_palettes(project_id: int, session: SessionDep, user=Depends(optional_user)):
    return Content.palettes(project_id, user.id if user else None, session)


@router.post("/projects/{project_id}/palettes", status_code=201)
def create_project_palette(project_id: int, data: PaletteCreate, session: SessionDep, user=Depends(verify_token)):
    data.project_id = project_id
    palette = content_result(PaletteService.create_palette, data, user.id, session)
    return {**palette.model_dump(), 'folder_path': PaletteService._get_folder_path(palette.folder_id, session)}


@router.post("/projects/{project_id}/palettes/{palette_id}")
def import_project_palette(project_id: int, palette_id: int, data: PaletteUpdate, session: SessionDep, user=Depends(verify_token)):
    return content_result(Content.import_palette, project_id, palette_id, user.id, data, session)


@router.delete("/projects/{project_id}/palettes/{palette_id}")
def remove_project_palette(project_id: int, palette_id: int, session: SessionDep, user=Depends(verify_token),
                           strategy: Literal['make_public', 'delete'] = 'make_public'):
    return content_result(Content.remove_palette, project_id, palette_id, user.id, PaletteUpdate(), session, strategy)


@router.get("/projects/by-path/{username}/{slug}/palette-history", response_model=PaletteHistoryGraphResponse)
def project_palette_history(username: str, slug: str, path: str, session: SessionDep, user=Depends(optional_user)):
    return content_result(Content.history, username, slug, path, user.id if user else None, session)


@router.get("/projects/{project_id}/members")
def members(project_id: int, session: SessionDep, user=Depends(optional_user)):
    return Service.members(project_id, user.id if user else None, session)


@router.post("/projects/{project_id}/leave", status_code=204)
def leave_project(project_id: int, session: SessionDep, user=Depends(verify_token)):
    Service.leave(project_id, user.id, session)


@router.post("/projects/{project_id}/invitations", status_code=201)
def invite(project_id: int, data: ProjectMemberInput, session: SessionDep, user=Depends(verify_token)):
    return Service.invite(project_id, user.id, data, session)


@router.put("/projects/{project_id}/members")
def change_member(project_id: int, data: ProjectMemberInput, session: SessionDep, user=Depends(verify_token)):
    Service.set_member(project_id, user.id, data, session)
    return Service.members(project_id, user.id, session)


@router.delete("/projects/{project_id}/members/{username}", status_code=204)
def remove_member(project_id: int, username: str, session: SessionDep, user=Depends(verify_token)):
    project = Service.require(project_id, user.id, session, "manage_access", lock=True)
    target = session.exec(select(User).where(User.username == username)).first()
    if not target or target.id == project.creator_id:
        raise HTTPException(400, "Cannot remove the project creator.")
    session.exec(delete(ProjectAccess).where(ProjectAccess.project_id == project_id, ProjectAccess.user_id == target.id))
    session.exec(delete(ProjectInvitation).where(ProjectInvitation.project_id == project_id, ProjectInvitation.user_id == target.id))
    session.commit()
