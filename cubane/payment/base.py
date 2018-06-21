# coding=UTF-8
from __future__ import unicode_literals
from django.http import Http404
from django.core.urlresolvers import reverse
from cubane.lib.url import get_absolute_url


class RegistrationContext(object):
    """
    Holds the information that is returned by a payment gateway during
    the registration process for a transaction.
    """
    def __init__(self, transaction_id, payment_details = {}):
        self.transaction_id = transaction_id
        self.payment_details = payment_details


class PaymentGateway(object):
    STATUS_PAYMENT_CONFIRMED      = 1
    STATUS_PAYMENT_DECLINED       = 2
    STATUS_PAYMENT_ERROR          = 3
    STATUS_PENDING                = 4


    RESPONSE_SUCCESS = 1
    RESPONSE_ERROR   = 2


    def __init__(self, config, identifier):
        self._config = config
        self._identifier = identifier
        self._message = ''


    @property
    def name(self):
        return self.__class__.__name__


    @property
    def message(self):
        return self._message


    def set_message(self, message):
        self._message = message


    def get_response_url(self, request):
        """
        Return the payment response url used for this gateway.
        """
        return get_absolute_url('shop.order.payment_response', args=[self._identifier])


    def is_redirect(self):
        """
        Returns True, if this payment gateway is based on redirecting
        to a 3rd party payment page. Return false if payment happends
        directly.
        """
        return True


    def register_payment(self, request, order, card_details=None, preauth=False):
        """
        Register payment. Payment gateway is suppose to return an instance
        of RegistrationContext, where the transaction_id is any gateway-specific
        identifier that is unique for the transaction and payment_details is any
        json-serializable entity which is then stored along with the order.
        A RegistrationContext instance is later passed on to payment_accept().
        """
        raise NotImplementedException()


    def payment_redirect(self, request, order, registration_context):
        """
        Return an HttpResponse that will either present a redirect form
        (based on a base template) or a redirect to the payment gateway
        directly. The givden registration context is the very same information
        as returned by a previous call to register_payment().
        """
        raise NotImplementedException()


    def get_transaction_id(self, request):
        """
        Return a valid order id based on the given response from the payment
        gateway. Return None, if no valid order id could be identified.
        """
        raise NotImplementedException()


    def payment_accept(self, request, order, registration_context):
        """
        Determine the status of the given order. Return either STATUS_PAYMENT_CONFIRMED,
        STATUS_PAYMENT_DECLINED or STATUS_PAYMENT_ERROR.
        """
        raise NotImplementedException()


    def payment_response(self, request, payment_status, order, registration_context, next_url):
        """
        Return a valid http response after the payment response has been processed.
        The given response type if either RESPONSE_SUCCESS or RESPONSE_ERROR.
        Pleasse not that order might be None with a response_type of RESPONSE_ERROR
        in the case that no order could be identified based on the order id that
        was returned by get_order_id() eilier.
        If response_type is RESPONSE_SUCCESS it is guarantued that a valid order object
        is available.
        """
        raise NotImplementedException()


    def payment_settle(self, order, amount):
        raise NotImplementedException()


    def payment_abort(self, order):
        raise NotImplementedException()


    def has_cancel(self):
        """
        Return True if Payment Gateway has payment_cancel implementation. Otherwise False.
        """
        return False


    def has_fulfilment(self):
        """
        Return True if Payment Gateway has payment_fulfilment implementation. Otherwise False.
        """
        return False


    def payment_cancel(self, order):
        """
        Provides option to cancel order.
        """
        raise NotImplementedException()


    def payment_fulfilment(self, order):
        """
        Provides option to do fulfilment.
        """
        raise NotImplementedException()


    def payment_update(self, request):
        """
        Called by the payment gateway endpoint as a callback whenever the status
        of a pending payment process changes. Return a valid HttpResponse as
        required by the payment gateway.
        """
        raise Http404(
            'This gateway does not support status callback notifications.'
        )


    def can_moto(self):
        """
        By default payment gateway cannot do mail / telephone orders.
        """
        return False


    def get_secret_id(self, request):
        """
        Get Secret ID if it is provided by GET arguments instead of POST method.
        """
        raise NotImplementedException()
