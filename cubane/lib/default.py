# coding=UTF-8
from __future__ import unicode_literals


def default_choice(choices):
    """
    Returns the first choice available based on the given list of choices or
    None if there is no choice available.
    """
    try:
        return choices[0][0]
    except:
        return None
