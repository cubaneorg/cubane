# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.list_tags import (
    split,
    is_list,
    get
)


class ListTagsSplitTestCase(CubaneTestCase):
    """
    cubane.templatetags.list_tags.split()
    """
    def test_should_split_string(self):
        self.assertEqual(split('My|Test|String', '|'), ['My', 'Test', 'String'])


class ListTagsIsListTestCase(CubaneTestCase):
    """
    cubane.templatetags.list_tags.is_list()
    """
    def test_should_return_true_or_false(self):
        self.assertEqual(is_list([]), True)
        self.assertEqual(is_list(None), False)


class ListTagsGetTestCase(CubaneTestCase):
    """
    cubane.templatetags.list_tags.get()
    """
    def test_should_return_none_if_value_is_none(self):
        self.assertEqual(get(None, 1), None)


    def test_should_return_none_if_index_is_none(self):
        self.assertEqual(get([], None), None)


    def test_should_traverse_django_nested_attribute_notation(self):
        self.assertEqual(get({'a': {'b': 'foo'}}, 'a__b'), 'foo')


    def test_should_return_list_element(self):
        self.assertEqual(get(['a', 'b'], 1), 'b')
        self.assertEqual(get([], 0), '')


    def test_should_return_letter_from_string(self):
        self.assertEqual(get('string', 1), 't')
        self.assertEqual(get('string', '1'), '')


    def test_should_return_element_from_dict(self):
        self.assertEqual(get({'foo': 'bar'}, 'foo'), 'bar')
        self.assertEqual(get({}, 'foo'), '')


    def test_should_call_method_if_exists(self):
        self.assertEqual(get(' my string ', 'strip'), 'my string')


    def test_should_return_empty_if_method_doesnt_exist(self):
        self.assertEqual(get('my string', 'trim'), '')


    def test_should_return_repr_for_method_not_called(self):
        # missing args for find()
        self.assertIn('built-in method find of unicode object', unicode(get('my string', 'find')))