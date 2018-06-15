# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.serve import serve_static_with_context


class LibServeStaticWithContextTestCase(CubaneTestCase):
    """
    cubane.lib.serve.serve_static_with_context()
    """
    def test_should_execute_template_with_context_from_apps(self):
        self.assertEqual(
            serve_static_with_context('body{background-color:{{background_color}};}'),
            'body{background-color:#123456;}'
        )


    @override_settings()
    def test_should_ignore_import_errors(self):
        installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = ['cubane.testapp', 'doesNotExist']
        try:
            self.test_should_execute_template_with_context_from_apps()
        finally:
            settings.INSTALLED_APPS = installed_apps