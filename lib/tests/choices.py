# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.choices import get_choices_value
from cubane.lib.choices import get_choices_display
from cubane.lib.choices import get_choices_from_values


GENDER_MALE    = 1
GENDER_FEMALE  = 2
GENDER_CHOICES = (
    (GENDER_MALE,   'Male'),
    (GENDER_FEMALE, 'Female')
)


class LibChoicesGetChoicesValueTestCase(CubaneTestCase):
    """
    cubane.lib.choices.get_choices_value()
    """
    def test_should_return_value_of_given_display(self):
        self.assertEqual(get_choices_value(GENDER_CHOICES, 'Male'), GENDER_MALE)


    def test_should_return_none_if_not_found(self):
        self.assertIsNone(get_choices_value(GENDER_CHOICES, 'Does Not Exist'))


    def test_should_return_default_if_not_found(self):
        self.assertEqual(get_choices_value(GENDER_CHOICES, 'Does Not Exist', -1), -1)


class LibChoicesGetChoicesDisplayTestCase(CubaneTestCase):
    """
    cubane.lib.choices.get_choices_display()
    """
    def test_should_return_display_of_given_value(self):
        self.assertEqual(get_choices_display(GENDER_CHOICES, GENDER_MALE), 'Male')


    def test_should_return_none_if_not_found(self):
        self.assertIsNone(get_choices_display(GENDER_CHOICES, 'Does Not Exist'))


    def test_should_return_default_if_not_found(self):
        self.assertEqual(get_choices_display(GENDER_CHOICES, 'Does Not Exist', -1), -1)


class LibChoicesGetChoicesFromValuesTestCase(CubaneTestCase):
    """
    cubane.lib.choices.get_choices_from_values()
    """
    def test_should_return_empty_choices_for_none(self):
        self.assertEqual([], get_choices_from_values(None))


    def test_should_return_empty_choices_for_empty_list_of_values(self):
        self.assertEqual([], get_choices_from_values([]))


    def test_should_make_list_of_values_presentable(self):
        self.assertEqual(
            [
                ('BAR',     'Bar'),
                ('foo',     'Foo'),
                ('foo_bar', 'Foo Bar')
            ],
            get_choices_from_values(['foo', 'foo_bar', 'BAR', ''])
        )


    def test_should_exclude_prefix_in_display_value(self):
        self.assertEqual(
            [
                ('BAR',     'Bar'),
                ('foo',     ''),
                ('foo_bar', 'Bar')
            ],
            get_choices_from_values(['foo', 'foo_bar', 'BAR', ''], prefix='foo')
        )