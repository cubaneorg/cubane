# coding=UTF-8
from __future__ import unicode_literals
from base import PaymentGateway, RegistrationContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
import datetime


class TestPaymentGateway(PaymentGateway):
    def register_payment(self, request, order, card_details=None, preauth=False):
        # normally we would communicate with the actual payment system
        # in order to register the transaction. In most cases, this
        # somehow involves a transaction id, which we are generating here.
        # this is executed again each time we try to make a payment. Please
        # note that the RegistrationContext can take additional information
        # if we are required to store additional payment details...
        return RegistrationContext('test-transaction-id-%s-%s' % (order.order_id, datetime.datetime.now().microsecond), {
            'additional-field': 'additional-value',
            'preauth': preauth
        })


    def payment_redirect(self, request, order, registration_context):
        # here we either present a form that will take us to the payment page
        # of our payment provider or we simple redirect directly by sending
        # a 301...
        return HttpResponseRedirect(reverse('shop.order.test_payment', args=[order.secret_id]))


    def get_transaction_id(self, request):
        # the given request object represents a request being made by the payment
        # gateway in order to signal the status of the payment. This method
        # should return the transaction_id that matches the request. The system
        # will then look up the correct order based on the transaction id returned.
        return request.POST.get('transaction_id', None)


    def payment_accept(self, request, order, registration_context):
        # if the order could be identified successfully, this method is called in
        # order to determine the status of the order. In this case, the status
        # was simpy posted along with the registration id.
        if registration_context.payment_details.get('preauth', False):
            order.preauth = True
            order.preauth_transaction_id = order.transaction_id

        s = request.POST.get('status', '')
        if s == 'CONFIRMED':
            return PaymentGateway.STATUS_PAYMENT_CONFIRMED
        elif s == 'DECLINED':
            return PaymentGateway.STATUS_PAYMENT_DECLINED
        else:
            return PaymentGateway.STATUS_PAYMENT_ERROR


    def payment_response(self, request, payment_status, order, registration_context, next_url):
        # return the http response that is send back to the payment gateway as
        # the result of the transaction. For the test gateway, we simply return
        # the url for the status page in the success case and the url for
        # an arbitary error page in the error case if we do not have an order.
        if order != None:
            return HttpResponseRedirect(next_url)
        else:
            return HttpResponseRedirect(reverse('shop.order.error'))


    def payment_settle(self, order, amount):
        return (True, 'Test payment settled successfully.')


    def payment_abort(self, order):
        return (True, 'Test payment aborted successfully.')


    def has_cancel(self):
        """
        Return True if Payment Gateway has payment_cancel implementation. Otherwise False.
        """
        return True


    def has_fulfilment(self):
        """
        Return True if Payment Gateway has payment_fulfilment implementation. Otherwise False.
        """
        return True


    def payment_cancel(self, order):
        """
        Provides option to cancel order.
        """
        return (True, 'Test payment cancelled successfully.')


    def payment_fulfilment(self, order):
        """
        Provides option to do fulfilment.
        """
        return (True, 'Test payment fulfilled successfully.')


    def can_moto(self):
        """
        Test Gateway should return True to allow testing.
        """
        return True
