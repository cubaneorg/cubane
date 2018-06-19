# coding=UTF-8
from __future__ import unicode_literals
from django import template
from django.conf import settings
from django.contrib.auth.models import User
from cubane.lib.templatetags import value_or_none
from cubane.lib.currency import format_currency
from cubane.lib.template import get_template
from cubane.backend.views import BackendSection

register = template.Library()


def assert_section(filter_name, section):
    if not isinstance(section, BackendSection):
        raise ValueError((
            "Expected instance of 'cubane.backend.views.BackendSection' " + \
            "of the value to which the template filter '%s' " + \
            "is applied to."
        ) % filter_name)


def assert_user(filter_name, user):
    if not isinstance(user, User):
        raise ValueError((
            "Expected instance of 'django.contrib.auth.models.User' " + \
            "of argument to template filter '%s'."
        ) % filter_name)


class ListingNode(template.Node):
    def render(self, context):
        t = get_template('cubane/backend/listing/listing.html')
        return t.render(context)


@register.tag('listing')
def listing(parser, token):
    """
    Renders a list of objects and provides extensive search, filter, ordering
    and access to basic CRUD operations.

    Syntax: {% listing %}
    """
    return ListingNode()


@register.simple_tag(takes_context=True)
def backend_edit_url(context, instance):
    """
    Find the edit url for editing the given instance.
    """
    backend = value_or_none('backend', context)
    if backend:
        return backend.get_url_for_model_instance(instance, view='edit') + ('?pk=%s' % instance.pk)
    else:
        return ''


@register.filter()
def is_visible_for(section, user):
    """
    Returns True, if the given backend section is visible to the current
    user due to the permission system.
    """
    assert_section('is_visible_for', section)
    assert_user('is_visible_for', user)

    return section.is_visible_to_user(user)


@register.filter()
def get_frist_visible_section_url_for(section, user):
    """
    Return the url for the first backend sub-section that is visible to the
    given user.
    """
    assert_section('get_frist_visible_section_url_for', section)
    assert_user('get_frist_visible_section_url_for', user)

    return section.get_frist_visible_section_url_for(user)


@register.filter
def class_name(obj):
    return obj.__class__.__name__


@register.filter
def listing_format_currency(v):
    return format_currency(v)


@register.filter
def listing_format_percent(v):
    if v:
        return '%s%%' % v
    else:
        return v