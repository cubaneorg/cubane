# coding=UTF-8
from __future__ import unicode_literals
import re


def headline_from_ident(ident):
    """
    Generate human readable headline text from given python identifier.
    """
    return re.sub(r'_+', ' ', ident).title()


def to_camel_case(ident):
    """
    Generate a camel case version of the given python identifier.
    """
    components = ident.lower().strip().split('_')
    return ''.join(c.title() for c in components if len(c.strip()) > 0)


def camel_to_ident(camel):
    """
    Convert given camel case name to an identifier.
    Based on: https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()