# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.format_tags import *


class LibNotXTestCase(CubaneTestCase):
    """
    cubane.templatetags.format_tags.not_x()
    """
    def test_should_return_negation_of_value(self):
        self.assertEqual(not_x(True), False)


class LibAsIntTestCase(CubaneTestCase):
    """
    cubane.templatetags.format_tags.as_int()
    """
    def test_should_return_int(self):
        self.assertEqual(as_int('True'), 1)
        self.assertEqual(as_int(True), 1)
        self.assertEqual(as_int('5'), 5)
        self.assertEqual(as_int(None), 0)
        self.assertEqual(as_int('0'), 0)
        self.assertEqual(as_int(''), 0)
        self.assertEqual(as_int(False), 0)