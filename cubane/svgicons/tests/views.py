# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.http import Http404
from django.core.exceptions import PermissionDenied
from cubane.tests.base import CubaneTestCase
from cubane.svgicons.views import media_api_svgicons


class SvgIconsViewsMediaApiSvgiconsTestCase(CubaneTestCase):
    """
    cubane.svgicons.views.media_api_svgicons()
    """
    @classmethod
    def setUpClass(cls):
        super(SvgIconsViewsMediaApiSvgiconsTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')


    @override_settings(DEBUG=False)
    def test_should_raise_permission_denied_in_production_mode(self):
        with self.assertRaisesRegexp(PermissionDenied, 'SVG icon sets via the media api are only available in DEBUG mode.'):
            media_api_svgicons(self.request, 'frontend', 'email')


    @override_settings(DEBUG=True)
    def test_should_return_svg_icon_set_containing_single_icon(self):
        response = media_api_svgicons(self.request, 'frontend', 'email')
        self.assertEqual(200, response.status_code)
        self.assertIn('<symbol id="svgicon-email"', response.content)
        self.assertNotIn('<symbol id="svgicon-phone"', response.content)


    @override_settings(DEBUG=True)
    def test_should_return_full_svg_icon_set_containing_all_icons_if_icon_name_is_not_given(self):
        response = media_api_svgicons(self.request, 'frontend')
        self.assertEqual(200, response.status_code)
        self.assertIn('<symbol id="svgicon-email"', response.content)
        self.assertIn('<symbol id="svgicon-phone"', response.content)


    @override_settings(DEBUG=True)
    def test_should_raise_404_if_no_icons_found(self):
        with self.assertRaisesRegexp(Http404, 'No icons found for the given target and/or icon name.'):
            media_api_svgicons(self.request, 'does_not_exist')