from __future__ import unicode_literals
from django.test.utils import override_settings
from django.http.request import QueryDict
from cubane.tests.base import CubaneTestCase
from cubane.lib.request import request_int
from cubane.lib.request import request_bool
from cubane.lib.request import request_int_list


DATA = QueryDict(
    'number=17&' +
    'not_a_number=NotANumber&' +
    'bool=true&' +
    'bool_upper=True&' +
    'numbers=1&numbers=NotANumber&numbers=3'
)
DEFAULT = 99


class CubaneLibRequestIntTestCase(CubaneTestCase):
    """
    cubane.lib.resources.request_int()
    """
    def test_should_parse_int(self):
        self.assertEqual(request_int(DATA, 'number'), 17)


    def test_should_return_default_if_not_a_number(self):
        self.assertEqual(request_int(DATA, 'not_a_number', DEFAULT), DEFAULT)


    def test_should_return_default_if_key_does_not_exist(self):
        self.assertEqual(request_int(DATA, 'does_not_exist', DEFAULT), DEFAULT)


    def test_should_return_default_if_none(self):
        self.assertEqual(request_int(None, None, DEFAULT), DEFAULT)


class CubaneLibRequestBoolTestCase(CubaneTestCase):
    """
    cubane.lib.resources.request_bool()
    """
    def test_should_parse_true(self):
        self.assertTrue(request_bool(DATA, 'bool'))


    def test_should_parse_true_uppercase(self):
        self.assertTrue(request_bool(DATA, 'bool_upper'))


    def test_should_parse_not_true_as_false(self):
        self.assertFalse(request_bool(DATA, 'number'))


    def test_should_return_false_if_key_does_not_exist(self):
        self.assertFalse(request_bool(DATA, 'does_not_exist'))


    def test_should_return_false_if_none(self):
        self.assertFalse(request_bool(None, None))


class CubaneLibRequestIntListTestCase(CubaneTestCase):
    """
    cubane.lib.resources.request_int_list()
    """
    def test_should_parse_int_values_skipping_errors(self):
        self.assertEqual(request_int_list(DATA, 'numbers'), [1, 3])


    def test_should_return_empty_list_if_key_does_not_exist(self):
        self.assertEqual(request_int_list(DATA, 'does_not_exist'), [])


    def test_should_return_empty_list_if_none(self):
        self.assertEqual(request_int_list(None, None), [])