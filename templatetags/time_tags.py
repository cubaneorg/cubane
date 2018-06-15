from __future__ import unicode_literals
from django import template
from cubane.lib.text import pluralize
import datetime
register = template.Library()


@register.filter
def get_time_from_now(before):
    """
    Get the time difference between two times.
    """
    if not before:
        return ''

    if type(before) == datetime.date:
        before = datetime.datetime.combine(before, datetime.datetime.min.time())

    time_passed = datetime.datetime.now() - before

    days, seconds = time_passed.days, time_passed.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if days > 0:
        return pluralize(days, 'day', 'ago')
    elif hours > 0:
        return pluralize(hours, 'hour', 'ago')
    elif minutes > 0:
        return pluralize(minutes, 'minute', 'ago')
    else:
        return 'few seconds ago'