# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db.models import Q
from cubane.decorators import template
from cubane.cms.decorators import cubane_cms_context
from cubane.lib.parse import parse_int_list
from cubane.lib.libjson import to_json_response
from cubane.lib.paginator import create_paginator
from cubane.ishop import get_category_model, get_product_model
from cubane.ishop.views import get_shop
from cubane.ishop.mail import *
from cubane.ishop.models import ProductBase
from cubane.ishop.models import VarietyAssignment
from cubane.media.models import Media
from forms import ProductOrderByForm, MailChimpForm
from mailsnake import MailSnake
import random
import re
import datetime


@template('cubane/ishop/pages/search.html')
@cubane_cms_context()
def search(request):
    """
    Search Result Page.
    """
    shop = get_shop()
    return shop.search_page(request)


@template('cubane/ishop/pages/category.html')
@cubane_cms_context()
def category(request, slug, pk):
    """
    Present a list of products for the given category and allow customers
    to drill down by filtering by varieties.
    """
    shop = get_shop()

    # current category based on slug url and pk
    category = shop.get_category_or_404(pk, slug)
    if isinstance(category, HttpResponse):
        return category

    return shop.category_page(request, category)


@template('cubane/ishop/pages/product.html')
@cubane_cms_context()
def product(request, slug, pk):
    """
    Present single product and description and allow customers to add
    the product to their basket.
    """
    shop = get_shop()

    # get product
    product = shop.get_product_or_404(pk, slug)
    if isinstance(product, HttpResponse):
        return product

    return shop.product_page(request, product)


def product_price(request):
    """
    Calculate the total product price for the given product and the given
    varieties.
    """
    # arguments
    product_id = request.GET.get('product', None)
    if not product_id:
        raise Http404('Argument product required.')
    try:
        ids = [int(x) for x in request.GET.getlist('varieties[]')]
    except ValueError:
        raise Http404('Invalid numeric argument for varieties.')
    try:
        quantity = int(request.GET.get('quantity', 1))
    except ValueError:
        raise Http404('Invalid numeric value for quantity argument.')

    # get product
    product = get_object_or_404(get_product_model(), pk=product_id, client=request.client)

    # get variety options
    varieties = list(VarietyAssignment.objects.select_related('variety_option').filter(
        id__in=ids,
        product=product
    ))

    return to_json_response({
        'net': quantity * (product.net_price + sum([option.price_net for option in varieties])),
        'gross': quantity * (product.gross_price + sum([option.price_gross for option in varieties]))
    })
