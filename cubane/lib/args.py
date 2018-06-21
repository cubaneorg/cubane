# coding=UTF-8
from __future__ import unicode_literals
from django.db.models.query import QuerySet


def get_pks(data, single_pk_name='pk', multiple_pks_name='pks[]'):
    """
    Return a list of pk values from the given data source. We try the single
    pk name first. If no value is defined, we try the multiple pk name.
    """
    pk = data.get(single_pk_name)
    if pk:
        return [pk]
    else:
        return data.getlist(multiple_pks_name, [])


def list_of_list(a):
    """
    Make sure that a is defined as a list of list, e.g. [[a]].
    """
    if not isinstance(a, list):
        return [[a]]
    elif len(a) > 0 and not isinstance(a[0], list):
        return [a]
    else:
        return a


def list_of(a):
    """
    Make sure that a is defined as a list of items, e.g. [a].
    """
    if a == None:
        return []

    if isinstance(a, QuerySet):
        return list(a)

    if not isinstance(a, list):
        return [a]

    return a


def clean_dict(d):
    """
    Return a new dictionary d, where None value keys have been removed from the
    dictionary.
    """
    result = {}

    if d is not None:
        for k, v in d.items():
            if v is not None:
                result[k] = v

    return result