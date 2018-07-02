# coding=UTF-8
from __future__ import unicode_literals
from django.db import models
from django.template import TemplateSyntaxError, VariableDoesNotExist, Variable
from django.template.base import VARIABLE_ATTRIBUTE_SEPARATOR
from django.template.context import BaseContext
from django.forms.utils import flatatt
import copy
import re


def get_template_args(bits):
    """
    Split given list of arguments for a template tag into regular (positional)
    arguments and a list of keyword arguments.
    """
    args = []
    kwargs = {}

    if bits is not None and len(bits) > 1:
        # first bit is always the tag name
        tag_name = bits[0]
        bits = bits[1:]

        for bit in bits:
            m = re.match(r'^(?P<name>.*?)=(?P<value>.*?)$', bit)
            if m:
                name = m.group('name')
                value = m.group('value')
                if name in kwargs:
                    raise TemplateSyntaxError(
                        'Duplicate keyword argument \'%s\' with value \'%s\' for template tag \'%s\'.' % (name, value, tag_name)
                    )
                kwargs[name] = value
            else:
                args.append(bit)

    return args, kwargs


def template_error(msg):
    """
    Return a stadadised error message for template errors. A template error
    is usually presented on the screen and does not trigger django's default
    error/exception page.
    """
    return '[%s]' % msg


def is_literal(argument_value):
    """
    Return True, if the given argument value is a string literal. The argument
    is considered to be a string literal if it is enclosed in quote characters
    (' or ").
    """
    v = argument_value
    return v != None and len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'")


def literal(tag_name, argument_name, argument_value):
    """
    Return a string literal from given string s, where s must starts and end
    with the same string literal character ' or ".
    """
    if is_literal(argument_value):
        return argument_value[1:-1]
    else:
        raise TemplateSyntaxError('Template tag %s argument %s should be in quotes.' % (
            tag_name,
            argument_name
        ))


def value_or_literal(name, context):
    """
    Resolve given template variable name based on given template context.
    If the name is enclosed in quotes, the name is considered to be the string
    literal and the value (without the quote characters) is returned; otherwise
    the expression is considered as a reference to a template variable and the
    value of such template variable is returned instead.
    """
    if name == None:
        return None
    elif is_literal(name):
        return name[1:-1]
    else:
        try:
            return Variable(name).resolve(context)
        except VariableDoesNotExist:
            return None


def value_or_none(name, context):
    """
    Resolve given template variable name based on given template context or
    return None.
    """
    if name == None:
        return None
    else:
        try:
            return Variable(name).resolve(context)
        except VariableDoesNotExist:
            return None


def value_or_default(name, context, default):
    """
    Resolve given template variable name based on given template context or
    return the given default value.
    """
    if name == None:
        return default
    else:
        try:
            return Variable(name).resolve(context)
        except VariableDoesNotExist:
            return default


def htmltag(tag, attrs = None, content = ''):
    """
    Renders an html tag with given tag name and given list of attributes.
    """
    return '<%(tag)s%(attrs)s>%(content)s</%(tag)s>' % {
        'tag': tag,
        'attrs': flatatt(attrs),
        'content': content
    }


def resolve_object_property_reference(
    context,
    reference,
    separator=VARIABLE_ATTRIBUTE_SEPARATOR,
    default=None,
    error_if_not_found=True,
    accept_unknown_reference=True):
    """
    Resolve the given object/property reference based on the given context and
    return the resulting object instance, the property name and its value. If
    no such property exists and error_if_not_found is True then an exception is
    raised; otherwise the given default value is returned.
    """
    bits = reference.split(separator)
    current = context
    instance = None
    property_name = None
    for bit in bits:
        v = None

        # dictionary lookup
        try:
            v = current[bit]
        except (TypeError, AttributeError, KeyError, ValueError, IndexError):
            pass

        # attribute lookup
        if v is None:
            try:
                v = getattr(current, bit)
            except (TypeError, AttributeError):
                pass

        # list-index lookup
        if v is None:
            try:
                current = current[int(bit)]
            except (IndexError, ValueError, KeyError, TypeError):
                pass

        # unable to resolve
        if v is None:
            # if we already resolved the instance, we accept this as a valid
            # property name anyway, perhabs the property belongs to the form
            # and not to the model directly...
            if instance is not None and accept_unknown_reference:
                property_name = bit
                break
            else:
                if error_if_not_found:
                    raise VariableDoesNotExist('Failed lookup for key \'%s\' in object \'%s\'.', (bit, current))
                else:
                    return (instance, property_name, default)

        # callable
        if callable(v) and not isinstance(current, object):
            # method call (assuming no args required)
            v = current()

        # collect object instance / property name
        if isinstance(v, models.Model):
            instance = v
            property_name = None
        elif instance is not None and property_name is None:
            property_name = bit

        # current value becomes context for next reference in sequence
        current = v

    return (instance, property_name, current)


def get_object_reference_value(context, reference, separator=VARIABLE_ATTRIBUTE_SEPARATOR, default=None):
    """
    Resolve the given object/property reference based on the given context and
    only return the value or the given default value. If no such property exist
    then the given default value is returned.
    """
    _, _, v = resolve_object_property_reference(
        context,
        reference,
        separator,
        default,
        error_if_not_found=False,
        accept_unknown_reference=False
    )
    return v