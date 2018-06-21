# coding=UTF-8
from __future__ import unicode_literals
from django.utils.dateparse import parse_datetime as django_parse_datetime
import datetime


def parse_int(s, default_value=0):
    """
    Parse given value as an integer, if that fails, apply default value
    """
    try:
        v = int(s)
    except:
        v = default_value

    return v


def parse_int_list(s):
    """
    Parse a comma seperated list of integer values from given input string s
    and retur a list of integer in the same order. If a value cannnot be
    interpreted as an integer, the value is simply obmitted.
    """
    if s == None or s == '': return []

    r = []
    for x in s.split(','):
        try:
            r.append(int(x))
        except ValueError:
            pass
    return r


def parse_bool(text, default=False):
    """
    Parse and return a boolean value from the given char.
    """
    return text.strip().lower() in ['y', '1'] if text != None else default


def parse_datetime(text):
    """
    Parse and return a datetime value from the given text that represents
    a date and time.
    """
    return django_parse_datetime(text)


def parse_unix_timestamp(text, default=None):
    """
    Parse and return a datetime value from the given text that represents a
    unix timestamp.
    """
    try:
        return datetime.datetime.fromtimestamp(
            int(text)
        )
    except:
        return default