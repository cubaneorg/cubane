# coding=UTF-8
from __future__ import unicode_literals
from django import template


register = template.Library()


@register.inclusion_tag('cubane/flash.html')
def flash(messages):
    """
    Presents a list of flash messages.
    """
    return {
        'messages': messages
    }
