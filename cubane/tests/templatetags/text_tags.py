# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.text_tags import *
from cubane.models import Country


class TextTagsWithoutSpacesTestCase(CubaneTestCase):
    """
    cubane.templatetags.text_tags.without_spaces()
    """
    def test_should_remove_all_spaces(self):
        self.assertEqual(without_spaces('  a    b  '), 'ab')


    def test_string_as_none_should_return_empty_string(self):
        self.assertEqual(without_spaces(None), '')


class TextTagsPhoneDisplayTestCase(CubaneTestCase):
    """
    cubane.templatetags.text_tags.phone_display()
    """
    def test_should_return_empty_string_for_none(self):
        self.assertEqual('', phone_display(None))


    def test_should_strip_whitespace(self):
        self.assertEqual('0999 12 34 56', phone_display('  0999 12 34 56  '))


    def test_should_remove_country_code_with_zero_zero_prefix(self):
        self.assertEqual('0999 123456', phone_display('0044 0999 123456'))


    def test_should_remove_country_code_with_plus_prefix(self):
        self.assertEqual('0999 123456', phone_display('+44 0999 123456'))


    def test_should_add_leading_zero_after_having_country_code_removed(self):
        self.assertEqual('0999 123456', phone_display('0044 999 123456'))
        self.assertEqual('0999 123456', phone_display('+44 999 123456'))


class TextTagsPhoneNumberTestCase(CubaneTestCase):
    """
    cubane.templatetags.text_tags.phone_number()
    """
    def test_should_return_empty_string_for_none(self):
        self.assertEqual('', phone_number(None))


    def test_should_remove_spaces(self):
        self.assertEqual('+44999123456', phone_number('  0999\t12\n\n34 56   '))


    def test_should_remove_non_valid_characters(self):
        self.assertEqual('+44999123456', phone_number('  (0)999 12.34.56'))


    def test_should_rewrite_zero_zero_country_prefix(self):
        self.assertEqual('+44999123456', phone_number('0044 999 123456'))


    def test_should_add_missing_country_code_without_zero_prefix(self):
        self.assertEqual('+44999123456', phone_number('0999 123456'))


    def test_should_add_missing_country_code(self):
        self.assertEqual('+44999123456', phone_number('999 123456'))


    def test_should_add_missing_country_code_using_given_country_argument(self):
        de = Country.objects.get(pk='DE')
        self.assertEqual('+49999123456', phone_number('999 123456', de))
        self.assertEqual('+49999123456', phone_number('0999 123456', de))


class TextTagsNullableTestCase(CubaneTestCase):
    """
    cubane.templatetags.text_tags.nullable()
    """
    def test_should_return_value(self):
        self.assertEqual(nullable(5), 5)


    def test_should_return_hyphen_if_value_is_none(self):
        self.assertEqual(nullable(None), '-')


class TextTagsTruncatewordsByCharsTestCase(CubaneTestCase):
    """
    cubane.templatetags.text_tags.truncatewords_by_chars()
    """
    def test_should_return_value_if_arg_is_none(self):
        self.assertEqual(truncatewords_by_chars('test test', 'five'), 'test test')


    def test_should_return_value_if_text_shorter_than_arg(self):
        self.assertEqual(truncatewords_by_chars('test test', 50), 'test test')


    def test_should_return_truncated_value_if_lenght_char_is_space(self):
        self.assertEqual(truncatewords_by_chars('test test', '5'), 'test...')


    def test_should_return_truncated_value_if_length_char_is_not_space(self):
        self.assertEqual(truncatewords_by_chars('test test, test', 10), 'test test,...')


class TextTagsTruncateCharsTestCase(CubaneTestCase):
    """
    cubane.templatetags.text_tags.truncate_chars()
    """
    def test_should_strip_input_before_truncation(self):
        self.assertEqual('test...', truncate_chars('   test test   ', 5))


    def test_should_truncate_matching_word_length(self):
        self.assertEqual('test...', truncate_chars('test test', 4))


    def test_should_truncate_without_leaving_spaces(self):
        self.assertEqual('test...', truncate_chars('test test', 5))


    def test_should_truncate_without_leaving_multiple_spaces(self):
        self.assertEqual('test...', truncate_chars('test  test', 6))


    def test_should_truncate_inbeteen_words(self):
        self.assertEqual('test te...', truncate_chars('test test', 7))


    def test_should_not_truncate_if_excerpt_encloses_input(self):
        self.assertEqual('test test', truncate_chars('test test', 9))


    def test_should_not_truncate_if_excerpt_exceeds_input(self):
        self.assertEqual('test test', truncate_chars('test test', 10))


class TextTagsRandomNumberTestCase(CubaneTestCase):
    """
    cubane.templatetags.text_tags.random_number()
    """
    def test_should_return_random_number_as_string(self):
        n = random_number()

        # should be a unicode string
        self.assertIsInstance(n, unicode)

        # should represent a number
        int(n)