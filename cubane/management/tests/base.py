# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.file import file_get_contents
import os
import shutil
import glob


@CubaneTestCase.complex()
class ManagementTestCaseBase(CubaneTestCase):
    def setUp(self):
        # favicon
        favicon = os.path.join(settings.PUBLIC_HTML_ROOT, 'favicon.ico')
        if os.path.isfile(favicon):
            os.remove(favicon)

        # favicons versions
        favicons = os.path.join(settings.STATIC_ROOT, 'cubane', 'favicons')
        if os.path.isdir(favicons):
            shutil.rmtree(favicons)

        # compressed resources
        for filename in glob.glob(os.path.join(settings.STATIC_ROOT, '*')):
            if os.path.isfile(filename):
                os.remove(filename)


    def _assertStaticFile(self, filename, contains_content=None):
        path = os.path.join(settings.STATIC_ROOT, filename)
        self.assertTrue(os.path.isfile(path), 'expected file to exist: %s' % path)

        if contains_content:
            self.assertIn(contains_content, file_get_contents(path))