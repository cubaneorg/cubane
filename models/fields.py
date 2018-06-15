# coding=UTF-8
from __future__ import unicode_literals
from django.db import models
from django.utils.text import capfirst
from django.forms import MultipleChoiceField, SelectMultiple, ValidationError
from cubane.forms import MultiSelectFormField


class MultiSelectField(models.TextField):
    """
    Stores multiple choices as a comma-seperated list (stored as text field).
    This implementation does NOT perform any validation.
    Implementation based on:
    https://djangosnippets.org/snippets/2753/
    """
    def get_internal_type(self):
        return "TextField"


    def formfield(self, **kwargs):
        # don't call super, as that overrides default widget if it has choices
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name),
                    'help_text': self.help_text, 'choices': self.choices}
        if self.has_default():
            defaults['initial'] = self.get_default()
        defaults.update(kwargs)
        return MultiSelectFormField(**defaults)


    def get_db_prep_value(self, value, connection=None, prepared=False):
        if isinstance(value, basestring):
            return value
        elif isinstance(value, list):
            return ','.join(value)


    def _parse_value(self, value):
        if value is not None:
            return value if isinstance(value, list) else [v.strip() for v in value.split(',') if v]
        return []


    def from_db_value(self, value, expression, connection, context):
        return self._parse_value(value)


    def to_python(self, value):
        return self._parse_value(value)


    def contribute_to_class(self, cls, name):
        super(MultiSelectField, self).contribute_to_class(cls, name)
        if self.choices:
            func = lambda self, fieldname = name, choicedict = dict(self.choices): ', '.join([choicedict.get(value, value) for value in getattr(self, fieldname)])
            setattr(cls, 'get_%s_display' % self.name, func)


    def validate(self, value, model_instance):
        if self.choices and value:
            allowed_values = []
            for option_key, option_value in self.choices:
                if isinstance(option_value, (list, tuple)):
                    # this is an optgroup, so look inside the group for
                    # options.
                    for optgroup_key, optgroup_value in option_value:
                        allowed_values.append(optgroup_key)
                else:
                    allowed_values.append(option_key)

            for v in value:
                if v not in allowed_values:
                    raise ValidationError(
                        self.error_messages['invalid_choice'],
                        code='invalid_choice',
                        params={'value': value},
                    )


    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_db_prep_value(value)


class TagsField(models.CharField):
    """
    Based on MultiSelectField, this field stores a list of tags
    separated by # characters, so that any given tag can be matched
    by searching for #tag#.
    """
    def get_internal_type(self):
        return "CharField"


    def formfield(self, **kwargs):
        # don't call super, as that overrides default widget if it has choices
        defaults = {
            'required': not self.blank,
            'label': capfirst(self.verbose_name),
            'help_text': self.help_text,
            'choices': self.choices,
            'widget': SelectMultiple(attrs={'class': 'select-tags'})
        }

        if self.has_default():
            defaults['initial'] = self.get_default()
        defaults.update(kwargs)
        return MultiSelectFormField(**defaults)


    def get_db_prep_value(self, value, connection=None, prepared=False):
        if isinstance(value, basestring):
            return value
        elif isinstance(value, list):
            return '#' + ('#'.join(value)) + '#'


    def _parse_value(self, value):
        if value is not None:
            if isinstance(value, list):
                return value
            elif value == '' or value == '##':
                return []
            else:
                return value.strip('#').split('#')
        return []


    def from_db_value(self, value, expression, connection, context):
        return self._parse_value(value)


    def to_python(self, value):
        return self._parse_value(value)


    def contribute_to_class(self, cls, name):
        super(TagsField, self).contribute_to_class(cls, name)
        func = lambda self, fieldname = name: ', '.join(getattr(self, fieldname))
        setattr(cls, 'get_%s_display' % self.name, func)


    def validate(self, value, model_instance):
        if self.choices and value:
            allowed_values = []
            for option_key, option_value in self.choices:
                if isinstance(option_value, (list, tuple)):
                    # This is an optgroup, so look inside the group for
                    # options.
                    for optgroup_key, optgroup_value in option_value:
                        allowed_values.append(optgroup_key)
                else:
                    allowed_values.append(option_key)

            for v in value:
                if v not in allowed_values:
                    raise ValidationError(
                        self.error_messages['invalid_choice'],
                        code='invalid_choice',
                        params={'value': value},
                    )


    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_db_prep_value(value)


class IntegerRangeField(models.IntegerField):
    """
    Provides min-max validation for integer fields.
    Implementation based on:
    http://stackoverflow.com/questions/849142/how-to-limit-the-maximum-value-of-a-numeric-field-in-a-django-model
    """
    def __init__(self, verbose_name=None, name=None, min_value=None, max_value=None, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        models.IntegerField.__init__(self, verbose_name, name, **kwargs)


    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value':self.max_value}
        defaults.update(kwargs)
        return super(IntegerRangeField, self).formfield(**defaults)
