# coding=UTF-8
from __future__ import unicode_literals
from django import template
from django.conf import settings
from cubane.lib.html import transpose_html_headlines
from cubane.lib.url import get_compatible_url
import re
register = template.Library()


@register.filter
def transpose_headlines(value, x):
    """
    Transpose existing headlines within the given html by the given
    amount of levels, for example a transpose of headlines by a level of 1
    would change every h1 headline into a h2 headline, every h2 headline into
    a h3 headline and so forth. The max. number of headlines supported by html
    is h6, therefore transposing an h6 would result into an h6.
    """
    try:
        level = int(x)
    except ValueError:
        return value

    return transpose_html_headlines(value, level)


@register.filter
def compatible(content):
    """
    Make any image links compatible with the site in terms of HTTP/HTTPS in
    order to avoid mixed content security warnings, assuming that for any
    http:// image we encounter, an equivalent https:// link exists.
    """
    if content is None:
        return ''

    def replace_image_src(m):
        attrs = re.findall(r'(?P<attr>\w+)=(?P<value>[^\s]*)', m.group('img'))
        attrs = [(attr.lower(), value.strip('"')) for attr, value in attrs]
        attrs = [(attr, get_compatible_url(value) if attr == 'src' else value) for attr, value in attrs]
        return '<img %s>' % ' '.join(['%s="%s"' % (attr, value) for attr, value in attrs])

    return re.sub(r'<(?P<img>img.*?)/?>', replace_image_src, content)