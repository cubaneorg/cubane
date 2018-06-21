# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.tags import *


class LibGetStringTagsTestCase(CubaneTestCase):
    """
    cubane.lib.tags.get_string_tags()
    """
    def test_should_return_empty_array(self):
        self.assertEqual(get_string_tags(None), [])


    def test_should_return_tags(self):
        self.assertEqual(get_string_tags('#TESt #TaG #ValuE # #'), ['test', 'tag', 'value'])


class LibSetStringTags(CubaneTestCase):
    """
    cubane.lib.tags.set_string_tags()
    """
    def test_should_return_none(self):
        self.assertEqual(set_string_tags(None), None)
        self.assertEqual(set_string_tags([]), None)


    def test_should_return_string_tags(self):
        self.assertEqual(set_string_tags(['test', 'VALUE', 'TaG']), '#test #value #tag')