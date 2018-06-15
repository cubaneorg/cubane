# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.http import HttpResponse
from cubane.lib.http import wget
from cubane.lib.http import wpost
from cubane.lib.http import wget_json
import json


class LibHttpResponseTestCase(CubaneTestCase):
    """
    cubane.lib.http.HttpResponse
    """
    def test_should_initialise_with_data_and_response_code(self):
        r = HttpResponse('foo', code=201)
        self.assertEqual('foo', r.data)
        self.assertEqual(201, r.code)


    def test_unicode_should_return_data(self):
        r = HttpResponse('foo')
        self.assertEqual('foo', unicode(r))


@CubaneTestCase.complex()
class LibHttpWGetTestCase(CubaneTestCase):
    """
    cubane.lib.http.wget()
    """
    def test_wget_should_download_document(self):
        response = wget('http://httpbin.org/')
        self.assertEqual(response.code, 200)
        self.assertTrue('HTTP Request &amp; Response Service' in response.data)


    def test_wget_with_args(self):
        response = wget('http://httpbin.org/get', {
            'foo': 'bar'
        })
        j = json.loads(response.data)
        self.assertEqual(j.get('args').get('foo'), 'bar')


    def test_wget_404(self):
        response = wget('http://httpbin.org/404')
        self.assertEqual(response.code, 404)


@CubaneTestCase.complex()
class LibHttpWGetJsonTestCase(CubaneTestCase):
    """
    cubane.lib.http.wget_json()
    """
    def test_should_fail_if_no_json(self):
        self.assertRaises(ValueError, self._wget_non_json)


    def test_wget_json_404(self):
        response = wget_json('http://httpbin.org/404')
        self.assertEqual(len(response.keys()), 0)


    def test_should_return_json(self):
        json = wget_json('http://httpbin.org/get', {
            'foo': 'bar'
        })
        self.assertEqual(json.get('args').get('foo'), 'bar')


    def _wget_non_json(self):
        return wget_json('http://httpbin.org/')


@CubaneTestCase.complex()
class LibHttpWPostTestCase(CubaneTestCase):
    """
    cubane.lib.http.wpost()
    """
    def test_wpost_should_post_data(self):
        response = wpost('http://httpbin.org/post', {
            'foo': 'bar'
        })
        self.assertEqual(response.code, 200)
        j = json.loads(response.data)
        self.assertEqual(j.get('form').get('foo'), 'bar')


    def test_wpost_404(self):
        response = wpost('http://httpbin.org/404')
        self.assertEqual(response.code, 404)