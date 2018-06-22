# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test import Client
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.cache import SessionStore
from cubane.tests.base import CubaneTestCase
from cubane.context_processors import config
from cubane.context_processors import backend


class ContextProcessorsDialogTestCase(CubaneTestCase):
    def setUp(self):
        self.request = RequestFactory()

    def test_config(self):
        c = config(self.request.get('/'))
        self.assertEqual('testapp.cubane.innershed.com', c.get('DOMAIN_NAME'))
        self.assertFalse(c.get('DEBUG'))
        self.assertEqual('/static/', c.get('STATIC_URL'))


    @override_settings(INSTALLED_APPS=[])
    def test_backend_should_be_empty_if_backend_not_installed(self):
        self.assertEqual({}, backend(self.request.get('/')))


    def test_backend_without_args(self):
        c = backend(self.request.get('/'))
        self.assertFalse(c.get('is_browse_dialog'))
        self.assertFalse(c.get('is_create_dialog'))
        self.assertFalse(c.get('is_edit_dialog'))
        self.assertFalse(c.get('is_dialog'))
        self.assertTrue(c.get('cms_publish'))


    def test_backend_with_browse_args(self):
        c = backend(self.request.get('/?browse=true'))
        self.assertTrue(c.get('is_browse_dialog'))
        self.assertFalse(c.get('is_create_dialog'))
        self.assertFalse(c.get('is_edit_dialog'))
        self.assertTrue(c.get('is_dialog'))


    def test_backend_with_create_args(self):
        c = backend(self.request.get('/?create=true'))
        self.assertFalse(c.get('is_browse_dialog'))
        self.assertTrue(c.get('is_create_dialog'))
        self.assertFalse(c.get('is_edit_dialog'))
        self.assertTrue(c.get('is_dialog'))


    def test_backend_with_edit_args(self):
        c = backend(self.request.get('/?edit=true'))
        self.assertFalse(c.get('is_browse_dialog'))
        self.assertFalse(c.get('is_create_dialog'))
        self.assertTrue(c.get('is_edit_dialog'))
        self.assertTrue(c.get('is_dialog'))


class ContextProcessorsBackendTestCase(CubaneTestCase):
    def setUp(self):
        self.factory = RequestFactory()


    def test_backend_should_include_theme(self):
        c = backend(self.factory.get('/admin/'))
        self.assertEqual(settings.BACKEND_THEME, c.get('THEME'))


    def test_backend_without_backend_view(self):
        c = backend(self.factory.get('/admin/'))
        self.assertIsNone(c.get('BACKEND'))


    def test_backend_should_include_backend_view_if_present(self):
        request = self.factory.get('/admin/')
        request.backend = 'BackendView'
        c = backend(request)
        self.assertEqual('BackendView', c.get('BACKEND'))


    def test_backend_should_contain_no_error_messages_if_no_errors_have_been_raised(self):
        request = self.factory.get('/admin/')
        c = backend(request)
        self.assertEqual([], c.get('error_messages'))


    def test_backend_should_contain_error_messages_if_errors_have_been_raised(self):
        request = self.factory.get('/admin/')
        request.session = SessionStore()
        request._messages = FallbackStorage(request)

        # add some messages to filter. Add some non-error messages as well
        messages.add_message(request, messages.SUCCESS, 'SUCCESS')
        messages.add_message(request, messages.INFO, 'INFO')
        messages.add_message(request, messages.ERROR, 'ERROR')

        c = backend(request)
        self.assertEqual(['ERROR'], [m.message for m in c.get('error_messages')])
