# coding=UTF-8
from __future__ import unicode_literals
from main import *

try:
    if DEBUG:
        from dev import *
    else:
        from live import *
except ImportError, e:
    pass