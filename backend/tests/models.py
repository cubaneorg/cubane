# coding=UTF-8
from __future__ import unicode_literals
from django.db import IntegrityError
from django.http import Http404
from django.test import RequestFactory
from django.contrib.auth.models import User
from cubane.cms.views import get_cms
from cubane.tests.base import CubaneTestCase
from cubane.backend.models import UserToken
from cubane.backend.models import UserProfile
import datetime


class BackendModelsUserProfileTestCase(CubaneTestCase):
    def test_deleting_user_should_delete_user_profile(self):
        user = User.objects.create_user('admin', password='password')
        profile = UserProfile.objects.create(user=user)

        try:
            user.delete()

            self.assertEqual(0, UserProfile.objects.filter(user__username='admin').count())
            self.assertEqual(0, User.objects.filter(username='admin').count())
        finally:
            UserProfile.objects.filter(user__username='admin').delete()
            User.objects.filter(username='admin').delete()


class BackendModelsUserTokenCreateTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(BackendModelsUserTokenCreateTestCase, cls).setUpClass()
        cls.user = User.objects.create_user('foo', 'foo@bar.com', 'password')


    @classmethod
    def tearDownClass(cls):
        [token.delete() for token in UserToken.objects.all()]
        cls.user.delete()
        super(BackendModelsUserTokenCreateTestCase, cls).tearDownClass()


    def test_should_create_user_token(self):
        now = datetime.datetime.now()
        token = UserToken.create(self.user, 'usage')
        self.assertEqual(token.user.pk, self.user.pk)
        self.assertEqual(token.usage, 'usage')
        self.assertIsNotNone(token.hashcode)
        self.assertTrue(token.created_on >= now)


    def test_should_raise_exception_if_user_is_none(self):
        with self.assertRaisesRegexp(ValueError, 'User cannot be none'):
            UserToken.create(None, 'usage')


    def test_should_raise_exception_if_usage_is_none(self):
        with self.assertRaisesRegexp(ValueError, 'Usage cannot be none or empty'):
            UserToken.create(self.user, None)


class BackendModelsUserTokenGenerateHashcodeTestCase(CubaneTestCase):
    MAX_HASHCODES = 20


    def test_should_generate_unique_hashcode(self):
        hashcodes = []
        for i in range(0, self.MAX_HASHCODES):
            hashcode = UserToken.generate_hashcode()
            if hashcode not in hashcodes:
                hashcodes.append(hashcode)

        self.assertEqual(self.MAX_HASHCODES, len(hashcodes))


class BackendModelsUserTokenGetExpiredTestCase(CubaneTestCase):
    def test_should_return_current_minus_expiry_delta(self):
        expected = datetime.datetime.now() - datetime.timedelta(hours=UserToken.EXPIRES_HOURS)
        actual = UserToken.get_expired()
        delta = actual - expected
        self.assertTrue(delta.seconds < 1)


class BackendModelsUserTokenGetOr404TestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(BackendModelsUserTokenGetOr404TestCase, cls).setUpClass()
        cls.user = User.objects.create_user('foo', 'foo@bar.com', 'password')
        cls.token = UserToken.create(cls.user, 'usage')

    @classmethod
    def tearDownClass(cls):
        cls.token.delete()
        cls.user.delete()
        super(BackendModelsUserTokenGetOr404TestCase, cls).tearDownClass()


    def test_should_return_valid_user_token_by_hashcode_and_usage(self):
        token = UserToken.get_or_404(self.token.hashcode, self.token.usage)
        self.assertEqual(self.token.pk, token.pk)


    def test_should_raise_404_on_hashcode_mismatch(self):
        with self.assertRaises(Http404):
            UserToken.get_or_404('does-not-match', self.token.usage)


    def test_should_raise_404_on_usage_mismatch(self):
        with self.assertRaises(Http404):
            UserToken.get_or_404(self.token.hashcode, 'does-not-match')


    def test_should_raise_404_on_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        with self.assertRaises(Http404):
            UserToken.get_or_404(self.token.hashcode, self.token.usage)

        self.user.is_active = True
        self.user.save()


    def test_should_raise_404_on_expired_token(self):
        created_on = self.token.created_on
        self.token.created_on = \
            datetime.datetime.now() - \
            datetime.timedelta(hours=UserToken.EXPIRES_HOURS) - \
            datetime.timedelta(minutes=1)
        self.token.save()

        with self.assertRaises(Http404):
            UserToken.get_or_404(self.token.hashcode, self.token.usage)

        self.token.created_on = created_on
        self.token.save()


class BackendModelsUserTokenCleanupTestCase(CubaneTestCase):
    def test_should_keep_valid_tokens(self):
        user = User.objects.create_user('foo', 'foo@bar.com', 'password')
        token = UserToken.create(user, 'usage')

        UserToken.cleanup()

        self.assertEqual(1, UserToken.objects.count())
        token.delete()
        user.delete()


    def test_should_delete_token_with_inactive_users(self):
        user = User.objects.create_user('foo', 'foo@bar.com', 'password')
        user.is_active = False
        user.save()
        token = UserToken.create(user, 'usage')

        UserToken.cleanup()

        self.assertEqual(0, UserToken.objects.count())
        user.delete()


    def test_should_delete_expired_tokens(self):
        user = User.objects.create_user('foo', 'foo@bar.com', 'password')
        token = UserToken.create(user, 'usage')
        token.created_on = \
            datetime.datetime.now() - \
            datetime.timedelta(hours=UserToken.EXPIRES_HOURS) - \
            datetime.timedelta(minutes=1)
        token.save()

        UserToken.cleanup()

        self.assertEqual(0, UserToken.objects.count())
        user.delete()


@CubaneTestCase.complex()
class BackendModelsUserTokenSendEmailTestCase(CubaneTestCase):
    def test_should_send_email_to_token_user_with_link(self):
        cms = get_cms()
        cms.settings.name = 'Test'
        cms.settings.save()

        user = User.objects.create_user('foo', 'foo@bar.com', 'password')
        token = UserToken.create(user, 'usage')
        factory = RequestFactory()
        request = factory.post('/')
        template = 'cubane/backend/mail/password_forgotten.html'
        url = 'http://www.foo.com/'

        token.send_email(request, template, url, 'Foo', 'Bar', reason='Reason')
        m = self.get_latest_email()
        body = m.message().as_string()

        self.assertTrue('foo@bar.com' in m.to, 'incorrect to-address: %s' % m.to)
        self.assertTrue('Foo' in m.subject, 'incorrect subject line: %s' % m.subject)
        self.assertTrue('Bar' in body, 'message not in body')
        self.assertTrue('Reason' in body, 'reason not in body')
        self.assertTrue(url in body, 'url link not in body')