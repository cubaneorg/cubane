# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.date import humanize_days
from freezegun import freeze_time


@freeze_time('2016-06-01')
class LibDateHumanizeDaysTestCase(CubaneTestCase):
    def test_should_skip_weeks_and_days_if_zero(self):
        self.assertEqual('2 years', humanize_days(730))


    def test_should_skip_years_if_less_than_a_year(self):
        self.assertEqual('11 months, 4 weeks, 2 days', humanize_days(364))


    def test_should_obmit_year_weeks_and_days_if_zero(self):
        self.assertEqual('11 months', humanize_days(334))


    def test_should_obmit_weeks_if_zero(self):
        self.assertEqual('1 year, 1 day', humanize_days(366))


    def test_should_skip_months_if_less_than_a_month(self):
        self.assertEqual('4 weeks, 1 day', humanize_days(29))


    def test_should_obmit_days_if_zero(self):
        self.assertEqual('1 year, 1 week', humanize_days(372))


    def test_should_represent_n_days(self):
        self.assertEqual('3 days', humanize_days(3))


    def test_should_represent_one_day(self):
        self.assertEqual('1 day', humanize_days(1))


    def test_should_represent_today(self):
        self.assertEqual('0 days', humanize_days(0))


    def test_should_represent_negative_day(self):
        self.assertEqual('1 day', humanize_days(-1))


    def test_should_represent_negative_days(self):
        self.assertEqual('3 days', humanize_days(-3))


    def test_should_represent_negative_weeks(self):
        self.assertEqual('4 weeks, 1 day', humanize_days(-29))


    def test_should_represent_negative_weeks(self):
        self.assertEqual('11 months, 4 weeks, 2 days', humanize_days(-365))


    def test_represent_years_only(self):
        self.assertEqual('1 year', humanize_days(366, display_years=True))


    def test_represent_months_only(self):
        self.assertEqual('1 month', humanize_days(32, display_months=True))


    def test_represent_weeks_only(self):
        self.assertEqual('3 weeks', humanize_days(23, display_weeks=True))


    def test_represent_days_only(self):
        self.assertEqual('2 days', humanize_days(23, display_days=True))