# coding=UTF-8
from __future__ import unicode_literals
from django.test import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.fonts.backends import (
    FontDescriptor,
    FontBackendBase,
    GoogleFontsBackend
)
from requests.exceptions import ConnectionError
from datetime import datetime
from mock import patch
import re


class FontsFontDescriptorTestCase(CubaneTestCase):
    """
    cubane.fonts.backends.FontDescriptor()
    """
    def test_should_create_font_descriptor(self):
        d = FontDescriptor(
            'font_name',
            'family',
            'category',
            'variants',
            'v13',
            'mtime'
        )
        self.assertEqual('font_name', d.font_name)
        self.assertEqual('family', d.family)
        self.assertEqual('category', d.category)
        self.assertEqual('variants', d.variants)
        self.assertEqual('v13', d.version)
        self.assertEqual('mtime', d.mtime)


class FontsFontBackendBaseTestCase(CubaneTestCase):
    """
    cubane.fonts.backends.FontBackendBase()
    """
    def test_should_raise_error_if_not_overridden(self):
        with self.assertRaisesRegexp(NotImplementedError, 'Override get_font()'):
            FontBackendBase().get_font('foo')


@CubaneTestCase.complex()
class FontsGoogleFontsBackendGetFontTestCase(CubaneTestCase):
    """
    cubane.fonts.backends.GoogleFontsBackend.get_font()
    """
    def test_should_return_none_if_font_does_not_exist(self):
        backend = GoogleFontsBackend()
        self.assertIsNone(backend.get_font('DoesNotExist'))


    def test_should_return_font_descriptor_for_known_font(self):
        backend = GoogleFontsBackend()
        d = backend.get_font('Abel')
        self.assertEqual('Abel', d.font_name)
        self.assertEqual('Abel', d.family)
        self.assertEqual('sans-serif', d.category)
        self.assertEqual('v8', d.version)
        self.assertEqual([{
            'id': 'regular',
            'fontFamily': 'Abel',
            'fontStyle': 'normal',
            'fontWeight': '400',
            'local': ['Abel Regular', 'Abel-Regular'],
            'svg': 'https://fonts.gstatic.com/l/font?kit=MwQ5bhbm2POE2V9BOg&skey=bf47258294911e6d&v=v8#Abel',
            'eot': 'https://fonts.gstatic.com/s/abel/v8/MwQ5bhbm2POE2V9BOQ.eot',
            'ttf': 'https://fonts.gstatic.com/s/abel/v8/MwQ5bhbm2POE2V9BOA.ttf',
            'woff': 'https://fonts.gstatic.com/s/abel/v8/MwQ5bhbm2POE2V9BOw.woff',
            'woff2': 'https://fonts.gstatic.com/s/abel/v8/MwQ5bhbm2POE2V9BPQ.woff2',
        }], d.variants)
        self.assertEqual(datetime(2017, 10, 10), d.mtime)


    @patch('requests.get')
    @override_settings(DEBUG=False)
    def test_should_ignore_connection_error_in_production(self, get):
        get.side_effect = ConnectionError

        # simply cannot find fond, but will not raise exception
        backend = GoogleFontsBackend()
        self.assertIsNone(backend.get_font('Abel'))


    @patch('requests.get')
    @override_settings(DEBUG=True)
    def test_should_raise_connection_error_in_debug(self, get):
        get.side_effect = ConnectionError

        # will raise exception in debug
        backend = GoogleFontsBackend()
        with self.assertRaises(ConnectionError):
            backend.get_font('Abel')