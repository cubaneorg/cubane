# coding=UTF-8
from __future__ import unicode_literals
from django import template
from django.conf import settings
from cubane.lib.text import text_from_html as _text_from_html
import re
import random
register = template.Library()


@register.filter
def without_spaces(s):
    """
    Filter out white space from input.
    """
    if s:
        return re.sub(r'\s', '', s)
    else:
        return ''


@register.filter
def phone_display(s):
    """
    Present a phone number for display purposes, where the country calling code
    (if present) is removed (at least as long as we do not have full i18n
    support).
    """
    if not s:
        return ''

    s = s.strip()

    # rewrite 00 with +
    if s.startswith('00'):
        s = '+' + s[2:]

    # remove country code
    m = re.match('^\+\d+\s(.*?)$', s)
    if m:
        s = m.group(1).strip()

    # add leading 0 if missing
    if not s.startswith('0'):
        s = '0' + s

    return s


@register.filter
def phone_number(s, country=None):
    """
    Make sure that the given phone number is presented in a way that it can
    be dialled. If no country calling code is present, the default calling code
    if the country in settings is used.
    """
    if not s:
        return ''

    # remove spaces and invalid characters
    s = re.sub(r'[^\+\d]', '', s)

    # rewrite 00 with +
    if s.startswith('00'):
        s = '+' + s[2:]

    # add missing country code from settings
    if not s.startswith('+'):
        # determine country from settings, fall back to UK
        if country and country.calling_code:
            calling_code = country.calling_code
        else:
            calling_code = '44'

        # remove leading 0
        if s.startswith('0'):
            s = s[1:]

        # add country prefix +xyz
        s = '+' + calling_code + s

    return s


@register.filter
def nullable(value):
    """
    If value is None, return '-' instead.
    """
    return value if value != None else u'-'


@register.filter
def truncatewords_by_chars(value, arg):
    """
    Truncate the text when it exceeds a certain number of characters.
    Delete the last word only if partial.
    Adds '...' at the end of the text.
    """
    try:
        length = int(arg)
    except ValueError:
        return value

    if len(value) > length:
        if value[length:length + 1].isspace():
            return value[:length].rstrip() + '...'
        else:
            return value[:length].rsplit(' ', 1)[0].rstrip() + '...'
    else:
        return value


@register.filter('truncate_chars')
def truncate_chars(value, max_length):
    """
    Truncates the given text when it exceeds a certain number of characters.
    Text might be truncated in-between words.
    """
    value = value.strip()
    if len(value) > max_length:
        return value[:max_length].rstrip() + '...'
    else:
        return value


@register.simple_tag()
def random_number():
    """
    Returns a random number.
    """
    return '%s' % random.randint(0, 99999)


@register.filter('text_from_html')
def text_from_html(html):
    """
    Strip tags from potential HTML content.
    """
    # none
    if html is None:
        return ''

    # enforce string
    html = unicode(html)

    # enforce text
    return _text_from_html(html)