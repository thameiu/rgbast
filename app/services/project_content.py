from fastapi import HTTPException
from sqlmodel import delete, select

from app.models.folder import Folder
from app.models.palette import Palette, Palette_Branch, Palette_Snapshot
from app.models.user import User
from app.models.project import Project
from app.services.palette import PaletteService
from app.services.project import ProjectService


class ProjectContentService:
    @staticmethod
    def add_palette(project_id, user_id, data, session):
        from app.schemas.palette import PaletteCreate, PaletteUpdate
        ProjectService.require(project_id, user_id, session, 'add_palettes', lock=True)
        source = None
        if data.source_palette_id is not None:
            source = PaletteService.get_palette(data.source_palette_id, session, user_id)
            if not source:
                raise HTTPException(404, 'Palette not found.')
        if data.mode == 'move':
            if source is None:
                raise HTTPException(400, 'A saved personal palette is required to move it.')
            return ProjectContentService.import_palette(project_id, source.id, user_id,
                PaletteUpdate(title=data.title, folder_id=data.folder_id), session)
        colors = data.palette_colors
        if not colors and source:
            _, colors = PaletteService.get_latest_palette_snapshot(source.id, session)
        if not colors:
            raise HTTPException(422, 'Palette must contain at least one color.')
        palette = PaletteService.create_palette(PaletteCreate(
            project_id=project_id, folder_id=data.folder_id, title=data.title,
            description=data.description, palette_colors=[{'hex': c.hex, 'label': c.label} for c in colors]), user_id, session)
        return palette

    @staticmethod
    def folders(project_id, viewer_id, session):
        ProjectService.require(project_id, viewer_id, session)
        return list(session.exec(select(Folder).where(Folder.project_id == project_id).order_by(Folder.name)).all())

    @staticmethod
    def folder(project_id, folder_id, session):
        if folder_id is None:
            return None
        folder = session.get(Folder, folder_id)
        if not folder or folder.project_id != project_id:
            raise HTTPException(404, "Folder not found in this project.")
        return folder

    @staticmethod
    def unique_folder(project_id, parent_id, name, session, ignore=None):
        query = select(Folder.id).where(Folder.project_id == project_id, Folder.name == name,
                                        Folder.parent_folder_id == parent_id)
        if ignore is not None:
            query = query.where(Folder.id != ignore)
        if session.exec(query).first() is not None:
            raise HTTPException(409, "Folder name already exists in this parent.")

    @staticmethod
    def create_folder(project_id, user_id, data, session):
        ProjectService.require(project_id, user_id, session, "manage_folders", lock=True)
        ProjectContentService.folder(project_id, data.parent_folder_id, session)
        ProjectContentService.unique_folder(project_id, data.parent_folder_id, data.name, session)
        folder = Folder(project_id=project_id, user_id=user_id, name=data.name, parent_folder_id=data.parent_folder_id)
        session.add(folder)
        session.commit()
        session.refresh(folder)
        return folder

    @staticmethod
    def update_folder(project_id, folder_id, user_id, data, session):
        ProjectService.require(project_id, user_id, session, "manage_folders", lock=True)
        folder = ProjectContentService.folder(project_id, folder_id, session)
        parent_id = data.parent_folder_id if "parent_folder_id" in data.model_fields_set else folder.parent_folder_id
        parent = ProjectContentService.folder(project_id, parent_id, session)
        seen = {folder_id}
        while parent:
            if parent.id in seen:
                raise HTTPException(400, "Folder cannot be moved into its own child.")
            seen.add(parent.id)
            parent = ProjectContentService.folder(project_id, parent.parent_folder_id, session)
        name = data.name if data.name is not None else folder.name
        ProjectContentService.unique_folder(project_id, parent_id, name, session, folder.id)
        folder.name, folder.parent_folder_id = name, parent_id
        session.add(folder)
        session.flush()
        for palette in session.exec(select(Palette).where(Palette.project_id == project_id)).all():
            PaletteService._assert_path_length("", PaletteService._get_folder_path(palette.folder_id, session), palette.title, project_id, session)
        session.commit()
        session.refresh(folder)
        return folder

    @staticmethod
    def palettes(project_id, viewer_id, session):
        ProjectService.require(project_id, viewer_id, session)
        rows = session.exec(select(Palette).where(Palette.project_id == project_id).order_by(Palette.created_at.desc(), Palette.id.desc())).all()
        result = []
        for palette in rows:
            snapshot, colors = PaletteService.get_latest_palette_snapshot(palette.id, session)
            result.append({**palette.model_dump(), "owner_username": session.get(User, palette.user_id).username,
                           "folder_path": PaletteService._get_folder_path(palette.folder_id, session),
                           "palette_colors": [{"hex": c.hex, "label": c.label} for c in colors],
                           "last_snapshot_at": snapshot.created_at if snapshot else palette.created_at})
        return result

    @staticmethod
    def history(username, slug, path, viewer_id, session):
        project = session.exec(select(Project).join(User, User.id == Project.creator_id).where(
            User.username == username, Project.slug == slug)).first()
        if not project:
            raise HTTPException(404, "Project not found.")
        ProjectService.require(project.id, viewer_id, session)
        segments = [part for part in path.split('/') if part]
        if not segments:
            raise HTTPException(404, "Palette not found.")
        folder_id = PaletteService._resolve_folder_path(project.creator_id, segments[:-1], session, project.id)
        palette = session.exec(select(Palette).where(Palette.project_id == project.id,
                               Palette.folder_id == folder_id, Palette.title == segments[-1])).first()
        if not palette:
            raise HTTPException(404, "Palette not found.")
        session.info['viewer_id'] = viewer_id
        return PaletteService.get_palette_history(palette, session, session.get(User, palette.user_id).username)

    @staticmethod
    def import_palette(project_id, palette_id, user_id, data, session):
        ProjectService.require(project_id, user_id, session, "add_palettes", lock=True)
        palette = session.get(Palette, palette_id)
        if not palette or palette.project_id is not None or palette.user_id != user_id:
            raise HTTPException(404, "Personal palette not found.")
        folder_id = data.folder_id
        ProjectContentService.folder(project_id, folder_id, session)
        title = data.title or palette.title
        PaletteService._ensure_palette_unique(user_id, folder_id, title, session, project_id=project_id)
        palette.project_id, palette.folder_id, palette.title = project_id, folder_id, title
        PaletteService._assert_path_length("", PaletteService._get_folder_path(folder_id, session), title, project_id, session)
        session.add(palette)
        session.commit()
        session.refresh(palette)
        return palette

    @staticmethod
    def remove_palette(project_id, palette_id, user_id, data, session, strategy="make_public"):
        ProjectService.require(project_id, user_id, session, "remove_palettes", lock=True)
        palette = session.get(Palette, palette_id)
        if not palette or palette.project_id != project_id:
            raise HTTPException(404, "Palette not found in this project.")
        if strategy not in ("make_public", "delete"):
            raise HTTPException(422, "Invalid palette removal strategy.")
        if strategy == "delete":
            if palette.user_id != user_id:
                raise HTTPException(403, "Only the palette creator can delete this palette.")
            ProjectContentService.delete_palette_data(palette, session)
            session.commit()
            return {"palette_id": palette_id, "deleted": True}
        title = data.title or palette.title
        PaletteService._ensure_palette_unique(palette.user_id, None, title, session)
        palette.project_id, palette.folder_id, palette.title = None, None, title
        session.add(palette)
        session.commit()
        session.refresh(palette)
        return palette

    @staticmethod
    def delete_palette_data(palette, session):
        ids = list(session.exec(select(Palette_Snapshot.id).where(Palette_Snapshot.palette_id == palette.id)).all())
        PaletteService._delete_snapshots_and_related(ids, session)
        session.exec(delete(Palette_Branch).where(Palette_Branch.palette_id == palette.id))
        session.delete(palette)

    @staticmethod
    def delete_folder(project_id, folder_id, user_id, strategy, session):
        ProjectService.require(project_id, user_id, session, "manage_folders", lock=True)
        ProjectContentService.folder(project_id, folder_id, session)
        folders = list(session.exec(select(Folder).where(Folder.project_id == project_id)).all())
        ids, ordered = {folder_id}, [folder_id]
        for current in ordered:
            for folder in folders:
                if folder.parent_folder_id == current and folder.id not in ids:
                    ids.add(folder.id)
                    ordered.append(folder.id)
        palettes = list(session.exec(select(Palette).where(Palette.project_id == project_id, Palette.folder_id.in_(ids))).all())
        if strategy == "delete":
            if any(p.user_id != user_id for p in palettes):
                raise HTTPException(403, "Only palette creators can delete palettes. Move them to project root instead.")
            for palette in palettes:
                ProjectContentService.delete_palette_data(palette, session)
        else:
            titles = set()
            for palette in palettes:
                if palette.title in titles:
                    raise HTTPException(409, "Palette name already exists in this folder.")
                titles.add(palette.title)
                PaletteService._ensure_palette_unique(palette.user_id, None, palette.title, session, project_id=project_id)
            for palette in palettes:
                palette.folder_id = None
                session.add(palette)
        session.flush()
        for fid in reversed(ordered):
            session.delete(next(folder for folder in folders if folder.id == fid))
            session.flush()
        session.commit()
        return {"deleted_folder_ids": ordered}

    @staticmethod
    def delete_contents(project_id, session):
        for palette in session.exec(select(Palette).where(Palette.project_id == project_id)).all():
            ProjectContentService.delete_palette_data(palette, session)
        session.flush()
        folders = list(session.exec(select(Folder).where(Folder.project_id == project_id)).all())
        while folders:
            parents = {f.parent_folder_id for f in folders}
            leaves = [f for f in folders if f.id not in parents]
            if not leaves:
                raise HTTPException(400, "Invalid folder hierarchy.")
            for folder in leaves:
                session.delete(folder)
                folders.remove(folder)
            session.flush()
