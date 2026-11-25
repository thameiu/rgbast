from sqlmodel import select
import unittest

import tests.test_projects as project_tests
from app.api.projects import remove
from app.models.folder import Folder
from app.models.palette import Palette, Palette_Snapshot
from app.models.project import ProjectAccess
from app.schemas.folder import FolderCreate, FolderUpdate
from app.schemas.palette import PaletteCreate, PaletteColorSave, PaletteUpdate, PaletteSnapshotSave
from app.schemas.project import ProjectDelete
from app.services.folder import FolderService
from app.services.palette import PaletteService
from app.services.project_content import ProjectContentService as Content


class ProjectContentTests(unittest.TestCase):
    setUp = project_tests.ProjectTests.setUp
    tearDown = project_tests.ProjectTests.tearDown
    project = project_tests.ProjectTests.project
    assert_status = project_tests.ProjectTests.assert_status
    def create_palette(self, project=None, folder=None, title='Palette', user=None):
        return PaletteService.create_palette(PaletteCreate(
            project_id=project, folder_id=folder, title=title, description='Description',
            palette_colors=[PaletteColorSave(hex='AABBCC', label='Original')]), user or self.owner.id, self.session)

    def grant(self, project, *permissions):
        for permission in permissions:
            self.session.add(ProjectAccess(project_id=project, user_id=self.member.id, permission=permission))
        self.session.commit()

    def test_project_and_personal_namespaces(self):
        project = self.project()
        folder = Content.create_folder(project['id'], self.owner.id, FolderCreate(name='Folder'), self.session)
        personal = FolderService.create_folder(FolderCreate(name='Folder'), self.owner.id, self.session)
        palette = self.create_palette(project['id'], folder.id)
        own = self.create_palette(None, personal.id)
        self.assertEqual([f.id for f in FolderService.list_folders_by_username(self.owner.username, self.session)], [personal.id])
        self.assertEqual([p['id'] for p in PaletteService.get_palettes_by_username(self.owner.username, self.session)['palettes']], [own.id])
        self.assertEqual([p['id'] for p in Content.palettes(project['id'], self.owner.id, self.session)], [palette.id])
        with self.assertRaises(ValueError):
            self.create_palette(project['id'], personal.id, 'Invalid')
        with self.assertRaises(ValueError):
            self.create_palette(None, folder.id, 'Invalid')
        with self.assertRaises(ValueError):
            PaletteService._resolve_folder_path(self.owner.id, ['Unknown'], self.session)

    def test_create_project_palette_from_frontend_payload(self):
        from app.api.projects import create_project_palette
        project = self.project()
        data = PaletteCreate.model_validate({'title': 'Untitled', 'description': '', 'palette_colors': [{'hex': 'AABBCC'}]})
        result = create_project_palette(project['id'], data, self.session, self.owner)
        self.assertEqual(result['project_id'], project['id'])
        self.assertEqual(result['folder_path'], [])
        _, colors = PaletteService.get_latest_palette_snapshot(result['id'], self.session)
        self.assertEqual([(c.hex, c.label) for c in colors], [('AABBCC', None)])

    def test_copy_accessible_palette_without_modifying_original(self):
        from app.schemas.project import ProjectPaletteAdd
        project = self.project()
        source = self.create_palette(user=self.other.id, title='OtherPalette')
        copied = Content.add_palette(project['id'], self.owner.id, ProjectPaletteAdd(
            source_palette_id=source.id, title='Copy', description='Copy'), self.session)
        self.assertNotEqual(source.id, copied.id)
        self.assertEqual(copied.project_id, project['id'])
        self.assertIsNone(self.session.get(Palette, source.id).project_id)
        self.assertEqual(self.session.get(Palette, source.id).user_id, self.other.id)
        _, colors = PaletteService.get_latest_palette_snapshot(copied.id, self.session)
        self.assertEqual([(c.hex, c.label) for c in colors], [('AABBCC', 'Original')])
        self.assert_status(404, Content.add_palette, project['id'], self.owner.id, ProjectPaletteAdd(
            source_palette_id=source.id, mode='move', title='Move', description=''), self.session)

    def test_copy_requires_access_to_source_and_write_access_to_destination(self):
        from app.schemas.project import ProjectPaletteAdd
        project = self.project()
        source = self.create_palette(project['id'], title='PrivateSource')
        self.assert_status(404, Content.add_palette, project['id'], self.other.id, ProjectPaletteAdd(
            source_palette_id=source.id, title='Copy', description=''), self.session)
        public = self.create_palette(user=self.other.id)
        self.grant(project['id'], 'read')
        self.assert_status(403, Content.add_palette, project['id'], self.member.id, ProjectPaletteAdd(
            source_palette_id=public.id, title='Copy', description=''), self.session)
        target = project_tests.Service.create(project_tests.ProjectCreate(title='Target'), self.other.id, self.session)
        self.assert_status(404, Content.add_palette, target['id'], self.other.id, ProjectPaletteAdd(
            source_palette_id=source.id, title='Copy', description=''), self.session)

    def test_add_unsaved_palette_colors_to_project(self):
        from app.schemas.project import ProjectPaletteAdd
        project = self.project()
        palette = Content.add_palette(project['id'], self.owner.id, ProjectPaletteAdd(
            title='Draft', description='From editor', palette_colors=[{'hex': '112233', 'label': 'Custom'}]), self.session)
        _, colors = PaletteService.get_latest_palette_snapshot(palette.id, self.session)
        self.assertEqual([(c.hex, c.label) for c in colors], [('112233', 'Custom')])

    def test_snapshot_authors_and_batched_project_counts(self):
        from sqlalchemy import event
        from app.services.project import ProjectService
        project = self.project()
        palette = self.create_palette(project['id'])
        first, _ = PaletteService.get_latest_palette_snapshot(palette.id, self.session)
        self.assertEqual(first.author, self.owner.username)
        self.grant(project['id'], 'read', 'edit_palettes')
        saved, _ = PaletteService.save_palette(palette.id, PaletteSnapshotSave(
            parent_snapshot_id=first.id, palette_colors=[PaletteColorSave(hex='112233')]), self.member.id, self.session)
        self.assertEqual(saved.author, self.member.username)
        self.assertEqual(PaletteService._snapshot_to_commit(saved, self.session)['author'], self.member.username)
        branch_snapshot, _ = PaletteService.save_palette(palette.id, PaletteSnapshotSave(
            parent_snapshot_id=saved.id, create_branch=True, branch_title='Experiment',
            palette_colors=[PaletteColorSave(hex='445566')]), self.member.id, self.session)
        _, merged, _ = PaletteService.merge_branch(palette.id, branch_snapshot.branch_id, self.owner.id, self.session)
        self.assertEqual(branch_snapshot.author, self.member.username)
        self.assertEqual(merged.author, self.owner.username)
        viewer_id = self.owner.id
        queries = []
        def record(*args):
            queries.append(args[2])
        event.listen(self.engine, 'before_cursor_execute', record)
        try:
            rows = ProjectService.list_visible(self.session, viewer_id, mine=True)
        finally:
            event.remove(self.engine, 'before_cursor_execute', record)
        self.assertEqual(len(queries), 2)
        self.assertEqual(rows[0]['palette_count'], 1)
        self.assertEqual(rows[0]['bookmark_count'], 0)
        self.assertEqual(rows[0]['member_count'], 2)

    def test_private_history_and_legacy_id_access(self):
        project = self.project()
        palette = self.create_palette(project['id'])
        self.assert_status(404, PaletteService.get_palette, palette.id, self.session, self.other.id)
        self.assert_status(404, Content.history, self.owner.username, project['slug'], palette.title, None, self.session)
        history = Content.history(self.owner.username, project['slug'], palette.title, self.owner.id, self.session)
        self.assertEqual(history['project']['id'], project['id'])
        self.assertIn('edit_palettes', history['project']['permissions'])
        with self.assertRaises(ValueError):
            PaletteService.get_palette_by_path(self.owner.username, palette.title, self.session)

    def test_collaborator_edits_but_cannot_delete_palette(self):
        project = self.project()
        palette = self.create_palette(project['id'])
        base, _ = PaletteService.get_latest_palette_snapshot(palette.id, self.session)
        self.grant(project['id'], 'read', 'edit_palettes')
        saved, changes = PaletteService.save_palette(palette.id, PaletteSnapshotSave(
            parent_snapshot_id=base.id, palette_colors=[PaletteColorSave(hex='AABBCC', label='Edited')]), self.member.id, self.session)
        self.assertEqual(PaletteService.get_diff_counts(saved.id, self.session), (0, 0, 1))
        with self.assertRaises(PermissionError):
            PaletteService.delete_palette(palette.id, self.member.id, self.session)
        self.assert_status(403, Content.create_folder, project['id'], self.member.id, FolderCreate(name='No'), self.session)

    def test_folders_cycle_rename_and_move_root(self):
        project = self.project()
        root = Content.create_folder(project['id'], self.owner.id, FolderCreate(name='Root'), self.session)
        child = Content.create_folder(project['id'], self.owner.id, FolderCreate(name='Child', parent_folder_id=root.id), self.session)
        palette = self.create_palette(project['id'], child.id)
        self.assert_status(400, Content.update_folder, project['id'], root.id, self.owner.id, FolderUpdate(parent_folder_id=child.id), self.session)
        Content.update_folder(project['id'], root.id, self.owner.id, FolderUpdate(name='Renamed'), self.session)
        self.assertEqual(Content.palettes(project['id'], self.owner.id, self.session)[0]['folder_path'], ['Renamed', 'Child'])
        Content.delete_folder(project['id'], root.id, self.owner.id, 'move_root', self.session)
        self.assertEqual(Content.folders(project['id'], self.owner.id, self.session), [])
        self.assertIsNone(self.session.get(Palette, palette.id).folder_id)
        self.assertEqual(self.session.get(Palette, palette.id).project_id, project['id'])

    def test_import_remove_keeps_history_and_checks_conflicts(self):
        project = self.project()
        palette = self.create_palette()
        snapshot, _ = PaletteService.get_latest_palette_snapshot(palette.id, self.session)
        Content.import_palette(project['id'], palette.id, self.owner.id, PaletteUpdate(), self.session)
        self.assertEqual(self.session.get(Palette, palette.id).project_id, project['id'])
        removed = Content.remove_palette(project['id'], palette.id, self.owner.id, PaletteUpdate(), self.session)
        self.assertIsNone(removed.project_id)
        self.assertIsNotNone(self.session.get(Palette_Snapshot, snapshot.id))

    def test_remove_project_palette_delete_strategy(self):
        from app.api.projects import remove_project_palette
        project = self.project()
        palette = self.create_palette(project['id'])
        palette_id = palette.id
        result = remove_project_palette(project['id'], palette_id, self.session, self.owner, strategy='delete')
        self.assertEqual(result, {'palette_id': palette_id, 'deleted': True})
        self.session.expire_all()
        self.assertIsNone(self.session.get(Palette, palette_id))
        self.assertEqual(self.session.exec(select(Palette_Snapshot).where(Palette_Snapshot.palette_id == palette_id)).all(), [])

    def test_remove_project_palette_requires_creator_for_deletion(self):
        project = self.project()
        palette = self.create_palette(project['id'])
        self.grant(project['id'], 'read', 'remove_palettes')
        self.assert_status(403, Content.remove_palette, project['id'], palette.id, self.member.id,
                           PaletteUpdate(), self.session, 'delete')
        self.assertEqual(self.session.get(Palette, palette.id).project_id, project['id'])

    def test_remove_project_palette_checks_strategy_and_permissions(self):
        project = self.project()
        palette = self.create_palette(project['id'])
        self.assert_status(422, Content.remove_palette, project['id'], palette.id, self.owner.id,
                           PaletteUpdate(), self.session, 'invalid')
        self.grant(project['id'], 'read')
        self.assert_status(403, Content.remove_palette, project['id'], palette.id, self.member.id,
                           PaletteUpdate(), self.session, 'make_public')

    def test_project_deletion_removes_palettes_folders_and_versions(self):
        project = self.project()
        folder = Content.create_folder(project['id'], self.owner.id, FolderCreate(name='Folder'), self.session)
        palette = self.create_palette(project['id'], folder.id)
        pid, fid = palette.id, folder.id
        remove(project['id'], ProjectDelete(confirm_title=project['title']), self.session, self.owner)
        self.session.expire_all()
        self.assertIsNone(self.session.get(Palette, pid))
        self.assertIsNone(self.session.get(Folder, fid))
        self.assertEqual(self.session.exec(select(Palette_Snapshot).where(Palette_Snapshot.palette_id == pid)).all(), [])

    def test_private_project_does_not_leak_in_search_or_discover(self):
        project = self.project()
        private = self.create_palette(project['id'], title='Secret')
        public = self.create_palette(title='Public')
        self.assertEqual(PaletteService.search_palettes(self.session, title_query='Secret'), [])
        recent = PaletteService.get_recent_palette_items(self.session)
        self.assertNotIn(private.id, {p['id'] for p in recent})
        self.assertIn(public.id, {p['id'] for p in recent})

    def test_account_deletion_cleans_owned_projects_content(self):
        from app.services.user import UserService
        from app.models.user import User
        project = self.project()
        folder = Content.create_folder(project['id'], self.owner.id, FolderCreate(name='Folder'), self.session)
        palette = self.create_palette(project['id'], folder.id)
        pid, uid = palette.id, self.owner.id
        UserService.delete_me(uid, self.session)
        self.assertIsNone(self.session.get(User, uid))
        self.assertIsNone(self.session.get(Palette, pid))
