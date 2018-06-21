# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from cubane.svgicons import get_combined_svg
from cubane.lib.resources import get_resources


def media_api_svgicons(request, target, name=None):
    """
    Serve an SVG icon set file for given target in debug mode.
    """
    if not settings.DEBUG:
        raise PermissionDenied(
            'SVG icon sets via the media api are only available in DEBUG mode.'
        )

    # get list of SVG resource files
    resources = get_resources(target, 'svg', name=name)
    styled_resources = get_resources(target, 'svg', 'with-style', name=name)

    # raise 404 if we cannot find an icon
    if not resources and not styled_resources:
        raise Http404('No icons found for the given target and/or icon name.')

    # construct svg icon set file content
    content = get_combined_svg(
        resources,
        styled_resources
    )

    # construct http response
    response = HttpResponse(content, content_type='image/svg+xml')
    response['Content-Length'] = len(content)

    return response