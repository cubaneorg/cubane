# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.loop_tags import *


class LibGetItemAfterDivisibleTestCase(CubaneTestCase):
    """
    cubane.templatetags.loop_tags.get_item_after_divisible()
    """
    def test_should_return_true(self):
        self.assertEqual(get_item_after_divisible(5, 2), True)


    def test_should_convert_count_to_int_and_return_false(self):
        self.assertEqual(get_item_after_divisible('6', 2), False)


    def test_should_convert_divisiblybynumber_to_int_and_return_true(self):
        self.assertEqual(get_item_after_divisible('9', '4'), True)


class LibNumberToRangeTestCase(CubaneTestCase):
    """
    cubane.templatetags.loop_tags.number_to_range()
    """
    def test_should_return_range(self):
        self.assertEqual(len(number_to_range(10)), 10)


    def test_should_convert_string_to_int_and_return_range(self):
        self.assertEqual(len(number_to_range('10')), 10)