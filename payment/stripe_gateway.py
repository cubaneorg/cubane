# coding=UTF-8
from __future__ import unicode_literals
from base import PaymentGateway, RegistrationContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
import datetime
import settings
import stripe


class StripePaymentGateway(PaymentGateway):
    def is_redirect(self):
        return False


    def register_payment(self, request, order, card_details=None, preauth=False):
        # stripe charge client without any redirections so we are
        # charging straightaway...
        token = request.POST.get('stripe_token', None)
        stripe_keys = settings.CLIENT_STRIPE.get(request.client.slug, {})
        stripe.api_key = stripe_keys['secret']

        if token:
            try:
                charge = stripe.Charge.create(
                    amount=(int)(order.total_payment * 100), # amount in cents, again
                    currency="gbp",
                    source=token,
                    description='Order ' + unicode(order.id)
                )
                return RegistrationContext(order.id, {
                    'success': True
                })
            except:
                # The card has been declined
                pass

        return RegistrationContext(order.id, {
            'success': False
        })


    def payment_redirect(self, request, order, registration_context):
        return HttpResponseRedirect(reverse('shop.order.status', args=[order.secret_id]))


    def get_transaction_id(self, request):
        return request.POST.get('transaction_id', None)


    def payment_accept(self, request, order, registration_context):
        if order.payment_details['success']:
            return PaymentGateway.STATUS_PAYMENT_CONFIRMED
        else:
            return PaymentGateway.STATUS_PAYMENT_DECLINED


    def payment_response(self, request, payment_status, order, registration_context, next_url):
        return HttpResponseRedirect(next_url)
