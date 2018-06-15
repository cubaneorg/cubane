# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.num import base36encode


class LibNumBase36EncodeTestCase(CubaneTestCase):
    def test_should_zero_with_first_letter_of_alphabet(self):
        self.assertEqual('2', base36encode(0))


    def test_should_encode_base36(self):
        self.assertEqual('5V', base36encode(123))


    def test_should_respect_sign(self):
        self.assertEqual('-5V', base36encode(-123))