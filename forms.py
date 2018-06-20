# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core import exceptions
from django.http import QueryDict
from django.forms.utils import flatatt, ErrorList
from django.forms.models import ModelChoiceField
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.template import Context
from django.template.defaultfilters import slugify
from cubane.templatetags.form_tags import FormNode
from cubane.lib.text import text_with_prefix, text_with_suffix
from cubane.lib.utf8 import ENCODING_CHOICES, DEFAULT_ENCOPDING
from cubane.lib.tree import TreeModelChoiceIterator
from cubane.lib.queryset import MaterializedQuerySet
from cubane.lib.libjson import to_json
from cubane.lib.model import collect_meta_list, collect_meta_dict
from cubane.lib.widget import build_attrs
from django.utils.encoding import force_text
from cubane.lib.email_validator import validate_email, EmailNotValidError
from django.core.validators import EmailValidator
from django.utils import datetime_safe
from itertools import chain
from collections import OrderedDict
import os
import copy
import re
import datetime



class NumberInput(forms.widgets.Input):
    """
    Renders a number widget (HTML5).
    """
    input_type = 'number'


class DateInput(forms.widgets.TextInput):
    """
    Renders a date widget (HTML5).
    """
    input_type = 'text'

    def __init__(self, attrs=None, format=None):
        super(DateInput, self).__init__(attrs)
        self.format = '%d/%m/%Y'


    def _format_value(self, value):
        if hasattr(value, 'strftime'):
            value = datetime_safe.new_date(value)
            return value.strftime(self.format)
        return value


    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = ''
        final_attrs = build_attrs(self.attrs, attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
        return format_html('<div class="input-append date-field"><input{0} placeholder="dd/mm/yyyy" /><span class="add-on"><span class="icon icon-calendar"></span></span></div>', flatatt(final_attrs))


class TimeInput(forms.widgets.Input):
    """
    Renders a time widget (HTML5).
    """
    input_type = 'text'


    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = ''
        final_attrs = build_attrs(self.attrs, attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
        return format_html('<div class="input-append time-field"><input{0} placeholder="HH:MM" /><span class="add-on"><span class="icon icon-time"></span></span></div>', flatatt(final_attrs))


class DateTimeInput(forms.widgets.Input):
    """
    Renders a date/time widget for local time (HTML5).
    """
    input_type = 'datetime-local'


class DateTimeZoneInput(forms.widgets.Input):
    """
    Renders a date/time widget with timezone (HTML5).
    """
    input_type = 'datetime'


class EmailInput(forms.widgets.Input):
    """
    Renders an email widget (HTML5).
    """
    input_type = 'email'


class PhoneInput(forms.widgets.Input):
    """
    Renders an telephone widget (HTML5).
    """
    input_type = 'tel'


class RangeInput(forms.widgets.Input):
    """
    Renders a range widget (HTML5).
    """
    input_type = 'range'


class ColorInput(forms.widgets.Input):
    """
    Renders a color picker.
    """
    input_type = 'text'

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = ''
        final_attrs = build_attrs(self.attrs, attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
        return format_html('<input{0} class="color-text" />', flatatt(final_attrs))


class StaticTextWidget(forms.Widget):
    """
    Plain text widget (no input)
    """
    def __init__(self, *args, **kwargs):
        self.text = kwargs.pop('text', None)
        super(StaticTextWidget, self).__init__(*args, **kwargs)


    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(u'<span class="static-text">%s</span>' % unicode(self.text if self.text else value))


class BootstrapTextInput(forms.TextInput):
    """
    Based on the bootstrap UI framework, this widget provides a flexiable way
    of having content before and/or after an input field.
    """
    def __init__(self, *args, **kwargs):
        self._prepend = kwargs.pop('prepend', None)
        self._append = kwargs.pop('append', None)
        super(BootstrapTextInput, self).__init__(*args, **kwargs)


    def render(self, *args, **kwargs):
        html = super(BootstrapTextInput, self).render(*args, **kwargs)

        if self._prepend != None and self._append != None:
            return mark_safe(u'<div class="input-prepend input-append""><span class="add-on">%s</span>%s<span class="add-on">%s</span></div>' % (self._prepend, html, self._append))
        elif self._prepend != None:
            return mark_safe(u'<div class="input-prepend"><span class="add-on">%s</span>%s</div>' % (self._prepend, html))
        elif self._append != None:
            return mark_safe(u'<div class="input-append">%s<span class="add-on">%s</span></div>' % (html, self._append))
        else:
            return html


class UrlInput(BootstrapTextInput):
    input_type = 'url'

    def __init__(self, *args, **kwargs):
        kwargs['prepend'] = 'URL:'
        super(UrlInput, self).__init__(*args, **kwargs)


class SectionWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = build_attrs(self.attrs, attrs)
        help_text = final_attrs.get('help_text', None)
        if help_text == '': help_text = None
        help = '<div class="form-section-help">%s</div>' % help_text if help_text != None else ''
        return mark_safe('<h2 class="form-section%s">%s</h2>%s' % (' with-help-text' if help_text != None else '', final_attrs.get('label', ''), help))


class SectionField(forms.Field):
    widget = SectionWidget

    def __init__(self, *args, **kwargs):
        kwargs['required'] = False
        self.fill = kwargs.pop('fill', False)

        if kwargs.get('label', '').startswith('!'):
            self.fill = True
            kwargs['label'] = kwargs.get('label')[1:]

        super(SectionField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        attrs = super(SectionField, self).widget_attrs(widget)
        attrs['label'] = self.label
        attrs['fill'] = self.fill
        attrs['help_text'] = self.help_text
        return attrs


class LocationMapWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        if attrs == None: attrs = {}
        attrs.update(self.attrs)
        attrs.setdefault('data-key', settings.CUBANE_GOOGLE_MAP_API_KEY)

        if 'class' not in attrs: attrs['class'] = ''
        if len(attrs['class']) > 0: attrs['class'] += ' '
        attrs['class'] += 'map-canvas'

        if 'data-lat' not in attrs: attrs['data-lat'] = 'id_lat'
        if 'data-lng' not in attrs: attrs['data-lng'] = 'id_lng'
        if 'data-zoom' not in attrs: attrs['data-zoom'] = 'id_zoom'

        final_attrs = build_attrs(self.attrs, attrs)
        return format_html('<div{0}></div>', flatatt(final_attrs))


class LocationMapField(forms.Field):
    widget = LocationMapWidget

    def __init__(self, *args, **kwargs):
        kwargs['required'] = False
        super(LocationMapField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        return super(LocationMapField, self).widget_attrs(widget)


class ExtFileField(forms.FileField):
    """
    Same as forms.FileField, but you can specify a list of allowed file
    extensions.
    """
    def __init__(self, *args, **kwargs):
        ext = kwargs.pop('ext', [])
        self.ext = [x.lower() for x in ext]
        super(ExtFileField, self).__init__(*args, **kwargs)


    def clean(self, *args, **kwargs):
        d = super(ExtFileField, self).clean(*args, **kwargs)
        if d:
            _, ext = os.path.splitext(d.name)
            ext = ext.lower()
            if ext not in self.ext:
                raise forms.ValidationError(
                    ("The given file extension '%s' is not allowed. Allowed file " +
                     "extensions are: %s.") % (
                        ext,
                        ', '.join(["'%s'" % x for x in self.ext])
                    )
                )


class RadioSelect(forms.RadioSelect):
    """
    Radio select widget which is also considering choices from its form field
    unlike Django's implementation in DJango 1.11.
    """
    def set_choices(self, choices):
        self._choices = choices


    def get_choices(self):
        if not self._choices:
            if hasattr(self, '_field'):
                return self._field.choices
        else:
            return self._choices


    choices = property(get_choices, set_choices)


class MultiSelectFormField(forms.MultipleChoiceField):
    """
    Based on django's CheckboxSelectMultiple, it provides a list of
    multiple choices where each can be selected independently.
    The field returns a string containing all selected options
    (comma-seperated).
    Implementation based on:
    https://djangosnippets.org/snippets/2753/
    """
    widget = forms.CheckboxSelectMultiple


    def __init__(self, *args, **kwargs):
        self.max_choices = kwargs.pop('max_choices', 0)
        super(MultiSelectFormField, self).__init__(*args, **kwargs)


    def clean(self, value):
        if not value and self.required:
            raise forms.ValidationError(self.error_messages['required'])
        return value


class ModelChoiceTreeField(forms.ModelChoiceField):
    """
    Like model choice field, but represents items as a tree structure.
    """
    def __init__(self, *args, **kwargs):
        self._tabs = kwargs.pop('tabs', 2)
        super(ModelChoiceTreeField, self).__init__(*args, **kwargs)


    def label_from_instance(self, obj):
        return mark_safe(('&nbsp;' * self._tabs * obj.level) + obj.title)


    def _get_choices(self):
        # make sure that the queryset is not cached
        if not isinstance(self._queryset, MaterializedQuerySet):
            self._queryset = copy.deepcopy(self._queryset)
        return TreeModelChoiceIterator(self, self._queryset)


    choices = property(_get_choices, forms.ChoiceField._set_choices)


class FormTab(object):
    """
    Describes a form tab including the title, slug and a list of fields
    associated with it.
    """
    def __init__(self, title, fields):
        self.title = title
        self.slug = slugify(self.title)
        self.fields = fields


class FormLayout(object):
    """
    Provides different layout options for rendering forms.
    """
    FLAT = 'flat'
    COLUMNS = 'columns'

    CHOICES = (
        'Flat', FLAT,
        'Columns', COLUMNS,
    )


class FormSectionLayout(object):
    """
    Provides section layout options.
    """
    NONE    = 'none'
    INHERIT = 'inherit'

    CHOICES = (
        (NONE,    'None'),
        (INHERIT, 'Inherit')
    )


class FormVisibilityPredicate(object):
    """
    Represents a predicate condition to evaluate form field visibility.
    """
    def __init__(self, field, value, compare='=='):
        if compare == '=':
            compare = '=='

        self.field = field
        self.value = value
        self.compare = compare


    def to_dict(self):
        """
        Return dict. encoded representation of this form visibility predicate.
        """
        if self.field and self.value is not None:
            return {
                'f': self.field,
                'v': self.value,
                'c': self.compare
            }
        else:
            return None


    def is_true(self, data):
        """
        Return True, if this predicate holds true for the given form data.
        """
        return data.get(self.field) == self.value


class FormVisibility(object):
    """
    Encodes form field visibility rules that are executed on the client-side
    to control the visibility of form fields based on current values of other
    form fields.
    """
    def __init__(self, predicates=None, field=None, value=None, compare='==', visible=None, required=None, clear=None):
        if predicates:
            self.predicates = predicates
        elif field and value is not None:
            self.predicates = [FormVisibilityPredicate(field, value, compare)]
        else:
            self.predicates = []

        self.visible = visible
        self.required = required
        self.clear = clear
        self.field = field


    def to_dict(self):
        """
        Return dict. encoded representation of form field visibility.
        """
        if self.predicates and (self.visible or self.required or self.clear):
            return {
                'p': [p.to_dict() for p in self.predicates],
                'v': self.visible,
                'r': self.required,
                'c': self.clear
            }
        else:
            return None


    def is_true(self, data):
        """
        Return True, if the predicate holds true for the given form data.
        """
        for predicate in self.predicates:
            if not predicate.is_true(data):
                return False
        return True


class FormInputLimit(object):
    """
    Represents input limits for form fields and will generate additional
    output information to users as they type.
    """
    def __init__(self, max_characters):
        self.max_characters = max_characters


    def to_dict(self):
        """
        Return dict. encoded representation of an input limit.
        """
        return {
            'max_characters': self.max_characters
        }


def form_clean(form, cleaned_data):
    """
    When cleaning form data, verify that the form checksum (if available)
    matches the checksum of the underlying database entity. If the checksum
    does not match, then an error is raised to indicate that the underlying
    database entity has been modified by someone else in the meantime. This is
    suppose to prevent unwanted modifications of the underlying database
    entity when multiple people are  working on the same thing.
    """
    if hasattr(form, '_edit'):
        # verify checksum
        if form._edit and form._instance and hasattr(form._instance, 'get_checksum'):
            checksum = cleaned_data.get('_cubane_instance_checksum')
            if checksum:
                if checksum != form._instance.get_checksum():
                    user = form._instance.updated_by

                    if user:
                        user_display = user.get_full_name() if user.get_full_name() else user.username
                    else:
                        user_display = 'Unknown User'

                    raise forms.ValidationError(mark_safe(
                        ("<span class=\"alert-text\">" +
                         "This entity was modified while you were editing " +
                         "it. Your changes were discarded in order to prevent " +
                         "data loss.</span><a class=\"btn\" href=\"%s\">Start Over</a>") % (
                            form._request.get_full_path()
                        )
                    ))

    # verify required field in combination with field visibility
    if hasattr(form, '_visibility'):
        for visibility_rule in form._visibility:
            if visibility_rule.is_true(cleaned_data):
                # make sure that fields are required
                ref_field = form.fields.get(visibility_rule.field)
                if visibility_rule.required:
                    for fieldname in visibility_rule.required:
                        field = form.fields.get(fieldname)
                        if field:
                            if not cleaned_data.get(fieldname):
                                form_field_error(form, fieldname, 'This field is required due to your choice for the field \'%s\'.' % ref_field.label)

    return cleaned_data


def form_exclude_fields(form):
    """
    Remove excluded fields from cleaned_data.
    """
    if hasattr(form, 'cleaned_data'):
        if hasattr(form, '_exclude'):
            for fieldname in form._exclude:
                if fieldname in form.cleaned_data:
                    del form.cleaned_data[fieldname]


def form_required_fields(form):
    """
    Return a list of BoundField objects that are required for this form
    to be filled out. We are avoiding to use the default iterator for bound
    fields on the form, since this would materialise bound fields before we
    ever would have a chance to change the fields for a form.
    """
    return [field.get_bound_field(form, name) for name, field in form.fields.items() if field.required]


def form_are_all_fields_required(form):
    """
    Return True, if all fields of this form are required fields and must
    all be filled out by the user.
    """
    for field in form:
        if not isinstance(field.field, SectionField):
            if not field.field.required:
                return False
    return True


def form_has_required_fields(form):
    """
    Return True, if the form contains at least one required field.
    """
    return len(form.required_fields()) > 0


def form_configure(form, request, instance=None, edit=True):
    """
    Overridden by derived class: Configures this form by configuring
    additional information that may be used during form validation or
    contains additional logic to adjust the form or to remove certain
    fields that do not apply.
    """
    # inject operational data
    form._request = request
    form._instance = instance
    form._edit = edit

    # form attributes
    if not hasattr(form, 'is_duplicate'): form.is_duplicate = False
    if not hasattr(form, 'is_embedded'): form.is_embedded = False
    if not hasattr(form, 'parent_form'): form.parent_form = None
    if not hasattr(form, 'parent_instance'): form.parent_instance = None

    #  inject current checksum as hidden field
    if edit and instance and not form.is_embedded and hasattr(instance, 'get_checksum'):
        form.fields['_cubane_instance_checksum'] = forms.CharField(
                max_length=255,
                initial=instance.get_checksum(),
                widget=forms.HiddenInput()
            )

    # configure form fields and assign to widgets
    for field in form.fields.values():
        field.widget._field = field

        if hasattr(field, 'configure'):
            field.configure(request, form, instance, edit)


def form_unicode(form):
    """
    Render this form by using a default form layout scheme depending on
    the user interface framework that is used.
    """
    renderer = FormNode('form')
    return renderer.render(Context({'form': form}))


def form_to_dict(form):
    """
    Return a dictionary-representation of this form and its fields
    that can easily be represented as JSON.
    """
    return [{
        'name': name,
        'label': field.label,
        'required': field.required,
        'type': field.widget.__class__.__name__.lower().replace('input', '')
    } for name, field in form.fields.items()]


def form_is_tabbed(form):
    """
    Return True, if the form has tabs.
    """
    return form._tabs is not None and len(form._tabs) > 0


def form_has_sections(form):
    """
    Return True, if the form has sections.
    """
    return len(form._sections.keys()) > 0


def form_get_all_tabs(form):
    """
    Return a list of all tabs for this form including the title, the slug and
    a list of all field names that are included in each tab in order in which
    they are listed to appear.
    """
    tabs = []
    if form_is_tabbed(form):
        form_fields = [field for field in form]
        for tab in form._tabs:
            name = tab['title']
            fieldnames = tab.get('fields', [])
            fields = []
            for fieldname in fieldnames:
                for field in form_fields:
                    if field.name == fieldname:
                        fields.append(field)
            tabs.append(FormTab(name, fields))

    return tabs


def form_has_tabs(cls):
    """
    Return True, if the given form class has tabs not specifically turned off.
    """
    if hasattr(cls, 'Meta') and hasattr(cls.Meta, 'tabs'):
        if cls.Meta.tabs is None:
            return False
    return True


def form_get_tabs(cls):
    """
    Return a list of tabs for the given form class. This does not include
    tabs from parent classes. If no tabs are defined, the empty list is returned.
    """
    if hasattr(cls, 'Meta') and hasattr(cls.Meta, 'tabs'):
        return copy.deepcopy(cls.Meta.tabs)
    else:
        return []


def form_get_tab_by_title(tabs, title):
    """
    Return the tab with the given title within the given list of tabs or None.
    """
    for tab in tabs:
        if tab['title'] == title:
            return tab
    return None


def form_remove_field_from_existing_tab(fieldname, tabs):
    """
    Remove the field with the given name from any existing tab.
    """
    for tab in tabs:
        for field in tab['fields']:
            m = re.match(r'^(?P<fieldname>[_\w\d]+)(:(?P<ref>before|after)\((?P<ref_fieldname>[_\w\d]+)\))?$', field)
            if m.group('fieldname') == fieldname:
                tab['fields'].pop(tab['fields'].index(field))


def form_merge_tabs(src, dst):
    """
    Merge given source list of tabs into given dest. list of tabs by returning
    a new list of tabs which is the result of the merge.
    """
    dst_tabs = copy.deepcopy(dst)
    dst_titles = [tab['title'] for tab in dst_tabs]
    for tab in src:
        # parse title, which might be presented as
        # OriginalTitle:as(New Title Name)
        tab_title = tab['title']
        tab_title_text = tab_title

        # evaluate tab title to extract alternative name
        if tab_title:
            m = re.match(r'(?P<title>[-\._\w\d\s]+)(:as\((?P<title_text>[-\._\w\d\s]+)\))?$', tab_title)
            if m:
                tab_title = m.group('title')
                tab_title_text = m.group('title_text')

        if tab_title in dst_titles:
            # get tab by title
            dst_tab = form_get_tab_by_title(dst_tabs, tab_title)

            # optionally rename title
            if tab_title_text:
                dst_tab['title'] = tab_title_text

            # process fields
            for field in tab.get('fields', []):
                m = re.match(r'^(?P<fieldname>[_\w\d]+)(:(?P<ref>before|after)\((?P<ref_fieldname>[_\w\d]+)\))?$', field)
                if m:
                    form_remove_field_from_existing_tab(m.group('fieldname'), dst_tabs)

                    if m.group('ref_fieldname'):
                        # insert before|after referenced field
                        # (which must exist)
                        try:
                            i = dst_tab['fields'].index(m.group('ref_fieldname'))
                        except ValueError:
                            raise ValueError(
                                ("Unable to insert form field '%(fieldname)s' %(ref)s field " +
                                 "'%(ref_fieldname)s', because field '%(ref_fieldname)s' does not exist.") % {
                                    'fieldname': m.group('fieldname'),
                                    'ref': m.group('ref'),
                                    'ref_fieldname': m.group('ref_fieldname')
                                }
                            )

                        if m.group('ref') == 'after':
                            i += 1

                        if m.group('fieldname') not in dst_tab['fields']:
                            dst_tab['fields'].insert(i, m.group('fieldname'))
                    else:
                        if field not in dst_tab['fields']:
                            dst_tab['fields'].append(field)
                else:
                    raise ValueError("Incorrect field reference '%s' for refering tab fields." % field)
        else:
            dst_tabs.append(tab)
            dst_titles.append(tab_title_text)
    return dst_tabs


def form_collect_tabs(cls):
    """
    Collect all tabs from the given form class including all tabs from all base
    classes and the class itself. Tabs a merged by appending fields to existing
    tabs (in top to bottom order).
    """
    # merge tabs from all sub-clases
    tabs = []
    for base in cls.__bases__:
        base_tabs = form_collect_tabs(base)
        tabs = form_merge_tabs(base_tabs, tabs)

    # merge tabs defined in this class with tabs from all parent classes
    return form_merge_tabs(form_get_tabs(cls), tabs)


def form_update_sections(form):
    """
    Update form sections.
    """
    form._sections = {}
    def collect_sections(cls):
        if hasattr(cls, 'Meta'):
            # collect sections from form class
            if hasattr(cls.Meta, 'sections'):
                # stop collection if we do not want sections to begin with
                if cls.Meta.sections == FormSectionLayout.NONE:
                    return

                for fieldname, section in cls.Meta.sections.items():
                    if fieldname in form.fields:
                        if fieldname not in form._sections:
                            form._sections[fieldname] = copy.deepcopy(section)

            # collect sections form fields (tabs)
            if hasattr(cls.Meta, 'tabs'):
                for tab in cls.Meta.tabs:
                    fields = tab.get('fields', [])
                    for field, next_field in zip(fields, fields[1:]):
                        if field.startswith(':') and next_field:
                            form._sections[next_field] = field[1:]

        # collect for base classes
        for subcls in cls.__bases__:
            collect_sections(subcls)

    collect_sections(form.__class__)


def validate_email_address(value):
    """
    Email Validation for the form_setup as the replacement for django built-in validator.
    """
    try:
        validate_email(value)
    except EmailNotValidError as e:
        raise ValidationError(unicode(e))


def form_setup_initial(form, initial):
    """
    Process the given form initial and give each form field a chance to
    intercept and/or alter the initial value.
    """
    if initial:
        for fieldname, field in form.base_fields.items():
            if fieldname in initial and hasattr(field, 'before_initial'):
                initial[fieldname] = field.before_initial(initial[fieldname])


def form_setup(form):
    """
    Setup and validate form. Raise error if there is at least one required
    field that does not appear in tabs if a tabbed form is used.
    """
    # defaults
    form._request = None
    form._instance = None
    form._edit = False

    # create Meta if it does not exist yet, since other parts of the form
    # library expect Meta to be present...
    if not hasattr(form, 'Meta'):
        form.Meta = {}

    # collect section_fields
    section_fields = []
    def collect_section_fields(cls):
        if hasattr(cls, 'Meta') and hasattr(cls.Meta, 'section_fields'):
            if not isinstance(cls.Meta.section_fields, list):
                raise ValueError('Form \'%s\' is declaring field \'Meta.section_fields\'. List expected but was \'%s\'.' % (
                    cls.__name__,
                    cls.Meta.section_fields.__class__.__name__
                ))

            section_fields.extend(cls.Meta.section_fields)
        for subcls in cls.__bases__:
            collect_section_fields(subcls)
    collect_section_fields(form.__class__)

    # if we have a list of fields with sections, split them into fields
    # and sections...
    fields = []
    sections = {}
    if section_fields:
        for field, next_field in zip(section_fields, section_fields[1:] + [None]):
            if field.startswith(':') and next_field:
                sections[next_field] = field[1:]
            else:
                fields.append(field)

        if hasattr(form.Meta, 'fields') and form.Meta.fields != '__all__':
            form.Meta.fields.extend(fields)
        else:
            form.Meta.fields = fields

        if hasattr(form.Meta, 'sections'):
            form.Meta.sections.update(sections)
        else:
            form.Meta.sections = sections

        # fix field order
        for fieldname in fields:
            _field = form.fields.get(fieldname)
            if _field is None:
                raise ValueError('Form field \'%s\' as referenced via \'section_fields\' in form \'%s\' does not exist.' % (
                    fieldname,
                    form.__class__.__name__
                ))
            del form.fields[fieldname]
            form.fields[fieldname] = _field

    # collect field exclusions
    def collect_exclude(cls):
        excludes = []
        def extend(_excludes):
            for e in _excludes:
                if e not in excludes:
                    excludes.append(e)
        if hasattr(cls, 'Meta') and hasattr(cls.Meta, 'exclude'):
            extend(cls.Meta.exclude)
        for subcls in cls.__bases__:
            extend(collect_exclude(subcls))
        return excludes
    form._exclude = collect_exclude(form.__class__)

    # create deep copy of tabs, we do not want to modify
    # class data, only instance data
    if form_has_tabs(form.__class__) and getattr(form, 'has_tabs', True):
        form._tabs = form_collect_tabs(form.__class__)
    else:
        form._tabs = None

    # collect all widget overrides from all parent classes
    widgets = {}
    def collect_widgets(cls):
        if hasattr(cls, 'Meta') and hasattr(cls.Meta, 'widgets'):
            for fieldname, widget in cls.Meta.widgets.items():
                if fieldname not in widgets:
                    widgets[fieldname] = copy.deepcopy(widget)
        for subcls in cls.__bases__:
            collect_widgets(subcls)
    collect_widgets(form.__class__)

    # patch fields with widgets
    for fieldname, widget in widgets.items():
        if fieldname in form.fields:
            form.fields[fieldname].widget = widget

    # patch email field with custom validator (django built-in validator is
    # not following the latest specification)
    for fieldname in form.fields:
        if isinstance(form.fields[fieldname], forms.EmailField):
            for validator in form.fields[fieldname].validators:
                if isinstance(validator, EmailValidator):
                    loc = form.fields[fieldname].validators.index(validator)
                    form.fields[fieldname].validators.remove(validator)
                    form.fields[fieldname].validators.insert(loc, validate_email_address)

    # collect all sections from all parent classes
    form_update_sections(form)

    # copy form layout from meta class to form instance
    if hasattr(form.Meta, 'layout'):
        form.layout = form.Meta.layout
    else:
        # if the form has sections, the default layout method is COLUMNS,
        # which renders all sections in a two-column layout.
        if form_has_sections(form):
            form.layout = FormLayout.COLUMNS
        else:
            form.layout = FormLayout.FLAT

    # construct list of references field names
    names = []
    if form._tabs:
        for tab in form._tabs:
            for fieldname in tab.get('fields', []):
                if not fieldname.startswith(':'):
                    names.append(fieldname)
    elif fields:
        for fieldname in fields:
            if fieldname not in names:
                names.append(fieldname)

    # verify that each required field is references when using tabs or
    # section_fields
    if len(names) > 0 and (form._tabs or fields):
        for field in form_required_fields(form):
            if field.name not in names and not field.name.startswith('_'):
                raise ValueError(
                    ("Form '%s' does not refer to required field " +
                     "'%s'. Add a reference to this field to Meta.tabs or " +
                     "Meta.section_fields.") % (
                        form.__class__.__name__,
                        field.name
                    )
                )

    # collect visibility rules
    form._visibility = collect_meta_list(form, 'visibility')

    # collect blueprint rules
    blueprints = collect_meta_dict(form, 'blueprints')
    form._blueprints = {}
    for fieldname, fields in blueprints.items():
        field = form.fields.get(fieldname)
        if field and isinstance(field, ModelChoiceField):
            model = field.queryset.model
            form._blueprints[fieldname] = {
                'model': '%s.%s' % (model.__module__, model.__name__),
                'fields': fields
            }

    # collect limits
    form._limits = collect_meta_dict(form, 'limits')


def form_remove_section_fields(form):
    """
    Remove any existing section fields from the form and tabs.
    """
    section_fieldnames = [fieldname for fieldname, field in form.fields.items() if isinstance(field, SectionField)]

    for fieldname in section_fieldnames:
        del form.fields[fieldname]

    if form_is_tabbed(form):
        for tab in form._tabs:
            for fieldname in section_fieldnames:
                if fieldname in tab['fields']:
                    tab['fields'].remove(fieldname)


def form_inject_sections(form):
    """
    Inject section fields into the form. sections are also injected into
    tabs.
    """
    # remove existing sections
    form_remove_section_fields(form)

    # insert new sections
    is_tabbed = form_is_tabbed(form)

    # insert section field to form
    tmp_fields = OrderedDict()
    for field in form.fields.items():
        for fieldname, title in form._sections.items():
            section_name = '_%s' % fieldname

            p = title.split('|', 1)
            if len(p) == 2:
                title = p[0].strip()
                help_text = p[1].strip()
            else:
                help_text = None

            if field[0] == fieldname:
                tmp_fields.update({section_name: SectionField(label=title, help_text=help_text)})
        tmp_fields.update({field})
    form.fields = tmp_fields

    # insert reference to tabs
    for fieldname, title in form._sections.items():
        section_name = '_%s' % fieldname
        if is_tabbed:
            for tab in form._tabs:
                for i, refname in enumerate(tab['fields'], start=0):
                    if refname == fieldname:
                        tab['fields'].insert(i, section_name)
                        break
                else:
                    continue
                break


def form_field_with_prefix(form, fieldname, prefix):
    """
    Transform the form field value for the given form field, so that the
    value always starts with the given prefix value.
    """
    return text_with_prefix(form.cleaned_data.get(fieldname), prefix)


def form_field_with_suffix(form, fieldname, suffix):
    """
    Transform the form field value for the given form field, so that the
    value always ends with the given suffix value.
    """
    return text_with_suffix(form.cleaned_data.get(fieldname), suffix)


def form_remove_tab(form, title, remove_fields=False):
    """
    Remove the tab with the given title from the given form (including all
    referenced form fields).
    """
    try:
        index = [tab.get('title') for tab in form._tabs].index(title)
    except ValueError:
        raise ValueError('Tab \'%s\' does not exist.' % title)

    # remove fields
    if remove_fields:
        form_remove_fields(form, form._tabs[index].get('fields', []))

    # remove tab from tabs
    del form._tabs[index]


def form_remove_tabs(form):
    """
    Remove all tabs, leaving the form as a non-tabbed form.
    """
    form._tabs = []


def form_has_tab(form, title):
    """
    Return True, if the given form has a tab with the given title.
    """
    return title in [tab.get('title') for tab in form._tabs]


def form_remove_field(form, fieldname, if_exists=False):
    """
    Remove a field with given name.
    """
    if fieldname in form.fields:
        del form.fields[fieldname]
    elif not if_exists:
        raise ValueError('Field \'%s\' does not exist.' % fieldname)


def form_remove_fields(form, fieldnames, if_exists=False):
    """
    Remove a list of form fields.
    """
    for fieldname in fieldnames:
        form_remove_field(form, fieldname, if_exists)


def form_field_error(form, fieldname, msg):
    """
    Raise the given error message for the given form field for the given form.
    """
    if fieldname in form.fields:
        if not hasattr(form, '_errors') or form._errors is None:
            form._errors = {}

        form._errors.setdefault(fieldname, ErrorList()).append(msg)
    else:
        raise ValueError('Field \'%s\' does not exist.' % fieldname)


def form_has_visibility_rules(form):
    """
    Return True, if there is at least one visibility rule present for the
    given form.
    """
    return len(form._visibility) > 0


def form_get_encoded_visibility_rules(form):
    """
    Return a list of visibility rules encoded in a DOM-safe format to be
    interpreted via Javascript on the client to dynamically change the
    visibility of for form fields.
    """
    return to_json([v.to_dict() for v in form._visibility])


def form_has_blueprint_rules(form):
    """
    Return True, if there is at least one blueprint rule present for the
    given form.
    """
    return len(form._blueprints) > 0


def form_get_encoded_blueprint_rules(form):
    """
    Return a list of blueprint rules encoded in a DOM-safe format to be
    interpreted via javascript on the client to dynamically change the value
    of other form fields based on values obtained from a related instance.
    """
    return to_json(form._blueprints)


def form_has_limit_rules(form):
    """
    Return True, if there is at least one limit rule present for the
    given form.
    """
    return len(form._limits) > 0


def form_get_encoded_limit_rules(form):
    """
    Return a list of limit rules encoded in a DOM-safe format to be
    interpreted via Javascript on the client to dynamically update
    information as characters are being typed.
    """
    d = {}

    for fieldname, limit in form._limits.items():
        d[fieldname] = limit.to_dict()

    return to_json(d)


def form_is_unique_constraint(form, queryset, **kwargs):
    """
    Return True, if the given queryset - with keyword arguments applied as
    filter predicates - yield no other instances, which would indicate that
    the given predicate constraints are unique. If the form is in edit mode
    then the current instance is excluded from such query.
    """
    instances = queryset.filter(**kwargs)
    if form._edit:
        instances = instances.exclude(pk=form._instance.id)
    return instances.count() == 0


class BaseFormMixin(object):
    """
    Cubane base form implementation that is used for BaseForm and BaseModelForm,
    which is why this implementation is organised as a Mixin.
    """
    ERROR_REQUIRED = 'This field is required.'


    @property
    def is_tabbed(self):
        return form_is_tabbed(self)


    @property
    def has_sections(self):
        return form_has_sections(self)


    @property
    def has_visibility_rules(self):
        return form_has_visibility_rules(self)


    @property
    def has_blueprint_rules(self):
        return form_has_blueprint_rules(self)


    @property
    def has_limit_rules(self):
        return form_has_limit_rules(self)


    @property
    def tabs(self):
        return form_get_all_tabs(self)


    @property
    def excluded_fields(self):
        return self._exclude


    @property
    def is_duplicate(self):
        return self._is_duplicate


    @property
    def has_line_items(self):
        from cubane.backend.forms import RelatedEditWidget

        for field in self.fields.values():
            if isinstance(field.widget, RelatedEditWidget):
                return True
        return False


    @is_duplicate.setter
    def is_duplicate(self, value):
        self._is_duplicate = value
    _is_duplicate = False


    def setup_initial(self, initial):
        return form_setup_initial(self, initial)


    def setup(self):
        return form_setup(self)


    def required_fields(self):
        return form_required_fields(self)


    def are_all_fields_requried(self):
        return form_are_all_fields_required(self)


    def has_required_fields(self):
        return form_has_required_fields(self)


    def configure(self, request, instance=None, edit=True):
        form_configure(self, request, instance, edit)


    def field_with_prefix(self, fieldname, prefix):
        return form_field_with_prefix(self, fieldname, prefix)


    def field_with_suffix(self, fieldname, suffix):
        return form_field_with_suffix(self, fieldname, suffix)


    def get_tab_by_title(self, title):
        return form_get_tab_by_title(self._tabs, title)


    def remove_tab(self, title, remove_fields=False):
        return form_remove_tab(self, title, remove_fields)


    def remove_tabs(self):
        return form_remove_tabs(self)


    def has_tab(self, title):
        return form_has_tab(self, title)


    def remove_field(self, fieldname, if_exists=False):
        return form_remove_field(self, fieldname, if_exists)


    def remove_fields(self, fieldnames, if_exists=False):
        return form_remove_fields(self, fieldnames, if_exists)


    def field_error(self, fieldname, msg):
        return form_field_error(self, fieldname, msg)


    def update_sections(self, collect=True):
        if collect:
            form_update_sections(self)
        form_inject_sections(self)


    def get_encoded_visibility_rules(self):
        return form_get_encoded_visibility_rules(self)


    def get_encoded_blueprint_rules(self):
        return form_get_encoded_blueprint_rules(self)


    def get_encoded_limit_rules(self):
        return form_get_encoded_limit_rules(self)


    def to_dict(self):
        return form_to_dict(self)


class BaseForm(forms.Form, BaseFormMixin):
    """
    Cubane base form implementaton that provides additional capabilities,
    helper methods, form configuration and form rendering.
    """
    def __init__(self, *args, **kwargs):
        self.setup_initial(kwargs.get('initial'))
        super(BaseForm, self).__init__(*args, **kwargs)
        self.setup()
        form_inject_sections(self)


    def full_clean(self):
        super(BaseForm, self).full_clean()
        form_exclude_fields(self)


    def clean(self):
        d = super(BaseForm, self).clean()
        d = form_clean(self, d)
        return d


    def __unicode__(self):
        return form_unicode(self)


class BaseModelForm(forms.ModelForm, BaseFormMixin):
    """
    Cubane base form implementation that provides the capabilities of django's
    ModelForm but also provides the general form helpers, configuration and
    rendering capabilities in the same way as BaseForm provides.
    """
    def __init__(self, *args, **kwargs):
        self.setup_initial(kwargs.get('initial'))
        super(BaseModelForm, self).__init__(*args, **kwargs)
        self.setup()
        form_inject_sections(self)


    def full_clean(self):
        super(BaseModelForm, self).full_clean()
        form_exclude_fields(self)


    def clean(self):
        d = super(BaseModelForm, self).clean()
        d = form_clean(self, d)
        return d


    def is_unique_constraint(self, queryset, **kwargs):
        return form_is_unique_constraint(self, queryset, **kwargs)


    def __unicode__(self):
        return form_unicode(self)


class BaseUserAuthForm(BaseForm):
    ERROR_INACTIVE_ACCOUNT = 'This account is inactive.'


class BaseLoginForm(BaseUserAuthForm):
    """
    Generic login form without fields but provides general infrastructure. You
    would derive your own custom login form from this base form and then add
    the fields username and password to it. You may customise labels and widgets
    as you need them.
    """
    ERROR_INVALID_USERNAME_OR_PASSWORD = 'Please enter a correct username and password. Note that both fields are case-sensitive.'


    def clean(self):
        d = super(BaseLoginForm, self).clean()

        username = d.get('username')
        password = d.get('password')

        if username and password:
            # lowercase email and leave username as it is
            try:
                validate_email(username)
                username = username.lower()
            except EmailNotValidError:
                pass
            except forms.ValidationError:
                pass

            # try authentification by username or email
            self.user_cache = self.authenticate(username=username, password=password)

            if self.user_cache is None:
                # inactive account?
                try:
                    if not User.objects.get(username=username).is_active:
                        raise forms.ValidationError(self.ERROR_INACTIVE_ACCOUNT)
                except User.DoesNotExist:
                    pass

                # incorrect username/password
                raise forms.ValidationError(self.ERROR_INVALID_USERNAME_OR_PASSWORD)
        else:
            raise forms.ValidationError(self.ERROR_INVALID_USERNAME_OR_PASSWORD)

        return d


    def authenticate(self, username, password):
        self.user_cache = authenticate(username=username, password=password)
        return self.user_cache


    def get_user_id(self):
        if hasattr(self, 'user_cache'):
            return self.user_cache.id
        return None


    def get_user(self):
        if hasattr(self, 'user_cache'):
            return self.user_cache
        return None


class BasePasswordForgottenForm(BaseUserAuthForm):
    """
    Standard form for resetting the password in case it was forgotten.
    """
    ERROR_UNKNOWN_EMAIL = 'We did not recognise this email address. Please try again.'


    email = forms.EmailField(
        label='Email Address',
        max_length=75,
        widget=forms.TextInput(attrs={'placeholder': 'Email Address'})
    )


    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email:
            # get user
            try:
                self.user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                raise forms.ValidationError(self.ERROR_UNKNOWN_EMAIL)

            # inactive?
            if not self.user.is_active:
                raise forms.ValidationError(self.ERROR_INACTIVE_ACCOUNT)

        return email


    def get_user(self):
        """
        Return the user who initiated the password forgotten process.
        """
        return self.user


class BaseChangePasswordForm(BaseForm):
    """
    Standard form for changing a user's password.
    """
    ERROR_PASSWORDS_DO_NOT_MATCH = (
        'Password confirmation does not match password. Please try again.'
    )


    password = forms.CharField(
        label='Password',
        max_length=64,
        widget=forms.PasswordInput(attrs={'placeholder': 'Your New Password'})
    )

    password_confirm = forms.CharField(
        label='Password (Confirm)',
        max_length=64,
        widget=forms.PasswordInput(attrs={'placeholder': 'Your New Password (Confirm)'})
    )


    def clean(self):
        d = self.cleaned_data

        password = d.get('password')
        confirm = d.get('password_confirm')

        if password and confirm:
            if password != confirm:
                self.field_error(
                    'password_confirm',
                    self.ERROR_PASSWORDS_DO_NOT_MATCH
                )

        return d


class MemberLoginForm(BaseLoginForm):
    """
    Standard login form for authenticating members.
    """
    username = forms.CharField(
        label='Username or Email',
        max_length=75,
        widget=forms.TextInput(attrs={'placeholder': 'Username or Email Address'})
    )

    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )


class DataImportForm(BaseForm):
    """
    Provides a basic data import form to upload a CSV file. This is used by the
    default ModelView that provides data import/export facilities out of the
    box.
    """
    csvfile = ExtFileField(
        label='CSV Data File',
        ext=['.csv'],
        help_text='Select and upload a CSV data file to import data from.'
    )

    encoding = forms.ChoiceField(
        required=True,
        choices=ENCODING_CHOICES,
        initial=DEFAULT_ENCOPDING,
        help_text='Choose the correct file encoding of the uploaded file.'
    )


class DataExportForm(BaseForm):
    """
    Provides a basic form for data export via CSV file by choosing the
    encoding type.
    """
    encoding = forms.ChoiceField(
        required=True,
        choices=ENCODING_CHOICES,
        initial=DEFAULT_ENCOPDING,
        help_text='Choose the file encoding of the file to be exported.'
    )


class FilterFormMixin(object):
    """
    Provides a set of default properties for filtering by common cubane-related
    fields, such as creation date.
    """
    FILTER_DATE_BEFORE  = 'before'
    FILTER_DATE_AFTER   = 'after'
    FILTER_DATE_EXACT   = 'exact'
    FILTER_DATE_CHOICES = (
        (FILTER_DATE_BEFORE, 'Before'),
        (FILTER_DATE_AFTER,  'After'),
        (FILTER_DATE_EXACT,  'Exact'),
    )


    def add_filter_by_created_on(self):
        self.fields['filter_created_on_type'] = forms.ChoiceField(
            label='Creation Date Filter Type',
            choices=self.FILTER_DATE_CHOICES
        )
        self.fields['filter_created_on'] = forms.DateField(
            label='Creation Date',
            widget=DateInput
        )


    def add_filter_by_updated_on(self):
        self.fields['filter_updated_on_type'] = forms.ChoiceField(
            label='Update Filter Type',
            choices=self.FILTER_DATE_CHOICES
        )
        self.fields['filter_updated_on'] = forms.DateField(
            label='Update Date',
            widget=DateInput
        )


    def filter_by(self, objects, args):
        objects = self._filter_by_date('created_on', objects, args)
        objects = self._filter_by_date('updated_on', objects, args)
        return objects


    def _filter_by_date(self, name, objects, args):
        filter_type = args.get('filter_%s_type' % name)
        filter_date = args.get('filter_%s' % name)
        if filter_type and filter_date:
            try:
                filter_date = datetime.datetime.strptime(filter_date, '%Y-%m-%d')
                filter_date = filter_date.date()
            except:
                filter_date = None

            if filter_date:
                if filter_type == self.FILTER_DATE_BEFORE:
                    objects = objects.filter(**{'%s__lt' % name: filter_date})
                elif filter_type == self.FILTER_DATE_AFTER:
                    objects = objects.filter(**{'%s__gt' % name: filter_date})
                elif filter_type == self.FILTER_DATE_EXACT:
                    objects = objects.filter(**{
                        '%s__year' % name: filter_date.year,
                        '%s__month' % name: filter_date.month,
                        '%s__day' % name: filter_date.day
                    })

        return objects
