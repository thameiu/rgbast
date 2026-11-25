import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Session, SQLModel, create_engine

from app.models.project import Project, ProjectAccess
from app.models.user import User
from app.schemas.color_bookmark import ColorBookmarkCreate, ColorBookmarkUpsert
from app.services.color_bookmark import ColorBookmarkService as Service
from app.controllers.color_bookmark import ColorBookmarkController


@compiles(BigInteger, 'sqlite')
def sqlite_bigint(element, compiler, **kw):
    return 'INTEGER'


class BookmarkDuplicateTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.owner = User(username='owner', email='owner@example.com', password='unused')
        self.other = User(username='other', email='other@example.com', password='unused')
        self.session.add_all([self.owner, self.other])
        self.session.flush()
        self.project = Project(title='Private', slug='private', creator_id=self.owner.id, private=True)
        self.session.add(self.project)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def create(self, label='Same', project_id=None, user=None):
        return Service.create(user or self.owner.id, ColorBookmarkCreate(
            hex='#aabbcc', label=label, project_id=project_id), self.session)

    def denied(self, status, fn, *args):
        with self.assertRaises(HTTPException) as error:
            fn(*args)
        self.assertEqual(error.exception.status_code, status)

    def test_create_duplicate_and_target_update_delete_by_id(self):
        first, second = self.create(), self.create()
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(len(Service.list_by_user_id(self.owner.id, self.session, 'AABBCC')), 2)
        response = ColorBookmarkController.list_mine_control(self.owner.id, self.session, 'AABBCC')
        self.assertEqual({b.id for b in response.bookmarks}, {first.id, second.id})
        Service.update(self.owner.id, first.id, ColorBookmarkUpsert(label='Changed'), self.session)
        self.session.expire_all()
        self.assertEqual(Service.get(second.id, self.owner.id, self.session).label, 'Same')
        result = Service.delete(self.owner.id, second.id, self.session)
        self.assertEqual(result['id'], second.id)
        self.assertEqual([b.id for b in Service.list_by_user_id(self.owner.id, self.session)], [first.id])
        self.assertEqual(Service.get(first.id, self.owner.id, self.session).label, 'Changed')

    def test_no_access_to_another_users_personal_bookmark(self):
        bookmark = self.create()
        self.denied(404, Service.get, bookmark.id, self.other.id, self.session)
        self.denied(404, Service.update, self.other.id, bookmark.id, ColorBookmarkUpsert(label='Unauthorized'), self.session)
        self.denied(404, Service.delete, self.other.id, bookmark.id, self.session)

    def test_multiple_duplicates_in_project_and_personal_are_separate(self):
        personal = self.create()
        first = self.create(project_id=self.project.id)
        second = self.create(project_id=self.project.id)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual([b.id for b in Service.list_by_user_id(self.owner.id, self.session)], [personal.id])
        self.assertEqual(len(Service.list_by_user_id(self.owner.id, self.session, project_id=self.project.id)), 2)
        _, public = Service.list_by_username(self.owner.username, self.session)
        self.assertEqual([b.id for b in public], [personal.id])
        self.denied(404, Service.list_by_user_id, self.other.id, self.session, None, self.project.id)

    def test_project_permissions_apply_independently(self):
        bookmark = self.create(project_id=self.project.id)
        for permission in ['read', 'add_bookmarks']:
            self.session.add(ProjectAccess(project_id=self.project.id, user_id=self.other.id, permission=permission))
        self.session.commit()
        created = self.create(project_id=self.project.id, user=self.other.id)
        self.assertEqual(created.user_id, self.other.id)
        self.denied(403, Service.update, self.other.id, bookmark.id, ColorBookmarkUpsert(label='No'), self.session)
        self.denied(403, Service.delete, self.other.id, created.id, self.session)
        self.session.add(ProjectAccess(project_id=self.project.id, user_id=self.other.id, permission='edit_bookmarks'))
        self.session.commit()
        Service.update(self.other.id, bookmark.id, ColorBookmarkUpsert(label='Shared edit'), self.session)
        self.assertEqual(Service.get(bookmark.id, self.owner.id, self.session).label, 'Shared edit')
        self.denied(403, Service.delete, self.other.id, bookmark.id, self.session)
        self.session.add(ProjectAccess(project_id=self.project.id, user_id=self.other.id, permission='remove_bookmarks'))
        self.session.commit()
        Service.delete(self.other.id, bookmark.id, self.session)
        self.assertEqual(len(Service.list_by_user_id(self.other.id, self.session, project_id=self.project.id)), 1)

    def test_public_project_read_does_not_grant_write(self):
        self.project.private = False
        self.session.add(self.project)
        self.session.commit()
        self.create(project_id=self.project.id)
        self.assertEqual(len(Service.list_by_user_id(None, self.session, project_id=self.project.id)), 1)
        self.denied(403, self.create, 'No', self.project.id, self.other.id)

    def test_request_validation(self):
        self.assertEqual(ColorBookmarkCreate(hex='#aabbcc', label='  Name  ').hex, 'AABBCC')
        for data in [dict(hex='xyz', label='Name'), dict(hex='AABBCC', label='   ')]:
            with self.assertRaises(ValidationError):
                ColorBookmarkCreate(**data)

    def test_project_deletion_removes_all_duplicate_bookmarks(self):
        from app.api.projects import remove
        from app.schemas.project import ProjectDelete
        from app.models.color_bookmark import Color_Bookmark
        personal = self.create()
        first = self.create(project_id=self.project.id)
        second = self.create(project_id=self.project.id)
        first_id, second_id = first.id, second.id
        remove(self.project.id, ProjectDelete(confirm_title=self.project.title), self.session, self.owner)
        self.session.expire_all()
        self.assertIsNone(self.session.get(Color_Bookmark, first_id))
        self.assertIsNone(self.session.get(Color_Bookmark, second_id))
        self.assertIsNotNone(self.session.get(Color_Bookmark, personal.id))
