# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect
from django.db.models import Q, Max, Min, Prefetch, Case, When
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from cubane.backend.views import BackendSection
from cubane.cms.views import get_cms_settings, CMSGenericSitemap
from cubane.ishop import get_category_model, get_product_model, get_customer_model, get_order_model
from cubane.ishop.models import ProductBase, ShopEntity, VarietyAssignment, FinanceOption, ProductCategory, RelatedProducts, OrderBase, DeliveryAddress
from cubane.ishop.apps.merchant.orders.views import ProcessingOrderBackendSection, OrderBackendSection
from cubane.ishop.apps.merchant.customers.views import CustomerBackendSection
from cubane.ishop.apps.merchant.categories.views import CategoryBackendSection
from cubane.ishop.apps.merchant.products.views import ProductBackendSection
from cubane.ishop.apps.merchant.varieties.views import VarietyBackendSection
from cubane.ishop.apps.merchant.varieties.views import VarietyOptionBackendSection
from cubane.ishop.apps.merchant.delivery.views import DeliveryBackendSection
from cubane.ishop.apps.merchant.vouchers.views import VoucherBackendSection
from cubane.ishop.apps.merchant.inventory.views import InventoryBackendSection
from cubane.ishop.apps.shop.account.forms import BillingAddressForm, DeliveryAddressForm, ChangePasswordForm, ChangeDetailsForm
from cubane.ishop.apps.shop.forms import CustomerLoginForm, NewCustomerForm, SignupForm, PasswordForgottenForm, ProductOrderByForm
from cubane.ishop.basket import Basket
from cubane.ishop.templatetags.shop_tags import get_shop_price
from cubane.enquiry.views import validate_captcha
from cubane.lib.auth import login_user_without_password
from cubane.lib.module import get_class_from_string
from cubane.lib.parse import parse_int_list
from cubane.lib.paginator import create_paginator
from cubane.lib.fts import fts_query
from cubane.lib.range import get_ranges_for_min_max
from cubane.lib.libjson import to_json
from cubane.lib.app import get_models
from cubane.views import View, ModelView
from mailsnake import MailSnake, ListNotSubscribedException, EmailNotExistsException, ListAlreadySubscribedException
import math
import collections
import random
import datetime
import hashlib


SHOP_CLASS = None


def get_shop_content_backend_sections(backend_section):
    return [
        CategoryBackendSection(),
        ProductBackendSection(),
        InventoryBackendSection(),
        VarietyBackendSection(),
        VarietyOptionBackendSection(),
    ]


class ShopContentView(ModelView):
    """
    Edit CMS entity.
    """
    template_path = 'cubane/cms/pages/'


    def __init__(self, model, *args, **kwargs):
        self.model = model
        self.namespace = 'cubane.cms.%s' % \
            slugify(model._meta.verbose_name_plural)
        super(ShopContentView, self).__init__(*args, **kwargs)


    def _get_objects(self, request):
        return self.model.objects.all()


class ShopContentEntitySection(BackendSection):
    def __init__(self, model, group, *args, **kwargs):
        super(ShopContentEntitySection, self).__init__(*args, **kwargs)
        self.view = ShopContentView(model)
        self.title = model._meta.verbose_name_plural
        self.slug = slugify(self.title)
        self.group = group


class ShopSalesBackendSection(BackendSection):
    """
    Backend section for editing sales-related content, such as
    customer and orders.
    """
    title = 'Sales'
    priority = 5
    sections = [
        ProcessingOrderBackendSection(),
        OrderBackendSection(),
        CustomerBackendSection(),
    ]


class ShopBackendSection(BackendSection):
    """
    Backend section for editing shop content, such as categories and products.
    """
    title = 'Shop'
    sections = [
        DeliveryBackendSection(),
        VoucherBackendSection(),
    ]

    def __init__(self, *args, **kwargs):
        super(ShopBackendSection, self).__init__(*args, **kwargs)

        # finance options
        if settings.SHOP_LOAN_ENABLED:
            from cubane.ishop.apps.merchant.finance.views import FinanceOptionBackendSection
            self.sections.append(FinanceOptionBackendSection())

        # append all known shop entities
        entity_models = []
        for model in get_models():
            if issubclass(model, ShopEntity):
                entity_models.append(model)

        # sort by name
        entity_models = sorted(entity_models, key=lambda m: m.__name__)

        # create sections
        self.sections.extend([ShopContentEntitySection(model, model.get_backend_section_group()) for model in entity_models])


def get_shop():
    """
    Return the custom CMS implementation that is used to render CMS content.
    A site may implement its own CMS by deriving from the CMS base class.
    The custom class needs to be setup via settings.CMS, for example
    CMS = 'myproject.views.MyCMS'.
    """
    global SHOP_CLASS

    if not SHOP_CLASS:
        if hasattr(settings, 'SHOP') and settings.SHOP:
            SHOP_CLASS = get_class_from_string(settings.SHOP)
        else:
            raise ValueError(
                "cubane.cms requires the settings variable 'SHOP' " +
                "to be set to the full path of the shop class that represents " +
                "the cms system (derived from cubane.ishop.views.Shop), " +
                "for example myproject.views.MyProjectShop"
            )

    # creates a new instance every time...
    return SHOP_CLASS()


class Shop(View):
    """
    Shop base class. This may be overridden in order to hook custom things
    into the pipeline.
    """
    @property
    def settings(self):
        """
        Return the CMS/Shop settings object (cached).
        """
        return get_cms_settings()


    def get_category_model(self):
        """
        Return the model for a shop category.
        """
        return get_category_model()


    def get_product_model(self):
        """
        Return the model for a shop product.
        """
        return get_product_model()


    def get_customer_model(self):
        """
        Return the model for a shop customer.
        """
        return get_customer_model()


    def get_products(self):
        """
        Base queryset for returning products (listing).
        """
        products = self.get_product_model().objects.select_related('image', 'category').filter(draft=False)

        # select related categories
        if settings.SHOP_MULTIPLE_CATEGORIES:
            products = products.prefetch_related(
                Prefetch('categories', queryset=ProductCategory.objects.select_related('category').order_by('seq'))
            )

        # category must be enabled
        if settings.SHOP_MULTIPLE_CATEGORIES:
            # multiple categories -> at least one category must be enabled
            products = products.filter(categories__enabled=True).distinct()
        else:
            # single category -> category must be enabled
            products = products.filter(category__enabled=True)

        return products


    def get_related_products(self):
        """
        Return a queryset on which basis related products are fetched.
        """
        if settings.SHOP_MULTIPLE_CATEGORIES:
            return RelatedProducts.objects.select_related('to_product', 'to_product__image')
        else:
            return RelatedProducts.objects.select_related('to_product', 'to_product__image', 'to_product__category')


    def get_categories(self):
        """
        Base queryset for returning all categories.
        """
        return self.get_category_model().objects.filter(enabled=True)


    def search_products(self, q):
        """
        Search for products based on given query q.
        """
        products = self.get_products().filter(draft=False)

        if settings.SHOP_MULTIPLE_CATEGORIES:
            products = products.filter(
                categories__enabled=True
            ).exclude(
                categories=None
            ).distinct()
        else:
            products = products.filter(
                category_id__isnull=False,
                category__enabled=True
            )

        return fts_query(products, 'fts_index', q)


    def get_payment_config(self, identifier):
        """
        Return the payment configuration details.
        """
        if hasattr(settings, 'SHOP_PAYMENT_CONFIG'):
            for config in settings.SHOP_PAYMENT_CONFIG:
                if config['payment_gateway'] == identifier:
                    return config
        else:
            return {}


    def get_payment_gateway_by_identifier(self, identifier):
        """
        Return the payment gateway based on the given identifier.
        """
        # get payment config
        config = self.get_payment_config(identifier)

        # determine payment system or error
        if identifier == settings.GATEWAY_TEST:
            from cubane.payment.test_gateway import TestPaymentGateway
            return TestPaymentGateway(config, settings.GATEWAY_TEST)

        elif identifier == settings.GATEWAY_SAGEPAY:
            from cubane.payment.sagepay import SagepayPaymentGateway
            return SagepayPaymentGateway(config, settings.GATEWAY_SAGEPAY)

        elif identifier == settings.GATEWAY_PAYPAL:
            from cubane.payment.paypal import PaypalPaymentGateway
            return PaypalPaymentGateway(config, settings.GATEWAY_PAYPAL)

        elif identifier == settings.GATEWAY_OMNIPORT:
            from cubane.payment.omniport import OmniPortPaymentGateway
            return OmniPortPaymentGateway(config, settings.GATEWAY_OMNIPORT)

        elif identifier == settings.GATEWAY_STRIPE:
            from cubane.payment.stripe_gateway import StripePaymentGateway
            return StripePaymentGateway(config, settings.GATEWAY_STRIPE)

        elif identifier == settings.GATEWAY_DEKO:
            from cubane.payment.deko import DekoPaymentGateway
            return DekoPaymentGateway(config, settings.GATEWAY_DEKO)

        # TODO: Add payment gateways here
        raise ValueError(
            'Unknown or unsupported payment gateway %s.' % (
                identifier
            )
        )


    def get_default_payment_gateway(self):
        """
        Return the default payment gateway.
        """
        if settings.SHOP_TEST_MODE:
            return settings.GATEWAY_TEST
        else:
            return settings.SHOP_DEFAULT_PAYMENT_GATEWAY


    def get_payment_gateway_for_basket(self, basket):
        """
        Return the payment gateway identifier of the payment gateway that
        shall be used for a new order that is created from the given basket.
        """
        # pay by invoice does not have a payment gateway!
        if basket.is_invoice():
            return None

        if settings.SHOP_TEST_MODE:
            return settings.GATEWAY_TEST
        if basket.finance_option and settings.SHOP_LOAN_ENABLED:
            return settings.SHOP_LOAN_PAYMENT_GATEWAY
        else:
            return settings.SHOP_DEFAULT_PAYMENT_GATEWAY


    def get_products_for_category(self, category):
        """
        Return all products of the given category (including all products from any
        sub-category and sub-sub category etc).
        """
        if settings.SHOP_MULTIPLE_CATEGORIES:
            # multiple categories per product
            return self.get_products().filter(
                Q(categories=category) |
                Q(categories__parent=category) |
                Q(categories__parent__parent=category) |
                Q(categories__parent__parent__parent=category) |
                Q(categories__parent__parent__parent__parent=category),
                draft=False
            )
        else:
            # single category per product
            return self.get_products().filter(
                Q(category=category) |
                Q(category__parent=category) |
                Q(category__parent__parent=category) |
                Q(category__parent__parent__parent=category) |
                Q(category__parent__parent__parent__parent=category),
                draft=False
            )


    def categories_with_products(self, categories):
        """
        Filters out empty categories given a list of categories.
        """
        # valid products
        products = get_product_model().objects.filter(draft=False)

        # filter out categories without products
        if settings.SHOP_MULTIPLE_CATEGORIES:
            # multiple categories per product
            product_categories = ProductCategory.objects.filter(product__in=products)
            return categories.filter(
                Q(pk__in=product_categories) |
                Q(siblings__pk__in=products) |
                Q(siblings__siblings__pk__in=products) |
                Q(siblings__siblings__siblings__pk__in=products) |
                Q(siblings__siblings__siblings__siblings__pk__in=products)
            ).distinct()
        else:
            # single category per product
            return categories.filter(
                Q(products__in=products) |
                Q(siblings__products__in=products) |
                Q(siblings__siblings__products__in=products) |
                Q(siblings__siblings__siblings__products__in=products) |
                Q(siblings__siblings__siblings__siblings__products__in=products)
            ).distinct()


    def get_varieties_for_products(self, request, products, current_options, min_max_price):
        """
        Return all varieties that apply for the given set of products.
        """
        # price filter comes first
        price_filter_options = self.get_price_filter_options(products)
        prices = self.get_price_filter(min_max_price, price_filter_options)
        varieties = collections.OrderedDict([('price', prices['price'])])

        # append product varieties and attributes
        current = parse_int_list(current_options)
        varieties = VarietyAssignment.objects.get_variety_filters_for_products(products, current, varieties)
        return varieties


    def get_price_filter_options(self, products):
        """
        Return list of options for price filtering.
        """
        max_price = products.aggregate(Max('price')).get('price__max')
        min_price = products.aggregate(Min('price')).get('price__min')
        new_options = get_ranges_for_min_max((min_price, max_price), settings.SHOP_PRICE_FILTER_NUMBER_OF_DIVIDERS, settings.SHOP_PRICE_FILTER_DIVDERS)
        return new_options


    def get_price_filter(self, current_price_options, price_filter_options):
        """
        Return a price filter that is used for the filter panel.
        """
        price_filter = collections.OrderedDict()
        price_filter['price'] = {
            'id': 'price',
            'display_title': 'Price',
            'checked': 0,
            'options': [],
            'arg': 'min_max_price'
        }

        # get options for price filtering
        for i, option in enumerate(price_filter_options):
            title = '%s - %s' % (
                get_shop_price(option[0], decimal=False),
                get_shop_price(option[1], decimal=False)
            )
            price_filter['price']['options'].append({
                'id': 'min_max_price_%s' % i,
                'title': title,
                'value': '-'.join(map(str, option))
            })

        # split current_price_options to check values against
        current_price_options = current_price_options.split(',')

        # determine which variety group has at least one option checked
        for v in price_filter['price']['options']:
            if v['value'] in current_price_options:
                v['checked'] = 1
            else:
                v['checked'] = 0
        return price_filter


    def get_current_variety_filter_url(self, varieties):
        """
        Return current_variety_filter as url.
        """
        args = {}
        for _, v in varieties.items():
            for o in v.get('options'):
                if o.get('checked'):
                    arg = v.get('arg')
                    args.setdefault(arg, [])
                    args[arg].append(unicode(o.get('id')))
        return '&'.join(['%s=%s' % (arg, ','.join(options)) for arg, options in args.items()])


    def get_default_order_by(self, request, category=None):
        """
        Return the default order for a set of products, optionally for the
        given category.
        """
        default_order_by = None

        if category is not None:
            default_order_by = category.ordering_default

        if default_order_by is None:
            default_order_by = request.settings.ordering_default

        return default_order_by


    def order_product_listing_by_relavance(self, request, products):
        """
        Order given queryset of products based on relevance (seq).
        """
        if settings.SHOP_MULTIPLE_CATEGORIES:
            # multiple categories per product
            pks = [x.get('id') for x in products.order_by(
                'category_assignments__category__parent__parent__parent__parent__seq',
                'category_assignments__category__parent__parent__parent__seq',
                'category_assignments__category__parent__parent__seq',
                'category_assignments__category__parent__seq',
                'category_assignments__category__seq',
                'category_assignments__seq',
                'title'
            ).values('id')]

            preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pks)])
            products = products.order_by(preserved_order)
        else:
            # single category per product
            products = products.order_by(
                'category__parent__parent__parent__parent__seq',
                'category__parent__parent__parent__seq',
                'category__parent__parent__seq',
                'category__parent__seq',
                'category__seq',
                'seq',
                'title'
            )

        return products


    def order_product_listing(self, request, products, order_by):
        """
        Order given queryset of products based on the given order criterium.
        """
        if order_by == ProductBase.ORDER_BY_DATE_ADDED:
            products = products.order_by('-created_on')
        elif order_by == ProductBase.ORDER_BY_PRICE_HIGH_TO_LOW:
            products = products.order_by('-price')
        elif order_by == ProductBase.ORDER_BY_PRICE_LOW_TO_HIGH:
            products = products.order_by('price')
        elif order_by == ProductBase.ORDER_BY_RELEVANCE:
            products = self.order_product_listing_by_relavance(request, products)

        return products


    def product_listing(self, request, products, context={}, category=None, has_subcategories=False):
        """
        Return a template context for presenting a list of products including filter
        varieties.
        """
        # current page
        try:
            page_number = int(request.GET.get('page', '1'))
        except ValueError:
            page_number = 1

        # varieties and variety filter (optional)
        if settings.SHOP_VARIETY_FILTER_ENABLED:
            products, varieties, has_variety_filtered, variety_filter, active_varieties = \
                self.load_listing_varieties_and_filter(request, products)
        else:
            varieties = None
            has_variety_filtered = False
            variety_filter = None
            active_varieties = None

        # determine default order. If we are presenting a category with
        # sub-categories, we are looking at an aggregated result and order
        # by relevance would not work.
        default_order_by = self.get_default_order_by(request, category)

        # order by
        order_by = request.GET.get('o', default_order_by)

        if not order_by and not request.settings.ordering_default and request.settings.ordering_options:
            order_by = request.settings.ordering_options[0]

        # order products
        products = self.order_product_listing(request, products, order_by)

        # paginator
        products = create_paginator(
            request,
            products,
            page_size=request.settings.products_per_page,
            min_page_size=request.settings.products_per_page,
            max_page_size=request.settings.max_products_per_page
        )

        # order by form
        order_by_form = ProductOrderByForm(initial={
            'sort_by': order_by
        })
        order_by_form.configure(request, has_subcategories)

        # load varieties preview
        if settings.SHOP_LOAD_VARIETY_PREVIEW:
            has_variety_preview = self.load_variety_preview(products)
        else:
            has_variety_preview = False

        # update context
        context.update({
            'products': products,
            'varieties': varieties,
            'has_variety_preview': has_variety_preview,
            'has_variety_filtered': has_variety_filtered,
            'variety_filter': variety_filter,
            'active_varieties': active_varieties,
            'order_by_form': order_by_form,
            'order_by': order_by,
        })

        return context


    def load_variety_preview(self, products):
        """
        Load variety preview information for the given products.
        """
        if products.count() > 0:
            # load varieties for all products that are configured to be
            # previewed in listing...
            return VarietyAssignment.objects.inject_product_variety_preview(
                products.object_list
            )
        else:
            return False


    def load_listing_varieties_and_filter(self, request, products):
        """
        Load varieties and listing.
        """
        varieties = None
        has_variety_filtered = 'v' in request.GET
        current_options = request.GET.get('v', '')
        min_max_price = request.GET.get('min_max_price', '')
        varieties = self.get_varieties_for_products(request, products, current_options, min_max_price)
        products = self.get_filtered_products(varieties, products)
        variety_filter = self.get_current_variety_filter_url(varieties)
        active_varieties = self.get_active_varieties(varieties, self.get_current_variety_filter(varieties))

        return products, varieties, has_variety_filtered, variety_filter, active_varieties


    def get_filtered_products(self, varieties, products):
        """
        Return products based on the given set of products and varieties,
        where the list of products is filtered according to given variety
        filter options.
        """
        for vid, v in varieties.items():
            q = Q()
            min_max_price_parts = []
            for o in v.get('options'):
                if o.get('checked'):
                    if v.get('arg') == 'min_max_price':
                        for p in o.get('value').split('-'):
                            min_max_price_parts.append(int(p))
                    elif v.get('arg') == 'v':
                        q |= Q(varieties__id=o.get('value'))

            if len(min_max_price_parts) > 0:
                q &= Q(price__gte=min(min_max_price_parts))
                q &= Q(price__lte=max(min_max_price_parts))
            products = products.filter(q)
        return products


    def get_current_variety_filter(self, varieties):
        """
        Return the current variety filter based on the given set of varieties.
        """
        variety_filter = []
        for _, v in varieties.items():
            for o in v.get('options'):
                if o.get('checked'):
                    variety_filter.append(unicode(o.get('id')))
        return variety_filter


    def get_active_varieties(self, varieties, active_options):
        """
        Return active varieties based on the given set of varieties.
        """
        active_varieties = []
        for _, v in varieties.items():
            for o in v.get('options'):
                if o.get('checked'):
                    active_varieties.append({
                        'id': o.get('id'),
                        'group_title': v.get('display_title'),
                        'title': o.get('title'),
                    })

        return active_varieties


    def get_category_base(self, category_model):
        """
        Return the base queryset for fetching categories based on the given
        model.
        """
        return category_model.objects.select_related('parent')


    def get_category_by_pk(self, category_model, pk):
        """
        Return category with given pk or throw exception.
        """
        return self.get_category_base(category_model).get(enabled=True, pk=pk)


    def get_category_or_404(self, pk, slug):
        """
        Return the shop category matching given slug/pk or raise 404. If the
        slug does not match, return a redirect response to the correct url.
        """
        category_model = self.get_category_model()
        try:
            category = self.get_category_by_pk(category_model, pk)
            if category.slug != slug:
                return HttpResponsePermanentRedirect(reverse('shop.category', args=[category.slug, category.pk]))
        except category_model.DoesNotExist:
            raise Http404('Category matching id %s does not exist or category has been disabled.' % pk)

        return category


    def get_product_base(self, product_model):
        """
        Return the base queryset for loading a product.
        """
        return product_model.objects.all()


    def get_product_or_404(self, pk, slug):
        """
        Return the shop product matching given slug/pk or raise 404. If the
        slug does not match, return a redirect response to the correct url.
        """
        try:
            products = self.get_product_base(get_product_model()).filter(draft=False)

            if settings.SHOP_MULTIPLE_CATEGORIES:
                # multiple categories -> at least one category must be enabled
                products = products.filter(categories__enabled=True).prefetch_related(
                    Prefetch('categories', queryset=ProductCategory.objects.select_related('category').order_by('seq'))
                ).distinct()
            else:
                # single category -> category must be enabled
                products = products.filter(category__enabled=True)

            product = products.get(pk=pk)

            if product.slug != slug:
                return HttpResponsePermanentRedirect(reverse('shop.product', args=[product.slug, product.pk]))
        except get_product_model().DoesNotExist:
            raise Http404('Product matching id %s does not exist or product is a draft.' % pk)

        # if not connected to category
        if settings.SHOP_MULTIPLE_CATEGORIES:
            if product.categories.count() == 0:
                raise Http404('Product has not been assigned to any category.')
        else:
            if not product.category:
                raise Http404('Product has not been assigned to a category.')

        return product


    def on_basket_context(self, request, basket, template_context):
        """
        Allow for the basket context to be updated before rendering the basket.
        """
        return template_context


    def on_basket_added(self, request, basket, product, variety_options, quantity):
        """
        Called whenever a product has been added to the basket.
        """
        pass


    def on_customer_login(self, request, basket, user):
        """
        Called whenever a customer logged in (either as part of the checkout process
        or otherwise)...
        """
        pass


    def on_customer_logout(self, request, basket):
        """
        Called whenever a customer is logged out manually by clicking the
        logout button.
        """
        pass


    def category_page(self, request, category):
        """
        Category page.
        """
        # get products matching category (or any sub-category)
        products = self.get_products_for_category(category).distinct()
        subcategories = self.categories_with_products(
            category.get_children_queryset().select_related('image').filter(enabled=True)
        )

        if category.get_parent():
            sibling_categories_query = category.get_parent().get_children_queryset()
            sibling_categories = self.categories_with_products(sibling_categories_query)
        else:
            sibling_categories = False

        return self.product_listing(request, products, {
            'page': category,
            'category': category,
            'subcategories': subcategories,
            'sibling_categories': sibling_categories,
            'category_page': True
        }, category, subcategories.count() > 0)


    def product_page(self, request, product):
        """
        Product page.
        """
        finance_options = []
        if settings.SHOP_LOAN_ENABLED:
            # get all finance_options for this product
            rates = FinanceOption.objects.filter(enabled=True).order_by('seq')

            per_product_finance_option_ids = []
            for finance_option in product.finance_options.all():
                per_product_finance_option_ids.append(finance_option.pk)

            # exclude not assigned finances
            rates = list(rates)

            for rate in rates:
                if rate.per_product:
                    if rate.pk not in per_product_finance_option_ids:
                        continue
                finance_options.append(rate)

        return {
            'page': product,
            'product': product,
            'request_url': request.build_absolute_uri(),
            'product_page': True,
            'finance_options': finance_options
        }


    def search_page(self, request):
        """
        Search Page.
        """
        q = request.GET.get('q', '')
        q = q[:40]
        products = self.search_products(q)

        return self.product_listing(request, products, {
            'search': True,
            'q': q,
            'meta_title': 'Search Result for %s' % q
        })


    def get_variety_display_title(self, request, option_label, assignment):
        """
        Construct variety drop down display title.
        """
        price = assignment.price
        if price > 0:
            option_label = '%s (+%s)' % (
                option_label,
                get_shop_price(price)
            )

        return option_label


    def account_index(self, request):
        profile = get_customer_model().objects.get(user=request.user)
        orders = get_order_model().objects.get_processing_orders(user=request.user)[:3]
        try:
            address = request.user.delivery_addresses.all()[0]
        except IndexError:
            address = None

        return {
            'account_section': True,
            'profile': profile,
            'orders': orders,
            'address': address
        }


    def account_login(self, request):
        basket = Basket(request)
        checkout = request.GET.get('checkout', False) == '1'
        initial = {
            'checkout': checkout
        }

        login_form = CustomerLoginForm(request=request, prefix='customer', initial=initial)
        guest_form = NewCustomerForm(prefix='guest', initial=initial)
        guest_form.configure(request)
        form = None

        if request.method == 'POST':
            if request.POST.get('password_forgotten', None) != None:
                login_form = PasswordForgottenForm(request.POST, prefix='customer')
                form = login_form
            elif request.POST.get('customer', None) != None:
                login_form = CustomerLoginForm(request.POST, request=request, prefix='customer')
                form = login_form
            else:
                guest_form = NewCustomerForm(request.POST, prefix='guest')
                guest_form.configure(request)
                form = guest_form

        if form != None and form.is_valid():
            if isinstance(form, PasswordForgottenForm):
                email = form.cleaned_data.get('email')
                checkout = form.cleaned_data.get('checkout', '0')

                if request.context.password_forgotten(request, email):
                    messages.success(request, 'Your new password has been sent to \'%s\'.' % email)
                else:
                    messages.error(request, 'We were not able to recognise the email address \'%s\'. Please make sure that you entered your email address correctly.' % email)

                return HttpResponseRedirect(reverse('shop.account.login') + '?checkout=%s' % checkout)
            elif isinstance(form, CustomerLoginForm):
                user = form.get_user()
                checkout = form.cleaned_data.get('checkout', '0')

                if user.is_authenticated():
                    auth_login(request, user)

                    if checkout:
                        response = HttpResponseRedirect(reverse('shop.order.delivery'))
                    else:
                        response = HttpResponseRedirect(reverse('shop.account.index'))

                    response.set_cookie('cubaneShopLogin', '1')

                    # hook
                    shop = get_shop()
                    shop.on_customer_login(request, basket, user)

                    return response
            else:
                checkout = form.cleaned_data.get('checkout', '0')

                if request.user.is_authenticated():
                    auth_logout(request)

                    # hook
                    shop = get_shop()
                    shop.on_customer_logout(request, basket)
                    basket.save()

                request.session[settings.SIGNUP_EMAIL_SESSION_VAR] = form.cleaned_data['email']

                return HttpResponseRedirect(reverse('shop.account.signup') + '?checkout=%s' % checkout)

        request.session.set_test_cookie()

        return {
            'account_section': True,
            'login_form': login_form,
            'guest_form': guest_form,
        }


    def account_orders(self, request, status):
        order_model = get_order_model()

        if status == 'processing':
            orders = order_model.objects.get_processing_orders(user=request.user)
        else:
            orders = order_model.objects.get_complete_orders(user=request.user)

        return {
            'account_section': True,
            'orders': orders,
            'status': status,
        }


    def account_details(self, request):
        if request.method == 'POST':
            form = ChangeDetailsForm(request.POST)
        else:
            form = ChangeDetailsForm()

        form.configure(request)

        if form.is_valid():
            data = form.cleaned_data

            u = request.user
            p = get_customer_model().objects.get(user=u)

            if request.settings.mailchimp_enabled:
                # subscription details
                ms = MailSnake(request.settings.mailchimp_api)
                person_name = [data.get('first_name'), data.get('last_name')]
                merge_vars = {'FNAME': ' '.join(person_name)}

                # unsubscribe if email changed or we no longer want to be subscribed
                if 'email_address' in form.changed_data or ('newsletter' in form.changed_data and not data.get('newsletter')):
                    try:
                        ms.listUnsubscribe(id=request.settings.mailchimp_list_id, email_address=u.email)
                    except:
                        pass

                # subscribe if newsletter subscription changed or email was changed
                if ('email_address' in form.changed_data or 'newsletter' in form.changed_data) and data.get('newsletter'):
                    try:
                        ms.listSubscribe(id=request.settings.mailchimp_list_id, email_address=data.get('email_address'), merge_vars=merge_vars)
                    except:
                        pass

                # update newletter state in profile
                p.newsletter = data.get('newsletter')

            # update personal details on user record
            u.first_name = data.get('first_name')
            u.last_name = data.get('last_name')
            u.email = data.get('email_address')
            u.save()

            # update personal details on profile record
            p.title = data.get('title')
            p.first_name = data.get('first_name')
            p.last_name = data.get('last_name')
            p.telephone = data.get('phone')
            p.email = data.get('email_address')
            p.save()

            # success message and redirect to dashboard
            messages.success(request, 'Your details have been changed.')
            return HttpResponseRedirect(reverse('shop.account.index'))


        return {
            'account_section': True,
            'form': form
        }


    def account_billing(self, request):
        if request.method == 'POST':
            form = BillingAddressForm(request.POST)
        else:
            form = BillingAddressForm()

        form.configure(request)

        if form.is_valid():
            data = form.cleaned_data

            request.user.first_name = data.get('first_name')
            request.user.last_name = data.get('last_name')
            request.user.save()

            profile = get_customer_model().objects.get(user=request.user)
            profile.title       = data.get('title')
            profile.company     = data.get('company')
            profile.address1    = data.get('address1')
            profile.address2    = data.get('address2')
            profile.address3    = data.get('address3')
            profile.city        = data.get('city')
            profile.county      = data.get('county')
            profile.postcode    = data.get('postcode')
            profile.country     = data.get('country')

            profile.save()

            messages.success(request, 'Your delivery address has been changed.')
            return HttpResponseRedirect(reverse('shop.account.index'))

        return {
            'account_section': True,
            'form': form
        }


    def account_delivery(self, request):
        addresses = request.user.delivery_addresses.all()
        return {
            'account_section': True,
            'addresses': addresses
        }


    def account_delivery_address(self, request, pk=None):
        if pk:
            address = get_object_or_404(DeliveryAddress, pk=pk, user=request.user)
            initial = {
                'name': address.name,
                'company': address.company,
                'address1': address.address1,
                'address2': address.address2,
                'address3': address.address3,
                'city': address.city,
                'county': address.county,
                'postcode': address.postcode,
                'country': address.country
            }
        else:
            address = DeliveryAddress()
            initial = {}

        if request.method == 'POST':
            form = DeliveryAddressForm(request.POST)
        else:
            form = DeliveryAddressForm(initial=initial)

        form.configure(request)

        if form.is_valid():
            d = form.cleaned_data

            address.user = request.user
            address.name        = d.get('name')
            address.title       = d.get('title')
            address.company     = d.get('company')
            address.address1    = d.get('address1')
            address.address2    = d.get('address2')
            address.address3    = d.get('address3')
            address.city        = d.get('city')
            address.county      = d.get('county')
            address.postcode    = d.get('postcode')
            address.country     = d.get('country')
            address.save()

            if pk:
                messages.success(request, 'Your delivery address has been changed.')
            else:
                messages.success(request, 'A new delivery address has been created.')

            return HttpResponseRedirect(reverse('shop.account.delivery'))

        return {
            'account_section': True,
            'form': form,
            'address': address,
            'edit': pk != None
        }


    def account_delete_delivery_address(self, request, pk):
        address = get_object_or_404(DeliveryAddress, pk=pk, user=request.user)
        title = unicode(address)
        address.delete()

        messages.success(request, "Your delivery address '%s' has been deleted." % title)

        return HttpResponseRedirect(reverse('shop.account.delivery'))


    def account_password(self, request):
        if request.method == 'POST':
            form = ChangePasswordForm(request.POST)
        else:
            form = ChangePasswordForm()

        form.configure(request)

        if form.is_valid():
            request.user.set_password(form.cleaned_data.get('password'))
            request.user.save()
            update_session_auth_hash(request, request.user)

            messages.success(request, 'Your password has been changed.')
            return HttpResponseRedirect(reverse('shop.account.index'))

        return {
            'account_section': True,
            'form': form
        }


    def account_logout(self, request):
        basket = Basket(request)
        auth_logout(request)

        # hook
        shop = get_shop()
        shop.on_customer_logout(request, basket)

        basket.save()

        response = HttpResponseRedirect(reverse('shop.account.index'))
        response.set_cookie('cubaneShopLogin', '0')
        return response


    def get_account_signup_form(self):
        return SignupForm


    def account_signup(self, request):
        email = request.session.get(settings.SIGNUP_EMAIL_SESSION_VAR, None)
        if email == '':
            raise Http404('Missing email address.')

        checkout = request.GET.get('checkout', False) == '1'
        form_class = self.get_account_signup_form()
        if request.method == 'POST':
            form = form_class(request.POST, initial={'checkout': checkout})
        else:
            form = form_class(initial={
                'email': email,
                'checkout': checkout
            })

        form.configure(request)

        if request.method == 'POST':
            captcha = validate_captcha(request)
            if not captcha:
                messages.add_message(request, messages.ERROR,
                    'Please tick the checkbox at the bottom of the form to prevent SPAM.'
                )

            if form.is_valid() and captcha:
                d = form.cleaned_data

                # create user account
                md5 = hashlib.md5()
                md5.update(d['email'])
                user = User.objects.create(
                    username = md5.hexdigest()[:30],
                    first_name = d['first_name'],
                    last_name = d['last_name'],
                    email = d['email']
                )

                # replace username with user id, set password and add user to list of customers
                user.username = unicode(user.id)
                user.set_password(d['password'])

                user.save()

                # create customer
                newsletter = 0
                if request.settings.mailchimp_enabled:
                    if d['newsletter']:
                        person_name = (d['first_name'],d['last_name'])
                        merge_vars = {'FNAME': " ".join(person_name)}
                        ms = MailSnake(request.settings.mailchimp_api)
                        try:
                            ms.listSubscribe(id=request.settings.mailchimp_list_id, email_address=d['email'], merge_vars=merge_vars)
                        except:
                            pass
                        newsletter = d['newsletter']
                customer = get_customer_model().objects.create(
                    user=user,
                    first_name = d['first_name'],
                    last_name = d['last_name'],
                    email=d['email'],
                    title=d['title'],
                    address1='',
                    city='',
                    county='',
                    postcode='',
                    country=d['country'],
                    telephone='',
                    newsletter=newsletter
                )

                # log customer in
                login_user_without_password(request, user)

                # go to dashboard or deliver page
                messages.success(request, 'Thank you for signing up with us.')
                if d['checkout']:
                    response = HttpResponseRedirect(reverse('shop.order.delivery'))
                else:
                    response = HttpResponseRedirect(reverse('shop.account.index'))

                response.set_cookie('cubaneShopLogin', '1')
                return response

        return {
            'account_section': True,
            'is_signup_page': True,
            'form': form
        }


class ShopCategoriesSitemap(CMSGenericSitemap):
    """
    Shop category pages sitemap.
    """
    def items(self):
        return get_category_model().objects.exclude(enabled=False)


class ShopProductsSitemap(CMSGenericSitemap):
    """
    Shop product pages sitemap.
    """
    def items(self):
        return get_product_model().objects.exclude(category__enabled=False).exclude(draft=True).exclude(category_id__isnull=True)


class CMSExtensions(object):
    """
    Extends the CMS class with shop-specific operations and extending other
    aspects, such as sitemaps.
    """
    def get_sitemaps(self):
        """
        Add shop-specific content to sitemap.
        """
        _sitemaps = super(CMSExtensions, self).get_sitemaps()

        # shop categories and products
        _sitemaps[slugify(get_category_model()._meta.verbose_name)] = ShopCategoriesSitemap(self)
        _sitemaps[slugify(get_product_model()._meta.verbose_name)] = ShopProductsSitemap(self)

        return _sitemaps


    def on_generate_cache(self, generator, verbose=False):
        """
        Override: Add shop content to cache system.
        """
        super(CMSExtensions, self).on_generate_cache(generator, verbose)

        shop = get_shop()

        for category in shop.get_categories():
            if generator.quit: break
            generator.process_page_by_url('shop.category', args=[category.slug, category.pk], verbose=verbose)

        for product in shop.get_products():
            if generator.quit: break
            generator.process_page_by_url('shop.product', args=[product.slug, product.pk], verbose=verbose)


    def on_object_links(self, links):
        """
        Override: Support for link-able categories and products.
        """
        shop = get_shop()
        links.add(get_category_model(), shop.get_categories())
        links.add(get_product_model(), shop.get_products())
