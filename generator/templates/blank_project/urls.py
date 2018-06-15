# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.conf.urls import url, include
from django.contrib.sitemaps import views as sitemaps_views
from cubane.backend.views import Backend
from cubane.cms.views import get_cms
from cubane.urls import *
from cubane import views as cubane_views


backend = Backend()
cms = get_cms()


setup_default_urls(__name__)


urlpatterns += [
    url(r'^admin/', include(backend.urls)),
    url(r'^sitemap\.xml$', sitemaps_views.sitemap, {'sitemaps': cms.sitemaps}),
    url(r'^robots\.txt$', cubane_views.robots_txt),
    url(r'^', include(cms.urls)),
]