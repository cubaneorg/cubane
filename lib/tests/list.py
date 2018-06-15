# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.list import list_unify_in_order


class LibListUnifyInOrderTestCase(CubaneTestCase):
    """
    cubane.lib.list.list_unify_in_order()
    """
    def test_should_return_empty_list_for_empty_set_of_options(self):
        self.assertEqual([], list_unify_in_order([[], [], []]))


    def test_should_return_options_from_single_set(self):
        self.assertEqual(['s', 'm', 'l'], list_unify_in_order([['s', 'm', 'l']]))


    def test_should_return_combined_options_from_two_sets(self):
        self.assertEqual(['s', 'm', 'l'], list_unify_in_order([
            ['s', 'm'],
            ['s', 'm', 'l'],
        ]))


    def test_should_return_combined_options_from_four_sets(self):
        self.assertEqual(['s', 'm', 'l', 'xl', 'xxl'], list_unify_in_order([
            ['s', 'm'],
            ['s', 'm', 'l'],
            ['xl', 'xxl'],
            ['l', 'xl']
        ]))


    def test_should_combine_disconnected_sets(self):
        self.assertEqual(['s', 'm', 'xl', 'xxl'], list_unify_in_order([
            ['s', 'm'],
            ['xl', 'xxl'],
        ]))


    def test_should_combine_combined_sets_appending_before_items_already_found(self):
        self.assertEqual(['xs', 's', 'm', 'l'], list_unify_in_order([
            ['s', 'm'],
            ['s', 'm', 'l'],
            ['xs', 's']
        ]))


    def test_real_data(self):
        self.assertEqual(
            ['26/28"', '28/30"', '30/32"', '34/36"', '38/40"', 'xs', 's', 'm', 'l', 'xl', 'xxl'],
            list_unify_in_order([
                ['26/28"', '28/30"', '30/32"', '34/36"', '38/40"'],
                ['xs', 's', 'm', 'l', 'xl', 'xxl'],
                ['xs', 's', 'm', 'l', 'xl', 'xxl'],
            ])
        )
