# coding=UTF-8
from __future__ import unicode_literals
import datetime
from dateutil.relativedelta import relativedelta
import collections


def humanize_days(
    days,
    display_years=False,
    display_months=False,
    display_weeks=False,
    display_days=False,
    year='year',
    month='month',
    week='week',
    day='day',
    sep=', ',
    last_sep=', '):
    """
    Return a humanised representation of the time differences between now and the given
    amount of days in the future or past. Missing components are not presented.
    """
    fdays = _format_days(days, year, month, week, day)

    if fdays[0] > 0 and display_years:
        return _pluralize(fdays[0][1], year)

    if fdays[1] > 0 and display_months:
        return _pluralize(fdays[1][1], month)

    if fdays[2] > 0 and display_weeks:
        return _pluralize(fdays[2][1], week)

    if fdays[3] > 0 and display_days:
        return _pluralize(fdays[3][1], day)

    parts = [_pluralize(number, label) for label, number in fdays if number > 0]

    if len(parts) > 1:
        s =  sep.join(parts[:-1]) + last_sep + parts[-1]
    elif len(parts) == 1:
        s = parts[0]
    else:
        s = _pluralize(0, day)

    return s


def _pluralize(n, name):
    """
    Return the given number and the name of the time component, for example day(s).
    """
    if not isinstance(name, list):
        name = [name, '%ss' % name]

    return '%d %s' % (n, name[1] if abs(n) > 1 or n == 0 else name[0])


def _format_days(
    days,
    year,
    month,
    week,
    day):
    """
    Split the time difference between now and given amount of days in the
    future or past into individual components, such as years, months, weeks and
    days.
    """
    t = datetime.date.today()
    if days > 0:
        t2 = t + datetime.timedelta(days=days)
        tdelta = relativedelta(t2, t)
    else:
        t2 = t - datetime.timedelta(days=abs(days))
        tdelta = relativedelta(t, t2)
    return [
        (year, tdelta.years),
        (month, tdelta.months),
        (week, tdelta.days / 7),
        (day, tdelta.days % 7)
    ]