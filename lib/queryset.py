# coding=UTF-8
from __future__ import unicode_literals
from django.db.models.query import QuerySet
import copy


class MaterializedQuerySet(QuerySet):
    """
    A queryset that will keep its cached result.
    """
    def __init__(self, model=None, query=None, using=None, hints=None, queryset=None):
        if queryset is None:
            super(MaterializedQuerySet, self).__init__(model, query, using, hints)
        else:
            super(MaterializedQuerySet, self).__init__(queryset.model, queryset.query, queryset.db, queryset._hints)
        self._queryset = queryset
        self._objects = None


    def _clone(self, **kwargs):
        clone = super(MaterializedQuerySet, self)._clone(**kwargs)
        clone._queryset = self._queryset
        clone._objects = self._objects
        return clone


    def iterator(self):
        if self._objects is None:
            self._objects = list(self._queryset)

        for value in self._objects:
            yield value