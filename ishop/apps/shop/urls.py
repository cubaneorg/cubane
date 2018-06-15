# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.conf.urls import *
from . import views

urlpatterns = [
    # search
    url(r'^search/$', views.search, name='shop.search'),

    # basket, order and account services
    url(r'^basket/', include('cubane.ishop.apps.shop.basket.urls')),
    url(r'^order/', include('cubane.ishop.apps.shop.order.urls')),
    url(r'^account/', include('cubane.ishop.apps.shop.account.urls')),

    # price quries
    url(r'^product-price/$', views.product_price, name='shop.product_price'),

    # categories and products
    url(r'^category/(?P<slug>[-_\w]+)-(?P<pk>[\d]+)/$', views.category, name='shop.category'),
    url(r'^product/(?P<slug>[-_\w]+)-(?P<pk>[\d]+)/$', views.product, name='shop.product'),
]
