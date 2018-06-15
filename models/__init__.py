# coding=UTF-8
from __future__ import unicode_literals
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from cubane.lib.model import get_fields, get_model_checksum
import datetime
import re


class PostCodeField(models.CharField):
    def __init__(self, *args, **kwargs):
        # enforce max length
        kwargs['max_length'] = 10
        super(PostCodeField, self).__init__(*args, **kwargs)


    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return self._parse_postcode(value)


    def to_python(self, value):
        if isinstance(value, basestring):
            return value

        if value is None:
            return value

        return self._parse_postcode(value)


    def _parse_postcode(self, parse_string):
        p = re.compile('^[a-zA-Z0-9 -]+$', re.IGNORECASE)
        if re.match(p, parse_string):
            return parse_string
        raise ValidationError(_("Invalid Postcode"))


class DateTimeReadOnlyBase(models.Model):
    """
    Abstract base class for models that need to keep track of creation time and
    deletion time but do not track editing, since model instances are
    generally real-only.
    """
    class Meta:
        abstract = True


    created_on = models.DateTimeField(
        verbose_name='Created on',
        null=True,
        blank=False,
        db_index=True,
        editable=False
    )

    deleted_on = models.DateTimeField(
        verbose_name='Deleted on',
        null=True,
        blank=True,
        db_index=True,
        editable=False
    )

    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        verbose_name='Deleted by',
        editable=False,
        on_delete=models.SET_NULL,
        related_name='+'
    )


    def save(self, *args, **kwargs):
        if not self.created_on:
            self.created_on = timezone.now()
        super(DateTimeReadOnlyBase, self).save(*args, **kwargs)


class DateTimeBase(models.Model):
    """
    Abstract base class for models that need to keep track of last modufication
    and creation timestamps.
    """
    class Meta:
        abstract = True


    created_on = models.DateTimeField(
        verbose_name='Created on',
        db_index=True,
        null=True,
        blank=False,
        editable=False
    )

    created_by = models.ForeignKey(
        User,
        verbose_name='Created by',
        editable=False,
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    updated_on = models.DateTimeField(
        verbose_name='Updated on',
        db_index=True,
        null=True,
        blank=False,
        editable=False
    )

    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        verbose_name='Updated by',
        editable=False,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    deleted_on = models.DateTimeField(
        verbose_name='Deleted on',
        null=True,
        blank=True,
        db_index=True,
        editable=False
    )

    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        verbose_name='Deleted by',
        editable=False,
        on_delete=models.SET_NULL,
        related_name='+'
    )


    @classmethod
    def get_acl(cls):
        if not hasattr(cls, '_acl'):
            cls._acl = Acl.of(cls)
        return cls._acl


    def get_checksum(self):
        """
        Calculate checksum over all database fields.
        """
        return get_model_checksum(self)


    def save(self, *args, **kwargs):
        # maintain modification timestamps
        if not self.created_on:
            self.created_on = timezone.now()
        self.updated_on = timezone.now()

        # save
        super(DateTimeBase, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        # check we have set on_delete=Null for foreign keys
        self.clear_nullable_related()
        super(DateTimeBase, self).delete(*args, **kwargs)


    def clear_nullable_related(self):
        """
        Recursively clears any nullable foreign key fields on related objects.
        Django is hard-wired for cascading deletes, which is not what we want
        by default. This simulates ON DELETE SET NULL behavior manually.
        """
        all_related_objects = [
            f for f in self._meta.get_fields()
            if (f.one_to_many or f.one_to_one)
            and f.auto_created and not f.concrete
        ]

        for related in all_related_objects:
            accessor = related.get_accessor_name()
            try:
                related_set = getattr(self, accessor)
            except ObjectDoesNotExist: # pragma: no cover
                continue

            if related.field.null:
                # if its nullable, we can simply clear the connection, so
                # it becomes safe to delete the instance.
                related_set.clear()
            else:
                # the connection is NOT nullable, therefore the related object
                # WILL be deleted. Therefore we at least isolate it as well
                # by traversing its related fields...
                for related_object in related_set.all():
                    try:
                        related_object.clear_nullable_related()
                    except AttributeError: # pragma: no cover
                        pass


class Country(models.Model):
    """
    Country and various ISO codes for it.
    """
    class Meta:
        verbose_name        = 'Country'
        verbose_name_plural = 'Countries'
        ordering            = ['name']


    class Cubane:
        fixtures = 'cubane/country.xml'


    iso = models.CharField(
        'ISO alpha-2',
        max_length=2,
        primary_key=True
    )

    name = models.CharField(
        'Official name (CAPS)',
        max_length=128,
        db_index=True
    )

    printable_name = models.CharField(
        'Country name',
        max_length=128,
        db_index=True
    )

    iso3 = models.CharField(
        'ISO alpha-3',
        max_length=3,
        null=True
    )

    numcode = models.PositiveSmallIntegerField(
        'ISO numeric',
        null=True
    )

    landlocked = models.BooleanField(
        db_index=True,
        default=False
    )

    flag_state = models.BooleanField(
        db_index=True,
        default=False
    )

    calling_code = models.CharField(
        max_length=8,
        null=True
    )


    @property
    def title(self):
        return self.printable_name


    def __unicode__(self):
        return self.printable_name


    def to_dict(self):
        return {
            'name': self.name,
            'printable_name': self.printable_name,
            'iso': self.iso,
            'iso3': self.iso3,
            'numcode': self.numcode
        }
