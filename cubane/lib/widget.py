# coding=UTF-8
from __future__ import unicode_literals


def build_attrs(attrs, extra_attrs=None, **kwargs):
    """
    Helper function for building an attribute dictionary.
    """
    attrs = dict(attrs, **kwargs)
    if extra_attrs:
        attrs.update(extra_attrs)
    return attrs