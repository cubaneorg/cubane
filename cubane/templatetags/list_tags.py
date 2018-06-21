# coding=UTF-8
from __future__ import unicode_literals
from django import template
from django.conf import settings
import re
import random
import inspect
register = template.Library()


@register.filter
def split(str, splitter):
    """
    Split given string by given splitter and return a list of components, where
    each component is trimmed from white spaces.
    """
    return [x.strip() for x in str.split(splitter)]


@register.filter
def is_list(lst):
    """
    Return True, if the given list is indeed a list of tuple.
    """
    return isinstance(lst, (list, tuple))


@register.filter
def get(value, arg):
    """
    Gets an attribute of an object dynamically from a string name
    """
    # none value or arg
    if value == None or arg == None:
        return None

    # traverse elements (__)
    if isinstance(arg, basestring) and '__' in arg:
        m = re.match(r'^(?P<relname>.*?)__(?P<fieldname>.*?)$', arg)
        if m:
            v = get(value, m.group('relname'))
            return get(v, m.group('fieldname'))

    # get attribute or dictionary item
    if hasattr(value, unicode(arg)):
        attr = getattr(value, arg)
    else:
        try:
            attr = value[arg]
        except:
            attr = ''

    # callable?
    if callable(attr):
        try:
            attr = attr()
        except:
            pass

    return attr