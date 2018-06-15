# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from django.test.utils import override_settings
from cubane.templatetags.html_tags import transpose_headlines
from cubane.templatetags.html_tags import compatible


class HtmlTagsTransposeHeadlinesTestCase(CubaneTestCase):
    """
    cubane.templatetags.html_tags.transpose_headlines()
    """
    HTML = \
        '<h1>h1</h1>' + \
        '<h2>h2</h2>' + \
        '<h3>h3</h3>' + \
        '<h4>h4</h4>' + \
        '<h5>h5</h5>' + \
        '<h6>h6</h6>'


    TRANSPOSED_HTML = \
        '<h3>h1</h3>' + \
        '<h4>h2</h4>' + \
        '<h5>h3</h5>' + \
        '<h6>h4</h6>' + \
        '<h6>h5</h6>' + \
        '<h6>h6</h6>'


    def test_should_ignore_non_numeric_level_argument(self):
        self.assertEqual(
            self.HTML,
            transpose_headlines(self.HTML, 'not-a-number')
        )


    def test_should_transpose_headlines_by_given_level(self):
        self.assertEqual(
            self.TRANSPOSED_HTML,
            transpose_headlines(self.HTML, 2)
        )


class HtmlTagsCompatibleTestCase(CubaneTestCase):
    """
    cubane.templatetags.html_tags.compatible()
    """
    @override_settings(SSL=False)
    def test_should_not_rewrite_image_url_with_ssl_mode_disabled(self):
        self.assertEqual(
            '<img src="http://www.innershed.com/foo.jpg">',
            compatible('<img src="http://www.innershed.com/foo.jpg"/>')
        )


    @override_settings(SSL=True)
    def test_should_rewrite_image_url_with_ssl_mode_enabled(self):
        self.assertEqual(
            '<img src="https://www.innershed.com/foo.jpg">',
            compatible('<img src="http://www.innershed.com/foo.jpg"/>')
        )


    @override_settings(SSL=True)
    def test_should_rewrite_image_url_without_quotes_with_ssl_mode_enabled(self):
        self.assertEqual(
            '<img src="https://www.innershed.com/foo.jpg">',
            compatible('<img src=http://www.innershed.com/foo.jpg>')
        )


    @override_settings(SSL=True)
    def test_should_rewrite_image_url_without_quotes_and_additional_attributes_with_ssl_mode_enabled(self):
        self.assertEqual(
            '<img src="https://www.innershed.com/foo.jpg" alt="Foo">',
            compatible('<img src=http://www.innershed.com/foo.jpg alt="Foo">')
        )


    @override_settings(SSL=True)
    def test_should_rewrite_image_url_with_quotes_and_additional_attributes_with_ssl_mode_enabled(self):
        self.assertEqual(
            '<img src="https://www.innershed.com/foo.jpg" alt="Foo">',
            compatible('<img src="http://www.innershed.com/foo.jpg" alt="Foo">')
        )


    @override_settings(SSL=True)
    def test_should_rewrite_image_url_with_quotes_and_additional_attributes_and_self_terminating_syntax_with_ssl_mode_enabled(self):
        self.assertEqual(
            '<img src="https://www.innershed.com/foo.jpg" alt="Foo">',
            compatible('<img src="http://www.innershed.com/foo.jpg" alt="Foo"/>')
        )


    @override_settings(SSL=True)
    def test_should_rewrite_image_url_independently_of_order_if_attributes_with_ssl_mode_enabled(self):
        self.assertEqual(
            '<img alt="Foo" src="https://www.innershed.com/foo.jpg">',
            compatible('<img alt="Foo" src="http://www.innershed.com/foo.jpg">')
        )