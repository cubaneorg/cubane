# coding=UTF-8
from __future__ import unicode_literals


def base36encode(number, alphabet='23456789ABCDEFGHJKMNOPQRSTUVWXYZ'):
    """
    Convert positive integer to a base36 string.
    Based on: http://en.wikipedia.org/wiki/Base_36#Python_implementation
    """
    # zero
    if number == 0:
        return alphabet[0]

    # sign
    sign = ''
    if number < 0:
        sign = '-'
        number = -number

    # encode
    base36 = ''
    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[int(i)] + base36

    return sign + base36