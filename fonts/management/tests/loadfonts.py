# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from cubane.tests.base import CubaneTestCase
from cubane.lib.file import folder_is_empty
import cubane.testapp as testapp
import os


@CubaneTestCase.complex()
class CubaneFontsManagementLoadFontsCommandTestCase(CubaneTestCase):
    def test_should_load_fonts(self):
        resources = testapp.RESOURCES
        try:
            # 100 does not exist, the font system should ignore it
            testapp.RESOURCES = [
                'font|Open Sans:300'
            ]

            # clear cache first
            call_command('clearfonts')
            self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))

            # call load fonts command
            call_command('loadfonts', refresh=True)

            # folder should contain data
            self.assertFalse(folder_is_empty(settings.CUBANE_FONT_ROOT))
        finally:
            testapp.RESOURCES = resources