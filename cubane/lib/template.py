# coding=UTF-8
from __future__ import unicode_literals
from django.template import TemplateDoesNotExist
from django.template.loader import get_template as django_get_template
from django.template.backends.django import Template
from django.utils import six


class CubaneTemplate(Template):
    """
    Extension of django templates to allow rendering of templates based on
    a context, not just dictionaries.
    """
    def render(self, context=None, request=None):
        if isinstance(context, dict):
            return super(CubaneTemplate, self).render(context, request)
        else:
            try:
                return self.template.render(context)
            except TemplateDoesNotExist as exc:
                reraise(exc, self.backend)


def get_compatible_template(t):
    """
    Return a compatible template that can render content based on a template
    context and not only a dictionary.
    """
    # Django 1.11 migration:
    # django.template.backends.django.Template.render()
    #   prohibits non-dict context
    #
    # re-pack Template object so that it supports rendering based on an existing
    # Context avoiding having to flatten the context which will be slow.
    if isinstance(t, Template):
        t = CubaneTemplate(t.template, t.backend)
    return t


def get_template(template_name, using=None):
    """
    Return a template based on the given template name.
    """
    return get_compatible_template(
        django_get_template(template_name, using)
    )