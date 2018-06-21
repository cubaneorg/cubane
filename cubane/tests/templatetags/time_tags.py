# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.time_tags import *
from datetime import datetime, date, timedelta


class LibGetTimeFromNow(CubaneTestCase):
    """
    cubane.templatetags.time_tags.get_time_from_now()
    """
    def test_should_return_days(self):
        time = datetime.now() - timedelta(days=3)
        self.assertEqual(get_time_from_now(time), '3 days ago')


    def test_should_return_hours(self):
        time = datetime.now() - timedelta(hours=4)
        self.assertEqual(get_time_from_now(time), '4 hours ago')


    def test_should_return_minutes(self):
        time = datetime.now() - timedelta(minutes=1)
        self.assertEqual(get_time_from_now(time), '1 minute ago')


    def test_should_return_seconds(self):
        time = datetime.now() - timedelta(seconds=5)
        self.assertEqual(get_time_from_now(time), 'few seconds ago')


    def test_should_accept_date(self):
        time = date.today() - timedelta(days=3)
        self.assertEqual(get_time_from_now(time), '3 days ago')


    def test_should_return_empty_string_if_no_time_given(self):
        self.assertEqual(get_time_from_now(None), '')