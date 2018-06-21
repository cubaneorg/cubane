# coding=UTF-8
from __future__ import unicode_literals
from base import PaymentGateway, RegistrationContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
import datetime


class PaypalPaymentGateway(PaymentGateway):
    def register_payment(self, request, order, card_details=None, preauth=False):
        return RegistrationContext(order.id, {
                'payment_details': ''
            })

    def payment_redirect(self, request, order, registration_context):
        return HttpResponseRedirect(reverse('shop.order.status', args=[order.secret_id]))


    def get_transaction_id(self, request):
        return request.POST.get('transaction_id', None)


    def payment_accept(self, request, order, registration_context):
        return PaymentGateway.STATUS_PAYMENT_CONFIRMED


    def payment_response(self, request, payment_status, order, registration_context, next_url):
        return HttpResponseRedirect(next_url)
