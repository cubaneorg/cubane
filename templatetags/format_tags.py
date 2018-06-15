# coding=UTF-8
from __future__ import unicode_literals
from django import template
from django.conf import settings
from cubane.lib.currency import format_currency
import re
register = template.Library()


@register.filter(name='not')
def not_x(x):
    """
    Given x as a boolean expression, not x is returned.
    """
    return not x


@register.filter
def as_int(x):
    """
    Converts given template variable x into an integer, specifically usefull
    for expressing boolean values as 0 and 1.
    """
    if x == 'True':
        return 1
    else:
        try:
            return int(x)
        except:
            return 0


@register.simple_tag
def price(v, lc=None):
    """
    Return the given price value x formatted as a currency value.
    """
    return format_currency(v, lc=lc)


@register.simple_tag
def percent(v):
    """
    Return the given value x formatted as a percentage value. Full numbers are converted to integers.
    """
    if v is not None:
        if int(v) == v:
            v = int(v)
        return '%s%%' % v
    else:
        return ''