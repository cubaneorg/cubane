# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.message_tags import *


class LibFlashTestCase(CubaneTestCase):
    """
    cubane.templatetags.message_tags.flash()
    """
    def test_should_return_messages(self):
        messages = ['message 1', 'message 2', 'message 3']
        flash_messages = flash(messages)

        self.assertIsInstance(flash_messages, dict)
        self.assertEqual(len(flash_messages.get('messages')), 3)