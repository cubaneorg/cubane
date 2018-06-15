# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.conf.urls import url, include
from django.urls.utils import get_callable
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views import static
from cubane.lib.module import get_module_by_name


#
# Validate configuration
#
from cubane.settings import validate_settings
validate_settings(settings)


def setup_default_urls(module_name):
    """
    Setup default url patterns by adding additional url patterns to the given
    list of url patterns. Such additional patterns are concerned about
    serving media in DEBUG mode and adding default 404 and 500 handlers in
    PRODUCTION mode.
    """
    # get urls module
    urls = get_module_by_name(module_name)

    # create empty urlpatterns if not there yet
    if not hasattr(urls, 'urlpatterns'):
        urls.urlpatterns = []

    # django debug toolbar (debug only)
    if settings.DEBUG and settings.DEBUG_TOOLBAR:
        import debug_toolbar
        urls.urlpatterns += [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ]

    # 404 and 500 pages (PRODUCTION only)
    if not settings.DEBUG:
        urls.handler404 = settings.HANDLER_404
        urls.handler500 = settings.HANDLER_500
    else: # pragma: no cover
        urls.urlpatterns += [
            url(r'^404/$', get_callable(settings.HANDLER_404)),
            url(r'^500/$', get_callable(settings.HANDLER_500)),
        ]

    # enable postcode view if postcode in installed apps
    if 'cubane.postcode' in settings.INSTALLED_APPS:
        from cubane.postcode import views as postcode_views
        urls.urlpatterns += [
            url(r'^postcode-lookup/$', postcode_views.postcode_lookup, name='cubane.postcode_lookup')
        ]


    # serve media assets through django dev server (DEBUG only)
    if settings.DEBUG: # pragma: no cover
        # uploaded media files
        urls.urlpatterns += [
            url(
                r'^%s(?P<path>.*)$' % settings.MEDIA_URL,
                static.serve,
                {'document_root': settings.MEDIA_ROOT}
            )
        ]


    # serve media assets through frontend media api to allow for on-demand
    # media customisation and for downloading SVG icon sets
    if 'cubane.media' in settings.INSTALLED_APPS:
        from cubane.media import views as media_views

        # shapes
        urls.urlpatterns += [
            url(
                r'^%sshapes/(?P<shape>[-_\w]+)/(?P<size>[-_\w]+)/(?P<bucket>\d+)/(?P<pk>\d+)/(?P<filename>.*?)$' % settings.MEDIA_API_URL,
                media_views.media_api,
                name='cubane.media_api.shape'
            )
        ]

        # originals
        urls.urlpatterns += [
            url(
                r'^%soriginals/(?P<bucket>\d+)/(?P<pk>\d+)/(?P<filename>.*?)$' % settings.MEDIA_API_URL,
                media_views.media_api_original,
                name='cubane.media_api.original'
            )
        ]

        # by identifier alone
        urls.urlpatterns += [
            url(
                r'^%spk/(?P<pk>\d+)/$' % settings.MEDIA_API_URL,
                media_views.media_api_pk,
                name='cubane.media_api.pk'
            )
        ]

        # SVG icons sets (DEBUG only)
        if settings.DEBUG and 'cubane.svgicons' in settings.INSTALLED_APPS:
            from cubane.svgicons import views as svgicons_views
            urls.urlpatterns += [
                # individual icon
                url(
                    r'^%ssvgicons/(?P<target>[-_\w\d]+)/(?P<name>[-_\w\d]+)\.svg$' % settings.MEDIA_API_URL,
                    svgicons_views.media_api_svgicons
                ),

                # full icon set
                url(
                    r'^%ssvgicons/(?P<target>[-_\w\d]+)\.svg$' % settings.MEDIA_API_URL,
                    svgicons_views.media_api_svgicons,
                    kwargs={'name': None}
                )
            ]
