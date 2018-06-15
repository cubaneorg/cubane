# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from cubane.svgicons import get_svg_name_from_file
from cubane.svgicons import get_svg_content
from cubane.svgicons import get_combined_svg
from cubane.svgicons import get_svgicons_filename
from cubane.lib.resources import get_resources
from cubane.lib.resources import load_resource_version_identifier
from cubane.lib.resources import get_resource_target_definition
from cubane.lib.file import file_get_contents
import os


register = template.Library()


@register.simple_tag()
def svgicon(name):
    """
    Renders markup for presenting an svg icon with the given name, where the
    given SVG icon is assumed to be inlined within the DOM of the current page.
    """
    if not name:
        raise AttributeError(
            'Expected valid \'name\' argument for template tag \'svgicon\'.'
        )

    return format_html(
        '<i class="svgicon svgicon-{}">' +
            '<svg><use xlink:href="#svgicon-{}"/></svg>' +
        '</i>',
        name,
        name
    )


@register.simple_tag()
def svgiconref(ref):
    """
    Renders markup for presenting an SVG icon with the given name referencing
    the SVG icon set from an external source.
    """
    if not ref:
        raise AttributeError(
            'Expected valid \'ref\' argument for template tag \'svgiconref\'.'
        )

    # split reference into target and icon name
    try:
        target, name = ref.split('/', 2)
    except ValueError:
        raise AttributeError(
            'Expected valid \'ref\' argument for template tag \'svgiconref\' ' +
            'in the format \'<target>/<icon-name>\'.'
        )

    # determine target icon set filename
    if settings.DEBUG:
        # in debug mode, we use the media api to refer to an individual
        # SVG file. We need to use the media api, since there
        # is some processing involved here in order to guarantee that the
        # SVG icon behaves in the same way as in production mode.
        url = '/%ssvgicons/%s/%s.svg' % (settings.MEDIA_API_URL, target, name)
    else:
        # the deployment process should have generated all required SVG icon
        # files, so we simply refer to it...
        identifier = load_resource_version_identifier()
        filename = get_svgicons_filename(target, identifier)
        url = '%s%s' % (settings.STATIC_URL, filename)

    return format_html(
        '<i class="svgicon svgicon-{}"><svg>' +
            '<use xlink:href="{}#svgicon-{}"/></svg>' +
        '</i>',
        name,
        url,
        name
    )


@register.simple_tag()
def inline_svgicons(target):
    """
    Renders inline markup for defining an SVG icon sheet for all SVG icon
    assets defined for the given bucket name (target). SVG assets are using the
    standard resource system that is also used for CSS and Javascript assets in
    combination with resources and inline_resources template tags.
    """
    if target not in get_resource_target_definition():
        raise AttributeError(
            'Expected valid \'target\' argument for template ' +
            'tag \'inline_svgicons\'.'
        )

    if settings.DEBUG:
        return mark_safe(
            get_combined_svg(
                get_resources(target, 'svg'),
                get_resources(target, 'svg', 'with-style')
            )
        )
    else:
        identifier = load_resource_version_identifier()
        filename = get_svgicons_filename(target, identifier)
        path = os.path.join(settings.STATIC_ROOT, filename)
        return mark_safe(file_get_contents(path))