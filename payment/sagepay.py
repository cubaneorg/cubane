# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from cubane.lib.url import get_absolute_url
from base import PaymentGateway, RegistrationContext
import cubane.payment.lib.sagepay as sagepay
import datetime


class SagepayPaymentGateway(PaymentGateway):
    def register_payment(self, request, order, card_details=None, preauth=False):
        # register transaction with sagepay
        config = self._config['config']
        sp = sagepay.RegisterTransaction(
            order,
            None,
            self.get_response_url(request),
            config['vendor'],
            config['currency'],
            preauth
        )
        sp.order_details(order.total_payment, 'Payment for order #%s' % order.order_id)
        sp.user_details(order.billing_address.get('first_name', '')[:20], order.billing_address.get('last_name', '')[:20])

        billing_address = {
            'address_1': order.billing_address.get('address1', '')[:100],
            'address_2': order.billing_address.get('address2', '')[:100],
            'city':      order.billing_address.get('city', '')[:40],
            'postcode':  order.billing_address.get('postcode','')[:10],
            'country':   order.billing_address.get('country-iso'),
            'state':     order.billing_address.get('state')
        }
        sp.user_address('billing', billing_address)
        if order.delivery_address and not order.is_click_and_collect:
            delivery_address = {
                'address_1': order.delivery_address.get('address1', '')[:100],
                'address_2': order.delivery_address.get('address2', '')[:100],
                'city':      order.delivery_address.get('city', '')[:40],
                'postcode':  order.delivery_address.get('postcode','')[:10],
                'country':   order.delivery_address.get('country-iso'),
                'state':     order.delivery_address.get('state')
            }
            sp.user_address('shipping', delivery_address)
        else:
            sp.user_address('shipping', billing_address)

        transaction = sp.process_query(config['url'])

        if transaction.status:
            return RegistrationContext(transaction.transaction_id, {
                'sp_security_key': transaction.security_key,
                'preauth':         preauth,
                'vendor_tx_code':  transaction.vendor_tx_code,
                'redirect_url':    transaction.next_url
            })
        else:
            self.set_message(transaction.response)
            return None


    def payment_redirect(self, request, order, registration_context):
        # here we either present a form that will take us to the payment page
        # of our payment provider or we simple redirect directly by sending
        # a 302...
        return HttpResponseRedirect(registration_context.payment_details.get('redirect_url'))


    def get_transaction_id(self, request):
        # the given request object represents a request being made by the payment
        # gateway in order to signal the status of the payment. This method
        # should return the transaction_id that matches the request. The system
        # will then look up the correct order based on the transaction id returned.
        rtnr = sagepay.RegisterTransactionNotificationResponse(request.POST)
        return rtnr.transaction_id


    def payment_accept(self, request, order, registration_context):
        config = self._config['config']
        # if the order could be identified successfully, this method is called in
        # order to determine the status of the order. In this case, the status
        # was simpy posted along with the registration id.
        rtnr = sagepay.RegisterTransactionNotificationResponse(request.POST)

        if not (rtnr.short_status == 'SUCCESS' or rtnr.short_status == 'OK'):
            return PaymentGateway.STATUS_PAYMENT_DECLINED

        if not rtnr.hash_check(order.payment_details['sp_security_key'], config['vendor']):
            return PaymentGateway.STATUS_PAYMENT_ERROR

        # if this is a deferred payment, expect to see TxType == DEFERRED and TxAuthNo present
        if registration_context.payment_details.get('preauth', False):
            if rtnr.tx_type != 'DEFERRED':
                return PaymentGateway.STATUS_PAYMENT_ERROR
            order.preauth = True
            order.preauth_transaction_id = rtnr.tx_auth_no

        return PaymentGateway.STATUS_PAYMENT_CONFIRMED


    def payment_response(self, request, payment_status, order, registration_context, next_url):
        # return the http response that is send back to the payment gateway as
        # the result of the transaction. For the test gateway, we simply return
        # the url for the status page in the success case and the url for
        # an arbitary error page in the error case if we do not have an order.
        rtnr = sagepay.RegisterTransactionNotificationResponse(request.POST)

        if payment_status == PaymentGateway.STATUS_PAYMENT_CONFIRMED and order != None:
            res = rtnr.build_response(
                rtnr.SUCCESS,
                next_url
            )
        else:
            res = rtnr.build_response(
                rtnr.FAILURE,
                next_url,
                message='Failure',
            )

        return HttpResponse(res, content_type='text/plain')


    def payment_settle(self, order, amount):
        config = self._config['config']
        return sagepay.SagepayRelease(
            config['vendor'],
            config['release_url'] if 'release_url' in config else None,
            order.payment_details.get('vendor_tx_code'),
            order.transaction_id,
            order.payment_details.get('sp_security_key'),
            order.preauth_transaction_id,
            amount
        ).send()


    def payment_abort(self, order):
        config = self._config['config']
        return sagepay.SagepayAbort(
            config['vendor'],
            config['abort_url'] if 'abort_url' in config else None,
            order.payment_details.get('vendor_tx_code'),
            order.transaction_id,
            order.payment_details.get('sp_security_key'),
            order.preauth_transaction_id
        ).send()


    def can_moto(self):
        return True
