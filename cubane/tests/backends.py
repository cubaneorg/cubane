# coding=UTF-8
from __future__ import unicode_literals
from django.contrib.auth.models import User
from cubane.tests.base import CubaneTestCase
from cubane.backends import EmailAuthBackend


class EmailAuthBackendTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(EmailAuthBackendTestCase, cls).setUpClass()
        cls.user = User.objects.create_user('foo', 'foo@bar.com', 'password')


    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        super(EmailAuthBackendTestCase, cls).tearDownClass()


    def test_should_fail_with_matching_username_but_not_email(self):
        backend = EmailAuthBackend()
        self.assertIsNone(backend.authenticate('foo', 'username'))


    def test_should_fail_with_email_mismatch(self):
        backend = EmailAuthBackend()
        self.assertIsNone(backend.authenticate('foo-does-not-match@bar.com', 'password'))


    def test_should_fail_with_password_mismatch(self):
        backend = EmailAuthBackend()
        self.assertIsNone(backend.authenticate('foo@bar.com', 'does-not-match'))


    def test_should_auth_user_by_email_with_correct_password(self):
        backend = EmailAuthBackend()
        auth_user = backend.authenticate('foo@bar.com', 'password')
        self.assertIsNotNone(auth_user)
        self.assertEqual(self.user.pk, auth_user.pk)


    def test_get_user_with_mismatching_pk_should_return_none(self):
        backend = EmailAuthBackend()
        self.assertIsNone(backend.get_user(0))


    def test_get_user_with_matching_pk_should_return_user(self):
        backend = EmailAuthBackend()
        self.assertEqual(self.user.pk, backend.get_user(self.user.pk).pk)