# coding=UTF-8
from __future__ import unicode_literals
import re


def get_choices_value(choices, display, default=None):
    """
    Parse given display value by mapping it to the right hand side of
    the given list of choices, returning the corresponding left hand side
    value or None.
    """
    try:
        return (k for k, v in choices if v == display).next()
    except StopIteration:
        return default


def get_choices_display(choices, value, default=None):
    """
    Map the given choices value to the given list of choices and return the
    corresponding display value or None.
    """
    return dict(choices).get(value, default)


def get_choices_from_values(values, prefix=None, sort=True):
    """
    Return a list of choices from the given set of possible values. The display
    title is generated for each value based on the value itself. If a prefix is
    given, any value that contains the prefix is reflected with a display value
    that is based on the original value excluding the prefix.
    """
    if not values:
        return []

    # sort?
    if sort:
        values = sorted(values)

    # generate choices
    def display_value(v):
        if prefix:
            if v.startswith(prefix):
                v = v[len(prefix):]
        return re.sub(r'[-_]', ' ', v).title().strip()

    return [(v, display_value(v)) for v in values if v]