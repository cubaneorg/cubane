# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import render_to_response, render
from django.template import Template
from cubane.models import Country
from cubane.decorators import template
from cubane.cms.decorators import cubane_cms_context
from cubane.lib.libjson import to_json, to_json_response
from cubane.lib.template import get_template
from cubane.ishop import get_product_model, get_order_model
from cubane.ishop.views import get_shop
from cubane.ishop.models import OrderBase, Voucher, DeliveryOption
from cubane.ishop.apps.shop.basket.forms import AddToBasketForm
from cubane.ishop.basket import Basket, BasketItem, get_basket_variety_update
from decimal import Decimal
import datetime


def get_basket_prefix(request, request_data):
    """
    Return a valid basket prefix for the given request data.
    """
    prefix = request_data.get('prefix')

    if not prefix:
        prefix = settings.SHOP_BASKET_SESSION_VAR

    if prefix not in settings.SHOP_BASKET_ALLOWED_PREFIX:
        if not (request is not None and hasattr(request, 'user') and (request.user.is_staff or request.user.is_superuser)):
            prefix = settings.SHOP_BASKET_SESSION_VAR

    return prefix


def get_return_url(request):
    """
    Get return url from request object and return it. The url may come from the
    r argument (GET) or (if that is not present) from the referer url. If the
    url does not match the client domain name or the url is invalid or the url
    is the basket page, the url for the default browse page is returned instead.
    """
    import urlparse

    referer = request.GET.get('r', None)
    if referer == None:
        referer = request.META.get('HTTP_REFERER', '')

    # parse referer url
    try:
        p = urlparse.urlparse(referer)
        domain = p.netloc

        # ignore port (production only)
        if ':' in domain and not settings.DEBUG:
            domain = domain.rsplit(':', 2)[0]

        return p.path
    except:
       pass

    # default
    return reverse('shop.index')


def get_basket_html(request, basket):
    """
    Return the basket (html).
    """
    if basket.prefix not in settings.SHOP_BASKET_ALLOWED_PREFIX and request.user and (request.user.is_staff or request.user.is_superuser):
        template_name = 'cubane/ishop/elements/order/basket/basket.html'
    else:
        template_name = 'cubane/ishop/elements/basket/basket_panel.html'

    template = get_template(template_name)
    template_context = {
        'settings': request.settings,
        'basket': basket,
        'post_url': reverse('shop.basket.update') + '?r=%s' % get_return_url(request)
    }

    # allow for the template context to be updated before rendering the basket
    shop = get_shop()
    template_context = shop.on_basket_context(request, basket, template_context)
    return template.render(template_context, request)


def get_delivery_option_details_html(request, delivery_option_details):
    """
    Return delivery option details (html).
    """
    template = get_template('cubane/ishop/elements/order/delivery_option_details.html')
    context = {
        'delivery_option': delivery_option_details
    }
    return template.render(context, request)


def index(request):
    """
    Return basket html content.
    """
    if not request.is_ajax():
        raise Http404('Ajax only.')

    # get basket
    prefix = get_basket_prefix(request, request.GET)
    basket = Basket(request, prefix=prefix)
    return HttpResponse(get_basket_html(request, basket))


def get_product_or_404(request):
    product_id = request.POST.get('product_id', None)
    if product_id == None:
        raise Http404('Missing argument: product_id.')

    try:
        product_id = int(product_id)
    except ValueError:
        raise Http404('Argument product_id is not an integer.')

    return get_object_or_404(get_product_model(), pk=product_id, draft=False)


@require_POST
def add(request):
    """
    Add given product to the customer's basket and redirect to the basket page.
    """
    product = get_product_or_404(request)

    return_url = get_return_url(request)

    form = AddToBasketForm(
        request.POST,
        request=request,
        product=product
    )

    variant = ''
    quantity = 0
    price = 0
    prefix = None

    if form.is_valid():
        d = form.cleaned_data

        variety_options = form.get_variety_options()
        variety_option_labels = form.get_variety_option_labels(variety_options)
        variant = ', '.join([option.title for option in variety_options])
        quantity = form.get_quantity()
        prefix = get_basket_prefix(request, d)

        # add to basket
        basket = Basket(request, prefix=prefix)
        item = basket.add_item(
            product,
            variety_options,
            quantity,
            custom=None,
            labels=variety_option_labels
        )

        if item:
            price = item.total_product
        else:
            messages.error(request, "Please note that the product '%s' cannot be added to basket." % product.title)

        # alert for non-returnable products
        if product.non_returnable:
            messages.warning(request, "Please note that the product '%s' cannot be returned." % product.title)

        # hook
        shop = get_shop()
        shop.on_basket_added(request, basket, product, variety_options, quantity)
        basket.save()
        errors = False
    else:
        errors = form.errors

    if request.is_ajax():
        basket = Basket(request, prefix=prefix)
        return to_json_response({
            'success': True,
            'html': get_basket_html(request, basket),
            'errors': errors,
            'prefix': basket.prefix,
            'added': product.to_ga_dict({
                'variant': variant,
                'quantity': quantity,
                'price': price
            })
        })
    else:
        return HttpResponseRedirect(return_url)


@require_POST
def update(request):
    """
    Update basket. This may also trigger "continue shopping" and "checkout".
    """
    # get prefix
    prefix = get_basket_prefix(request, request.POST)

    # get basket
    basket = Basket(request, prefix=prefix)
    return_url = get_return_url(request)

    # keep track of removed items
    removed_items = []
    def add_removed_item(item):
        removed_items.append(item)

    if not basket.is_frozen:
        # update quantity
        for item in list(basket.items):
            k = 'qty_%s' % item.hash
            if k in request.POST:
                try:
                    qty = int(request.POST.get(k, 0))
                except ValueError:
                    qty = 0

                removed = basket.update_quantity_by_hash(item.hash, qty)
                if removed:
                    add_removed_item(item)

        # remove item
        item_hash = request.POST.get('remove_basket_item', '')
        if item_hash != '':
            item = basket.remove_item_by_hash(item_hash)
            if item:
                add_removed_item(item)

        # voucher
        if 'voucher-code' in request.POST:
            voucher_code = request.POST.get('voucher-code')
            if voucher_code:
                voucher_code = voucher_code.upper()
            if voucher_code:
                if voucher_code != basket.get_voucher_code():
                    # add voucher code to basket
                    if not basket.set_voucher(voucher_code):
                        if not request.is_ajax():
                            messages.error(request, 'Expired or unrecognised voucher code.')
            else:
                basket.remove_voucher()

        # delivery country
        if 'country_iso' in request.POST:
            try:
                country = Country.objects.get(iso=request.POST.get('country_iso'))
                basket.set_delivery_country(country)
            except Country.DoesNotExist:
                pass

        # custom total (staff only)
        if request.user.is_staff or request.user.is_superuser:
            if 'custom-total' in request.POST:
                custom_total = request.POST.get('custom-total')
                if custom_total == '':
                    basket.clear_custom_total()
                else:
                    custom_total = Decimal(custom_total)
                    basket.set_custom_total(custom_total)

    # click and collect
    if 'click_and_collect' in request.POST:
        basket.set_click_and_collect(
            request.POST.get('click_and_collect') in ['true', 'on']
        )

    # delivery option
    option_id = request.POST.get('delivery_option_id', None)
    delivery_option_details = None
    if option_id:
        try:
            option = DeliveryOption.objects.get(pk=option_id, enabled=True)
            delivery_option_details = basket.get_delivery_details(option)
            basket.set_delivery_option(option)
        except DeliveryOption.DoesNotExist:
            pass

    # processing state (backend only)
    if request.user.is_staff or request.user.is_superuser:
        for item in list(basket.items):
            k = 'processed_%s' % item.hash
            if k in request.POST:
                processed = request.POST.get(k, 'off') == 'on'
                basket.update_processed_by_hash(item.hash, processed)

    # save changes to basket
    basket.save()

    # ajax?
    if request.is_ajax():
        basket = Basket(request, prefix=prefix)
        return to_json_response({
            'success': True,
            'prefix': basket.prefix,
            'html': get_basket_html(request, basket),
            'delivery': get_delivery_option_details_html(request, delivery_option_details),
            'is_collection_only': basket.is_collection_only(),
            'finance_options': [option.to_dict() for option in basket.get_finance_options()],
            'removed': [item.to_ga_dict() for item in removed_items]
        })

    # next
    action = request.POST.get('action', 'update')
    if action == 'continue':
        return HttpResponseRedirect(return_url)
    elif action == 'checkout':
        return HttpResponseRedirect(reverse('shop.order.delivery'))
    else:
        return HttpResponseRedirect(return_url)


@require_POST
def get_basket_item_price(request):
    """
    Get basket item based on posted product and variety options.
    """
    product = get_product_or_404(request)
    return get_basket_variety_update(request, product)