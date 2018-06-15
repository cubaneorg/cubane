from __future__ import unicode_literals
from django import template
import datetime
register = template.Library()


@register.filter
def has_attr(instance, attr_name):
    """
    Return True, if the given instance has an attribute with given name.
    """
    return hasattr(instance, attr_name)


@register.filter
def get_dict_item(dictionary, key):
    """
    Return the element from the given dictionary with the given key.
    """
    return dictionary.get(key)


@register.filter
def get_class(obj):
    """
    Return the name of the class of given object.
    """
    return obj.__class__.__name__