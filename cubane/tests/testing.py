# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase


class ShouldTestInProductionModeTestCase(CubaneTestCase):
    """
    Test should run in production mode by default.
    """
    def test_should_test_in_production_mode_by_default(self):
        from django.conf import settings
        self.assertFalse(settings.DEBUG)
        self.assertTrue(settings.PREPEND_WWW)
        self.assertFalse(settings.MINIFY_RESOURCES)