import unittest
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Session, SQLModel, create_engine

from app.controllers.user import UserController
from app.models.user import User
from app.schemas.colleague import ColleagueUserResponse
from app.schemas.search import UserSearchItem
from app.schemas.user import UserCreate, UserUpdateMe
from app.services.auth import AuthService
from app.services.colleague import ColleagueService
from app.services.user import UserService


@compiles(BigInteger, "sqlite")
def sqlite_bigint(element, compiler, **kw):
    return "INTEGER"


class ProfileColorTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(UserUpdateMe(profile_color="abcdef").profile_color, "ABCDEF")
        for value in ("#AABBCC", "12345", "1234567", "zzzzzz", "", 123456):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                UserUpdateMe(profile_color=value)

    def test_registration_update_and_public_responses(self):
        engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            user = UserService.create_user(UserCreate(
                username="profile_test", email="profile@example.com", password="Test-password1!", birthdate=None,
            ), session)
            self.assertRegex(user.profile_color, r"^[0-9A-F]{6}$")
            original = user.profile_color
            response = UserController.update_me_control(user.id, UserUpdateMe(firstname="Test"), session)
            self.assertEqual(response.profile_color, original)
            response = UserController.update_me_control(user.id, UserUpdateMe(profile_color="abcdef"), session)
            self.assertEqual(response.profile_color, "ABCDEF")
            session.expire_all()
            self.assertEqual(session.get(User, user.id).profile_color, "ABCDEF")
            public = UserService.get_user_from_username(user.username, session)
            self.assertEqual(public.profile_color, "ABCDEF")
            self.assertNotIn("email", public.model_dump())
            # Check-auth must still include the private email and the color,
            # without passing duplicate fields from the public response.
            with patch.object(AuthService, "_get_secret_key", return_value="test-secret-at-least-thirty-two-bytes"):
                token = AuthService.create_access_token_for_user(user)
                me = AuthService.check_auth(token, session)
            self.assertEqual((me.email, me.profile_color), (user.email, "ABCDEF"))
            for schema in (ColleagueUserResponse, UserSearchItem):
                payload = schema.model_validate(user.model_dump())
                self.assertEqual(payload.profile_color, "ABCDEF")
                self.assertNotIn("email", payload.model_dump())
            self.assertEqual(ColleagueService._summarize_user(user)["profile_color"], "ABCDEF")
        engine.dispose()

    def test_model_generates_independent_colors(self):
        colors = {User().profile_color for _ in range(20)}
        self.assertGreater(len(colors), 1)
        self.assertTrue(all(len(color) == 6 for color in colors))
