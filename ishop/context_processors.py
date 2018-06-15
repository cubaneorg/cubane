# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings


def shop(request):
    # direct customer information
    try:
        customer = request.user.customer
    except:
        customer = None

    return {
        'CURRENCY': settings.CURRENCY,
        'SHOP_PREAUTH': settings.SHOP_PREAUTH,
        'customer': customer
    }
