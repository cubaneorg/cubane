# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings


'''

    The following must be in the settings file
    SAGE_VENDOR                     vendor login name
    SAGE_NOTIFICATION_URL           Callback URL
    SAGE_CURRENCY                   ie GBP
    SAGE_REGISTER_TRANSACTION_URL   sagepay.URL.TEST.REGISTER_TRANSACTION
    SAGE_PREFIX                     prefix for sage payments, unique to site

'''

VPS_PROTOCOL = '3.00'


class BASE:
    LIVE_BASE = 'https://live.sagepay.com/gateway/service/'
    TEST_BASE = 'https://test.sagepay.com/gateway/service/'

class URL:

    class TEST:
        ABORT = '%sabort.vsp' % BASE.TEST_BASE
        AUTHORISE = '%sauthorise.vsp' % BASE.TEST_BASE
        CANCEL = '%scancel.vsp' % BASE.TEST_BASE
        PURCHASE = '%svspserver-register.vsp' % BASE.TEST_BASE
        REFUND = '%srefund.vsp' % BASE.TEST_BASE
        RELEASE = '%srelease.vsp' % BASE.TEST_BASE
        REPEAT = '%srepeat.vsp' % BASE.TEST_BASE
        VOID = '%svoid.vsp' % BASE.TEST_BASE

    class LIVE:
        ABORT = '%sabort.vsp' % BASE.LIVE_BASE
        AUTHORISE = '%sauthorise.vsp' % BASE.LIVE_BASE
        CANCEL = '%scancel.vsp' % BASE.LIVE_BASE
        PURCHASE = '%svspserver-register.vsp' % BASE.LIVE_BASE
        REFUND = '%srefund.vsp' % BASE.LIVE_BASE
        RELEASE = '%srelease.vsp' % BASE.LIVE_BASE
        REPEAT = '%srepeat.vsp' % BASE.LIVE_BASE
        VOID = '%svoid.vsp' % BASE.LIVE_BASE


class RegisterTransaction:

    '''
        order_id, is used to calculate the vendor transaction code.
        Just needs to be unique
    '''
    def __init__(self, order, prefix, notification_url, vendor, currency, preauth=False):
        import time
        self.got_order_details = False
        self.got_user_details = False
        self.got_user_address_billing = False
        self.got_user_address_shipping = False
        self.vendor = vendor
        self.currency = currency
        self.preauth = preauth

        self.vendor_tx_code = '-'.join(filter(lambda x: x, [
            prefix, order.order_id, unicode(time.time())
        ]))

        # sd = send_details
        self.sd = []
        self.sd.append(('VPSProtocol', VPS_PROTOCOL))
        self.sd.append(('TxType', 'DEFERRED' if self.preauth else 'PAYMENT'))
        self.sd.append(('Vendor', self.vendor))
        self.sd.append(('VendorTxCode', self.vendor_tx_code))
        self.sd.append(('NotificationURL', notification_url))

        # set correct flag for MOTO order
        if order.is_backend_payment and order.can_moto:
            self.sd.append(('AccountType', 'M'))

    # details for the order
    def order_details(self, amount, description):
        self.sd.append(('Amount', u'%.2f' % amount))
        self.sd.append(('Currency', self.currency))
        self.sd.append(('Description', description.encode('utf8')))

        self.got_order_details = True

    # first & last name for the user
    def user_details(self, first_name, last_name):
        self.sd.append(('BillingFirstnames', first_name.encode('utf8')))
        self.sd.append(('BillingSurname', last_name.encode('utf8')))
        self.sd.append(('DeliveryFirstnames', first_name.encode('utf8')))
        self.sd.append(('DeliverySurname', last_name.encode('utf8')))

        self.got_user_details = True

    '''
        address of user, address must be dictionary containing
            address1
            address2 (optional)
            city
            postcode
            country (2 character iso)
    '''
    def user_address(self, type, address):
        if type == 'billing':
            type = 'Billing'
            self.got_user_address_billing = True
        elif type == 'shipping':
            type = 'Delivery'
            self.got_user_address_shipping = True
        else:
            raise 'Invalid "type" for address. billing/shipping'

        self.sd.append(('%sAddress1' % type, address['address_1'].encode('utf8')))

        if address.get('address_2'):
            self.sd.append(('%sAddress2' % type, address['address_2'].encode('utf8')))

        self.sd.append(('%sCity' % type, address['city'].encode('utf8')))
        self.sd.append(('%sPostCode' % type, address['postcode'].encode('utf8')))
        self.sd.append(('%sCountry' % type, address['country'].encode('utf8')))

        if 'state' in address and address.get('state'):
            self.sd.append(('%sState' % type, address['state'].upper().encode('utf8')))


    # Builds, escapes & sends the POST data query sent to sagepay
    def process_query(self, register_transaction_url):
        import urllib

        # check everything has been sent
        if not self.got_order_details:
            raise ValueError('Order details not set')
        if not self.got_user_details:
            raise ValueError('User details not set')
        #if not self.got_user_address_billing:
        #    raise ValueError('Billing address not set')
        #if not self.got_user_address_shipping:
        #    raise ValueError('Shipping address not set')

        request = urllib.urlencode(self.sd)

        opener = urllib.URLopener()

        r = opener.open('%s' % register_transaction_url, request)
        return RegisterTransactionResponse(self.vendor_tx_code, r.read())


class RegisterTransactionResponse:
    def __init__(self, vendor_tx_code, response):
        self.vendor_tx_code = vendor_tx_code

        lines = response.split("\n")
        self.cleaned = {}
        for line in lines:
            chunk = line.split('=', 1)
            if len(chunk) == 2:
                self.cleaned[chunk[0]] = chunk[1]

    @property
    def response(self):
        return self.cleaned

    @property
    def status(self):
        return True if self.cleaned['Status'].strip() == 'OK' else False

    @property
    def security_key(self):
        return self.cleaned['SecurityKey'].strip()

    @property
    def vendor_tx_code(self):
        return self.vendor_tx_code

    @property
    def transaction_id(self):
        return self.cleaned['VPSTxId'].strip()

    @property
    def next_url(self):
        return self.cleaned['NextURL'].strip()


class RegisterTransactionNotificationResponse:
    SUCCESS = 1
    FAILURE = 2


    def __init__(self, response):
        self.r = response
        from django.core.mail import mail_admins

        if response.get('Status', None) not in ['OK', 'ABORT', 'REJECTED']:
            import json
            mail_admins('Sagepay error handle', json.dumps(response, indent=4, sort_keys=True))


    def hash_check(self, security_key, vendor):
        h = []
        h.append(self.r.get('VPSTxId', ''))
        h.append(self.r.get('VendorTxCode', ''))
        h.append(self.r.get('Status', ''))
        h.append(self.r.get('TxAuthNo', ''))
        h.append(vendor)
        h.append(self.r.get('AVSCV2', ''))
        h.append(security_key)
        h.append(self.r.get('AddressResult', ''))
        h.append(self.r.get('PostCodeResult', ''))
        h.append(self.r.get('CV2Result', ''))
        h.append(self.r.get('GiftAid', ''))
        h.append(self.r.get('3DSecureStatus', ''))
        h.append(self.r.get('CAVV', ''))
        h.append(self.r.get('AddressStatus', ''))
        h.append(self.r.get('PayerStatus', ''))
        h.append(self.r.get('CardType', ''))
        h.append(self.r.get('Last4Digits', ''))
        h.append(self.r.get('DeclineCode', ''))
        h.append(self.r.get('ExpiryDate', ''))
        h.append(self.r.get('FraudResponse', ''))
        h.append(self.r.get('BankAuthCode', ''))

        import md5
        our_hash = md5.new(''.join(h)).hexdigest().upper()

        if our_hash == self.r.get('VPSSignature'):
            return True
        else:
            return False

    def build_response(self, status, redirect_url, message=False):
        if status == self.SUCCESS:
            status = 'OK'
        elif status == self.FAILURE:
            status = 'INVALID'
        else:
            raise 'Unknown status. Valid: SUCCESS/FAILURE'

        h = []
        h.append('Status=%s' % status)
        h.append('RedirectURL=%s' % redirect_url)
        if status == 'INVALID':
            if not message:
                raise 'FAILURE Sent with no message'

            h.append('StatusDetail=%s' % message)

        return '\r\n'.join(h)

    @property
    def transaction_id(self):
        return self.r.get('VPSTxId', '').strip()

    @property
    def last_digits(self):
        return self.r.get('Last4Digits', '').strip()

    @property
    def status(self):
        return self.r.get('StatusDetail', '').strip()

    @property
    def short_status(self):
        return self.r.get('Status', '').strip()

    @property
    def postcode_valid(self):
        return self.r.get('PostCodeResult', '').strip()

    @property
    def cv2_valid(self):
        return self.r.get('CV2Result', '').strip()

    @property
    def tx_type(self):
        return self.r.get('TxType', '').strip()

    @property
    def tx_auth_no(self):
        return self.r.get('TxAuthNo', '').strip()


class SagepayResponse(object):
    def __init__(self, response):
        lines = response.split("\n")
        self.cleaned = {}
        for line in lines:
            chunk = line.split('=', 1)
            if len(chunk) == 2:
                self.cleaned[chunk[0]] = chunk[1].strip()


class SagepayRequest(object):
    def __init__(self, url, tx_type, vendor, vendor_tx_code, transaction_id, security_key, tx_auth_no):
        self.url = url
        self.sd = []
        self.sd.append(('VPSProtocol', VPS_PROTOCOL))
        self.sd.append(('TxType', tx_type))
        self.sd.append(('Vendor', vendor))
        self.sd.append(('VendorTxCode', vendor_tx_code))
        self.sd.append(('VPSTxId', transaction_id))
        self.sd.append(('SecurityKey', security_key))
        self.sd.append(('TxAuthNo', tx_auth_no))


    def send(self):
        import urllib
        from django.core.mail import mail_admins

        request = urllib.urlencode(self.sd)
        opener = urllib.URLopener()
        r = opener.open(self.url, request)

        response_content = r.read()
        response = SagepayResponse(response_content)

        status = response.cleaned.get('Status')
        msg = response.cleaned.get('StatusDetails')

        if status == 'OK':
            return (True, msg)
        else:
            mail_admins('Sagepay command error: %s' % msg, response_content)
            return (False, msg)


class SagepayRelease(SagepayRequest):
    def __init__(self, vendor, release_url, vendor_tx_code, transaction_id, security_key, tx_auth_no, amount):
        if release_url:
            url = release_url
        else:
            url = URL.TEST.RELEASE if settings.DEBUG or settings.SHOP_TEST_MODE else URL.LIVE.RELEASE
        super(SagepayRelease, self).__init__(url, 'RELEASE', vendor, vendor_tx_code, transaction_id, security_key, tx_auth_no)
        self.sd.append(('ReleaseAmount', u'%s' % amount))


class SagepayAbort(SagepayRequest):
    def __init__(self, vendor, abort_url, vendor_tx_code, transaction_id, security_key, tx_auth_no):
        if abort_url:
            url = abort_url
        else:
            url = URL.TEST.ABORT if settings.DEBUG or settings.SHOP_TEST_MODE else URL.LIVE.ABORT
        super(SagepayAbort, self).__init__(url, 'ABORT', vendor, vendor_tx_code, transaction_id, security_key, tx_auth_no)
