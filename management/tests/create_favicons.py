# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from cubane.management.tests.base import ManagementTestCaseBase
import os


class CubaneManagementCreateFaviconsCommandTestCase(ManagementTestCaseBase):
    def test_deploy_should_deploy_website(self):
        call_command('create_favicons')

        # verify /favicon.ico is present
        path = os.path.join(settings.PUBLIC_HTML_ROOT, 'favicon.ico')
        self.assertTrue(os.path.isfile(path))

        # verify that all favicon versions have been generated
        for favicon in settings.FAVICON_PNG_SIZES:
            path = os.path.join(settings.MEDIA_ROOT, 'favicons', favicon.get('filename'))
            self.assertTrue(os.path.isfile(path))