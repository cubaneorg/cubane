# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from cubane.lib.url import get_absolute_url
from cubane.ishop import get_order_model
from requests.auth import HTTPBasicAuth
import requests
from cubane.ishop.models import OrderBase
from cubane.ishop.basket import Basket
from base import PaymentGateway, RegistrationContext
import os
from cubane.ishop.apps.shop.order.views import generate_emails_and_notes


class KlarnaPaymentGateway(PaymentGateway):
    URL = 'https://api.playground.klarna.com/' if os.environ.get('DEV_MODE') == '1' else 'https://api.klarna.com/'

    @staticmethod
    def place_order(request, secret_id, authorization_token, confirmation_url):
        auth = HTTPBasicAuth(os.environ.get('KLARNA_API_USERNAME'), os.environ.get('KLARNA_API_PASSWORD'))

        order = get_order_model().objects.get(secret_id=secret_id)
        order.paymet_gateway = settings.GATEWAY_KLARNA
        order.save()

        order_total = int(order.total_payment * 100)

        json = {
            'merchant_urls': {
                'confirmation': confirmation_url,
            },
            'merchant_reference1': secret_id,

            'purchase_currency': "GBP",
            "purchase_country": order.billing_address.get('country')['iso'],
            "order_amount": order_total,
            "order_lines": [{
                'name': 'Order #%s' % order.order_id,
                'quantity': 1,
                'total_amount': order_total,
                'unit_price': order_total
            }],
            "billing_address": {
                "given_name": order.billing_address.get('first_name', ''),
                "family_name": order.billing_address.get('last_name', ''),
                "email": order.billing_address.get('email'),
                "title": order.billing_address_title_display,
                "street_address": order.billing_address.get('address1', ''),
                "street_address2": order.billing_address.get('address2', ''),
                "postal_code": order.billing_address.get('postcode',''),
                "city": order.billing_address.get('city', ''),
                "region": "",
                "country": order.billing_address.get('country')['iso']
            },
            "shipping_address": {
                "given_name": order.billing_address.get('first_name', ''),
                "family_name": order.billing_address.get('last_name', ''),
                "email": order.billing_address.get('email'),
                "title": order.billing_address_title_display,
                "street_address": order.delivery_address.get('address1', ''),
                "street_address2": order.delivery_address.get('address2', ''),
                "postal_code": order.delivery_address.get('postcode',''),
                "city": order.delivery_address.get('city', ''),
                "region": "",
                "country": order.delivery_address.get('country')['iso'] if order.delivery_address.get('country') else ''
            }

        }

        headers = {
            'content-type': 'application/json'
        }

        response = requests.post('%s/payments/v1/authorizations/%s/order' % (KlarnaPaymentGateway.URL, authorization_token), json=json, auth=auth, headers=headers)

        json = response.json()

        # fraud_status can be ACCEPTED, PENDING, or REJECTED
        # PENDING only allowed in UK/US and may be updated later
        # https://docs.klarna.com/order-management/integration-guide/pending-orders/
        # naively assume if it's not accept that it's rejected
        if json['fraud_status'] == 'ACCEPTED':
            order.loan_status = OrderBase.LOAN_STATUS_ACCEPT
            order.status = OrderBase.STATUS_PAYMENT_CONFIRMED
        else:
            order.loan_status = OrderBase.LOAN_STATUS_DECLINE
            order.status = OrderBase.STATUS_PAYMENT_DECLINED
        order.save()

        return json


    @staticmethod
    def create_session(request, secret_id):
        order = get_order_model().objects.get(secret_id=secret_id)

        auth = HTTPBasicAuth(os.environ.get('KLARNA_API_USERNAME'), os.environ.get('KLARNA_API_PASSWORD'))
        order_total = int(order.total_payment * 100)

        # list real products
        json = {
            "purchase_country": order.billing_address.get('country')['iso'],
            "purchase_currency": "GBP",
            "locale": "en-GB",
            "order_amount": order_total,
            "order_lines": [{
                'name': 'Order #%s' % order.order_id,
                'quantity': 1,
                'total_amount': order_total,
                'unit_price': order_total
            }],
            "billing_address": {
                "given_name": order.billing_address.get('first_name', ''),
                "family_name": order.billing_address.get('last_name', ''),
                "email": order.billing_address.get('email'),
                "title": order.billing_address_title_display,
                "street_address": order.billing_address.get('address1', ''),
                "street_address2": order.billing_address.get('address2', ''),
                "postal_code": order.billing_address.get('postcode',''),
                "city": order.billing_address.get('city', ''),
                "region": "",
                "country": order.billing_address.get('country')['iso']
            },
            "shipping_address": {
                "given_name": order.billing_address.get('first_name', ''),
                "family_name": order.billing_address.get('last_name', ''),
                "email": order.billing_address.get('email'),
                "title": order.billing_address_title_display,
                "street_address": order.delivery_address.get('address1', ''),
                "street_address2": order.delivery_address.get('address2', ''),
                "postal_code": order.delivery_address.get('postcode',''),
                "city": order.delivery_address.get('city', ''),
                "region": "",
                "country": order.delivery_address.get('country')['iso'] if order.delivery_address.get('country') else ''
            }
        }

        headers = {
            'content-type': 'application/json'
        }

        response = requests.post('%s/payments/v1/sessions' % KlarnaPaymentGateway.URL, json=json, auth=auth, headers=headers)
        return response.json()
