# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.args import list_of_list, list_of, clean_dict
from cubane.testapp.models import CustomPage


class LibArgsListOfListTestCase(CubaneTestCase):
    """
    cubane.lib.args.list_of_list()
    """
    def test_list_of_list_with_item_should_return_list_of_list(self):
        self.assert_list_of_list(list_of_list('a'))


    def test_list_of_list_with_list_should_return_list_of_list(self):
        self.assert_list_of_list(list_of_list(['a']))


    def test_list_of_list_with_empty_list_should_return_list_of_list(self):
        self.assert_empty_list(list_of_list([]))


    def assert_list_of_list(self, a):
        self.assertIsInstance(a, list, 'must be list')
        self.assertEqual(len(a), 1, 'outer list must contain 1 item')
        self.assertIsInstance(a[0], list, 'must be list of list')
        self.assertEqual(len(a[0]), 1, 'inner list must contain 1 item')
        self.assertEqual(a[0][0], 'a')


    def assert_empty_list(self, a):
        self.assertIsInstance(a, list, 'must be list')
        self.assertEqual(len(a), 0, 'must be empty list')


class LibArgsListOfTestCase(CubaneTestCase):
    """
    cubane.lib.args.list_of()
    """
    def test_with_none_should_return_empty_list(self):
        self.assertEqual([], list_of(None))


    def test_with_item_should_return_list_of_item(self):
        self.assert_list_of_item(list_of('a'))


    def test_with_list_should_return_list(self):
        self.assert_list_of_item(list_of(['a']))


    def test_with_queryset_should_return_list(self):
        self.assertIsInstance(list_of(CustomPage.objects.all()), list)


    def assert_list_of_item(self, a):
        self.assertIsInstance(a, list, 'must be list')
        self.assertEqual(len(a), 1, 'list must contain 1 item')
        self.assertEqual(a[0], 'a')


class LibArgsCleanDictTestCase(CubaneTestCase):
    """
    cubane.lib.args.clean_dict()
    """
    def test_should_return_empty_dict_for_none(self):
        self.assertEqual({}, clean_dict(None))


    def test_should_return_new_dict(self):
        a = {'foo': 'bar'}
        b = clean_dict(a)
        self.assertFalse(a is b)


    def test_should_remove_keys_with_none_value(self):
        self.assertEqual(
            {'foo': 'bar'},
            clean_dict({'foo': 'bar', 'bar': None})
        )