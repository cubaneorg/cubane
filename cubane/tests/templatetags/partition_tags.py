# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.partition_tags import (
    rows,
    rows_distributed,
    columns
)


class PartitionTagsRowsTestCase(CubaneTestCase):
    """
    cubane.templatetags.partition_tags.rows()
    """
    def test_should_return_equally_sized_rows(self):
        m_rows = rows([1, 2, 3, 4], 2)
        self.assertEqual([[1, 2], [3, 4]], m_rows)


    def test_should_return_even_empty_rows(self):
        m_rows = rows([1, 2], 3)
        self.assertEqual([[1], [2], []], m_rows)


    def test_should_return_rows_from_not_list(self):
        my_rows = rows('test', 2)
        self.assertEqual([['t', 'e'], ['s', 't']], my_rows)


    def test_should_return_not_equally_sized_rows(self):
        my_rows = rows([1, 2, 3, 4, 5], 3)
        self.assertEqual([[1, 2], [3, 4], [5]], my_rows)


    def test_should_not_allow_zero_rows(self):
        my_rows = rows([], 0)
        self.assertEqual(my_rows, None)

        my_rows = rows([], '0')
        self.assertEqual(my_rows, None)


    def test_should_return_original_list_if_exception(self):
        my_rows = rows([1, 2, 3], 'test')
        self.assertEqual(my_rows, [[1, 2, 3]])

        my_rows = rows('test', 'test')
        self.assertEqual(['test'], my_rows)


class PartitionTagsRowsDistributedTestCase(CubaneTestCase):
    """
    cubane.templatetags.partition_tags.rows_distributed()
    """
    def test_should_return_original_list_if_exception(self):
        my_rows = rows_distributed([1, 2, 3], 'test')
        self.assertEqual(my_rows, [[1, 2, 3]])


    def test_should_not_allow_zero_rows(self):
        my_rows =  rows_distributed([], 0)
        self.assertEqual(my_rows, None)

        my_rows =  rows_distributed([], '0')
        self.assertEqual(my_rows, None)


    def test_should_return_equally_sized_rows(self):
        my_rows = rows_distributed(range(10), 5)

        self.assertEqual(my_rows, [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]])


    def test_should_return_distributed_rows(self):
        my_rows = rows_distributed(range(5), 2)

        self.assertEqual(my_rows, [[0, 1, 2], [3 ,4]])


    def test_should_filled_in_empty_rows(self):
        my_rows = rows_distributed([1], 2)

        self.assertEqual(my_rows, [[1], []])


class PartitionTagsColumnsTestCase(CubaneTestCase):
    """
    cubane.templategats.partition_tags.columns()
    """
    def test_should_not_allow_zero_columns(self):
        my_columns = columns([1, 2, 3], 0)
        self.assertEqual(my_columns, None)

        my_columns = columns([1, 2, 3], '0')
        self.assertEqual(my_columns, None)


    def test_should_return_original_list_if_exception(self):
        my_columns = columns([1, 2, 3], 'test')
        self.assertEqual(my_columns, [[1, 2, 3]])


    def test_should_return_columns_equally_sized(self):
        my_columns = columns([1, 2, 3, 4], 2)
        self.assertEqual(my_columns, [[1, 2], [3, 4]])


    def test_should_return_columns_not_equally_sized(self):
        my_columns = columns(range(7), 3)
        self.assertEqual(my_columns, [[0, 1, 2], [3, 4, 5], [6]])


    def test_should_not_present_empty_columns(self):
        my_columns = columns(range(4), 3)
        self.assertEqual(my_columns, [[0, 1, 2], [3]])