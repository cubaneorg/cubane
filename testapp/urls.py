# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.conf.urls import url, include
from django.contrib.sitemaps import views as sitemaps_views
from cubane import views as cubane_views
from cubane.backend.views import Backend
from cubane.cms.views import get_cms
from cubane.urls import *
from cubane.testapp import views as testapp_views


backend = Backend()
cms = get_cms()

setup_default_urls(__name__)


urlpatterns += [
    url(r'^dummy/', include('dummy.urls')),
    url(r'^admin/', include(backend.urls)),
    url(r'^sitemap\.xml$', sitemaps_views.sitemap, {'sitemaps': cms.sitemaps}),
    url(r'^robots\.txt$', cubane_views.robots_txt),
    url(r'^test-get-absolute-url/(?P<key>[-\w\d]+)/$', testapp_views.test_get_absolute_url, name='test_get_absolute_url'),
    url(r'^non-standard-page/$', testapp_views.test_non_standard_cms_page, name='test_non_standard_cms_page'),

    # shop
    url(r'^shop/', include('cubane.ishop.apps.shop.urls')),

    # cms
    url(r'^', include(cms.urls))
]
