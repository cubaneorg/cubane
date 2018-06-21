# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from cubane.tests.base import CubaneTestCase
from cubane.lib.file import folder_is_empty
from cubane.lib.file import ensure_dir
import cubane.testapp as testapp
import os


@CubaneTestCase.complex()
class CubaneFontsManagementClearFontsCommandTestCase(CubaneTestCase):
    def test_should_clear_font_cache_folder(self):
        # create test folder within font cache root path
        path = os.path.join(settings.CUBANE_FONT_ROOT, 'test')
        ensure_dir(path)
        try:
            # call clear command
            call_command('clearfonts')

            # font cache folder should be empty
            self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))
        finally:
            if os.path.isdir(path):
                os.rmdir(path)