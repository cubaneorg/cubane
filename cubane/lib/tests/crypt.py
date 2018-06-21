# coding=UTF-8
from __future__ import unicode_literals
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.crypt import *


@override_settings(CRYPT_KEY='secret')
class LibCryptTestCaseBase(CubaneTestCase):
    pass


class LibCryptEncryptTestCase(LibCryptTestCaseBase):
    def test_should_encrypt_plain_text(self):
        self.assertEqual('yZz3daPOYe0=', encrypt('alice'))


    def test_should_encrypt_empty_text(self):
        self.assertEqual('kNDpPuwSat8=', encrypt(''))


    def test_should_encrypt_none(self):
        self.assertEqual('xH+1oYR0+xs=', encrypt(None))


    def test_should_encrypt_dict(self):
        self.assertEqual('lkHsEvFU9Dk3H3euds5+4A==', encrypt({'foo': 'bar'}))


class LibCryptDecryptTestCase(LibCryptTestCaseBase):
    def test_should_decrypt_encrypted_plain_text(self):
        self._assertCrypt('alice')


    def test_should_decrypt_empty_text(self):
        self._assertCrypt('')


    def test_should_decrypt_none(self):
        self._assertCrypt(None)


    def test_should_decrypt_dict(self):
        self._assertCrypt({'foo': 'bar'})


    def _assertCrypt(self, secret):
        self.assertEqual(secret, decrypt(encrypt(secret)))