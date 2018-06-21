# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
import locale
import re
import subprocess


def get_available_locales():
    """
    Return a list of available locales.
    """
    # execute
    p = subprocess.Popen(
        'locale -a',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    (output, err_output) = p.communicate()
    p.wait()

    # raise exception on error
    if p.returncode == 0:
        result = re.split(r'\n', output)
        result = [x.strip() for x in result]
        result = filter(lambda x: x, result)
        result = filter(lambda x: x.upper().endswith('UTF-8') or x.upper().endswith('UTF8'), result)
        result = [x.replace('utf8', 'UTF-8') for x in result]
    else:
        result = []

    return result


def get_available_locales_choices():
    """
    Return a list of available locales as choices.
    """
    values = get_available_locales()
    def display_value(v):
        m = re.match(r'^(..)_(..)\..*?$', v)
        if m:
            return '%s_%s' % (m.group(1), m.group(2))
        else:
            return v
    return [(v, display_value(v)) for v in values if v]


def currency_symbol(lc=None):
    """
    Return the currency symbol.
    """
    if lc is None:
        lc = settings.CUBANE_LOCALE

    locale.setlocale(locale.LC_ALL, lc)
    d = locale.localeconv()
    symbol = d.get('currency_symbol')
    symbol = re.sub('Eu', '€', symbol)
    return symbol


def format_currency(amount, decimal=True, grouping=True, international=False, lc=None):
    """
    Return the given price correctly formatted in the target culture setting
    including delimiters and currency.
    """
    if amount is None:
        return ''

    if lc is None:
        lc = settings.CUBANE_LOCALE

    locale.setlocale(locale.LC_ALL, lc)
    s = locale.currency(amount, symbol=True, grouping=grouping, international=international).decode('utf-8')
    s = re.sub('Eu', '€', s)

    if not decimal:
        decimal_point = locale.localeconv().get('mon_decimal_point')
        if decimal_point == '.': decimal_point = '\.'
        s = re.sub(r'%s\d\d' % decimal_point, '', s)

    return s