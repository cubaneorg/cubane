# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponse
from cubane.decorators import template
from django.shortcuts import render_to_response


@template('cubane/404.html')
def custom404(request):
    """
    Render default 404 page if the CMS app is installed, otherwise
    return a default (empty) 404 page.
    """
    # if cms is installed, let the cms process it...
    response = None
    if 'cubane.cms' in settings.INSTALLED_APPS:
        from cubane.cms.views import get_cms
        cms = get_cms()
        response = cms.default_404(request)

    # fall back to default template without going though the cms
    # or we are not using the cms to begin with...
    if not response:
        response = HttpResponse()

        # enforce status code
        response.status_code = 404

    return response


@template('cubane/500.html', status_code=500)
def custom500(request):
    """
    Render a default 500 error page.
    """
    return {}
