# coding=UTF-8
from __future__ import unicode_literals
from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.index, name='shop.account.index'),
    url(r'^orders/(?P<status>processing|complete)/$', views.orders, name='shop.account.orders'),
    url(r'^details/$', views.details, name='shop.account.details'),
    url(r'^billing/$', views.billing, name='shop.account.billing'),
    url(r'^delivery/$', views.delivery, name='shop.account.delivery'),
    url(r'^delivery/create/$', views.delivery_address, kwargs={'pk': None}, name='shop.account.create_delivery_address'),
    url(r'^delivery/(?P<pk>\d+)/delete/$', views.delete_delivery_address, name='shop.account.delete_delivery_address'),
    url(r'^delivery/(?P<pk>\d+)/$', views.delivery_address, name='shop.account.delivery_address'),
    url(r'^password/$', views.password, name='shop.account.password'),
    url(r'^login/$', views.login, name='shop.account.login'),
    url(r'^logout/$', views.logout, name='shop.account.logout'),
    url(r'^signup/$', views.signup, name='shop.account.signup'),
]