# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.contrib.auth.models import User, AnonymousUser
from django.test import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.backend.accounts.forms import AccountForm, ChangePasswordForm


@CubaneTestCase.complex()
class BackendAccountsFormTestCase(CubaneTestCase):
    def setUp(self):
        self.user = User(username='admin')
        self.user.email = 'admin@cubane.org'
        self.user.set_password('password')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        self.factory = RequestFactory()
        self.request = self.factory.get('/admin/accounts/create/')
        self.request.user = self.user


    def tearDown(self):
        self.user.delete()


    def test_superuser_should_see_superuser_field(self):
        form = AccountForm()
        form.configure(self.request, False, None)
        self.assertIsInstance(form.fields.get('is_superuser'), forms.BooleanField)


    def test_ordinary_user_should_NOT_see_superuser_field(self):
        self.request.user = AnonymousUser()
        form = AccountForm()
        form.configure(self.request, False, None)
        self.assertIsNone(form.fields.get('is_superuser'))


    def test_initial_password_available_for_create(self):
        form = AccountForm()
        form.configure(self.request, False, None)
        self.assertIsInstance(form.fields.get('initial_password'), forms.CharField)
        self.assertIsInstance(form.fields.get('initial_password_confirm'), forms.CharField)


    def test_initial_password_NOT_available_for_edit(self):
        form = AccountForm()
        form.configure(self.request, True, self.user)
        self.assertIsNone(form.fields.get('initial_password'))
        self.assertIsNone(form.fields.get('initial_password_confirm'))


    def test_username_should_be_forced_lowercase(self):
        form = AccountForm({
            'username': 'Test',
            'initial_password': 'password',
            'initial_password_confirm': 'password'
        })
        form.configure(self.request, False, None)
        self.assertTrue(form.is_valid())
        self.assertEqual('test', form.cleaned_data.get('username'))


    def test_username_already_exists(self):
        form = AccountForm({
            'username': 'admin',
            'initial_password': 'password',
            'initial_password_confirm': 'password'
        })
        form.configure(self.request, False, None)
        self.assertFalse(form.is_valid())
        self.assertEqual({'username': ['A user with that username already exists.']}, form.errors)


    def test_email_already_exists(self):
        form = AccountForm({
            'username': 'foo',
            'email': 'admin@cubane.org',
            'initial_password': 'password',
            'initial_password_confirm': 'password'
        })
        form.configure(self.request, False, None)
        self.assertFalse(form.is_valid())
        self.assertEqual({'email': ['A user with that email address already exists.']}, form.errors)


    def test_password_do_not_match(self):
        form = AccountForm({
            'username': 'test',
            'initial_password': 'password',
            'initial_password_confirm': 'does-not-match'
        })
        form.configure(self.request, False, None)
        self.assertFalse(form.is_valid())
        self.assertEqual({'initial_password_confirm': ['Password Confirmation does not match Password.']}, form.errors)



class BackendChangePasswordFormTestCase(CubaneTestCase):
    def test_should_be_valid_if_passwords_match(self):
        form = ChangePasswordForm({
            'password': 'password',
            'password_confirm': 'password'
        })
        self.assertTrue(form.is_valid())


    def test_should_fail_if_passwords_do_not_match(self):
        form = ChangePasswordForm({
            'password': 'password',
            'password_confirm': 'does-not-match'
        })
        self.assertFalse(form.is_valid())
        self.assertEqual({'password_confirm': [u'Password Confirmation does not match Password.']}, form.errors)

