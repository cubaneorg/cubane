# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.http import Http404
from django.contrib.auth.models import User
from cubane.lib.url import make_absolute_url
from cubane.tests.base import CubaneTestCase
from cubane.backend.accounts.models import ProxyUser
from cubane.backend.accounts.forms import ChangePasswordForm
from cubane.backend.accounts.views import AccountView


@CubaneTestCase.complex()
class BackendAccountsEditTestCase(CubaneTestCase):
    def test_create_account_should_set_initial_password(self):
        view = AccountView()
        admin = User(username='admin', is_staff=True, is_superuser=True)

        context = self.run_view_handler(view, admin, 'create_edit', 'post', '/admin/accounts/create/', {
            'username': 'test',
            'first_name': 'Foo',
            'last_name': 'Bar',
            'email': 'foo@bar.com',
            'is_active': True,
            'initial_password': 'password',
            'initial_password_confirm': 'password'
        })

        self.assertIsRedirect(context, '/admin/accounts/')
        user = User.objects.get(username='test')
        self.assertEqual('Foo', user.first_name)
        self.assertEqual('Bar', user.last_name)
        self.assertEqual('foo@bar.com', user.email)
        self.assertUserPassword(user, 'password')
        user.delete()


@CubaneTestCase.complex()
class BackendAccountsChangePasswordTestCase(CubaneTestCase):
    def test_change_password_view_should_load_given_account(self):
        view = AccountView()
        admin = User(username='admin', is_staff=True, is_superuser=True)
        user = User(username='test', is_staff=True)
        user.set_password('password')
        user.save()

        context = self.run_view_handler(view, admin, 'change_password', 'get', '/admin/accounts/change-password/', {
            'pk': user.pk
        })
        self.assertIsInstance(context.get('form'), ChangePasswordForm)
        self.assertEqual(user.pk, context.get('account').pk)
        self.assertUserPassword(user, 'password')
        user.delete()


    def test_change_password_view_should_change_password(self):
        view = AccountView()
        admin = User(username='admin', is_staff=True, is_superuser=True)
        user = User(username='test', is_staff=True)
        user.set_password('password')
        user.save()

        context = self.run_view_handler(view, admin, 'change_password', 'post', '/admin/accounts/change-password/?pk=%s' % user.id, {
            'password':         'new-password',
            'password_confirm': 'new-password'
        })
        self.assertIsRedirect(context, '/admin/accounts/')
        self.assertUserPassword(user, 'new-password')
        user.delete()


    def test_staff_account_cannot_change_superuser(self):
        view = AccountView()
        admin = User(username='admin', is_staff=True)
        user = User(username='test', is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()

        with self.assertRaisesRegexp(Http404, 'Unknown primary key \d+ for proxyuser'):
            context = self.run_view_handler(view, admin, 'change_password', 'post', '/admin/accounts/change-password/?pk=%s' % user.id, {
                'password':         'new-password',
                'password_confirm': 'new-password'
            })

        # password did not change!
        self.assertUserPassword(user, 'password')
        user.delete()