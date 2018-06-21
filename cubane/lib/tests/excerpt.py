# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.excerpt import excerpt_from_text, excerpt_from_html


class LibExcerptFromTextTestCase(CubaneTestCase):
    """
    cubane.lib.excerpt.excerpt_from_text()
    """
    def test_excerpt_from_text_should_return_empty_string_for_none(self):
        self.assertEqual(excerpt_from_text(None), '')


    def test_excerpt_from_text_should_slice(self):
        self.assertEqual(excerpt_from_text('Hello World', length=5), 'Hello...')


    def test_excerpt_from_text_should_trim_after_slice(self):
        self.assertEqual(excerpt_from_text('Hello   World', length=8), 'Hello...')


    def test_except_from_text_should_slice_left_padded_in_prefix_mode(self):
        self.assertEqual(excerpt_from_text('Hello World', length=3, prefix=True), '...rld')


class LibExcerptFromHtmlTestCase(CubaneTestCase):
    """
    cubane.lib.excerpt.excerpt_from_html()
    """
    def test_excerpt_from_html_should_return_empty_string_for_none(self):
        self.assertEqual(excerpt_from_html(None), '')


    def test_excerpt_from_html_should_replace_html_entities(self):
        self.assertEqual(excerpt_from_html('&amp;&nbsp;x'), '& x')


    def test_excerpt_from_html_should_textualise_html_tags(self):
        self.assertEqual(excerpt_from_html('<h1>Headline</h1>'), 'Headline')
