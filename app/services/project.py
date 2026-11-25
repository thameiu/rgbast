import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy import or_, func
from sqlmodel import delete, select

from app.models.project import PERMISSIONS, Project, ProjectAccess, ProjectInvitation
from app.models.user import User
from app.models.palette import Palette
from app.models.color_bookmark import Color_Bookmark
from app.services.colleague import ColleagueService
from app.services.mail import MailService


class ProjectService:
    @staticmethod
    def leave(project_id, user_id, session):
        project = session.exec(select(Project).where(Project.id == project_id).with_for_update()).first()
        if not project:
            raise HTTPException(404, "Project not found.")
        if project.creator_id == user_id:
            raise HTTPException(403, "The project creator cannot leave the project.")
        access = session.exec(select(ProjectAccess.id).where(
            ProjectAccess.project_id == project_id, ProjectAccess.user_id == user_id,
        )).first()
        if access is None:
            raise HTTPException(404, "Project member not found.")
        session.exec(delete(ProjectAccess).where(ProjectAccess.project_id == project_id, ProjectAccess.user_id == user_id))
        session.exec(delete(ProjectInvitation).where(ProjectInvitation.project_id == project_id, ProjectInvitation.user_id == user_id))
        session.commit()

    @staticmethod
    def permissions(project, user_id, session):
        if project.creator_id == user_id:
            return list(PERMISSIONS)
        return list(session.exec(select(ProjectAccess.permission).where(
            ProjectAccess.project_id == project.id, ProjectAccess.user_id == user_id,
        )).all()) if user_id else []

    @staticmethod
    def require(project_id, user_id, session, permission="read", lock=False):
        query = select(Project).where(Project.id == project_id)
        if lock:
            query = query.with_for_update()
        project = session.exec(query).first()
        if not project:
            raise HTTPException(404, "Project not found.")
        permissions = ProjectService.permissions(project, user_id, session)
        if project.private and "read" not in permissions:
            raise HTTPException(404, "Project not found.")
        if permission != "read" and permission not in permissions:
            raise HTTPException(403, "Missing project permission.")
        return project

    @staticmethod
    def serialize(project, user_id, session):
        creator = session.get(User, project.creator_id)
        return {**project.model_dump(), "creator_username": creator.username,
                "permissions": ProjectService.permissions(project, user_id, session)}

    @staticmethod
    def create(data, user_id, session):
        slug = data.slug
        if not slug:
            ascii_title = unicodedata.normalize("NFKD", data.title).encode("ascii", "ignore").decode()
            base = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")[:45].rstrip("-") or "project"
            slug, number = base, 1
            while session.exec(select(Project.id).where(Project.creator_id == user_id, Project.slug == slug)).first():
                number += 1
                slug = f"{base}-{number}"
        elif session.exec(select(Project.id).where(Project.creator_id == user_id, Project.slug == slug)).first():
            raise HTTPException(409, "Project slug already exists.")
        project = Project(**data.model_dump(exclude={"slug"}), slug=slug, creator_id=user_id)
        session.add(project)
        session.commit()
        session.refresh(project)
        return ProjectService.serialize(project, user_id, session)

    @staticmethod
    def list_visible(session, viewer_id=None, owner_id=None, mine=False):
        access = select(ProjectAccess.project_id).where(ProjectAccess.user_id == viewer_id,
                                                       ProjectAccess.permission == "read")
        palette_count = select(func.count(Palette.id)).where(Palette.project_id == Project.id).correlate(Project).scalar_subquery()
        bookmark_count = select(func.count(Color_Bookmark.id)).where(Color_Bookmark.project_id == Project.id).correlate(Project).scalar_subquery()
        member_count = select(func.count(func.distinct(ProjectAccess.user_id))).where(
            ProjectAccess.project_id == Project.id, ProjectAccess.user_id != Project.creator_id,
        ).correlate(Project).scalar_subquery()
        query = select(Project, User.username, palette_count, bookmark_count, member_count).join(User, User.id == Project.creator_id)
        if owner_id is not None:
            query = query.where(Project.creator_id == owner_id)
        if mine:
            query = query.where(or_(Project.creator_id == viewer_id, Project.id.in_(access)))
        else:
            query = query.where(or_(Project.private.is_(False), Project.creator_id == viewer_id,
                                    Project.id.in_(access)))
        rows = session.exec(query.order_by(Project.created_at.desc(), Project.id.desc())).all()
        permissions = {}
        if viewer_id and rows:
            for project_id, permission in session.exec(select(ProjectAccess.project_id, ProjectAccess.permission).where(
                ProjectAccess.user_id == viewer_id, ProjectAccess.project_id.in_([row[0].id for row in rows]),
            )).all():
                permissions.setdefault(project_id, []).append(permission)
        return [{**p.model_dump(), "creator_username": username,
                 "permissions": list(PERMISSIONS) if p.creator_id == viewer_id else permissions.get(p.id, []),
                 "palette_count": palettes, "bookmark_count": bookmarks, "member_count": members + 1}
                for p, username, palettes, bookmarks, members in rows]

    @staticmethod
    def members(project_id, user_id, session):
        project = ProjectService.require(project_id, user_id, session)
        access = session.exec(select(ProjectAccess.user_id, ProjectAccess.permission).where(ProjectAccess.project_id == project_id)).all()
        permissions = {}
        for member_id, permission in access:
            permissions.setdefault(member_id, []).append(permission)
        ids = set(permissions)
        ids.add(project.creator_id)
        users = session.exec(select(User).where(User.id.in_(ids)).order_by(User.username)).all()
        result = [{**ColleagueService._summarize_user(user),
                 "creator": user.id == project.creator_id,
                 "pending": False,
                 "permissions": list(PERMISSIONS) if user.id == project.creator_id else permissions.get(user.id, [])} for user in users]
        if "manage_access" in ProjectService.permissions(project, user_id, session):
            invited = session.exec(select(User).join(ProjectInvitation, ProjectInvitation.user_id == User.id).where(
                ProjectInvitation.project_id == project_id, User.id.not_in(ids),
            ).order_by(ProjectInvitation.created_at, User.username)).all()
            result.extend({**ColleagueService._summarize_user(user), "creator": False,
                           "pending": True, "permissions": []} for user in invited)
        return result

    @staticmethod
    def invite(project_id, user_id, data, session):
        project = ProjectService.require(project_id, user_id, session, "manage_access", lock=True)
        target = session.exec(select(User).where(User.username == data.username)).first()
        if not target:
            raise HTTPException(404, "User not found.")
        if target.id == project.creator_id or ProjectService.permissions(project, target.id, session):
            raise HTTPException(409, "User already belongs to this project.")
        existing = session.exec(select(ProjectInvitation).where(ProjectInvitation.project_id == project_id,
                                                                ProjectInvitation.user_id == target.id)).first()
        if existing:
            raise HTTPException(409, "Project invitation already sent.")
        invitation = ProjectInvitation(project_id=project_id, user_id=target.id, inviter_id=user_id,
                                       permissions=data.permissions)
        session.add(invitation)
        session.commit()
        creator = session.get(User, project.creator_id)
        inviter = session.get(User, user_id)
        MailService.project_invitation(target.email, inviter.username, project.title)
        return {"id": invitation.id, "project_id": project_id, "creator_username": creator.username}

    @staticmethod
    def invitations(user_id, session):
        rows = session.exec(select(ProjectInvitation, Project).join(Project).where(
            ProjectInvitation.user_id == user_id)).all()
        return [{"id": inv.id, "project_id": p.id, "title": p.title, "permissions": inv.permissions,
                 "inviter": ColleagueService._summarize_user(session.get(User, inv.inviter_id))}
                for inv, p in rows]

    @staticmethod
    def respond(invitation_id, user_id, accept, session):
        invitation = session.exec(select(ProjectInvitation).where(ProjectInvitation.id == invitation_id,
                                   ProjectInvitation.user_id == user_id).with_for_update()).first()
        if not invitation:
            raise HTTPException(404, "Invitation not found.")
        if accept:
            for permission in sorted(set(invitation.permissions) | {"read"}):
                session.add(ProjectAccess(project_id=invitation.project_id, user_id=user_id, permission=permission))
        session.delete(invitation)
        session.commit()

    @staticmethod
    def set_member(project_id, user_id, data, session):
        project = ProjectService.require(project_id, user_id, session, "manage_access", lock=True)
        target = session.exec(select(User).where(User.username == data.username)).first()
        if not target or target.id == project.creator_id:
            raise HTTPException(400, "Cannot modify the project creator.")
        if not ProjectService.permissions(project, target.id, session):
            raise HTTPException(404, "Project member not found.")
        session.exec(delete(ProjectAccess).where(ProjectAccess.project_id == project_id, ProjectAccess.user_id == target.id))
        for permission in data.permissions:
            session.add(ProjectAccess(project_id=project_id, user_id=target.id, permission=permission))
        session.commit()
