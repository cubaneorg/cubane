# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils.module_loading import import_module
from django.template import Template, Context
import inspect


def serve_static_with_context(response_content, identifier=None):
    """
    Render content in given template markup. This is used by cubane to execute
    resources through the django template system in order to substitute template
    expressions in asset files, such as css and js.
    """
    context = {}
    for app_name in settings.INSTALLED_APPS:
        try:
            app = import_module(app_name)
            if hasattr(app, 'get_deploy_context'):
                # get_deploy_context() may not take an identifier argument
                if len(inspect.getargspec(app.get_deploy_context)[0]) == 1:
                    context.update(app.get_deploy_context(identifier))
                else:
                    context.update(app.get_deploy_context())
        except ImportError:
            pass

    template = Template(response_content)
    content = template.render(Context(context))
    response_content = content

    return response_content