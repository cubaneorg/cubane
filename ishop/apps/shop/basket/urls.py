# coding=UTF-8
from __future__ import unicode_literals
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='shop.basket.index'),
    url(r'^add/$', views.add, name='shop.basket.add'),
    url(r'^update/$', views.update, name='shop.basket.update'),
    url(r'^get-basket-item-price/$', views.get_basket_item_price, name='shop.basket.get_basket_item_price'),
]