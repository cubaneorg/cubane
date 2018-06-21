# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404
from cubane.tests.base import CubaneTestCase
from cubane.cms.views import fake_request
from cubane.cms.api import *
from mock import patch


class CmsApiViewTestCase(CubaneTestCase):
    def test_cms_api_view_publish_returns_dict(self):
        view = CmsApiView()
        request = fake_request(path='/')
        response = view.publish(request)
        self.assertIsInstance(response, dict)
        cms = get_cms()
        cms.invalidate()


    @patch('cubane.cms.views.CMS.publish')
    def test_cms_api_view_publish_should_raise_value_error_on_http404(self, publish):
        publish.side_effect = Http404
        view = CmsApiView()
        request = fake_request(path='/')
        with self.assertRaises(ValueError):
            response = view.publish(request)