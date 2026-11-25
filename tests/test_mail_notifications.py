import unittest
from unittest.mock import patch

from app.services.mail import MailService


class MailNotificationTests(unittest.TestCase):
    @patch.dict('os.environ', {'FRONTEND_URL': 'https://rgbast.test/', 'LANG': 'fr_FR.UTF-8'})
    @patch.object(MailService, 'send_email', return_value=True)
    def test_colleague_request_is_english_and_links_to_sender(self, send_email):
        self.assertTrue(MailService.colleague_request('recipient@example.com', 'alice'))
        send_email.assert_called_once_with(
            'recipient@example.com',
            'RGBAST - New colleague request',
            'alice has sent you a colleague request on RGBAST.\n'
            'Sign in to view their profile and accept or decline the request.\n\n'
            'https://rgbast.test/users/alice',
        )

    @patch.dict('os.environ', {'FRONTEND_URL': 'https://rgbast.test', 'LANG': 'fr_FR.UTF-8'})
    @patch.object(MailService, 'send_email', return_value=True)
    def test_project_invitation_is_english_and_links_to_invitations(self, send_email):
        self.assertTrue(MailService.project_invitation('recipient@example.com', 'alice', 'Brand'))
        send_email.assert_called_once_with(
            'recipient@example.com',
            'RGBAST - Project invitation',
            'alice has invited you to join the project "Brand" on RGBAST.\n'
            'Sign in and open Projects in your Atelier to accept or decline the invitation.\n'
            'You will receive access only after accepting the invitation.\n\n'
            'https://rgbast.test/atelier/projects',
        )
