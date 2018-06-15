# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.text import *


class LibTextWithPrefixTestCase(CubaneTestCase):
    """
    cubane.lib.text.text_with_prefix()
    """
    def test_one_of_args_is_not_set_should_return_text(self):
        self.assertIsNone(text_with_prefix(None, 'prefix'))


    def test_text_starting_with_prefix_should_return_text(self):
        self.assertEqual(text_with_prefix('preText', 'pre'), 'preText')


    def test_text_longer_than_prefix_should_return_prefixed_text(self):
        self.assertEqual(text_with_prefix('Text', 'pre'), 'preText')


class LibTextWithSuffixTestCase(CubaneTestCase):
    """
    cubane.lib.text.text_with_suffix()
    """
    def test_one_of_args_is_not_set_should_return_text(self):
        self.assertIsNone(text_with_suffix(None, 'suffix'))


    def test_text_ending_with_suffix_should_return_text(self):
        self.assertEqual(text_with_suffix('Textsuffix', 'suffix'), 'Textsuffix')


    def test_text_longer_than_suffix_should_return_suffixed_text(self):
        self.assertEqual(text_with_suffix('Text', 'suffix'), 'Textsuffix')


class LibTextWithoutPrefixTestCase(CubaneTestCase):
    """
    cubane.lib.text.text_without_prefix()
    """
    def test_one_of_args_is_not_set_should_return_text(self):
        self.assertIsNone(text_without_prefix(None, 'prefix'))


    def test_text_longer_than_prefix_and_text_contains_prefix_should_return_text_without_prefix(self):
        self.assertEqual(text_without_prefix('preText', 'pre'), 'Text')


class LibTextWithoutSuffixTestCase(CubaneTestCase):
    """
    cubane.lib.text.text_without_suffix()
    """
    def test_one_of_args_is_not_set_should_return_text(self):
        self.assertIsNone(text_without_prefix(None, 'prefix'))


    def test_text_longer_than_suffix_and_text_contains_suffix_should_return_text_without_suffix(self):
        self.assertEqual(text_without_suffix('Textsuff', 'suff'), 'Text')


class LibTextFromHTMLTestCase(CubaneTestCase):
    """
    cubane.lib.text.text_from_html()
    """
    def test_html_should_be_converter_to_text(self):
        self.assertEqual(text_from_html('<p style="font-size:12px">Test</p>'), 'Test')


    def test_should_insert_spaces_for_tags(self):
        self.assertEqual('Foo Bar', text_from_html('<h1>Foo</h1><p>Bar</p>'))


    def test_should_replace_nbsp_with_plain_spaces(self):
        self.assertEqual('Foo Bar', text_from_html('Foo&nbsp;Bar'))


    def test_should_substitude_named_html_entities(self):
        self.assertEqual('£100', text_from_html('<p>&pound;100</p>'))


    def test_should_substitude_numeric_html_entities(self):
        self.assertEqual('£100', text_from_html('<p>&#163;100</p>'))


    def test_should_substitude_hex_html_entities(self):
        self.assertEqual('£100', text_from_html('<p>&#xA3;100</p>'))


    def test_should_ignore_unknown_named_html_entities(self):
        self.assertEqual('&pounds;100', text_from_html('<p>&pounds;100</p>'))


    def test_should_ignore_unknown_numeric_entities(self):
        self.assertEqual('&#1543263;100', text_from_html('<p>&#1543263;100</p>'))


    def test_should_remove_duplicate_space_characters(self):
        self.assertEqual(
            'Stops wheels from accidentally moving Ridged surface to grips the ground and tyre',
            text_from_html('<p>Stops wheels from accidentally moving Ridged surface to grips  the ground and tyre</p>')
        )


class LibFormattedTextFromHTMLTestCase(CubaneTestCase):
    """
    cubane.lib.text.formatted_text_from_html()
    """
    def test_should_convert_empty_html(self):
        self.assertEqual('', formatted_text_from_html(''))


    def test_should_convert_none_to_empty_string(self):
        self.assertEqual('', formatted_text_from_html(None))


    def test_should_convert_html_to_text_with_formatting(self):
        self.assertEqual(
            'Foo Bar\n\nLorem Ipsum.',
            formatted_text_from_html('  <h1>Foo <b>Bar</b></h1><p>Lorem <small>Ipsum</small>.</p>  ')
        )


    def test_should_retain_unformatted_content(self):
        self.assertEqual(
            'Lorem Ipsum!',
            formatted_text_from_html('  Lorem Ipsum!  ')
        )


class LibTextPluraliseTestCase(CubaneTestCase):
    """
    cubane.lib.text.pluralize()
    """
    def test_should_pluralize_positive_numbers(self):
        self.assertEqual(pluralize(2, 'item'), '2 items')


    def test_should_pluralize_negative_numbers(self):
        self.assertEqual(pluralize(-2, 'item'), '-2 items')


    def test_should_not_pluralize_1(self):
        self.assertEqual(pluralize(1, 'item'), '1 item')


    def test_should_not_pluralize_negative_1(self):
        self.assertEqual(pluralize(-1, 'item'), '-1 item')


    def test_should_pluralize_zero(self):
        self.assertEqual(pluralize(0, 'item'), '0 items')


    def test_should_format_as_message(self):
        self.assertEqual(pluralize(2, 'item', 'removed'), '2 items removed')


    def test_should_accept_singular_and_plural_terms(self):
        self.assertEqual(pluralize(1, ['body', 'bodies']), '1 body')
        self.assertEqual(pluralize(2, ['body', 'bodies']), '2 bodies')


class LibTextCleanUnicodeTestCase(CubaneTestCase):
    """
    cubane.lib.text.clean_unicode()
    """
    def test_clean_unicode_removes_characters_that_arent_unicode(self):
        text = 'This text has hidden characters that aren\'t unicode >  <'
        cleaned_text = clean_unicode(text)
        self.assertEqual(cleaned_text == text, False)
        # check hidden character is not in cleaned text
        self.assertEqual('  ' not in cleaned_text, True)


    def test_clean_unicode_should_keep_tabs_and_newlines(self):
        text = '\tThis text has hidden characters that aren\'t unicode >  <\n'
        cleaned_text = clean_unicode(text)
        self.assertEqual(cleaned_text == text, False)
        self.assertEqual('\t' in cleaned_text, True)
        self.assertEqual('\n' in cleaned_text, True)


class LibTextGetWordsTestCase(CubaneTestCase):
    """
    cubane.lib.text.get_words()
    """
    def test_should_return_empty_list_for_none(self):
        self.assertEqual([], get_words(None))


    def test_should_return_empty_list_for_empty_string(self):
        self.assertEqual([], get_words(''))


    def test_should_strip_out_non_letters_and_numbers(self):
        self.assertEqual(['water', 'world'], get_words('Water.World!'))


    def test_should_stip_out_apostrophe(self):
        self.assertEqual(['theory', 'einstein'], get_words('Einstein\'s Theory'))


    def test_should_work_with_line_breaks(self):
        self.assertEqual(
            ['water', 'world', 'screen'],
            get_words('Water\nWorld\r\nScreen.')
        )


    def test_should_filter_out_empty_words_and_spaces(self):
        self.assertEqual(
            ['water', 'world'],
            get_words('     water         world     \t    ')
        )


    def test_should_filter_out_stop_words(self):
        self.assertEqual([], get_words('and or if'))


    def test_should_remove_duplicates_if_instructed(self):
        self.assertEqual(
            ['water'],
            get_words('water, water and water.', remove_duplicates=True)
        )


    def test_should_keep_duplicates_if_instructed(self):
        self.assertEqual(
            ['water', 'water', 'water'],
            get_words('water, water and water.', remove_duplicates=False)
        )


class LibTextGetKeywordsTestCase(CubaneTestCase):
    """
    cubane.lib.text.get_keywords()
    """
    def test_should_generate_keywords_from_text(self):
        self.assertEqual(
            ['einstein', 'physics', 'german', 'quantum', 'theoretical'],
            get_keywords(
                'Albert Einstein (/ˈaɪnstaɪn/; German: [ˈalbɛɐ̯t ˈaɪnʃtaɪn]; 14 March 1879 – 18 April 1955) was a German-born theoretical physicist. He developed the general theory of relativity, one of the two pillars of modern physics (alongside quantum mechanics). ' +
                'Einstein\'s work is also known for its influence on the philosophy of science. Einstein is best known in popular culture for his mass–energy equivalence formula E = mc squared (which has been dubbed "the world\'s most famous equation"). ' +
                'He received the 1921 Nobel Prize in Physics for his "services to theoretical physics", in particular his discovery of the law of the photoelectric effect, a pivotal step in the evolution of quantum theory.',
                word_count=5
            )
        )


    def test_should_return_empty_list_for_none(self):
        self.assertEqual([], get_keywords(None))


    def test_should_return_empty_list_for_empty_string(self):
        self.assertEqual([], get_keywords(''))


    def test_should_strip_out_non_letters_and_numbers(self):
        self.assertEqual(['water', 'world'], get_keywords('Water.World!'))


    def test_should_filter_out_stop_words(self):
        self.assertEqual([], get_keywords('and or if'))