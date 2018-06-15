# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.app import require_app, get_app_label_ref
from cubane.lib.module import get_class_from_string
from django.conf import settings
require_app(__name__, 'django.contrib.sitemaps')
require_app(__name__, 'cubane.backend')


INCLUDE_RESOURCES = [
    'cubane.media'
]


RESOURCES = [
    'css/cubane.cms.css',
    'css/meta.preview.css',
    'css/sitemap.css',
    '/cubane/js/cubane.js',
    '/cubane/js/cubane.urls.js',
    '/cubane/js/cubane.dialog.js',
    '/cubane/js/cubane.format.js',
    'js/cubane.cms.js',
    'js/cubane.cms.sitemap.js',
]


RESOURCE_TARGETS = {
    'backend': [
        'cubane.cms'
    ]
}


def install_backend(backend):
    from cubane.cms.views import ContentBackendSection, SettingsBackendSection
    from cubane.cms.api import CmsApiView
    backend.register_section(ContentBackendSection())
    backend.register_section(SettingsBackendSection())
    backend.register_api(CmsApiView())


def install_cms(cms):
    from cubane.cms.scripting import CMSScriptingMixin
    return cms.register_extension(CMSScriptingMixin)


def get_page_model_name():
    """
    Return the name of the page model as configured by settings.CMS_PAGE_MODEL.
    """
    if hasattr(settings, 'CMS_PAGE_MODEL'):
        return get_app_label_ref(settings.CMS_PAGE_MODEL)
    else:
        return 'cms.Page'


def get_page_model():
    """
    Return the page model as configured by settings.CMS_PAGE_MODEL.
    """
    if hasattr(settings, 'CMS_PAGE_MODEL'):
        return get_class_from_string(settings.CMS_PAGE_MODEL)
    else:
        # default cms page model
        from cubane.cms.models import Page
        return Page
