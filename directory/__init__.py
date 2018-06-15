# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings


RESOURCES = [
]


RESOURCE_TARGETS = {
    'backend': [
        'cubane.directory'
    ]
}


class DirectoryOrder(object):
    ORDER_DEFAULT     = 1
    ORDER_RANDOM      = 2
    ORDER_SEQ         = 3
    ORDER_TITLE       = 4
    ORDER_DATE        = 5
    ORDER_CUSTOM_DATE = 6
    ORDER_CHOICES = (
        (ORDER_DEFAULT,     'Default (Global Settings)'),
        (ORDER_RANDOM,      'Random'),
        (ORDER_SEQ,         'Defined sequence'),
        (ORDER_TITLE,       'Title'),
        (ORDER_DATE,        'Creation Date (newest first)'),
        (ORDER_CUSTOM_DATE, 'Custom Date')
    )

    DEFAULT_ORDER_CHOICES = (
        (ORDER_RANDOM,      'Random'),
        (ORDER_SEQ,         'Defined sequence'),
        (ORDER_TITLE,       'Title'),
        (ORDER_DATE,        'Creation Date (newest first)'),
        (ORDER_CUSTOM_DATE, 'Custom Date')
    )


def install_backend(backend):
    """
    Install backend section for directory content.
    """
    from cubane.directory.views import DirectoryBackendSection
    backend.register_section(DirectoryBackendSection())


def install_backend_content(content_section):
    # install additional elements to the CMS content tab
    from cubane.directory.views import get_directory_content_backend_sections
    for section in get_directory_content_backend_sections(content_section):
        content_section.sections.append(section)


def install_cms(cms):
    """
    Extend cms class with additional capabilities for scripting directory
    content.
    """
    from cubane.directory.scripting import DirectoryScriptingMixin
    from cubane.directory.views import CMSExtensions
    return cms.register_extension(DirectoryScriptingMixin, CMSExtensions)


def install_page_context(page_context):
    """
    Installs a page context extension, which is used for rending CMS content.
    """
    from cubane.directory.cms import DirectoryPageContextExtensions
    return page_context.register_extension(DirectoryPageContextExtensions)


def install_nav(nav):
    from cubane.directory.nav import DirectoryNavigationExtensions
    return nav.register_extension(DirectoryNavigationExtensions)
