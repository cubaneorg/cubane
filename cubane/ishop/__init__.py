# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.app import require_app, get_app_label_ref
from cubane.lib.module import get_class_from_string
require_app(__name__, 'cubane.cms')


RESOURCES = [
    # css
    'css/default.css',
    'css/barcode.css',
    'css/varieties.css',
    'css/basket.css',
    'css/sku_editor.css',
    'css/basket_editor.css',
    'css/order.css',

    # js
    '/cubane/js/cubane.js',
    '/cubane/js/cubane.urls.js',
    '/cubane/js/cubane.dialog.js',
    'js/default.js',
    'js/varieties.js',
    'js/sku_editor.js',
    'js/basket.js',
    'js/basket_editor.js',
    'js/order.js',
    '/cubane/ishop/frontend/js/basket.js',
    '/cubane/ishop/frontend/js/product.js'
]


RESOURCE_TARGETS = {
    'backend': [
        'cubane.ishop',
        'cubane.usstates'
    ]
}


def install_backend(backend):
    from cubane.ishop.views import ShopSalesBackendSection
    from cubane.ishop.views import ShopBackendSection
    from cubane.ishop.featured.views import FeaturedItemBackendSection
    backend.register_section(ShopSalesBackendSection())
    backend.register_section(ShopBackendSection())
    backend.register_section(FeaturedItemBackendSection())


def install_backend_content(content_section):
    # install additional elements to the CMS content tab
    from cubane.ishop.views import get_shop_content_backend_sections
    for section in get_shop_content_backend_sections(content_section):
        content_section.sections.append(section)


def install_cms(cms):
    """
    Extend CMS class with additional capabilities.
    """
    from cubane.ishop.views import CMSExtensions
    return cms.register_extension(CMSExtensions)


def install_nav(nav):
    """
    Extends navigation
    """
    from cubane.ishop.nav import ShopNavigationExtensions
    return nav.register_extension(ShopNavigationExtensions)


def install_page_context(page_context):
    """
    Installs a page context extension, which is used for rending CMS content.
    """
    from cubane.ishop.cms import ShopPageContextExtensions
    return page_context.register_extension(ShopPageContextExtensions)


def get_category_model():
    """
    Return the shop category model as configured by
    settings.SHOP_CATEGORY_MODEL.
    """
    if hasattr(settings, 'SHOP_CATEGORY_MODEL'):
        return get_class_from_string(settings.SHOP_CATEGORY_MODEL)
    else:
        raise ValueError('Category model is not defined. Define settings.SHOP_CATEGORY_MODEL.')


def get_category_model_name():
    """
    Return the name of the shop category model as configured by
    settings.SHOP_CATEGORY_MODEL.
    """
    if hasattr(settings, 'SHOP_CATEGORY_MODEL'):
        return get_app_label_ref(settings.SHOP_CATEGORY_MODEL)
    else:
        raise ValueError('Category model is not defined. Define settings.SHOP_CATEGORY_MODEL.')


def get_product_model():
    """
    Return the shop product model as configured by
    settings.SHOP_PRODUCT_MODEL.
    """
    if hasattr(settings, 'SHOP_PRODUCT_MODEL'):
        return get_class_from_string(settings.SHOP_PRODUCT_MODEL)
    else:
        raise ValueError('Product model is not defined. Define settings.SHOP_PRODUCT_MODEL.')


def get_product_model_name():
    """
    Return the name of the shop product model as configured by
    settings.SHOP_PRODUCT_MODEL.
    """
    if hasattr(settings, 'SHOP_PRODUCT_MODEL'):
        return get_app_label_ref(settings.SHOP_PRODUCT_MODEL)
    else:
        raise ValueError('Product model is not defined. Define settings.SHOP_PRODUCT_MODEL.')


def get_order_model():
    """
    Return the shop order model as configured by
    settings.SHOP_ORDER_MODEL.
    """
    if hasattr(settings, 'SHOP_ORDER_MODEL'):
        return get_class_from_string(settings.SHOP_ORDER_MODEL)
    else:
        raise ValueError('Order model is not defined. Define settings.SHOP_ORDER_MODEL.')


def get_order_model_name():
    """
    Return the name of the shop order model as configured by
    settings.SHOP_ORDER_MODEL.
    """
    if hasattr(settings, 'SHOP_ORDER_MODEL'):
        return get_app_label_ref(settings.SHOP_ORDER_MODEL)
    else:
        raise ValueError('Order model is not defined. Define settings.SHOP_ORDER_MODEL.')


def get_customer_model():
    """
    Return the shop customer model as configured by
    settings.SHOP_CUSTOMER_MODEL.
    """
    if hasattr(settings, 'SHOP_CUSTOMER_MODEL'):
        return get_class_from_string(settings.SHOP_CUSTOMER_MODEL)
    else:
        raise ValueError('Customer model is not defined. Define settings.SHOP_CUSTOMER_MODEL.')


def get_customer_model_name():
    """
    Return the name of the shop customer model as configured by
    settings.SHOP_CUSTOMER_MODEL.
    """
    if hasattr(settings, 'SHOP_CUSTOMER_MODEL'):
        return get_app_label_ref(settings.SHOP_CUSTOMER_MODEL)
    else:
        raise ValueError('Customer model is not defined. Define settings.SHOP_CUSTOMER_MODEL.')
