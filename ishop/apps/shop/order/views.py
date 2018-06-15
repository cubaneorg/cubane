# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from cubane.payment.base import RegistrationContext, PaymentGateway
from cubane.payment.test_gateway import TestPaymentGateway
from cubane.decorators import template, deny_bot
from cubane.cms.decorators import cubane_cms_context
from cubane.lib.libjson import to_json, to_json_response
from cubane.lib.url import get_absolute_url
from cubane.lib.auth import login_user_without_password
from cubane.ishop import get_customer_model, get_order_model
from cubane.ishop.decorators import shop_checkout_login_required
from cubane.ishop.apps.shop.forms import CustomerLoginForm, GuestLoginForm, PasswordForgottenForm
from cubane.ishop.apps.shop.order.forms import DeliveryAddressFrom, DeliveryOptionsFrom
from cubane.ishop.views import get_shop
from cubane.ishop.mail import *
from cubane.ishop.models import OrderBase, DeliveryOption, DeliveryAddress
from cubane.ishop.models import ShopSettings
from cubane.ishop.basket import Basket
import re
import hashlib
import decimal
import datetime
from subprocess import call
import os
from mailsnake import MailSnake, ListAlreadySubscribedException


class CurrentPage(object):
    def __init__(self, current_page, order=None):
        self.current_page = current_page
        self.order = order


    @classmethod
    def DELIVERY_ADDRESS(cls):
        return CurrentPage('shop.order.delivery')


    @classmethod
    def DELIVERY_OPTIONS(cls):
        return CurrentPage('shop.order.delivery_options')


    @classmethod
    def COMPLETE(cls):
        return CurrentPage('shop.order.complete')


    @classmethod
    def ORDER_STATUS(cls, order):
        return CurrentPage('shop.order.status', order=order)


    def is_delivery_address(self):
        return self.current_page == 'shop.order.delivery'


    def is_delivery_options(self):
        return self.current_page == 'shop.order.delivery_options'


    def is_complete(self):
        return self.current_page == 'shop.order.complete'


    def is_order_status(self):
        return self.current_page == 'shop.order.status'


    def get_url(self):
        if self.is_delivery_address() or self.is_complete():
            return reverse(self.current_page)
        elif self.is_delivery_options():
            return reverse(self.current_page)
        elif self.is_order_status():
            return reverse(self.current_page, args=[self.order.secret_id])
        else:
            return u''


def get_next_checkout_step(request, basket, current_page):
    """
    Determine the next checkout step depending on the configuration
    and on the current status of the basket, until we have all required
    information in which case we redirect to the order creation step which
    then finally redirects to the order status page.
    """
    # empty basket -> we cannot checkout
    if basket.is_empty():
        return '/'

    # no billing address -> provide billing address
    if not basket.has_billing_address():
        return reverse('shop.order.delivery')

    # no delivery address -> provide delivery address
    if not basket.has_delivery_address() and not basket.is_click_and_collect():
        return reverse('shop.order.delivery')

    # next page after checkout is delivery options, unless we are intructed
    # to skip this step, perhabs this is an invoice order...
    if current_page.is_delivery_address() and not basket.is_default_delivery():
        return reverse('shop.order.delivery_options')

    # if everything is ok, we can create the order as the final step
    return None


def next_checkout_step(request, basket, current_page):
    """
    Return a redirect response redirecting to the next checkout step.
    """
    next = get_next_checkout_step(request, basket, current_page)

    # completed
    if not next:
        next = reverse('shop.order.complete')

    return HttpResponseRedirect(next)


@template('cubane/ishop/pages/order/login.html')
@cubane_cms_context()
def login(request):
    """
    Provide ability to choose to login with an existing account, create a new
    account or just providing an email address for a guest checkout.
    """
    basket = Basket(request)
    if basket.is_empty():
        return HttpResponseRedirect('/')

    login_form = CustomerLoginForm(request=request, prefix='customer')
    guest_form = GuestLoginForm(prefix='guest')
    form = None

    if request.method == 'POST':
        if request.POST.get('password_forgotten', None) != None:
            login_form = PasswordForgottenForm(request.POST, prefix='customer')
            form = login_form
        elif request.POST.get('customer', None) != None:
            login_form = CustomerLoginForm(request.POST, request=request, prefix='customer')
            form = login_form
        else:
            guest_form = GuestLoginForm(request.POST, prefix='guest')
            form = guest_form

    if form != None and form.is_valid():
        if isinstance(form, PasswordForgottenForm):
            email = form.cleaned_data.get('email')
            if request.context.password_forgotten(request, email):
                messages.success(request, 'Your new password has been send to: %s.' % email)
            else:
                messages.error(request, 'We were not able to send an email to: %s' % email)
            return HttpResponseRedirect(reverse('shop.order.login'))
        elif isinstance(form, CustomerLoginForm):
            user = form.get_user()
            if user.is_authenticated():
                auth_login(request, user)
                request.session[settings.GUEST_USER_SESSION_VAR] = ''
                response = HttpResponseRedirect(reverse('shop.order.delivery'))
                response.set_cookie('cubaneShopLogin', '1')

                # hook
                shop = get_shop()
                shop.on_customer_login(request, basket, user)

                return response
        else:
            if request.user.is_authenticated():
                auth_logout(request)

                # hook
                shop = get_shop()
                shop.on_customer_logout(request, basket)
                basket.save()

            request.session[settings.GUEST_USER_SESSION_VAR] = form.cleaned_data.get('email')
            return HttpResponseRedirect(reverse('shop.order.delivery'))

    return {
        'login_form': login_form,
        'guest_form': guest_form,
        'basket': basket
    }


@shop_checkout_login_required()
@template('cubane/ishop/pages/order/delivery.html')
@cubane_cms_context()
def delivery(request):
    """
    (1) Start to checkout by confirming the delivery address.
    The customer is required to login for checkout first (see login).
    """
    basket = Basket(request)
    if basket.is_empty():
        return HttpResponseRedirect('/')

    # if the basket contains collection only products,
    # force click and collect
    if basket.is_collection_only():
        basket.set_click_and_collect(True)

    if request.method == 'POST':
        form = DeliveryAddressFrom(request.POST)
    else:
        billing = basket.billing_address if basket.billing_address else {}
        delivery = basket.delivery_address if basket.delivery_address else {}

        profile = None
        default = {}
        user = request.user
        if not user.is_anonymous():
            try:
                profile = get_customer_model().objects.get(user=user)
                default = {
                    'title': profile.title,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'telephone': profile.telephone
                }

                if basket.has_billing_address():
                    default.update({
                        'company': profile.company,
                        'address1': profile.address1,
                        'address2': profile.address2,
                        'address3': profile.address3,
                        'city': profile.city,
                        'country': profile.country,
                        'county': profile.county,
                        'postcode': profile.postcode
                    })
            except get_customer_model().DoesNotExist:
                pass
        else:
            default = {
                'email': request.session.get(settings.GUEST_USER_SESSION_VAR),
                'country': 'GB'
            }

        def _get(name, data, fallback=None):
            v = data.get(name)
            if v is None and fallback is not None:
                v = fallback.get(name)
            return v

        form = DeliveryAddressFrom(initial={
            'title': _get('title', billing, default),
            'first_name': _get('first_name', billing, default),
            'last_name': _get('last_name', billing, default),
            'email': _get('email', billing, default),
            'telephone': _get('telephone', billing, default),

            'company': _get('company', billing, default),
            'address1': _get('address1', billing, default),
            'address2': _get('address2', billing, default),
            'address3': _get('address3', billing, default),
            'city': _get('city', billing, default),
            'country': _get('country', billing, default),
            'county': _get('county', billing, default),
            'postcode': _get('postcode', billing, default),

            'deliver_to': DeliveryAddressFrom.DELIVERY_COLLECTION if basket.is_click_and_collect() else DeliveryAddressFrom.DELIVERY_BILLING_ADDRESS,
            'free_name': _get('free_name', delivery),
            'delivery_name': _get('name', delivery),
            'delivery_company': _get('company', delivery),
            'delivery_address1': _get('address1', delivery),
            'delivery_address2': _get('address2', delivery),
            'delivery_address3': _get('address3', delivery),
            'delivery_city': _get('city', delivery),
            'delivery_country': _get('country', delivery, default),
            'delivery_county': _get('county', delivery),
            'delivery_postcode': _get('postcode', delivery),

            'finance_option': basket.finance_option,
            'loan_deposit': basket.loan_deposit,
            'newsletter': basket.newsletter,
            'terms': basket.terms,
            'special_req': basket.special_req,
            'survey': basket.survey,
            'signup': basket.signup != None,
            'password': basket.signup.get('password') if basket.signup else None,
            'password_confirm': basket.signup.get('password') if basket.signup else None,
            'update_profile': basket.update_profile
        })

    form.configure(request, basket)
    current_page = CurrentPage.DELIVERY_ADDRESS()

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data

        if 'email' in d:
            email = d.get('email')
        else:
            email = request.user.email

        # keep initial address information if we are not allowed to change the
        # billing address
        if not basket.can_edit_billing_address:
            for field in ['company', 'address1', 'address2', 'address3', 'city', 'country', 'county', 'postcode']:
                d[field] = basket.billing_address.get(field)

        # save billing address
        basket.set_billing_address(
            title=d.get('title'),
            first_name=d.get('first_name'),
            last_name=d.get('last_name'),
            email=email,
            telephone=d.get('telephone'),
            company=d.get('company'),
            address1=d.get('address1'),
            address2=d.get('address2'),
            address3=d.get('address3'),
            city=d.get('city'),
            country=d.get('country'),
            county=d.get('county'),
            postcode=d.get('postcode')
        )

        # get delivery method
        deliver_to = d.get('deliver_to', DeliveryAddressFrom.DELIVERY_BILLING_ADDRESS)

        basket.set_click_and_collect(deliver_to == DeliveryAddressFrom.DELIVERY_COLLECTION or basket.is_collection_only())
        basket.set_free_delivery_to(False)

        if deliver_to == DeliveryAddressFrom.FREE_DELIVERY_TO:
            location = basket.get_normalized_free_delivery_to_address()

            basket.set_delivery_address(
                name=d.get('delivery_free_name'),
                company=location.get('title'),
                address1=location.get('address1'),
                address2=location.get('address2'),
                address3=location.get('address3'),
                city=location.get('city'),
                country=location.get('country'),
                county=location.get('county'),
                postcode=location.get('postcode')
            )
            basket.set_free_delivery_to(True)
        elif deliver_to == DeliveryAddressFrom.DELIVERY_BILLING_ADDRESS:
            # deliver to my billing address
            basket.set_delivery_address(
                name='%s %s' % (d.get('first_name'), d.get('last_name')),
                company=d.get('company'),
                address1=d.get('address1'),
                address2=d.get('address2'),
                address3=d.get('address3'),
                city=d.get('city'),
                country=d.get('country'),
                county=d.get('county'),
                postcode=d.get('postcode')
            )
        elif deliver_to == DeliveryAddressFrom.DELIVERY_NEW_ADDRESS:
            # enter new delivery address
            basket.set_delivery_address(
                name=d.get('delivery_name'),
                company=d.get('delivery_company'),
                address1=d.get('delivery_address1'),
                address2=d.get('delivery_address2'),
                address3=d.get('delivery_address3'),
                city=d.get('delivery_city'),
                country=d.get('delivery_country'),
                county=d.get('delivery_county'),
                postcode=d.get('delivery_postcode')
            )

            # create a new record for the customer's profile
            if not request.user.is_anonymous():
                n = DeliveryAddress.objects.filter(
                    user=request.user,
                    address1=d.get('delivery_address1'),
                    address2=d.get('delivery_address2'),
                    address3=d.get('delivery_address3'),
                    city=d.get('delivery_city'),
                    country=d.get('delivery_country'),
                    county=d.get('delivery_county'),
                    postcode=d.get('delivery_postcode')
                ).count()

                if n == 0:
                    address = DeliveryAddress()
                    address.user = request.user
                    address.name=d.get('delivery_name')
                    address.company = d.get('delivery_company')
                    address.address1=d.get('delivery_address1')
                    address.address2=d.get('delivery_address2')
                    address.address3=d.get('delivery_address3')
                    address.city=d.get('delivery_city')
                    address.country=d.get('delivery_country')
                    address.county=d.get('delivery_county')
                    address.postcode=d.get('delivery_postcode')
                    address.save()
        else:
            if not basket.is_click_and_collect():
                # delivery to one of my delivery addresses taken from my profile
                delivery_address = DeliveryAddress.objects.get(
                    user=request.user,
                    pk=deliver_to
                )
                basket.set_delivery_address(
                    name=delivery_address.name,
                    company=delivery_address.company,
                    address1=delivery_address.address1,
                    address2=delivery_address.address2,
                    address3=delivery_address.address3,
                    city=delivery_address.city,
                    country=delivery_address.country,
                    county=delivery_address.county,
                    postcode=delivery_address.postcode
                )

        is_loan_available = settings.SHOP_LOAN_ENABLED and 'finance_option' in d and 'loan_deposit' in d

        if is_loan_available and deliver_to == DeliveryAddressFrom.DELIVERY_NEW_ADDRESS:
            # deliver to my billing address as it is required by law if finance option is chosen
            if d.get('finance_option'):
                basket.set_delivery_address(
                    name='%s %s' % (d.get('first_name'), d.get('last_name')),
                    company=d.get('company'),
                    address1=d.get('address1'),
                    address2=d.get('address2'),
                    address3=d.get('address3'),
                    city=d.get('city'),
                    country=d.get('country'),
                    county=d.get('county'),
                    postcode=d.get('postcode')
                )

        # loan application
        if is_loan_available:
            basket.set_finance_option(d.get('finance_option'))
            basket.set_loan_deposit(d.get('loan_deposit'))
        else:
            basket.set_finance_option(None)
            basket.set_loan_deposit(None)

        # newsletter
        if request.settings.mailchimp_enabled and 'newsletter' in d and d.get('newsletter'):
            basket.newsletter = True

        # terms and conditions
        if request.settings.has_terms and 'terms' in d and d.get('terms'):
            basket.terms = True

        # special requiremenets
        basket.special_req = d.get('special_req')

        # survey
        basket.survey = d.get('survey') if 'survey' in d else None

        # signup?
        if d.get('signup', False) == True:
            basket.set_signup(
                email=d.get('email'),
                first_name=d.get('first_name'),
                last_name=d.get('last_name'),
                password=d.get('password')
            )
        else:
            basket.clear_signup()

        # default delivery address?
        if 'update_profile' in d and d.get('update_profile'):
            basket.update_profile = True

        # next...
        next = next_checkout_step(request, basket, current_page)
        basket.save()
        return next

    # generate list of available delivery addresses from customer's profile
    if request.user.is_anonymous():
        delivery_addresses = []
    else:
        delivery_addresses = [{
            'id': i,
            'iso': addr.country.iso
        } for i, addr in enumerate(request.user.delivery_addresses.all(), start=3)]

    return {
        'basket': basket,
        'form': form,
        'delivery_addresses': to_json(delivery_addresses)
    }


@shop_checkout_login_required()
@template('cubane/ishop/pages/order/delivery_options.html')
@cubane_cms_context()
def delivery_options(request):
    """
    (2) Provide details on delivery options.
    """
    basket = Basket(request)
    if basket.is_empty():
        return HttpResponseRedirect('/')

    # construct delivery options form for entire basket
    items = basket.items
    choices = basket.get_delivery_choices()

    # construct form
    if request.method == 'POST':
        form = DeliveryOptionsFrom(request.POST)
        try:
            option = basket.get_delivery_options()[0]
        except IndexError:
            option = None
    else:
        option = basket.get_delivery_option_or_default()
        form = DeliveryOptionsFrom()

    # configure form with specific delivery options
    form.configure(request, choices, option)
    current_page = CurrentPage.DELIVERY_OPTIONS()

    # if the current open is not within the given set of choices,
    # then change the delivery option to the first one.
    if option:
        if option.id not in [_id for _id, _ in choices]:
            option = basket.get_default_delivery_option()
            basket.set_delivery_option(option)
            basket.save()
            basket = Basket(request)

    # form validation
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data

        # get delivery option
        option = DeliveryOption.objects.get(pk=d.get('delivery_option'))

        # configure delivery option
        basket.set_delivery_option(option)

        # next...
        next = next_checkout_step(request, basket, current_page)
        basket.save()
        return next
    else:
        if basket.is_click_and_collect() and request.method == 'POST':
            next = next_checkout_step(request, basket, current_page)
            basket.save()
            return next

    delivery_option = basket.get_delivery_details(option) if option != None else None

    return {
        'basket': basket,
        'items': items,
        'form': form,
        'is_click_and_collect': basket.is_click_and_collect(),
        'delivery_option': delivery_option,
        'choices': choices
    }


@shop_checkout_login_required()
def complete(request):
    """
    (3) Final checkout step, where the order is actually created from the basket.
    """
    basket = Basket(request)

    # redirect back to a previous step if we missed anything...
    next = get_next_checkout_step(request, basket, CurrentPage.COMPLETE())
    if next:
        return HttpResponseRedirect(next)

    # state or county
    if 'state' in basket.billing_address:
        county = basket.billing_address.get('state')
    else:
        county = basket.billing_address.get('county')

    # create account if requested
    if basket.signup:
        # create user account
        md5 = hashlib.md5()
        md5.update(basket.signup.get('email'))
        email = basket.signup.get('email')

        if User.objects.filter(email=email).count() > 0:
            messages.warning(request, 'There is already an account with this email: %s.' % email)
            return HttpResponseRedirect(reverse('shop.account.login'))
        user = User.objects.create(
            username = md5.hexdigest()[:30],
            first_name = basket.signup.get('first_name'),
            last_name = basket.signup.get('last_name'),
            email = email
        )

        # replace username with user id and set password
        user.username = unicode(user.id)
        user.set_password(basket.signup.get('password'))
        user.save()

        # create profile
        get_customer_model().objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            title=basket.billing_address.get('title'),
            address1=basket.billing_address.get('address1'),
            address2=basket.billing_address.get('address2'),
            address3=basket.billing_address.get('address3'),
            city=basket.billing_address.get('city'),
            county=county,
            postcode=basket.billing_address.get('postcode'),
            country=basket.billing_address.get('country'),
            telephone=basket.billing_address.get('telephone'),
            newsletter=basket.newsletter)

        # log user in
        login_user_without_password(request, user)
        basket.signup = None
    else:
        if request.user.is_anonymous():
            user = None
        else:
            user = request.user

        # if specified, copy relevant information to customer's profile
        if user != None and basket.update_profile:
            user.first_name = basket.billing_address.get('first_name')
            user.last_name = basket.billing_address.get('last_name')
            user.save()

            customer = get_customer_model().objects.get(user=user)
            customer.address1 = basket.billing_address.get('address1')
            customer.address2 = basket.billing_address.get('address2')
            customer.address3 = basket.billing_address.get('address3')
            customer.city     = basket.billing_address.get('city')
            customer.county   = county
            customer.postcode = basket.billing_address.get('postcode')
            customer.country  = basket.billing_address.get('country')
            customer.telephone = basket.billing_address.get('telephone')
            customer.save()

    # create single order
    order = get_order_model().create_from_basket(request, basket, user)

    # mailchimp
    if request.settings.mailchimp_enabled and basket.newsletter:
        email = basket.billing_address.get('email')
        first_name = basket.billing_address.get('first_name')
        last_name = basket.billing_address.get('last_name')
        person_name = (first_name, last_name)
        merge_vars = {'FNAME': " ".join(person_name)}
        ms = MailSnake(request.settings.mailchimp_api)
        try:
            ms.listSubscribe(id=request.settings.mailchimp_list_id, email_address=email, merge_vars=merge_vars)
        except:
            pass

    # redirect to order status page (payment from there...)
    basket.save()
    return HttpResponseRedirect(reverse('shop.order.status', args=[order.secret_id]))


@require_POST
def pay(request):
    """
    Start payment based on particular payment provided. At this point in time,
    the basket is destroyed.
    """
    # get order
    secret_id = request.POST.get('secret_id', None)
    if secret_id == None:
        raise Http404('Missing argument: secret_id.')

    if not re.match(r'^[a-fA-F0-9]+$', secret_id):
        raise Http404('Invalid format for argument: secret_id.')

    order = get_object_or_404(get_order_model(), secret_id=secret_id)

    # if the order is via invoice, accept order instantly without going through
    # online payment
    if order.is_invoice:
        # verify that the order can be placed
        if not order.can_be_placed_via_invoice():
            raise Http404('Unable to place the given order because of its status.')

        order.status = OrderBase.STATUS_PLACED_INVOICE
        order.save()

        generate_emails_and_notes(request, order)
        _destroy_basket(request)
        return HttpResponseRedirect(reverse('shop.order.status', args=[secret_id]))

    # if the total amount payable is zero, then skip the payment process
    # but the order is not an invoice as such.
    if order.is_zero_amount_checkout:
        order.status = OrderBase.STATUS_PLACED_ZERO_AMOUNT
        order.save()

        generate_emails_and_notes(request, order)
        _destroy_basket(request)
        return HttpResponseRedirect(reverse('shop.order.status', args=[secret_id]))

    # get gateway
    gateway = order.get_payment_gateway()

    # if we retry an existing order, clone the order first, which implicitly
    # generates a new order id...
    retry = request.POST.get('retry', '0') == '1'
    if retry == True and order.is_retry():
        order = order.clone(request)

    # verify that the order has not already been confirmed
    if not order.can_be_registered_for_payment():
        raise Http404('Unable to register the given order because of its status.')

    # if order can be moto
    order.is_backend_payment = False
    if order.can_moto and request.user.is_staff:
        order.is_backend_payment = True

    # register a new transaction for payment
    if order.is_backend_payment:
        preauth = False
    else:
        preauth = settings.SHOP_PREAUTH
    registration_context = gateway.register_payment(request, order, preauth=preauth)

    # if we do not get a valid registration content,
    # consider this payment attempt to be failed
    if registration_context == None:
        mail_error('Payment gateway %s was unable to register payment transaction. Message: %s' % (gateway.name, gateway.message))
        order.status = OrderBase.STATUS_PAYMENT_ERROR
        order.save()
        return HttpResponseRedirect(reverse('shop.order.status', args=[order.secret_id]))

    # save transcation details within order
    order.transaction_id  = registration_context.transaction_id
    order.payment_details = registration_context.payment_details
    order.status = OrderBase.STATUS_PAYMENT_AWAITING

    order.save()

    _destroy_basket(request)

    if gateway.is_redirect():
        # let the payment gateway render the response, which might be a redirect
        # or a custom submit form...
        return gateway.payment_redirect(request, order, registration_context)
    else:
        # handle payment directly
        return process_payment(request, gateway, order.transaction_id)


def _destroy_basket(request):
    # destroy basket
    basket = Basket(request)
    basket.clear()
    if request.user.is_anonymous():
        request.session[settings.GUEST_USER_SESSION_VAR] = None


def process_payment(request, gateway, transaction_id):
    """
    Process payment information for the order with the given transaction id.
    """
    # if the payment gateway returns no transaction id,
    # we consider this as an error.
    if transaction_id == None:
        mail_error('Payment gateway %s was unable to identify transaction id based on the payment response %s.' % (gateway, request))
        return gateway.payment_response(request, PaymentGateway.RESPONSE_ERROR, None, None)

    # get order based on transaction id
    order_model = get_order_model()
    try:
        order = order_model.objects.get(transaction_id=transaction_id)
        registration_context = RegistrationContext(order.transaction_id, order.payment_details)
    except order_model.DoesNotExist:
        # unable to identify correct order.
        return HttpResponse('', content_type='text/plain')

    # let the payment gateway determine the success of the payment
    # based on the response...
    payment_status = gateway.payment_accept(request, order, registration_context)

    # translate payment gateway payment status to system state
    if payment_status == PaymentGateway.STATUS_PAYMENT_CONFIRMED:
        if order.preauth:
            order.approval_status = OrderBase.APPROVAL_STATUS_WAITING
        else:
            order.approval_status = OrderBase.APPROVAL_STATUS_NONE
        order.status = OrderBase.STATUS_PAYMENT_CONFIRMED
        order.payment_confirmed_at = datetime.datetime.now()
        order.save()
    elif payment_status == PaymentGateway.STATUS_PAYMENT_DECLINED:
        order.status = OrderBase.STATUS_PAYMENT_DECLINED
        order.save()
    elif payment_status == PaymentGateway.STATUS_PENDING:
        order.status = OrderBase.STATUS_PENDING
        order.save()
    elif payment_status == PaymentGateway.STATUS_PAYMENT_ERROR:
        order.status = OrderBase.STATUS_PAYMENT_ERROR
        order.save()
        mail_error('Payment error (gateway %s): %s' % (gateway.__class__.__name__, gateway.message))
    else:
        order.status = OrderBase.STATUS_PAYMENT_ERROR
        order.save()
        mail_error('Received unknown payment response for order %s from gateway %s. Gateway message = %s' % (order.id, gateway.__class__.__name__, gateway.message))

    # send out emails and order/shipping notes
    generate_emails_and_notes(request, order)

    # send success back to payment gateway (this does not neccessarily
    # mean that the actual payment was successful)...
    if order.is_backend_payment:
        next_url = '%s?pk=%s' % (get_absolute_url('cubane.ishop.orders.edit'), order.pk)
    else:
        next_url = get_absolute_url('shop.order.status', args=[order.secret_id])

    return gateway.payment_response(request, PaymentGateway.RESPONSE_SUCCESS, order, registration_context, next_url)


def handle_payment_response(request, identifier):
    """
    Handle the response from a specific payment gateway specified by the
    given identifier.
    """
    # parse payment gateway identifier (int)
    try:
        identifier = int(identifier)
    except ValueError:
        raise Http404(
            'Invalid payment gateway identifier \'%s\'.' % identifier
        )

    # get payment gateway by identifier
    from cubane.ishop.views import get_shop
    shop = get_shop()
    gateway = shop.get_payment_gateway_by_identifier(identifier)

    # let the payment gateway figure out the correct transaction id that applies
    transaction_id = gateway.get_transaction_id(request)

    # process payment
    return process_payment(request, gateway, transaction_id)


@require_POST
def payment_response(request, identifier):
    """
    Accept the response from a specific payment gateway specified by the given
    identifier.
    """
    return handle_payment_response(request, identifier)


@require_POST
def default_payment_response(request):
    """
    Accept the response from the default payment gateway (legacy support)
    """
    return handle_payment_response(request, settings.SHOP_DEFAULT_PAYMENT_GATEWAY)


def get_payment_gateway_by_identifier(identifier):
    # parse payment gateway identifier (int)
    try:
        identifier = int(identifier)
    except ValueError:
        raise Http404(
            'Invalid payment gateway identifier \'%s\'.' % identifier
    )
    # get payment gateway by identifier
    from cubane.ishop.views import get_shop
    shop = get_shop()
    return shop.get_payment_gateway_by_identifier(identifier)


def payment_return(request, identifier):
    gateway = get_payment_gateway_by_identifier(identifier)
    secret_id = gateway.get_secret_id(request)
    return HttpResponseRedirect(reverse('shop.order.status', args=[secret_id]))


@require_POST
def payment_update(request, identifier):
    gateway = get_payment_gateway_by_identifier(identifier)

    # let the payment gateway handle the status update
    return gateway.payment_update(request)


def generate_emails_and_notes(request, order):
    # successfull order?
    if order.status in [OrderBase.STATUS_PAYMENT_CONFIRMED, OrderBase.STATUS_PLACED_INVOICE]:
        # update stock levels
        order.update_stock_levels()

        # send mail confirmation to customer and client
        mail_client_new_order(request, order)
        mail_customer_new_order(request, order)


@deny_bot()
@template('cubane/ishop/pages/order/status.html')
@cubane_cms_context()
def status(request, secret_id):
    """
    View current status of the given order. This page is publicly available
    on the internet without any user authentification.
    """
    order = get_object_or_404(get_order_model(), secret_id=secret_id)

    if order.is_placed() and not order.ga_sent:
        order.ga_sent = True
        order.save()

        # convince the template that ga has not been notified yet
        order.ga_sent = False

    return {
        'order': order,
        'basket': order.basket,
        'order_status_page': True
    }


@deny_bot()
@template('cubane/ishop/pages/order/shipping_notes.html')
@cubane_cms_context()
def shipping_notes(request, secret_id):
    """
    Display for PDF creation of the shipping note/status
    """
    basket = Basket(request)
    order = get_object_or_404(get_order_model(), secret_id=secret_id)

    return {
        'order': order
    }


@template('cubane/ishop/pages/order/test_payment.html')
@cubane_cms_context()
def test_payment(request, secret_id):
    """
    If the payment gateway is configured to use the innershed test
    payment gateway, the user will ultimatly redirected to this page, where a
    test payment can be confimed or declined.
    """
    # get order
    order = get_object_or_404(get_order_model(), secret_id=secret_id)

    # get payment gateway
    gateway = order.get_payment_gateway()

    # make sure that the payment gateway is the testing gateway
    if not isinstance(gateway, TestPaymentGateway):
        raise Http404('The system is not configured to use the test payment gateway.')

    return {
        'order': order,
        'details': order.payment_details,
        'post_url': gateway.get_response_url(request)
    }
