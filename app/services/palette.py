from datetime import timezone, datetime
from collections import defaultdict
from sqlmodel import delete, desc, select
import difflib
import re

from app.core.database import SessionDep
from app.models.folder import Folder
from app.models.palette import (
    Palette,
    Palette_Branch,
    Palette_Change,
    Palette_Color,
    Palette_Snapshot,
)
from app.models.user import User
from app.schemas.palette import PaletteCreate, PaletteSnapshotSave, PaletteUpdate
from app.utils.lexicographic_ranker import LexicographicRanker


class PaletteService:
    @staticmethod
    def _assert_palette_name(title: str) -> None:
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, title):
            raise ValueError("Title is invalid.")

    @staticmethod
    def _get_user(user_id: int, session: SessionDep) -> User:
        user = session.get(User, user_id)
        if not user:
            raise ValueError("User not found.")
        return user

    @staticmethod
    def _assert_folder_owner(folder_id: int | None, user_id: int, session: SessionDep) -> Folder | None:
        if folder_id is None:
            return None
        folder = session.get(Folder, folder_id)
        if not folder:
            raise ValueError("Folder not found.")
        if folder.user_id != user_id:
            raise PermissionError("You do not have permission to use this folder.")
        return folder

    @staticmethod
    def _get_folder_path(folder_id: int | None, session: SessionDep) -> list[str]:
        if folder_id is None:
            return []
        names: list[str] = []
        seen: set[int] = set()
        current_id = folder_id
        while current_id is not None:
            if current_id in seen:
                raise ValueError("Folder hierarchy is invalid.")
            seen.add(current_id)
            folder = session.get(Folder, current_id)
            if not folder:
                raise ValueError("Folder not found.")
            names.append(folder.name)
            current_id = folder.parent_folder_id
        names.reverse()
        return names

    @staticmethod
    def _resolve_folder_path(user_id: int, folder_names: list[str], session: SessionDep) -> int | None:
        parent_id: int | None = None
        for name in folder_names:
            query = select(Folder).where(
                Folder.user_id == user_id,
                Folder.name == name,
            )
            if parent_id is None:
                query = query.where(Folder.parent_folder_id.is_(None))
            else:
                query = query.where(Folder.parent_folder_id == parent_id)
            folder = session.exec(query).first()
            if not folder:
                raise ValueError("Folder path not found.")
            parent_id = folder.id
        return parent_id

    @staticmethod
    def _assert_path_length(username: str, folder_path: list[str], palette_title: str) -> None:
        full_path = "/users/" + "/".join([username] + folder_path + [palette_title])
        if len(full_path) > 300:
            raise ValueError("Palette path is too long.")

    @staticmethod
    def _ensure_palette_unique(
        user_id: int,
        folder_id: int | None,
        title: str,
        session: SessionDep,
        ignore_palette_id: int | None = None,
    ) -> None:
        query = select(Palette).where(
            Palette.user_id == user_id,
            Palette.title == title,
        )
        if folder_id is None:
            query = query.where(Palette.folder_id.is_(None))
        else:
            query = query.where(Palette.folder_id == folder_id)
        if ignore_palette_id is not None:
            query = query.where(Palette.id != ignore_palette_id)
        if session.exec(query).first():
            raise ValueError("Palette name already exists in this folder.")
    @staticmethod
    def _assert_palette_owner(palette_id: int, user_id: int, session: SessionDep) -> Palette:
        palette = PaletteService.get_palette(palette_id, session)
        if not palette:
            raise ValueError("Palette not found.")
        if palette.user_id != user_id:
            raise PermissionError("You do not have permission to modify this palette.")
        return palette

    @staticmethod
    def _delete_snapshots_and_related(snapshot_ids: list[int], session: SessionDep) -> tuple[int, int, int]:
        if not snapshot_ids:
            return 0, 0, 0

        deleted_changes = session.exec(
            delete(Palette_Change).where(Palette_Change.new_snapshot_id.in_(snapshot_ids))
        ).rowcount or 0

        deleted_changes += session.exec(
            delete(Palette_Change).where(Palette_Change.previous_snapshot_id.in_(snapshot_ids))
        ).rowcount or 0

        deleted_colors = session.exec(
            delete(Palette_Color).where(Palette_Color.palette_snapshot_id.in_(snapshot_ids))
        ).rowcount or 0

        deleted_snapshots = session.exec(
            delete(Palette_Snapshot).where(Palette_Snapshot.id.in_(snapshot_ids))
        ).rowcount or 0

        return deleted_snapshots, deleted_colors, deleted_changes

    @staticmethod
    def _snapshot_to_commit(snap: Palette_Snapshot, session: SessionDep):
        colors = PaletteService.get_snapshot_state(snap, session)
        added, deleted, modified = PaletteService.get_diff_counts(snap.id, session)
        return {
            "id": snap.id,
            "palette_id": snap.palette_id,
            "parent_snapshot_id": snap.parent_snapshot_id,
            "branch_id": snap.branch_id,
            "comment": snap.comment,
            "created_at": snap.created_at,
            "palette_colors": [{"hex": c.hex, "label": c.label} for c in colors],
            "colors_added": added,
            "colors_deleted": deleted,
            "colors_modified": modified,
        }

    # Creates a new palette along with its initial snapshot and starting colors.
    def create_palette(paletteSchema: PaletteCreate, user_id: int, session: SessionDep):
        folder_id = paletteSchema.folder_id
        if folder_id is None and paletteSchema.folder_path:
            folder_id = PaletteService._resolve_folder_path(
                user_id, paletteSchema.folder_path, session
            )

        PaletteService._assert_palette_name(paletteSchema.title)
        PaletteService._assert_folder_owner(folder_id, user_id, session)
        PaletteService._ensure_palette_unique(
            user_id, folder_id, paletteSchema.title, session
        )

        user = PaletteService._get_user(user_id, session)
        folder_path = PaletteService._get_folder_path(folder_id, session)
        PaletteService._assert_path_length(user.username, folder_path, paletteSchema.title)

        new_palette = Palette(
            user_id=user_id,
            title=paletteSchema.title,
            description=paletteSchema.description,
            folder_id=folder_id,
        )
        session.add(new_palette)
        session.flush()

        new_snapshot = Palette_Snapshot(
            palette_id=new_palette.id,
            branch_id=None,
            comment="Initial palette creation",
        )
        session.add(new_snapshot)
        session.flush()

        keys = LexicographicRanker.initial_keys(len(paletteSchema.palette_colors))
        for i, color_schema in enumerate(paletteSchema.palette_colors):
            new_color = Palette_Color(
                palette_snapshot_id=new_snapshot.id,
                hex=color_schema.hex,
                label=color_schema.label,
                position_key=keys[i],
            )
            session.add(new_color)

        session.commit()
        session.refresh(new_palette)
        return new_palette

    # Retrieves a palette by its ID.
    def get_palette(palette_id: int, session: SessionDep):
        query = select(Palette).where(Palette.id == palette_id)
        return session.exec(query).first()

    # Resolves a palette by username and folder path (e.g. "folder/sub/palette").
    def get_palette_by_path(username: str, path: str, session: SessionDep) -> Palette:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise ValueError("User not found.")

        segments = [seg for seg in path.split("/") if seg]
        if not segments:
            raise ValueError("Palette path is invalid.")

        palette_title = segments[-1]
        folder_names = segments[:-1]
        folder_id = PaletteService._resolve_folder_path(user.id, folder_names, session)

        query = select(Palette).where(
            Palette.user_id == user.id,
            Palette.title == palette_title,
        )
        if folder_id is None:
            query = query.where(Palette.folder_id.is_(None))
        else:
            query = query.where(Palette.folder_id == folder_id)
        palette = session.exec(query).first()
        if not palette:
            raise ValueError("Palette not found.")
        return palette

    # Retrieves all palettes for a username with the latest main-branch snapshot.
    def get_palettes_by_username(username: str, session: SessionDep):
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise ValueError("User not found.")

        palettes = session.exec(
            select(Palette)
            .where(Palette.user_id == user.id)
            .order_by(desc(Palette.created_at), desc(Palette.id))
        ).all()

        result = []
        for palette in palettes:
            folder_path = PaletteService._get_folder_path(palette.folder_id, session)
            latest_snapshot, _ = PaletteService.get_latest_palette_snapshot(
                palette.id, session, branch_id=None
            )
            result.append(
                {
                    "id": palette.id,
                    "title": palette.title,
                    "description": palette.description,
                    "folder_id": palette.folder_id,
                    "folder_path": folder_path,
                    "created_at": palette.created_at,
                    "latest_main_snapshot": (
                        PaletteService._snapshot_to_commit(latest_snapshot, session)
                        if latest_snapshot
                        else None
                    ),
                }
            )

        return {"username": username, "palettes": result}

    # Reconstructs the active color list for a specific snapshot by resolving past changes.
    def get_snapshot_state(
        snapshot: Palette_Snapshot, session: SessionDep
    ) -> list[Palette_Color]:
        current_snapshot = snapshot
        active_colors: dict[int, Palette_Color] = {}
        deleted_color_ids: set[int] = set()

        while current_snapshot:
            changes = session.exec(
                select(Palette_Change).where(
                    Palette_Change.new_snapshot_id == current_snapshot.id
                )
            ).all()
            for change in changes:
                if change.new_color_id is None and change.previous_color_id is not None:
                    deleted_color_ids.add(change.previous_color_id)
                elif change.new_color_id is not None:
                    if (
                        change.new_color_id not in deleted_color_ids
                        and change.new_color_id not in active_colors
                    ):
                        color = session.exec(
                            select(Palette_Color).where(
                                Palette_Color.id == change.new_color_id
                            )
                        ).first()
                        if color:
                            active_colors[color.id] = color
                    if change.previous_color_id is not None:
                        deleted_color_ids.add(change.previous_color_id)

            base_colors = session.exec(
                select(Palette_Color).where(
                    Palette_Color.palette_snapshot_id == current_snapshot.id
                )
            ).all()
            for color in base_colors:
                if color.id not in deleted_color_ids and color.id not in active_colors:
                    active_colors[color.id] = color

            if current_snapshot.parent_snapshot_id:
                current_snapshot = session.exec(
                    select(Palette_Snapshot).where(
                        Palette_Snapshot.id == current_snapshot.parent_snapshot_id
                    )
                ).first()
            else:
                break

        return sorted(active_colors.values(), key=lambda c: c.position_key)

    # Retrieves the most recent snapshot for a palette and its active colors.
    def get_latest_palette_snapshot(
        palette_id: int,
        session: SessionDep,
        branch_id: int | None = None,
        include_all_branches: bool = False,
    ) -> tuple[Palette_Snapshot | None, list[Palette_Color]]:
        query = select(Palette_Snapshot).where(
            Palette_Snapshot.palette_id == palette_id
        )
        if not include_all_branches:
            if branch_id is None:
                query = query.where(Palette_Snapshot.branch_id.is_(None))
            else:
                query = query.where(Palette_Snapshot.branch_id == branch_id)

        query = query.order_by(
            desc(Palette_Snapshot.created_at), desc(Palette_Snapshot.id)
        )
        latest_snapshot = session.exec(query).first()

        if not latest_snapshot:
            return None, []

        return latest_snapshot, PaletteService.get_snapshot_state(
            latest_snapshot, session
        )

    # Retrieves a branch by id and validates it belongs to a palette.
    def get_palette_branch(
        palette_id: int, branch_id: int, session: SessionDep
    ) -> Palette_Branch | None:
        return session.exec(
            select(Palette_Branch).where(
                Palette_Branch.id == branch_id,
                Palette_Branch.palette_id == palette_id,
            )
        ).first()

    # Calculates the number of added, deleted, and modified colors for a given snapshot.
    def get_diff_counts(snap_id: int, session: SessionDep):
        changes = session.exec(
            select(Palette_Change).where(Palette_Change.new_snapshot_id == snap_id)
        ).all()
        added, deleted, modified = 0, 0, 0
        for c in changes:
            if c.previous_color_id and c.new_color_id:
                modified += 1
            elif c.new_color_id:
                added += 1
            elif c.previous_color_id:
                deleted += 1
        return added, deleted, modified

    # Builds a graph of a palette's history, grouping snapshots by explicit branches.
    def get_palette_history(palette: Palette, session: SessionDep, owner_username: str):
        palette_id = palette.id
        main_snapshots = session.exec(
            select(Palette_Snapshot)
            .where(Palette_Snapshot.palette_id == palette_id)
            .where(Palette_Snapshot.branch_id.is_(None))
            .order_by(desc(Palette_Snapshot.created_at))
        ).all()

        branches = session.exec(
            select(Palette_Branch)
            .where(Palette_Branch.palette_id == palette_id)
            .order_by(Palette_Branch.created_at)
        ).all()

        folder_path = PaletteService._get_folder_path(palette.folder_id, session)

        return {
            "palette_id": palette_id,
            "owner_username": owner_username,
            "title": palette.title,
            "description": palette.description,
            "folder_path": folder_path,
            "main": [PaletteService._snapshot_to_commit(snap, session) for snap in main_snapshots],
            "branches": [
                {
                    "id": branch.id,
                    "title": branch.title,
                    "merged_at": branch.merged_at,
                    "is_merged": branch.merged_at is not None,
                    "snapshots": [
                        PaletteService._snapshot_to_commit(snap, session)
                        for snap in session.exec(
                            select(Palette_Snapshot)
                            .where(
                                Palette_Snapshot.palette_id == palette_id,
                                Palette_Snapshot.branch_id == branch.id,
                            )
                            .order_by(desc(Palette_Snapshot.created_at))
                        ).all()
                    ],
                }
                for branch in branches
            ],
        }

    # Update palette title/description/folder assignment.
    def update_palette(
        palette_id: int,
        updateSchema: PaletteUpdate,
        user_id: int,
        session: SessionDep,
    ) -> Palette:
        palette = PaletteService._assert_palette_owner(palette_id, user_id, session)

        next_title = updateSchema.title if updateSchema.title is not None else palette.title
        next_description = (
            updateSchema.description
            if updateSchema.description is not None
            else palette.description
        )
        next_folder_id = (
            updateSchema.folder_id
            if updateSchema.folder_id is not None
            else palette.folder_id
        )

        PaletteService._assert_palette_name(next_title)
        PaletteService._assert_folder_owner(next_folder_id, user_id, session)
        PaletteService._ensure_palette_unique(
            user_id, next_folder_id, next_title, session, ignore_palette_id=palette.id
        )

        user = PaletteService._get_user(user_id, session)
        folder_path = PaletteService._get_folder_path(next_folder_id, session)
        PaletteService._assert_path_length(user.username, folder_path, next_title)

        palette.title = next_title
        palette.description = next_description
        palette.folder_id = next_folder_id
        session.add(palette)
        session.commit()
        session.refresh(palette)
        return palette

    # Creates a branch and applies default naming when no title is provided.
    def create_palette_branch(
        palette_id: int,
        session: SessionDep,
        branch_title: str | None = None,
    ) -> Palette_Branch:
        if branch_title:
            title = branch_title
        else:
            branch_count = session.exec(
                select(Palette_Branch).where(Palette_Branch.palette_id == palette_id)
            ).all()
            title = f"Branch {len(branch_count) + 2}"

        new_branch = Palette_Branch(palette_id=palette_id, title=title)
        session.add(new_branch)
        session.flush()
        return new_branch

    # Creates a snapshot and records its diff against a previous snapshot.
    def create_snapshot_with_changes(
        palette_id: int,
        previous_snapshot: Palette_Snapshot,
        previous_colors: list[Palette_Color],
        new_inputs,
        comment: str,
        branch_id: int | None,
        session: SessionDep,
    ) -> tuple[Palette_Snapshot, list[Palette_Change]]:
        def _get_identity(c):
            return f"{c.hex}_{c.label}"

        old_ids = [_get_identity(c) for c in previous_colors]
        new_ids = [_get_identity(c) for c in new_inputs]

        matcher = difflib.SequenceMatcher(None, old_ids, new_ids)
        opcodes = matcher.get_opcodes()

        if (
            len(opcodes) == 1
            and opcodes[0][0] == "equal"
            and opcodes[0][2] - opcodes[0][1] == len(previous_colors)
        ):
            raise ValueError("No changes detected in palette colors.")

        new_snapshot = Palette_Snapshot(
            palette_id=palette_id,
            parent_snapshot_id=previous_snapshot.id,
            branch_id=branch_id,
            comment=comment,
        )
        session.add(new_snapshot)
        session.flush()

        new_colors_final = [None] * len(new_inputs)
        changes_to_record = []
        replacements_map = {}
        pending_deletions: list[Palette_Color] = []
        pending_deletions_by_identity: dict[str, list[int]] = defaultdict(list)

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                for old_idx, new_idx in zip(range(i1, i2), range(j1, j2)):
                    new_colors_final[new_idx] = previous_colors[old_idx]

            elif tag == "delete":
                for old_idx in range(i1, i2):
                    pending_deletions.append(previous_colors[old_idx])

            elif tag == "replace":
                old_indices = list(range(i1, i2))
                new_indices = list(range(j1, j2))

                for k in range(max(len(old_indices), len(new_indices))):
                    if k < len(old_indices) and k < len(new_indices):
                        replacements_map[new_indices[k]] = previous_colors[
                            old_indices[k]
                        ].id

                    elif k < len(old_indices):
                        pending_deletions.append(previous_colors[old_indices[k]])

        for old_color in pending_deletions:
            pending_deletions_by_identity[_get_identity(old_color)].append(old_color.id)

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "insert" or tag == "replace":
                for new_idx in range(j1, j2):
                    req_color = new_inputs[new_idx]

                    left_key = (
                        new_colors_final[new_idx - 1].position_key
                        if new_idx > 0 and new_colors_final[new_idx - 1]
                        else None
                    )
                    right_key = None

                    for scan_idx in range(new_idx + 1, len(new_inputs)):
                        if new_colors_final[scan_idx]:
                            right_key = new_colors_final[scan_idx].position_key
                            break

                    if left_key and not right_key:
                        pos_key = LexicographicRanker.increment(left_key[-1])
                        if len(left_key) > 1:
                            pos_key = left_key[:-1] + pos_key
                    elif not left_key and right_key:
                        pos_key = LexicographicRanker.midpoint("`", right_key)
                    else:
                        pos_key = LexicographicRanker.midpoint(
                            left_key or "`", right_key or "z"
                        )

                    new_c = Palette_Color(
                        palette_snapshot_id=new_snapshot.id,
                        hex=req_color.hex,
                        label=req_color.label,
                        position_key=pos_key,
                    )
                    session.add(new_c)
                    session.flush()
                    new_colors_final[new_idx] = new_c

                    prev_color_id = replacements_map.get(new_idx, None)
                    if prev_color_id is None:
                        identity_key = _get_identity(req_color)
                        if pending_deletions_by_identity[identity_key]:
                            prev_color_id = pending_deletions_by_identity[
                                identity_key
                            ].pop(0)

                    changes_to_record.append(
                        Palette_Change(
                            previous_snapshot_id=previous_snapshot.id,
                            new_snapshot_id=new_snapshot.id,
                            previous_color_id=prev_color_id,
                            new_color_id=new_c.id,
                        )
                    )

        for remaining_prev_ids in pending_deletions_by_identity.values():
            for prev_id in remaining_prev_ids:
                changes_to_record.append(
                    Palette_Change(
                        previous_snapshot_id=previous_snapshot.id,
                        new_snapshot_id=new_snapshot.id,
                        previous_color_id=prev_id,
                        new_color_id=None,
                    )
                )

        for change in changes_to_record:
            session.add(change)

        return new_snapshot, changes_to_record

    # Creates a new snapshot with calculated differences compared to its parent snapshot.
    def save_palette(
        palette_id: int,
        saveSchema: PaletteSnapshotSave,
        user_id: int,
        session: SessionDep,
    ):
        palette = PaletteService.get_palette(palette_id, session)
        if not palette:
            raise ValueError("Palette not found.")
        if palette.user_id != user_id:
            raise PermissionError("You do not have permission to modify this palette.")

        if saveSchema.create_branch and saveSchema.branch_id is not None:
            raise ValueError("Do not pass branch_id when create_branch=true.")

        target_branch_id = saveSchema.branch_id
        if target_branch_id is not None:
            branch = PaletteService.get_palette_branch(
                palette_id, target_branch_id, session
            )
            if not branch:
                raise ValueError("Branch not found for this palette.")
            if branch.merged_at:
                raise ValueError("This branch has already been merged.")

        latest_target_snapshot, _ = PaletteService.get_latest_palette_snapshot(
            palette_id, session, branch_id=target_branch_id
        )

        if saveSchema.parent_snapshot_id:
            prev_snapshot = session.exec(
                select(Palette_Snapshot).where(
                    Palette_Snapshot.id == saveSchema.parent_snapshot_id,
                    Palette_Snapshot.palette_id == palette_id,
                )
            ).first()
            if not prev_snapshot:
                raise ValueError("Parent snapshot not found for this palette.")
        else:
            if saveSchema.create_branch:
                # Always branch from the latest main snapshot when no explicit parent is given.
                # Using include_all_branches=True here would pick whichever snapshot was
                # created most recently across all branches, which could be a branch snapshot
                # — creating a dangling parent reference that breaks branch deletion later.
                prev_snapshot, _ = PaletteService.get_latest_palette_snapshot(
                    palette_id,
                    session,
                    branch_id=None,
                )
            else:
                prev_snapshot = latest_target_snapshot

        if not prev_snapshot:
            raise ValueError("Palette has no previous snapshot to save upon.")

        if saveSchema.create_branch:
            new_branch = PaletteService.create_palette_branch(
                palette_id,
                session,
                saveSchema.branch_title,
            )
            target_branch_id = new_branch.id
        else:
            if prev_snapshot.branch_id != target_branch_id:
                raise ValueError(
                    "Parent snapshot belongs to another branch. To branch from that snapshot, set create_branch=true."
                )
            if (
                latest_target_snapshot
                and prev_snapshot.id != latest_target_snapshot.id
                and saveSchema.parent_snapshot_id is not None
            ):
                raise ValueError(
                    "Parent snapshot is not the latest in this branch. Set create_branch=true to create a branch from this older snapshot."
                )

        prev_colors = PaletteService.get_snapshot_state(prev_snapshot, session)

        new_inputs = saveSchema.palette_colors
        new_snapshot, changes_to_record = PaletteService.create_snapshot_with_changes(
            palette_id=palette_id,
            previous_snapshot=prev_snapshot,
            previous_colors=prev_colors,
            new_inputs=new_inputs,
            comment=saveSchema.comment,
            branch_id=target_branch_id,
            session=session,
        )

        session.commit()
        session.refresh(new_snapshot)
        return new_snapshot, changes_to_record

    # Merges a branch by recreating its latest state as a new main-branch snapshot.
    def merge_branch(
        palette_id: int,
        branch_id: int,
        user_id: int,
        session: SessionDep,
    ) -> tuple[Palette_Branch, Palette_Snapshot, list[Palette_Change]]:
        palette = PaletteService.get_palette(palette_id, session)
        if not palette:
            raise ValueError("Palette not found.")
        if palette.user_id != user_id:
            raise PermissionError("You do not have permission to modify this palette.")

        branch = PaletteService.get_palette_branch(palette_id, branch_id, session)
        if not branch:
            raise ValueError("Branch not found for this palette.")
        if branch.merged_at:
            raise ValueError("This branch has already been merged.")

        branch_snapshot, branch_colors = PaletteService.get_latest_palette_snapshot(
            palette_id, session, branch_id=branch_id
        )
        if not branch_snapshot:
            raise ValueError("Cannot merge a branch without snapshots.")

        main_snapshot, main_colors = PaletteService.get_latest_palette_snapshot(
            palette_id, session, branch_id=None
        )
        if not main_snapshot:
            raise ValueError("Main branch has no snapshot to merge into.")

        merge_snapshot, recorded_changes = PaletteService.create_snapshot_with_changes(
            palette_id=palette_id,
            previous_snapshot=main_snapshot,
            previous_colors=main_colors,
            new_inputs=branch_colors,
            comment=f"Merge branch '{branch.title}'",
            branch_id=None,
            session=session,
        )

        branch.merged_at = datetime.now(timezone.utc)
        session.add(branch)
        session.commit()
        session.refresh(branch)
        session.refresh(merge_snapshot)
        return branch, merge_snapshot, recorded_changes

    @staticmethod
    def delete_palette(
        palette_id: int,
        user_id: int,
        session: SessionDep,
    ):
        palette = PaletteService._assert_palette_owner(palette_id, user_id, session)

        branch_ids = session.exec(
            select(Palette_Branch.id).where(Palette_Branch.palette_id == palette_id)
        ).all()
        deleted_branches = len(branch_ids)

        snapshot_ids = session.exec(
            select(Palette_Snapshot.id).where(Palette_Snapshot.palette_id == palette_id)
        ).all()
        deleted_snapshots, deleted_colors, deleted_changes = (
            PaletteService._delete_snapshots_and_related(snapshot_ids, session)
        )

        session.exec(delete(Palette_Branch).where(Palette_Branch.palette_id == palette_id))
        session.delete(palette)
        session.commit()

        return {
            "palette_id": palette_id,
            "deleted_branches": deleted_branches,
            "deleted_snapshots": deleted_snapshots,
            "deleted_colors": deleted_colors,
            "deleted_changes": deleted_changes,
        }

    @staticmethod
    def delete_branch(
        palette_id: int,
        branch_id: int,
        user_id: int,
        session: SessionDep,
    ):
        PaletteService._assert_palette_owner(palette_id, user_id, session)

        branch = PaletteService.get_palette_branch(palette_id, branch_id, session)
        if not branch:
            raise ValueError("Branch not found for this palette.")
        if branch.merged_at:
            raise ValueError("Merged branches cannot be deleted.")

        snapshot_ids = session.exec(
            select(Palette_Snapshot.id).where(
                Palette_Snapshot.palette_id == palette_id,
                Palette_Snapshot.branch_id == branch_id,
            )
        ).all()

        # Guard against FK violations: if any snapshot outside this branch has a
        # parent_snapshot_id pointing into this branch's snapshots, deletion would
        # fail at the DB level. This can happen if a branch was accidentally forked
        # from a branch snapshot instead of a main snapshot.
        if snapshot_ids:
            dependent = session.exec(
                select(Palette_Snapshot.id).where(
                    Palette_Snapshot.parent_snapshot_id.in_(snapshot_ids),
                    Palette_Snapshot.branch_id != branch_id,
                )
            ).first()
            if dependent:
                raise ValueError(
                    "Cannot delete this branch: one or more of its snapshots are "
                    "referenced as a parent by snapshots in another branch. "
                    "Delete the dependent branch first."
                )

        deleted_snapshots, deleted_colors, deleted_changes = (
            PaletteService._delete_snapshots_and_related(snapshot_ids, session)
        )

        session.delete(branch)
        session.commit()

        return {
            "palette_id": palette_id,
            "branch_id": branch_id,
            "deleted_snapshots": deleted_snapshots,
            "deleted_colors": deleted_colors,
            "deleted_changes": deleted_changes,
        }

    @staticmethod
    def revert_branch_to_snapshot(
        palette_id: int,
        branch_id: int,
        snapshot_id: int,
        user_id: int,
        session: SessionDep,
    ):
        PaletteService._assert_palette_owner(palette_id, user_id, session)

        branch = PaletteService.get_palette_branch(palette_id, branch_id, session)
        if not branch:
            raise ValueError("Branch not found for this palette.")
        if branch.merged_at:
            raise ValueError("Merged branches cannot be reverted.")

        branch_snapshots = session.exec(
            select(Palette_Snapshot)
            .where(
                Palette_Snapshot.palette_id == palette_id,
                Palette_Snapshot.branch_id == branch_id,
            )
            .order_by(desc(Palette_Snapshot.created_at), desc(Palette_Snapshot.id))
        ).all()

        if not branch_snapshots:
            raise ValueError("Branch has no snapshots to revert.")

        ordered_ids = [s.id for s in branch_snapshots]
        if snapshot_id not in ordered_ids:
            raise ValueError("Selected snapshot does not belong to this branch.")

        target_index = ordered_ids.index(snapshot_id)
        to_delete_ids = ordered_ids[:target_index]

        deleted_snapshots, deleted_colors, deleted_changes = (
            PaletteService._delete_snapshots_and_related(to_delete_ids, session)
        )

        session.commit()

        return {
            "palette_id": palette_id,
            "branch_id": branch_id,
            "target_snapshot_id": snapshot_id,
            "latest_snapshot_id": snapshot_id,
            "deleted_snapshots": deleted_snapshots,
            "deleted_colors": deleted_colors,
            "deleted_changes": deleted_changes,
        }

    @staticmethod
    def revert_main_to_snapshot(
        palette_id: int,
        snapshot_id: int,
        user_id: int,
        session: SessionDep,
    ):
        PaletteService._assert_palette_owner(palette_id, user_id, session)

        main_snapshots = session.exec(
            select(Palette_Snapshot)
            .where(
                Palette_Snapshot.palette_id == palette_id,
                Palette_Snapshot.branch_id == None,
            )
            .order_by(desc(Palette_Snapshot.created_at), desc(Palette_Snapshot.id))
        ).all()

        if not main_snapshots:
            raise ValueError("No main snapshots found.")

        ordered_ids = [s.id for s in main_snapshots]
        if snapshot_id not in ordered_ids:
            raise ValueError("Selected snapshot does not belong to main.")

        target_index = ordered_ids.index(snapshot_id)
        to_delete_ids = set(ordered_ids[:target_index])

        if not to_delete_ids:
            raise ValueError("No snapshots to delete — this is already the latest.")

        branches = session.exec(
            select(Palette_Branch).where(Palette_Branch.palette_id == palette_id)
        ).all()

        total_deleted_snapshots = 0
        total_deleted_colors = 0
        total_deleted_changes = 0
        deleted_branches = 0

        for branch in branches:
            branch_snaps = session.exec(
                select(Palette_Snapshot)
                .where(
                    Palette_Snapshot.palette_id == palette_id,
                    Palette_Snapshot.branch_id == branch.id,
                )
                .order_by(Palette_Snapshot.created_at, Palette_Snapshot.id)
            ).all()

            if not branch_snaps:
                continue

            first_snap = branch_snaps[0]

            if first_snap.parent_snapshot_id in to_delete_ids:
                # Branch forks from a deleted main snapshot — remove it entirely
                snap_ids = [s.id for s in branch_snaps]
                ds, dc, dch = PaletteService._delete_snapshots_and_related(snap_ids, session)
                total_deleted_snapshots += ds
                total_deleted_colors += dc
                total_deleted_changes += dch
                session.delete(branch)
                deleted_branches += 1
            elif branch.merged_at and any(
                s.comment == f"Merge branch '{branch.title}'" and s.id in to_delete_ids
                for s in main_snapshots
            ):
                # Branch was merged by a commit being deleted — unmerge it
                branch.merged_at = None
                session.add(branch)

        ds, dc, dch = PaletteService._delete_snapshots_and_related(list(to_delete_ids), session)
        total_deleted_snapshots += ds
        total_deleted_colors += dc
        total_deleted_changes += dch

        session.commit()

        return {
            "palette_id": palette_id,
            "target_snapshot_id": snapshot_id,
            "latest_snapshot_id": snapshot_id,
            "deleted_snapshots": total_deleted_snapshots,
            "deleted_branches": deleted_branches,
            "deleted_colors": total_deleted_colors,
            "deleted_changes": total_deleted_changes,
        }
