# coding=UTF-8
from __future__ import unicode_literals
from django.utils.safestring import SafeBytes
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.barcode_tags import barcode_image


class BarcodeTagsBarcodeImageTestCase(CubaneTestCase):
    """
    cubane.templatetags.barcode_tags.barcode_image()
    """
    def test_should_render_barcode_as_svg_image(self):
        markup = barcode_image('isbn', '978-0-597-80948-5')
        self.assertIn('<svg', markup)
        self.assertIsInstance(markup, SafeBytes)