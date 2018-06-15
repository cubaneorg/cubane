# coding=UTF-8
from __future__ import unicode_literals
from django.conf.urls import *
from . import views

urlpatterns = [
    url(r'^login/$', views.login, name='shop.order.login'),
    url(r'^delivery/$', views.delivery, name='shop.order.delivery'),
    url(r'^delivery-options/$', views.delivery_options, name='shop.order.delivery_options'),
    url(r'^complete/$', views.complete, name='shop.order.complete'),
    url(r'^status/(?P<secret_id>[a-fA-F0-9]+)/$', views.status, name='shop.order.status'),

    url(r'^shipping-notes/(?P<secret_id>[a-fA-F0-9]+)/$', views.shipping_notes, name='shop.order.shipping_notes'),

    # payment
    url(r'^pay/$', views.pay, name='shop.order.pay'),
    url(r'^payment-response/(?P<identifier>\d+)/$', views.payment_response, name='shop.order.payment_response'),
    url(r'^payment-response/$', views.default_payment_response, name='shop.order.default_payment_response'),
    url(r'^payment-update/(?P<identifier>\d+)/$', views.payment_update, name='shop.order.payment_update'),
    url(r'^payment-return/(?P<identifier>\d+)/$', views.payment_return, name='shop.order.payment_return'),
    url(r'^test-payment/(?P<secret_id>[a-fA-F0-9]+)/$', views.test_payment, name='shop.order.test_payment'),
]
