# coding=UTF-8
from __future__ import unicode_literals
from django.test.utils import override_settings
from django.test.client import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.default_views import *


class DefaultViewsTestCaseBase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(DefaultViewsTestCaseBase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')


class DefaultViewsCustom404TestCase(DefaultViewsTestCaseBase):
    def test_should_return_404_page_processed_by_cms_if_installed(self):
        response = custom404(self.request)
        self.assertEqual(404, response.status_code)
        self.assertEqual('', response.content)


    @override_settings(INSTALLED_APPS=[])
    def test_should_return_empty_responsewith_404_status_code_if_cms_is_not_installed(self):
        response = custom404(self.request)
        self.assertEqual(404, response.status_code)
        self.assertEqual('', response.content)


class DefaultViewsCustom500TestCase(DefaultViewsTestCaseBase):
    def test_should_render_default_500_template(self):
        response = custom500(self.request)
        self.assertEqual(500, response.status_code)
        self.assertIn('Oops, something went wrong', response.content)