from datetime import timezone, datetime
from sqlmodel import desc, select
import difflib

from app.core.database import SessionDep
from app.models.palette import (
    Palette,
    Palette_Branch,
    Palette_Change,
    Palette_Color,
    Palette_Snapshot,
)
from app.schemas.palette import PaletteCreate, PaletteSnapshotSave
from app.utils.lexicographic_ranker import LexicographicRanker


class PaletteService:
    # Creates a new palette along with its initial snapshot and starting colors.
    def create_palette(paletteSchema: PaletteCreate, user_id: int, session: SessionDep):
        new_palette = Palette(
            user_id=user_id,
            title=paletteSchema.title,
            description=paletteSchema.description,
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
    def get_palette_history(palette_id: int, session: SessionDep):
        main_snapshots = session.exec(
            select(Palette_Snapshot)
            .where(Palette_Snapshot.palette_id == palette_id)
            .where(Palette_Snapshot.branch_id.is_(None))
            .order_by(desc(Palette_Snapshot.created_at))
        ).all()

        def _snapshot_to_commit(snap: Palette_Snapshot):
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

        branches = session.exec(
            select(Palette_Branch)
            .where(Palette_Branch.palette_id == palette_id)
            .order_by(Palette_Branch.created_at)
        ).all()

        return {
            "main": [_snapshot_to_commit(snap) for snap in main_snapshots],
            "branches": [
                {
                    "id": branch.id,
                    "title": branch.title,
                    "merged_at": branch.merged_at,
                    "is_merged": branch.merged_at is not None,
                    "snapshots": [
                        _snapshot_to_commit(snap)
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

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                for old_idx, new_idx in zip(range(i1, i2), range(j1, j2)):
                    new_colors_final[new_idx] = previous_colors[old_idx]

            elif tag == "delete":
                for old_idx in range(i1, i2):
                    changes_to_record.append(
                        Palette_Change(
                            previous_snapshot_id=previous_snapshot.id,
                            new_snapshot_id=new_snapshot.id,
                            previous_color_id=previous_colors[old_idx].id,
                            new_color_id=None,
                        )
                    )

            elif tag == "replace":
                old_indices = list(range(i1, i2))
                new_indices = list(range(j1, j2))

                for k in range(max(len(old_indices), len(new_indices))):
                    if k < len(old_indices) and k < len(new_indices):
                        replacements_map[new_indices[k]] = previous_colors[
                            old_indices[k]
                        ].id

                    elif k < len(old_indices):
                        changes_to_record.append(
                            Palette_Change(
                                previous_snapshot_id=previous_snapshot.id,
                                new_snapshot_id=new_snapshot.id,
                                previous_color_id=previous_colors[old_indices[k]].id,
                                new_color_id=None,
                            )
                        )

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

                    changes_to_record.append(
                        Palette_Change(
                            previous_snapshot_id=previous_snapshot.id,
                            new_snapshot_id=new_snapshot.id,
                            previous_color_id=prev_color_id,
                            new_color_id=new_c.id,
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
                prev_snapshot, _ = PaletteService.get_latest_palette_snapshot(
                    palette_id,
                    session,
                    include_all_branches=True,
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
