# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.auth import generate_random_pw, DEFAULT_PASSWORD_CHARACTERS
from cubane.lib.auth import new_uuid2id, uuid2id, id2uuid, UUID_STR_LENGTH
import uuid


class LibAuthGenerateRandomPasswordTestCase(CubaneTestCase):
    """
    cubane.lib.auth.generate_random_pw()
    """
    def test_generate_random_pw_should_respect_length(self):
        for i in range(0, 32):
            self.assertEqual(len(generate_random_pw(length=i)), i)


    def test_generate_random_pw_should_respect_charset(self):
        chars = ['1', '2', '3']
        pw = generate_random_pw(8, chars)
        self.assert_password(pw, 8, chars)


    def test_generate_random_pw_with_empty_chars_should_use_default_chars(self):
        pw = generate_random_pw(8, chars=[])
        self.assert_password(pw, 8, DEFAULT_PASSWORD_CHARACTERS)


    def assert_password(self, pw, length, chars):
        self.assertEqual(len(pw), 8)
        for ch in pw:
            self.assertIn(ch, chars)


class LibAuthUUIDTestCase(CubaneTestCase):
    """
    cubane.lib.auth.new_uuid2id()
    cubane.lib.auth.uuid2id()
    cubane.lib.auth.id2uuid()
    """
    def test_new_uuid2id_should_return_id_with_22_characters(self):
        self.assertEqual(len(new_uuid2id()), UUID_STR_LENGTH)


    def test_convert_uuid_to_string_and_back(self):
        _uuid = unicode(uuid.uuid4())
        _id = uuid2id(_uuid)
        _uuid_from_id = id2uuid(_id)
        self.assertEqual(_uuid, _uuid_from_id)
