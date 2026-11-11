import unittest
import random
from types import SimpleNamespace

from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Session, SQLModel, create_engine

from app.controllers.palette import PaletteController
from app.models.palette import Palette, Palette_Color, Palette_Snapshot
from app.models.user import User
from app.schemas.palette import PaletteColorSave, PaletteSnapshotSave
from app.services.palette import PaletteService
from app.utils.palette_diff import diff_colors


@compiles(BigInteger, "sqlite")
def sqlite_bigint(element, compiler, **kw):
    return "INTEGER"


def colors(*entries):
    return [SimpleNamespace(hex=hex, label=label) for hex, label in entries]


class PaletteDiffTests(unittest.TestCase):
    def test_label_edit(self):
        changes = diff_colors(colors(("BBBBBB", "Vert")), colors(("BBBBBB", "Menthe")))
        self.assertEqual([(c.old_index, c.new_index, c.fields) for c in changes], [(0, 0, ("label",))])

    def test_empty_labels_are_equivalent(self):
        self.assertEqual(diff_colors(colors(("BBBBBB", None)), colors(("bbbbbb", "")))[0].fields, ())

    def test_setting_and_clearing_labels_are_modifications(self):
        for before, after in [(None, "Vert"), ("Vert", None), ("Vert", ""), (None, "None")]:
            with self.subTest(before=before, after=after):
                changes = diff_colors(colors(("BBBBBB", before)), colors(("BBBBBB", after)))
                self.assertEqual([(c.old_index, c.new_index, c.fields) for c in changes],
                                 [(0, 0, ("label",))])

    def test_actual_additions_and_deletions(self):
        added = diff_colors([], colors(("BBBBBB", None)))
        deleted = diff_colors(colors(("BBBBBB", None)), [])
        self.assertEqual([(c.old_index, c.new_index) for c in added], [(None, 0)])
        self.assertEqual([(c.old_index, c.new_index) for c in deleted], [(0, None)])

    def test_move_and_label_edit(self):
        old = colors(("111111", "A"), ("222222", "B"), ("333333", "C"))
        new = colors(("222222", "B"), ("333333", "C"), ("111111", "renamed"))
        changes = diff_colors(old, new)
        self.assertEqual((changes[2].old_index, changes[2].fields), (0, ("label", "position")))
        self.assertTrue(all(c.old_index is not None and c.new_index is not None for c in changes))

    def test_duplicate_colors_are_consumed_once(self):
        old = colors(("111111", "A"), ("111111", "A"))
        new = colors(("111111", "renamed"), ("111111", "A"))
        changes = diff_colors(old, new)
        self.assertEqual({c.old_index for c in changes}, {0, 1})
        self.assertEqual(sum("label" in c.fields for c in changes), 1)

    def test_insertion_does_not_modify_following_colors(self):
        changes = diff_colors(colors(("111111", None)), colors(("222222", None), ("111111", None)))
        self.assertEqual([(c.old_index, c.fields) for c in changes], [(None, ()), (0, ())])

    def test_save_response_history_and_reconstructed_state(self):
        engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            user = User(username="test", email="test@example.com", password="unused")
            session.add(user)
            session.flush()
            palette = Palette(user_id=user.id, title="test")
            session.add(palette)
            session.flush()
            snapshot = Palette_Snapshot(palette_id=palette.id)
            session.add(snapshot)
            session.flush()
            session.add(Palette_Color(palette_snapshot_id=snapshot.id, hex="BBBBBB", label="Vert", position_key="a"))
            session.commit()

            result = PaletteController.save_palette_control(palette.id, PaletteSnapshotSave(
                parent_snapshot_id=snapshot.id,
                palette_colors=[PaletteColorSave(hex="BBBBBB", label="Menthe")],
            ), user.id, session)
            self.assertEqual((result.colors_added, result.colors_deleted, result.colors_modified), (0, 0, 1))
            self.assertEqual(result.palette_colors[0].label, "Menthe")
            history = PaletteService.get_palette_history(palette, session, user.username)
            latest = history["main"][0]
            self.assertEqual((latest["colors_added"], latest["colors_deleted"], latest["colors_modified"]), (0, 0, 1))
            self.assertEqual(latest["palette_colors"], [{"hex": "BBBBBB", "label": "Menthe"}])

            # Repeated edits exercise persistence, duplicate occurrences, moves
            # and rank insertion, not just the pure diff's counters.
            rng = random.Random(24)
            parent_id = result.palette_snapshot_id
            for _ in range(80):
                inputs = [PaletteColorSave(hex=rng.choice(["111111", "222222", "333333"]),
                                           label=rng.choice([None, "A", "B"]))
                          for _ in range(rng.randint(1, 8))]
                current = session.get(Palette_Snapshot, parent_id)
                before = PaletteService.get_snapshot_state(current, session)
                if [(c.hex, c.label) for c in before] == [(c.hex, c.label) for c in inputs]:
                    continue
                result = PaletteController.save_palette_control(palette.id, PaletteSnapshotSave(
                    parent_snapshot_id=parent_id, palette_colors=inputs,
                ), user.id, session)
                self.assertEqual([(c.hex, c.label) for c in result.palette_colors],
                                 [(c.hex, c.label) for c in inputs])
                parent_id = result.palette_snapshot_id
        engine.dispose()
