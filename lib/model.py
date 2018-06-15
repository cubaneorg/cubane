# coding=UTF-8
from __future__ import unicode_literals
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.db.models.fields.related import ForeignKey, RelatedField, ManyToManyField
from django.forms.models import model_to_dict as django_model_to_dict
from cubane.lib.ident import headline_from_ident
from itertools import chain
import hashlib
import re


class IncompatibleModelError(ValueError):
    pass


def get_fields(model):
    """
    Return a list of model fields.
    """
    return model._meta.get_fields()


def get_model_field_names(model, reverse=False, json=False, exclude_many_to_many=False):
    """
    Return a list of all field names for the model. A model may implement
    get_json_fieldnames() to override the list of fields, which is used in the
    case that json is True.
    """
    if json:
        try:
            return model.get_json_fieldnames()
        except:
            pass

    # get all fields from model, which includes everything
    fields = get_fields(model)

    # filter out stuff we do not want to begin with
    fields = filter(
        lambda f: not (f.many_to_one and f.related_model is None),
        fields
    )

    # filter out reverse-related fields if they should not be included...
    if not reverse:
        fields = filter(lambda f: not isinstance(f, ForeignObjectRel), fields)

    # filter out many2many if they shopuld not be included...
    if exclude_many_to_many:
        fields = filter(lambda f: not isinstance(f, ManyToManyField), fields)

    # filter out generic related object managers
    from django.contrib.contenttypes.fields import GenericRelation
    fields = filter(lambda f: not isinstance(f, GenericRelation), fields)

    return [f.name for f in fields]


def model_has_many_to_many(instance):
    """
    Return True if there is at least one field in the given model instance
    that is a many to many relationship.
    """
    model = instance.__class__
    for attr_name in get_model_field_names(model):
        if hasattr(model, attr_name):
            if isinstance(
                getattr(model, attr_name),
                ReverseManyToOneDescriptor
            ):
                return True
    return False


def dict_to_model(d, instance, exclude_many_to_many=False, only_many_to_many=False):
    """
    Update all property values in given model instance based on the list
    of properties of the given dict.
    """
    model = instance.__class__
    for k, v in d.items():
        if (exclude_many_to_many or only_many_to_many) and \
           hasattr(model, k):
            is_many_to_many = isinstance(
                getattr(model, k),
                ReverseManyToOneDescriptor
            )
        else:
            is_many_to_many = False

        if exclude_many_to_many and is_many_to_many:
            continue

        if only_many_to_many and not is_many_to_many:
            continue

        # exclude many to many with custom through model anyhow,
        # since we would not be able to set it like this
        if isinstance(instance, models.Model):
            try:
                field = model._meta.get_field(k)
                if isinstance(field, ManyToManyField):
                    if exclude_many_to_many or field.rel.through is not None:
                        # check for custom through name and not build-in
                        # many-to-many intermediate model that is auto-generated
                        if not field.rel.through.__name__.endswith('_%s' % k):
                            continue
            except FieldDoesNotExist:
                pass

        setattr(instance, k, v)


def model_to_dict(instance, fetch_related=False, fields=None, exclude_many_to_many=False, json=False):
    """
    Take given model instance and return a dict containing all model
    properties.
    """
    if not fields:
        fields = get_model_field_names(
            instance.__class__,
            exclude_many_to_many=exclude_many_to_many,
            json=json
        )

    # general fields
    result = django_model_to_dict(
        instance,
        fields=fields
    )

    # related managers
    if fetch_related:
        for fieldname in fields:
            p = getattr(instance, fieldname)
            if 'django.db.models.fields.related_descriptors.ManyRelatedManager' in unicode(p.__class__):
                result[fieldname] = p.all()

    return result


def save_model(d, instance):
    """
    Save given form data d in given model instance. The first pass will not
    save any ManyToMany relationships if the instance does not exist yet.
    They will be applied afterwords.
    """
    if instance.pk or not model_has_many_to_many(instance):
        # already exists or has no many to many -> just copy data across
        dict_to_model(d, instance)
        instance.save()
    else:
        # create entity first by only copying all fields except ManyToMany
        dict_to_model(
            d,
            instance,
            exclude_many_to_many=True
        )
        instance.save()

        # assigning many to many fields does not require a save()
        dict_to_model(
            d,
            instance,
            only_many_to_many=True
        )

    return instance


def invalid_model_error(model, message):
    """
    Raise incompatibility error for the given model with given message.
    """
    raise IncompatibleModelError('Incompatible Model \'%s\': %s' % (
        model.__name__,
        message
    ))


def validate_model(model):
    """
    Validate the given model for compatibility with cubane.
    """
    # should have __unicode__
    if not hasattr(model, '__unicode__'):
        invalid_model_error(model, 'Missing __unicode__ method implementation.')


def get_model_checksum(instance):
    """
    Return a checksum over all model instance field values.
    """
    def to_string_value(model_instance, field):
        if isinstance(field, ForeignKey):
            return '-'

        if isinstance(field, (RelatedField, ForeignObjectRel)):
            return '-'

        try:
            v = field.value_to_string(model_instance)
        except AttributeError:
            v = '-'

        if v is None:
            v = '-'

        return v

    fields = get_fields(instance)
    k = '%s-' % len(fields) + \
        '-'.join([to_string_value(instance, f) for f in fields])
    return hashlib.sha1(k.encode('utf-8')).hexdigest()


def get_model_related_field(model, fieldname, title=None):
    """
    Return the name of a related field (foreign key) and the corresponding
    model for a field name in the form foo__bar, where foo is a foreign key
    to another model containing the field bar.
    """
    field = None
    related = None
    rel_fieldname = None
    rel_model = None
    m = re.match(r'^(?P<relname>.*?)__(?P<fieldname>.*?)$', fieldname)
    if m:
        relname = m.group('relname')
        try:
            _field = model._meta.get_field(relname)
        except FieldDoesNotExist:
            _field = None

        if _field and isinstance(_field, ForeignKey):
            _rel_fieldname = m.group('fieldname')

            try:
                _rel_field = _field.rel.to._meta.get_field(_rel_fieldname)
            except FieldDoesNotExist:
                _rel_field = None

            if _rel_field:
                field = _field
                related = relname
                rel_fieldname = _rel_fieldname
                rel_model = field.rel.to
                if not title:
                    title = headline_from_ident(rel_fieldname)

    return (field, related, rel_fieldname, rel_model, title)


def get_model_option(model, name, container_name, default=None):
    """
    Return the given model option from the given container
    or the given default value. Scan derived model classes if not declared by
    given model directly.
    """
    if model:
        # this instance
        try:
            container = getattr(model, container_name)
            return getattr(container, name)
        except AttributeError:
            pass

        # try base classes
        if hasattr(model, '__bases__'):
            for sub_model in model.__bases__:
                option = get_model_option(sub_model, name, container_name)
                if option:
                    return option

    # not found
    return default


def get_listing_option(model, name, default=None):
    """
    Return the given model listing option from the given model or
    (if no such option is declared) the given default value. Scan derived
    classes if the given option is not declared by the given model directly.
    """
    return get_model_option(model, name, 'Listing', default)


def get_listing_view_option(model, name, default=None):
    """
    Return the given model listing view option from the given model or
    (if no such option is declared) the given default value. Scan derived
    classes if the given option is not declared by the given model directly.
    """
    # try view options
    view_options = get_listing_option(model, 'View')
    if view_options:
        try:
            return getattr(view_options, name)
        except AttributeError:
            pass

    # try regular listing option
    return get_listing_option(model, name, default)


def collect_meta_list(obj, name):
    """
    Collect a list a items from the Meta definition of the given object
    (model or form) and its super classes recursively.
    """
    result = []

    def _collect(cls):
        if hasattr(cls, 'Meta') and hasattr(cls.Meta, name):
            for item in getattr(cls.Meta, name):
                result.append(item)
        for subcls in cls.__bases__:
            _collect(subcls)
    _collect(obj.__class__)

    return result


def collect_meta_dict(obj, name):
    """
    Collect a dict a items from the Meta definition of the given object
    (model or form) and its super classes recursively.
    """
    result = {}

    def _collect(cls):
        if hasattr(cls, 'Meta') and hasattr(cls.Meta, name):
            result.update(getattr(cls.Meta, name))
        for subcls in cls.__bases__:
            _collect(subcls)
    _collect(obj.__class__)

    return result