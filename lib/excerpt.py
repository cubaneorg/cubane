# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from bs4 import BeautifulSoup
import unicodedata


def excerpt_from_text(txt, length=settings.CMS_EXCERPT_LENGTH, prefix=False):
    """
    Generate a short excerpt message (plain text) from given plain text.
    If the maximum length is exceeded, ... is placed at the end of the text.
    """
    if txt == None:
        return ''

    txt = txt.strip()
    if len(txt) > length:
        if prefix:
            txt = txt[-length:].strip()
            txt = '...%s' % txt
        else:
            txt = txt[:length].strip()
            txt = '%s...' % txt

    return txt


def excerpt_from_html(markup, length=settings.CMS_EXCERPT_LENGTH):
    """
    Generate a short excerpt message (plain text) from given html markup.
    """
    if markup == None:
        return ''

    # strip html tags and convert html entities to unicode characters
    s = BeautifulSoup(markup, 'html5lib').text

    # normalise unicode result, in particular normalise white space
    s = unicodedata.normalize('NFKD', s)

    # generate excerpt from remaining text
    s = excerpt_from_text(s, length)
    return s