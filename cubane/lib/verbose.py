# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
import sys


def out(s, newline=True, verbose=True, channel=sys.stdout):
    """
    Print given string s if we are not running in TEST mode and the verbose
    argument is True.
    """
    if not settings.TEST and verbose:
        channel.write(s)
        if newline:
            channel.write('\n')


def conditional(callback, verbose=True):
    """
    Executes given callback function only if we are not under TEST mode and the
    verbose argument is True.
    """
    if not settings.TEST and verbose:
        callback()