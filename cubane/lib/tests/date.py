# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.date import humanize_days
from cubane.lib.date import get_monthly_renewal_date
from cubane.lib.date import get_yearly_renewal_date
from freezegun import freeze_time
import datetime


@freeze_time('2016-06-01')
class LibDateHumanizeDaysTestCase(CubaneTestCase):
    """
    cubane.lib.date.humanize_days()
    """
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


class LibDateGetMonthlyRenewalDateTestCase(CubaneTestCase):
    """
    cubane.lib.date.get_monthly_renewal_date()
    """
    def test_should_renew_on_same_day_of_next_month(self):
        self.assertEqual(
            datetime.date(2018, 8, 14),
            get_monthly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2018, 7, 28))
        )


    def test_should_renew_on_same_month(self):
        self.assertEqual(
            datetime.date(2018, 8, 14),
            get_monthly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2018, 8, 11))
        )


    def test_should_renew_today_next_month(self):
        self.assertEqual(
            datetime.date(2018, 9, 14),
            get_monthly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2018, 8, 14))
        )


    def test_should_renew_on_start_date(self):
        self.assertEqual(
            datetime.date(2018, 8, 14),
            get_monthly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2018, 7, 14))
        )


    def test_should_renew_on_start_date_if_date_is_before_start_date(self):
        self.assertEqual(
            datetime.date(2018, 7, 14),
            get_monthly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2016, 3, 9))
        )


    def test_should_adjust_if_day_of_month_does_not_exist(self):
        self.assertEqual(
            datetime.date(2018, 3, 1),
            get_monthly_renewal_date(datetime.date(2018, 1, 31), datetime.date(2018, 2, 22))
        )


    def test_should_adjust_if_day_of_month_for_next_month_does_not_exist(self):
        self.assertEqual(
            datetime.date(2018, 3, 1),
            get_monthly_renewal_date(datetime.date(2018, 1, 30), datetime.date(2018, 1, 31))
        )


class LibDateGetYearlyRenewalDateTestCase(CubaneTestCase):
    """
    cubane.lib.date.get_yearly_renewal_date()
    """
    def test_should_renew_on_same_day_of_month_next_year(self):
        self.assertEqual(
            datetime.date(2019, 7, 14),
            get_yearly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2018, 7, 24))
        )


    def test_should_renew_on_same_day_of_month_same_year(self):
        self.assertEqual(
            datetime.date(2019, 7, 14),
            get_yearly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2019, 3, 13))
        )


    def test_should_renew_today_next_year(self):
        self.assertEqual(
            datetime.date(2020, 7, 14),
            get_yearly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2019, 7, 14))
        )


    def test_should_renew_on_start_date(self):
        self.assertEqual(
            datetime.date(2019, 7, 14),
            get_yearly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2018, 7, 14))
        )


    def test_should_renew_on_start_date_if_date_is_before_start_date(self):
        self.assertEqual(
            datetime.date(2018, 7, 14),
            get_yearly_renewal_date(datetime.date(2018, 7, 14), datetime.date(2016, 3, 9))
        )


    def test_should_adjust_if_date_does_not_exist(self):
        self.assertEqual(
            datetime.date(2021, 3, 1),
            get_yearly_renewal_date(datetime.date(2020, 2, 29), datetime.date(2020, 3, 14))
        )