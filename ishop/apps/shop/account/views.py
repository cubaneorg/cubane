# coding=UTF-8
from __future__ import unicode_literals
from cubane.ishop.decorators import shop_login_required
from cubane.decorators import template
from cubane.cms.decorators import cubane_cms_context
from cubane.ishop.views import get_shop


@shop_login_required()
@template('cubane/ishop/pages/account/dashboard.html')
@cubane_cms_context()
def index(request):
    """
    Index Page.
    """
    shop = get_shop()
    return shop.account_index(request)


@template('cubane/ishop/pages/account/login.html')
@cubane_cms_context()
def login(request):
    """
    Login Page.
    """
    shop = get_shop()
    return shop.account_login(request)


@shop_login_required()
@template('cubane/ishop/pages/account/orders.html')
@cubane_cms_context()
def orders(request, status):
    """
    Order Page.
    """
    shop = get_shop()
    return shop.account_orders(request, status)


@shop_login_required()
@template('cubane/ishop/pages/account/details.html')
@cubane_cms_context()
def details(request):
    """
    Details Page.
    """
    shop = get_shop()
    return shop.account_details(request)


@shop_login_required()
@template('cubane/ishop/pages/account/billing.html')
@cubane_cms_context()
def billing(request):
    """
    Billing Page.
    """
    shop = get_shop()
    return shop.account_billing(request)


@shop_login_required()
@template('cubane/ishop/pages/account/delivery.html')
@cubane_cms_context()
def delivery(request):
    """
    Delivery Page.
    """
    shop = get_shop()
    return shop.account_delivery(request)


@shop_login_required()
@template('cubane/ishop/pages/account/delivery_address.html')
@cubane_cms_context()
def delivery_address(request, pk=None):
    """
    Delivery Address Page.
    """
    shop = get_shop()
    return shop.account_delivery_address(request, pk)


@shop_login_required()
def delete_delivery_address(request, pk):
    """
    Delete Delivery Address.
    """
    shop = get_shop()
    return shop.account_delete_delivery_address(request, pk)


@shop_login_required()
@template('cubane/ishop/pages/account/password.html')
@cubane_cms_context()
def password(request):
    """
    Password Page.
    """
    shop = get_shop()
    return shop.account_password(request)


def logout(request):
    """
    Logout.
    """
    shop = get_shop()
    return shop.account_logout(request)


@template('cubane/ishop/pages/account/signup.html')
@cubane_cms_context()
def signup(request):
    """
    Signup Page.
    """
    shop = get_shop()
    return shop.account_signup(request)
