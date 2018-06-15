# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.app import require_app


class LibAppRequireAppTestCase(CubaneTestCase):
    """
    cubane.lib.app.require_app()
    """
    @override_settings(DEBUG=True, TEST=False)
    def test_should_ignore_in_debug(self):
        require_app('test', 'cubane.doesnotexist')

    @override_settings(DEBUG=True)
    def test_should_pass_if_django_app_loaded(self):
        require_app('test', 'cubane.cms')


    @override_settings(DEBUG=True)
    def test_should_raise_if_django_app_not_loaded(self):
        with self.assertRaises(ImportError):
            require_app('test', 'cubane.doesnotexist')


    @override_settings(DEBUG=True)
    def test_should_pass_if_django_apps_loaded(self):
        require_app('test', ['cubane.cms', 'cubane.backend'])


    @override_settings(DEBUG=True)
    def test_should_pass_if_at_least_one_django_app_loaded(self):
        require_app('test', ['cubane.cms', 'cubane.doesnotexist'])


    @override_settings(DEBUG=True)
    def test_should_raise_if_django_apps_not_loaded(self):
        with self.assertRaises(ImportError):
            require_app('test', ['cubane.doesnotexist', 'cubane.doesnotexisteither'])