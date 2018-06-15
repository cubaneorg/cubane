# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.resources import *
from cubane.lib.libjson import *
import os


RESOURCES = [
    'js/cubane.frontendloader.templating.js',
]


RESOURCE_TARGETS = {
    'frontend-editing-loader': [
        'cubane.frontendloader'
    ]
}


TARGET = 'frontend-editing'


def get_deploy_context(identifier):
    js_resources = get_resources(TARGET, 'js')
    css_resources = get_resources(TARGET, 'css')
    filenames = []

    if settings.DEBUG:
        if js_resources:
            filenames.extend([('js', filename) for filename in js_resources])

        if css_resources:
            filenames.extend([('css', filename) for filename in css_resources])
    else:
        if js_resources:
            filenames.append(('js', get_minified_filename(TARGET, 'js', identifier=identifier)))

        if css_resources:
            filenames.append(('css', get_minified_filename(TARGET, 'css', identifier=identifier)))

    resources = [{
        'typ': typ,
        'path': os.path.join(settings.STATIC_URL, filename)
    } for typ, filename in filenames]

    return {
        'resources': to_json(resources)
    }