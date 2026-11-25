import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlmodel import SQLModel, Session, create_engine

from app.api import projects
from app.models.colleague import Colleague
from app.models.project import PERMISSIONS
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectDelete, ProjectMemberInput
from app.services.colleague import ColleagueService
from app.services.project import ProjectService as Service


@compiles(BigInteger, "sqlite")
def sqlite_bigint(element, compiler, **kw):
    return "INTEGER"


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.owner = User(username="owner", email="owner@example.com", password="unused")
        self.member = User(username="member", email="member@example.com", password="unused")
        self.other = User(username="other", email="other@example.com", password="unused")
        self.session.add_all([self.owner, self.member, self.other])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def project(self, private=True):
        return Service.create(ProjectCreate(title="Été Branding", private=private), self.owner.id, self.session)

    def assert_status(self, code, fn, *args):
        with self.assertRaises(HTTPException) as error:
            fn(*args)
        self.assertEqual(error.exception.status_code, code)

    def test_slug_and_visibility(self):
        project = self.project()
        self.assertEqual(project["slug"], "ete-branding")
        self.assertEqual(self.project()["slug"], "ete-branding-2")
        self.assertEqual(Service.list_visible(self.session), [])
        self.assertEqual(len(Service.list_visible(self.session, self.owner.id, mine=True)), 2)
        for permission in PERMISSIONS:
            Service.require(project["id"], self.owner.id, self.session, permission)
            self.assert_status(404, Service.require, project["id"], self.other.id, self.session, permission)
        public = self.project(private=False)
        Service.require(public["id"], None, self.session)
        for permission in PERMISSIONS[1:]:
            self.assert_status(403, Service.require, public["id"], self.other.id, self.session, permission)

    @patch("app.services.project.MailService.notify", return_value=True)
    def test_invitation_does_not_grant_access_until_accepted(self, mail):
        project = self.project()
        self.session.add(Colleague(from_user_id=self.owner.id, to_user_id=self.member.id, status="accepted"))
        self.session.commit()
        data = ProjectMemberInput(username=self.member.username, permissions=["edit_palettes"])
        invitation = Service.invite(project["id"], self.owner.id, data, self.session)
        mail.assert_called_once()
        self.assert_status(404, Service.require, project["id"], self.member.id, self.session)
        self.assert_status(404, Service.respond, invitation["id"], self.other.id, True, self.session)
        self.assert_status(409, Service.invite, project["id"], self.owner.id, data, self.session)
        mail.assert_called_once()
        self.assertEqual(len(Service.invitations(self.member.id, self.session)), 1)
        Service.respond(invitation["id"], self.member.id, True, self.session)
        self.assertEqual(set(Service.require(project["id"], self.member.id, self.session) and
                             Service.list_visible(self.session, self.member.id, mine=True)[0]["permissions"]),
                         {"read", "edit_palettes"})
        self.assert_status(403, Service.require, project["id"], self.member.id, self.session, "manage_access")
        self.assert_status(403, projects.remove, project["id"], ProjectDelete(confirm_title=project["title"]), self.session, self.member)
        members = Service.members(project["id"], self.member.id, self.session)
        self.assertTrue(all("email" not in user and "profile_color" in user for user in members))
        projects.remove_member(project["id"], self.member.username, self.session, self.owner)
        self.assert_status(404, Service.require, project["id"], self.member.id, self.session)

    @patch("app.services.project.MailService.project_invitation", return_value=True)
    def test_invite_non_colleague(self, mail):
        project = self.project()
        invitation = Service.invite(project["id"], self.owner.id,
                                   ProjectMemberInput(username="other", permissions=["read"]), self.session)
        self.assertEqual(invitation["project_id"], project["id"])
        self.assertEqual(len(Service.invitations(self.other.id, self.session)), 1)
        mail.assert_called_once()


    @patch("app.services.colleague.MailService.colleague_request", return_value=True)
    def test_colleague_email_only_for_new_request(self, mail):
        ColleagueService.send_or_accept(self.owner.id, self.member.username, self.session)
        ColleagueService.send_or_accept(self.owner.id, self.member.username, self.session)
        ColleagueService.send_or_accept(self.member.id, self.owner.username, self.session)
        mail.assert_called_once_with(self.member.email, self.owner.username)

    def test_delete_requires_title_and_creator(self):
        project = self.project()
        self.assert_status(400, projects.remove, project["id"], ProjectDelete(confirm_title="wrong"), self.session, self.owner)
        projects.remove(project["id"], ProjectDelete(confirm_title=project["title"]), self.session, self.owner)
        self.assert_status(404, Service.require, project["id"], self.owner.id, self.session)

    def test_leave_project_for_every_member_role(self):
        from app.models.project import ProjectAccess
        from sqlmodel import select
        project = self.project()
        for permissions in (['read'], ['read', 'add_palettes', 'edit_palettes'], list(PERMISSIONS), ['add_bookmarks']):
            with self.subTest(permissions=permissions):
                for permission in permissions:
                    self.session.add(ProjectAccess(project_id=project['id'], user_id=self.member.id, permission=permission))
                self.session.commit()
                projects.leave_project(project['id'], self.session, self.member)
                self.assertEqual(self.session.exec(select(ProjectAccess).where(
                    ProjectAccess.project_id == project['id'], ProjectAccess.user_id == self.member.id)).all(), [])
                self.assertEqual(Service.list_visible(self.session, self.member.id, mine=True), [])
                self.assert_status(404, Service.require, project['id'], self.member.id, self.session)
                self.assertIn('manage_access', Service.permissions(Service.require(project['id'], self.owner.id, self.session), self.owner.id, self.session))

    def test_creator_and_outsider_cannot_leave(self):
        project = self.project()
        self.assert_status(403, Service.leave, project['id'], self.owner.id, self.session)
        self.assert_status(404, Service.leave, project['id'], self.other.id, self.session)
        self.assert_status(404, Service.leave, 999999, self.other.id, self.session)

    @patch("app.services.project.MailService.project_invitation", return_value=True)
    def test_pending_members_visible_only_to_access_managers(self, mail):
        from app.models.project import ProjectAccess
        project = self.project(private=False)
        invitation = Service.invite(project['id'], self.owner.id,
                                   ProjectMemberInput(username=self.other.username, permissions=['read']), self.session)
        owner_list = Service.members(project['id'], self.owner.id, self.session)
        pending = [member for member in owner_list if member['pending']]
        self.assertEqual([member['username'] for member in pending], [self.other.username])
        self.assertEqual(pending[0]['permissions'], [])
        self.assertNotIn('email', pending[0])
        self.assertEqual(Service.permissions(Service.require(project['id'], self.owner.id, self.session), self.other.id, self.session), [])
        for viewer in (None, self.other.id):
            self.assertFalse(any(member['pending'] for member in Service.members(project['id'], viewer, self.session)))
        self.session.add(ProjectAccess(project_id=project['id'], user_id=self.member.id, permission='read'))
        self.session.commit()
        self.assertFalse(any(member['pending'] for member in Service.members(project['id'], self.member.id, self.session)))
        self.session.add(ProjectAccess(project_id=project['id'], user_id=self.member.id, permission='manage_access'))
        self.session.commit()
        self.assertTrue(any(member['pending'] for member in Service.members(project['id'], self.member.id, self.session)))
        Service.respond(invitation['id'], self.other.id, True, self.session)
        accepted = [member for member in Service.members(project['id'], self.owner.id, self.session) if member['id'] == self.other.id]
        self.assertEqual(len(accepted), 1)
        self.assertFalse(accepted[0]['pending'])

    @patch("app.services.project.MailService.project_invitation", return_value=True)
    def test_pending_invitation_can_be_cancelled_without_granting_access(self, mail):
        project = self.project()
        Service.invite(project['id'], self.owner.id,
                       ProjectMemberInput(username=self.other.username, permissions=['read']), self.session)
        projects.remove_member(project['id'], self.other.username, self.session, self.owner)
        self.assertFalse(any(member['pending'] for member in Service.members(project['id'], self.owner.id, self.session)))
        self.assertEqual(Service.invitations(self.other.id, self.session), [])
        self.assert_status(404, Service.require, project['id'], self.other.id, self.session)

    @patch("app.services.mail.MailService.send_email", side_effect=OSError("SMTP unavailable"))
    def test_mail_failure_does_not_revert_request(self, mail):
        with self.assertLogs("rgbast.mail", level="ERROR"):
            status, _, _ = ColleagueService.send_or_accept(self.owner.id, self.member.username, self.session)
        self.assertEqual(status, "pending")
