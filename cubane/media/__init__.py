# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.app import require_app
require_app(__name__, 'cubane.backend')


RESOURCES = [
    # style
    'css/cubane.media.css',

    # smartcrop
    'smartcrop/smartcrop.js',

    # javascript
    '/cubane/js/cubane.js',
    '/cubane/js/cubane.dom.js',
    '/cubane/js/cubane.urls.js',
    '/cubane/js/cubane.dialog.js',
    'js/cubane.media.js'
]


RESOURCE_TARGETS = {
    'backend': [
        'cubane.media'
    ]
}


def install_backend(backend):
    if settings.CUBANE_BACKEND_MEDIA:
        from cubane.media.views import MediaBackendSection
        backend.register_section(MediaBackendSection())


def install_cms(cms):
    from cubane.media.scripting import MediaScriptingMixin
    return cms.register_extension(MediaScriptingMixin)


def install_tasks(runner):
    if settings.CUBANE_BACKEND_MEDIA:
        from cubane.media.tasks import MediaTask
        runner.register(MediaTask())
