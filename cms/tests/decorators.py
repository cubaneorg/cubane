# coding=UTF-8
from __future__ import unicode_literals
from django.test.client import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.cms.decorators import cubane_cms_context


class CmsDecoratorsTestCase(CubaneTestCase):
    def test_should_run_decorated_func(self):
        @cubane_cms_context()
        def handler(request):
            return {'foo': 'bar'}

        factory = RequestFactory()
        request = factory.get('/')
        response = handler(request)

        self.assertEqual({}, response.get('images'))
        self.assertEqual([], response.get('slots'))
        self.assertFalse(response.get('cms_preview'))
        self.assertFalse(response.get('is_homepage'))