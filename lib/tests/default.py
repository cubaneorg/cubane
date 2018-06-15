# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.default import default_choice


class LibDefaultChoiceTestCase(CubaneTestCase):
    def test_default_choice_of_none_should_be_none(self):
        self.assertIsNone(default_choice(None))


    def test_default_choice_of_empty_list_should_be_none(self):
        self.assertIsNone(default_choice([]))


    def test_default_choice_of_choices_with_at_least_one_item_should_be_first_item_label(self):
        self.assertEqual(default_choice(self.create_choices(['a', 'b', 'c'])), 'a')


    def create_choices(self, items):
        """
        Create choices based on the given list of items, where each item is
        paired with a running index number starting with 1.
        """
        return zip(items, range(1, len(items)))
