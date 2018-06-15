# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Group
from cubane.lib.url import get_absolute_url
from cubane.lib.num import base36encode
from cubane.lib.mail import cubane_send_shop_mail
from cubane.lib.password import get_pronounceable_password
from cubane.ishop import get_order_model
from cubane.ishop.models import Voucher
import datetime
import random
import decimal
import hashlib


class IShopClientContext(object):
    def __init__(self, request):
        self._request = request


    @property
    def request(self):
        return self._request


    def get_accounts(self):
        """
        Return a list of all accounts.
        """
        return list(User.objects.order_by('username'))


    def get_account(self, account_id):
        """
        Return the account based on given account id.
        """
        try:
            return User.objects.get(pk=account_id)
        except User.DoesNotExist:
            return None


    def create_account(self, username, password, email, groups, first_name = '', last_name = ''):
        """
        Create and returns a new user account.
        """
        user = User.objects.create(username=username, email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        user.is_staff = True
        user.save()

        # add groups
        if not isinstance(groups, list): groups = [groups]
        for g in groups:
            try:
                grp = Group.objects.get(name=g)
                user.groups.add(grp)
            except Group.DoesNotExist:
                print "Unknown group %s." % g

        return user


    def password_forgotten(self, request, email):
        """
        Generate a new password for the given user and send the new password
        by email.
        """
        try:
            user = User.objects.get(email=email.lower().strip())
            password_plaintext = get_pronounceable_password()
            user.set_password(password_plaintext)
            user.save()

            from cubane.cms.views import get_cms
            cms = get_cms()
            cubane_send_shop_mail(
                request,
                email,
                '%s | New Password Request' % cms.settings.name,
                {
                    'password_reset': True,
                    'customer': user,
                    'password_plaintext': password_plaintext,
                    'login_url': get_absolute_url('shop.account.login', https=True)
                }
            )

            return True
        except User.DoesNotExist:
            return False


    def get_random(self):
        """
        Return random number generator.
        """
        if hasattr(random, 'SystemRandom'):
            return random.SystemRandom()
        else:
            return random.Random()


    def generate_secret_order_id(self, order):
        """
        Generate a unique secret order id which can be used within urls to point
        to order information on the internet without user authentification.
        """
        rnd = self.get_random()
        r = ''.join([unicode(rnd.randint(0, 9)) for i in range(0, 30)])
        s = '%s-%s-%s' % (order.id, r, settings.SECRET_KEY)
        return hashlib.sha224(s).hexdigest()


    def generate_numeric_order_id(self, order):
        """
        Generate unique order id based on year, month and primary key.
        """
        if order.id != None:
            oid = order.id
        else:
            rnd = self.get_random()
            oid = rnd.randint(0, 99999)

        date = datetime.date.today()

        return '%i-%02i-%02i' % (
            date.year, date.month, oid
        )


    def generate_seq_order_id(self, order):
        """
        Generate unique order id based on what looks like a sequential number.
        """
        rnd = self.get_random()
        n = get_order_model().objects.all().count()
        oid = rnd.randint(1234, n + (2 * 1234))
        return '%d' % oid


    def generate_alpha_order_id(self, order):
        """
        Generate a unique order id which can be used to refer to an order
        within an email or over the phone.
        This must be as short as possible and is base 36 encoded.
        """
        rnd = self.get_random()
        d = decimal.Decimal('%d%s' % (0 if order.id == None else order.id, ''.join([unicode(rnd.randint(0, 9)) for i in range(0, 4)])))
        return base36encode(d)


    def generate_order_id(self, order):
        """
        Generate a unique order id.
        """
        order_model = get_order_model()
        found = False
        i = 0
        while not found:
            # generate random ref. number for the given order
            if self._request.settings.order_id == 'numeric':
                order_id = self.generate_numeric_order_id(order)
            elif self._request.settings.order_id == 'seq':
                order_id = self.generate_seq_order_id(order)
            else:
                order_id = self.generate_alpha_order_id(order)

            # add prefix/suffix
            if self._request.settings.order_id_prefix:
                order_id = '%s%s' % (self._request.settings.order_id_prefix, order_id)
            if self._request.settings.order_id_suffix:
                order_id = '%s%s' % (order_id, self._request.settings.order_id_suffix)

            # make sure it is unqiue
            found = (order_model.objects.filter(order_id=order_id).count() == 0)

            i += 1
            if i > 100:
                raise UserWarning('Fatal: Unable to find another unique order id after %d iterations!' % i)
        return order_id


    def generate_voucher_code(self):
        """
        Generate a unique voucher code.
        """
        found = False
        i = 0
        while not found:
            rnd = random.Random()
            d = decimal.Decimal(''.join([unicode(rnd.randint(0, 9)) for i in range(0, 8)]))
            code = base36encode(d)

            found = (Voucher.objects.filter(code=code).count() == 0)

            i += 1
            if i > 10:
                raise IntegrityError('Fatal: Unable to find another unique voucher code after %d iterations!' % i)
        return code
