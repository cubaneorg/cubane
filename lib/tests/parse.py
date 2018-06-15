# coding=UTF-8
from __future__ import unicode_literals
import sys
from django.utils.dateparse import parse_datetime as django_parse_datetime
from cubane.tests.base import CubaneTestCase
from cubane.lib.parse import *


class LibParseIntTestCase(CubaneTestCase):
    """
    cubane.lib.parse.parse_int()
    """
    def test_should_parse_integer(self):
        self.assertEqual(13, parse_int('13'))


    def test_should_parse_negative_integer(self):
        self.assertEqual(-13, parse_int('-13'))


    def test_should_return_default_on_parsing_error(self):
        self.assertEqual(7, parse_int('13.7', 7))
        self.assertEqual(6, parse_int('not a number', 6))
        self.assertEqual(5, parse_int(None, 5))


    def test_default_should_be_zero(self):
        self.assertEqual(0, parse_int(None))


class LibParseIntListTestCase(CubaneTestCase):
    """
    cubane.lib.parse.parse_int_list()
    """
    def test_should_parse_list_of_integer_values(self):
        self.assertEqual([1, -2, 3], parse_int_list('  1, -2, 3  '))


    def test_should_ignore_parsing_errors(self):
        self.assertEqual([1, 2], parse_int_list('1, 1.5, not a number, 4 3 2, 2'))


class LibParseBoolTestCase(CubaneTestCase):
    """
    cubane.lib.parse.parse_bool()
    """
    def test_should_return_default(self):
        self.assertEqual(parse_bool(None, True), True)


    def test_should_return_true(self):
        self.assertEqual(parse_bool('1'), True)


    def test_should_return_false(self):
        self.assertEqual(parse_bool('0'), False)


class LibParseDatetimeTestCase(CubaneTestCase):
    """
    cubane.lib.parse.parse_datetime()
    """
    def test_should_return_django_datetime(self):
        self.assertEqual(parse_datetime('2016-05-05 14:10:00'), django_parse_datetime('2016-05-05 14:10:00'))


class LibParseUnixTimestampTestCase(CubaneTestCase):
    """
    cubane.lib.parse.parse_unix_timestamp()
    """
    def test_should_return_default(self):
        self.assertEqual(parse_unix_timestamp(sys.maxint, True), True)


    def test_should_return_datetime(self):
        self.assertEqual(parse_unix_timestamp(1446119936), parse_datetime('2015-10-29 11:58:56'))