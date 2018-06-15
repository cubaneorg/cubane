# coding=UTF-8
from __future__ import unicode_literals
from base import PaymentGateway, RegistrationContext
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
import datetime
from django.conf import settings
from decimal import Decimal
import requests
from bs4 import BeautifulSoup
from cubane.ishop.models import OrderBase
from cubane.ishop import get_order_model
from cubane.ishop.apps.shop.order.views import generate_emails_and_notes


class DekoPaymentGateway(PaymentGateway):
    MIN_DEPOSIT_PERCENTAGE = 10
    MAX_DEPOSIT_PERCENTAGE = 50
    MINIMUM_TOTAL = Decimal('277.78')
    LIVE_URL = 'https://secure.dekopay.com:6686/'
    TEST_URL = 'https://test.dekopay.com:3343/'


    def register_payment(self, request, order, card_details=None, preauth=False):
        config = self._config['config']

        if 'installation_id' not in config:
            raise Exception('[Deko]: Missing INSTALLATION ID in settings file.')

        finance_option = order.finance_option
        if not finance_option:
            raise Exception('[Deko]: FINANCE CODE is not provided in order.')
        finance_code = finance_option.code
        if DekoPaymentGateway.MINIMUM_TOTAL > order.total_payment:
            raise Exception('[Deko]: TOTAL IS SMALLER THAN MINIMUM TOTAL.')


        order_total = int(order.total_payment * 100)
        deposit = order_total * order.loan_deposit / 100

        is_order_valid = True
        if order_total < self.MINIMUM_TOTAL:
            is_order_valid = False


        # change order status to payment awaiting
        order.status = OrderBase.STATUS_PAYMENT_AWAITING
        order.save()

        if is_order_valid:
            post = {
                'action': 'credit_application_link',
                'Identification[api_key]': self._get_api_key(),
                'Identification[RetailerUniqueRef]': order.secret_id,
                'Identification[InstallationID]':config['installation_id'],
                'Goods[Description]': 'Order #%s' % order.order_id,
                'Goods[Price]': order_total,
                'Finance[Code]': finance_code,
                'Finance[Deposit]': deposit,
                'Consumer[Title]': order.billing_address_title_display,
                'Consumer[Forename]': order.billing_address.get('first_name', ''),
                'Consumer[Surname]': order.billing_address.get('last_name', ''),
                'Consumer[EmailAddress]': order.billing_address.get('email', ''),
                'Consumer[Postcode]': order.billing_address.get('postcode', '')
            }

            response = requests.post(self._get_url(), post)

            xml = BeautifulSoup(response.text, 'lxml')
            if xml.p4l:
                if xml.p4l.error:
                    raise Exception('[Deko]: %s' % xml.p4l.error.next)

            return RegistrationContext(order.id, {
                'redirect_url': response.text
            })
        else:
            raise Exception('[Deko]: Order is not valid check minimums, deposit percentage.')


    def payment_redirect(self, request, order, registration_context):
        return HttpResponseRedirect(registration_context.payment_details.get('redirect_url'))


    def get_transaction_id(self, request):
        return request.POST.get('transaction_id', None)


    def get_secret_id(self, request):
        secret_id = request.GET.get('retaileruniqueref', None)

        if not secret_id:
            raise Exception('[Deko]: Secret ID doesn\'t exists.')

        return secret_id.split('[')[0]


    def has_fulfilment(self):
        return True


    def has_cancel(self):
        return True


    def payment_response(self, request, payment_status, order, registration_context, next_url):
        return HttpResponseRedirect(next_url)


    def payment_cancel(self, order):
        post = {
            'cr_id': order.transaction_id,
            'api_key': self._get_api_key(),
            'new_state': 'cancelled',
            'cancellation_note': order.cancel_msg
        }
        response = requests.post(self._get_url(), post)

        return self._get_status_from_xml(response.text)


    def payment_fulfilment(self, order):
        post = {
            'cr_id': order.transaction_id,
            'api_key': self._get_api_key(),
            'new_state': 'fulfilled',
            'fulfilment_ref': order.secret_id
        }
        response = requests.post(self._get_url(), post)

        return self._get_status_from_xml(response.text)


    def payment_update(self, request):
        cr_id = request.POST.get('CreditRequestID', None)
        status = request.POST.get('Status', None)
        api_key = request.POST.get('Identification[api_key]', None)
        ref = request.POST.get('Identification[RetailerUniqueRef]', None)

        is_valid_request = True
        # check if api key is matching our api KEY
        if api_key != self._get_api_key():
            is_valid_request = False

        if status:
            status = status.lower()
        else:
            is_valid_request = False

        # credit id should be provided
        if not cr_id:
            is_valid_request = False

        # some requests are with [] some without
        if ref:
            ref = ref.split('[')[0]

        # get order by ref
        order = get_order_model().objects.filter(secret_id=ref)

        if order.count() != 1:
            is_valid_request = False

        if is_valid_request:
            order = order[0]
            if status == 'initialise':
                order.loan_status = OrderBase.LOAN_STATUS_NONE
            elif status == 'predecline':
                order.loan_status = OrderBase.LOAN_STATUS_PREDECLINE
            elif status == 'accept':
                order.loan_status = OrderBase.LOAN_STATUS_ACCEPT
            elif status == 'decline':
                order.loan_status = OrderBase.LOAN_STATUS_DECLINE
                order.status = OrderBase.STATUS_PAYMENT_DECLINED
            elif status == 'refer':
                order.loan_status = OrderBase.LOAN_STATUS_REFER
            elif status == 'verified':
                order.loan_status = OrderBase.LOAN_STATUS_VERIFIED
                order.status = OrderBase.STATUS_PAYMENT_CONFIRMED
                order.payment_confirmed_at = datetime.datetime.now()
            elif status == 'amended':
                order.loan_status = OrderBase.LOAN_STATUS_AMENDED
            elif status == 'fulfilled':
                order.loan_status = OrderBase.LOAN_STATUS_FULFILLED
            elif status == 'complete':
                order.loan_status = OrderBase.LOAN_STATUS_COMPLETE
            elif status == 'cancelled':
                order.loan_status = OrderBase.LOAN_STATUS_CANCELLED
                order.status = OrderBase.STATUS_PAYMENT_DECLINED
            elif status == 'info needed':
                order.loan_status = OrderBase.LOAN_STATUS_INFO_NEEDED
            elif status == 'action customer':
                order.loan_status = OrderBase.LOAN_STATUS_ACTION_CUSTOMER
            elif status == 'action retailer':
                order.loan_status = OrderBase.LOAN_STATUS_ACTION_RETAILER
            else:
                order.loan_status = OrderBase.LOAN_STATUS_NONE

            order.transaction_id = cr_id
            order.save()

            # Deko didn't define what kind of response they are expecting. Assuming 200...
            return HttpResponse('Status: OK')
        else:
            raise Exception('[Deko]: Payment Update couldn\'t update given order.')


    def _get_status_from_xml(self, xml):
        xml = BeautifulSoup(xml, 'lxml')

        if xml.result:
            return {
                'result': True if 'success' in xml.result.next else False,
                'message': None
            }
        return {
            'result': False,
            'message': xml.error.next.replace('\n', ' ').strip()
        }


    def _get_api_key(self):
        config = self._config['config']
        if 'api_key' not in config:
            raise Exception('[Deko]: Missing API KEY in settings file.')
        else:
            return config['api_key']


    def _get_url(self):
        config = self._config['config']
        if 'url' not in config:
            if settings.DEBUG:
                return self.TEST_URL
            else:
                return self.LIVE_URL
        else:
            return config['url']
