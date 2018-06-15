# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.conversion import inch_to_cm
from decimal import Decimal


class LibConversionInchToCmTestCase(CubaneTestCase):
    def test_should_convert_inch_to_cm(self):
        self.assertEqual(5.08, inch_to_cm(2.0))
        self.assertEqual(0, inch_to_cm(0))
        self.assertEqual(-7.62, inch_to_cm(-3))


    def test_should_convert_inch_to_cm_with_decimal_type(self):
        self.assertEqual(Decimal('5.08'), inch_to_cm(Decimal('2.0')))
        self.assertEqual(Decimal('0'), inch_to_cm(Decimal('0')))
        self.assertEqual(Decimal('-7.62'), inch_to_cm(Decimal('-3')))