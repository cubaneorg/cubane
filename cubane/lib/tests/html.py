# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.html import transpose_html_headlines
from cubane.lib.html import cleanup_html
from cubane.lib.html import embed_html
from cubane.lib.html import get_normalised_links


class LibHtmlTransposeHtmlHeadlinesTestCase(CubaneTestCase):
    """
    cubane.lib.html.transpose_html_headlines()
    """
    def test_should_not_transpose_by_zero_or_negative_levels(self):
        for i in range(0, 2):
            self.assertEqual(transpose_html_headlines('<h3>x</h3>', -i), '<h3>x</h3>')


    def test_should_transpose_by_level(self):
        self.assertEqual(
            transpose_html_headlines('<h1>1</h1> <h2>2</h2> <h3>3</h3> <h4>4</h4> <h5>5</h5>', 1),
            '<h2>1</h2> <h3>2</h3> <h4>3</h4> <h5>4</h5> <h6>5</h6>'
        )


    def test_should_transpose_case_insensetively(self):
        self.assertEqual(
            transpose_html_headlines('<H1>1</h1> <H2>2</h2> <h3>3</H3> <h4>4</H4> <H5>5</H5>', 1),
            '<h2>1</h2> <h3>2</h3> <h4>3</h4> <h5>4</h5> <h6>5</h6>'
        )


    def test_should_not_transpose_h6_any_further(self):
        self.assertEqual(
            transpose_html_headlines('<h4>4</h4> <h5>5</h5> <h6>6</h6>', 2),
            '<h6>4</h6> <h6>5</h6> <h6>6</h6>'
        )


class LibHtmlCleanupHtmlTestCase(CubaneTestCase):
    """
    cubane.lib.html.cleanup_html()
    """
    def test_should_return_empty_string_for_none(self):
        self.assertEqual('', cleanup_html(None))


    def test_should_strip_white_space(self):
        self.assertEqual('foo', cleanup_html('  foo  \n\n  '))


    def test_should_remove_empty_paragraphs(self):
        self.assertEqual(
            '<h1>Foo</h1><p>Lorem Ipsum</p>',
            cleanup_html(
                '<p> &nbsp; </p><h1>Foo</h1><p> \n </p><p>Lorem Ipsum</p>' + \
                '<p></p><p>&nbsp;\n</p>'
            )
        )


    def test_should_remove_empty_paragraphs_with_inline_style_or_attributes(self):
        self.assertEqual(
            '<h1>Foo</h1><p data-id="foo">Lorem Ipsum</p>',
            cleanup_html(
                '<p style="text-align: center;"> &nbsp; </p><h1>Foo</h1><p data-id="bar"> \n </p><p data-id="foo">Lorem Ipsum</p>' + \
                '<p></p><p>&nbsp;\n</p>'
            )
        )


    def test_should_not_remove_paragraphs_that_contain_whitespace_but_are_not_empty(self):
        self.assertEqual(
            '<p><small>X</small></p>',
            cleanup_html('<p><small>X</small></p>')
        )


    def test_should_not_remove_paragraphs_that_contain_whitespace_but_are_not_empty_with_inline_style_or_attribubtes(self):
        self.assertEqual(
            '<p style="text-align: center;"><small data-id="foo">X</small></p>',
            cleanup_html('<p style="text-align: center;"><small data-id="foo">X</small></p>')
        )


    def test_should_remove_leading_whitespace_for_paragraph_start(self):
        self.assertEqual(
            '<p>foo</p><p>bar</p><p>test</p>',
            cleanup_html('<p>  &nbsp;foo</p><p> bar</p><p>&nbsp;test</p>')
        )


class LibHtmlEmbedTestCase(CubaneTestCase):
    """
    cubane.lib.html.embed_html()
    """
    def test_should_embed_into_none(self):
        self.assertEqual('!', embed_html(None, '!'))


    def test_should_embed_into_empty_html(self):
        self.assertEqual('!', embed_html('', '!'))


    def test_should_embed_into_text_without_paragraphs(self):
        self.assertEqual('Hello World!', embed_html('Hello World', '!'))


    def test_should_not_insert_if_inital_budget_has_not_been_reached(self):
        self.assertEqual(
            '<p>Foo</p><p>Bar</p><p>FooBar</p>!<p>Hello World</p>',
            embed_html('<p>Foo</p><p>Bar</p><p>FooBar</p><p>Hello World</p>', '!', initial_words=3)
        )


    def test_should_insert_after_inital_budget(self):
        self.assertEqual(
            '<p>Foo Bar FooBar</p>!<p>Hello World</p>',
            embed_html('<p>Foo Bar FooBar</p><p>Hello World</p>', '!', initial_words=3)
        )


    def test_should_insert_repeatly(self):
        self.assertEqual(
            '<p>Foo Bar</p><p>FooBar</p>!<p>Foo</p>!<p>Foo</p>!<p>Foo</p>!',
            embed_html('<p>Foo Bar</p><p>FooBar</p><p>Foo</p><p>Foo</p><p>Foo</p>', '!', initial_words=3, subsequent_words=1)
        )



class LibHtmlGetNormalisedLinksTestCase(CubaneTestCase):
    """
    cubane.lib.html.get_normalised_links()
    """
    def test_should_return_empty_for_none(self):
        self.assertEqual(
            '',
            get_normalised_links(None)
        )


    def test_should_return_empty_for_empty(self):
        self.assertEqual(
            '',
            get_normalised_links('')
        )


    def test_should_remove_target_and_rel_if_href_is_internal(self):
        url = 'http://www.%s/foo/bar/' % settings.DOMAIN_NAME
        self.assertEqual(
            '<a href="%s">Foo</a>' % url,
            get_normalised_links('<a href="%s" rel="noopener noreferrer" target="_blank">Foo</a>' % url)
        )


    def test_should_add_target_and_rel_if_href_is_external(self):
        self.assertEqual(
            '<a href="https://www.google.co.uk/" rel="noopener noreferrer" target="_blank">Foo</a>',
            get_normalised_links('<a href="https://www.google.co.uk/">Foo</a>')
        )


    def test_should_remove_target_and_rel_for_email_href(self):
        self.assertEqual(
            '<a href="mailto:jan.kueting@innershed.com">Foo</a>',
            get_normalised_links('<a href="mailto:jan.kueting@innershed.com" rel="noopener noreferrer" target="_blank">Foo</a>')
        )


    def test_should_remove_beta_references_for_internal_url(self):
        self.assertEqual(
            '<a href="http://www.%s/foo/bar/">Foo</a>' % settings.DOMAIN_NAME,
            get_normalised_links('<a href="http://beta.%s/foo/bar/" rel="noopener noreferrer" target="_blank">Foo</a>' % settings.DOMAIN_NAME)
        )


    def test_should_not_remove_beta_prefix_if_not_internal(self):
        self.assertEqual(
            '<a href="https://beta.google.com" rel="noopener noreferrer" target="_blank">Foo</a>',
            get_normalised_links('<a href="https://beta.google.com" rel="noopener noreferrer" target="_blank">Foo</a>')
        )


    def test_should_remove_target_and_rel_if_href_is_internal_leaving_other_attributes_untouched(self):
        url = 'http://www.%s/foo/bar/' % settings.DOMAIN_NAME
        self.assertEqual(
            '<a class="btn btn-primary" disabled="" href="%s">Foo</a>' % url,
            get_normalised_links('<a href="%s" rel="noopener noreferrer" target="_blank" class="btn btn-primary" disabled>Foo</a>' % url)
        )






