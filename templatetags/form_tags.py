# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import template
from django import forms
from django.template import Context
from django.template.defaulttags import CsrfTokenNode
from cubane.lib.templatetags import value_or_literal, value_or_none
from cubane.lib.template import get_template
register = template.Library()


class FormNode(template.Node):
    def __init__(self, form, enctype=None):
        self.form = form
        self.enctype = enctype


    def get_template(self):
        return get_template('cubane/backend/form/form_submit.html')


    def render(self, context):
        form = value_or_none(self.form, context)
        enctype = value_or_literal(self.enctype, context)

        if form == None:
            return ''

        t = self.get_template()
        d = {
            'form': form,
            'enctype': enctype
        }
        with context.push(**d):
            return t.render(context)


class FilterFormNode(FormNode):
    def __init__(self, form):
        super(FilterFormNode, self).__init__(form)


    def get_template(self):
        return get_template('cubane/backend/form/filter_form.html')


class AutoCsrfTokenNode(CsrfTokenNode):
    """
    Renders the default django CSRF token if the CsrfViewMiddleware is
    installed; otherwise return an empty string and ignore CSRF tokens.
    """
    def render(self, context):
        if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE_CLASSES:
            return super(AutoCsrfTokenNode, self).render(context)
        else:
            return ''


@register.filter(name='field_type')
def field_type(value):
    """
    Return the type of the given form field which is the name of the class that
    implements the field, such as CharField, IntegerField etc.
    """
    return value.field.__class__.__name__


@register.filter(name='widget_type')
def widget_type(value):
    """
    Return the type of the form field widget which is the name of the class that
    implements the field widget such as InputField, Textarea etc...
    """
    return value.field.widget.__class__.__name__


@register.filter(name='is_captcha_widget')
def widget_type(value):
    """
    Return true, if the widget of the applied form field is a captcha widget.
    """
    from cubane.enquiry.captchas import is_captcha_widget
    return is_captcha_widget(value.field.widget)


@register.filter(name='fields_per_row')
def fields_per_row(fields):
    """
    Partition given list of form fields into a list of rows, where each row
    contains two columns containing a list of all fields in that column.
    """
    from cubane.forms import SectionField

    # partition into sections
    sections = []
    bucket = []
    for field in fields:
        if isinstance(field.field, SectionField) and len(bucket) > 0:
            sections.append(bucket)
            bucket = [field]
        else:
            bucket.append(field)
    sections.append(bucket)

    # partition into 2 columns
    rows = []
    cols = []
    for section in sections:
        cols.append(section)
        if len(cols) >= 2 or (section and isinstance(section[0].field, SectionField) and section[0].field.fill):
            rows.append(cols)
            cols = []
    if len(cols) > 0:
        rows.append(cols)

    return rows


@register.tag('form')
def form(parser, token):
    """
    Renders a form based on a set of templates depending on the UI framework
    that is loaded into django.

    Syntax: {% form [<form> <enctype>] %}
    """
    bits = token.split_contents()
    if len(bits) > 1:
        form = bits[1]
    else:
        form = 'form'

    if len(bits) > 2:
        enctype = bits[2]
    else:
        enctype = None

    if len(bits) > 3:
        raise template.TemplateSyntaxError("'%s' takes max. of three argument: [<form>] <enctype>]" % bits[0])

    return FormNode(form, enctype)


@register.tag('filter_form')
def filter_form(parser, token):
    """
    Renders a form based on a set of templates depending on the UI framework
    that is loaded into django. The form is rendered as a filter form in a
    very compacy multi-column layout.

    Syntax: {% filter_form [<filter_form>] %}
    """
    bits = token.split_contents()
    if len(bits) > 1:
        form = bits[1]
    else:
        form = 'filter_form'

    if len(bits) > 2:
        raise template.TemplateSyntaxError("'%s' takes max. of two argument: [<filter_form>]" % bits[0])

    return FilterFormNode(form)


@register.tag
def auto_csrf_token(parser, token):
    """
    Include CSRF token if CSRF middleware is used, otherwise do not include
    the CSRF token.
    """
    return AutoCsrfTokenNode()