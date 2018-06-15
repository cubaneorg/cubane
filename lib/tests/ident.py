# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.ident import headline_from_ident
from cubane.lib.ident import to_camel_case


class LibIdentHeadlineFromIdentTestCase(CubaneTestCase):
    """
    cubane.lib.ident.headline_from_ident()
    """
    def test_should_replace_underscore_with_single_space(self):
        self.assertEqual(headline_from_ident('foo__bar'), 'Foo Bar')


class LibIdentToCamelCaseTestCase(CubaneTestCase):
    """
    cubane.lib.ident.to_camel_case()
    """
    def test_should_camel_case_words(self):
        self.assertEqual('HelloWorldFooBar', to_camel_case('hello_world_foo_bar'))


    def test_should_trim_input(self):
        self.assertEqual('HelloWorld', to_camel_case('   hello_world   '))


    def test_should_ignore_empty_segments(self):
        self.assertEqual('HelloWorld', to_camel_case('_ _hello__world__'))