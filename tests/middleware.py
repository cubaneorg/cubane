# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponsePermanentRedirect
from cubane.middleware import SSLResponseRedirectMiddleware


class MiddlewareSSLResponseRedirectMiddlewareTestCase(CubaneTestCase):
    """
    cubane.middleware.SSLResponseRedirectMiddleware.process_response()
    """
    def setUp(self):
        self.middleware = SSLResponseRedirectMiddleware()
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.META['HTTP_HOST'] = 'www.innershed.com'


    @override_settings(SSL=True)
    def test_should_rewrite_response_location_with_domain_name_and_https(self):
        response = self.middleware.process_response(self.request, HttpResponseRedirect('/foo/'))
        self.assertEqual('https://www.innershed.com/foo/', response['Location'])


    @override_settings(SSL=True, APPEND_SLASH=True)
    def test_should_rewrite_response_location_with_appended_slash(self):
        response = self.middleware.process_response(self.request, HttpResponseRedirect('/foo'))
        self.assertEqual('https://www.innershed.com/foo/', response['Location'])


    @override_settings(SSL=True)
    def test_should_rewrite_response_location_with_domain_name_and_https_for_permanent_redirect_response(self):
        response = self.middleware.process_response(self.request, HttpResponsePermanentRedirect('/foo/'))
        self.assertEqual('https://www.innershed.com/foo/', response['Location'])


    @override_settings(SSL=False)
    def test_should_not_rewrite_response_location_if_ssl_is_not_turned_on(self):
        response = self.middleware.process_response(self.request, HttpResponseRedirect('/foo'))
        self.assertEqual('/foo', response['Location'])


    @override_settings(SSL=True)
    def test_should_not_rewrite_response_location_if_response_is_not_redirect(self):
        response = self.middleware.process_response(self.request, HttpResponse('<h1>Foo</h1>'))
        self.assertFalse('Location' in response)