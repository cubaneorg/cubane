# coding=UTF-8
from __future__ import unicode_literals
from decimal import Decimal


CM_PER_INCH = 2.54


def inch_to_cm(value_inches):
    """
    Return the given value (inches) as in centimeters.
    """
    if isinstance(value_inches, Decimal):
        return value_inches * Decimal(unicode(CM_PER_INCH))
    else:
        return value_inches * CM_PER_INCH