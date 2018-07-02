# coding=UTF-8
from __future__ import unicode_literals
from django.template import TemplateSyntaxError, VariableDoesNotExist, Variable, Context
from cubane.tests.base import CubaneTestCase
from cubane.lib.templatetags import *
from cubane.testapp.models import TestModel
from decimal import Decimal
from datetime import date, datetime, timedelta


class LibTemplateErrorTestCase(CubaneTestCase):
    """
    cubane.lib.templatetags.template_error()
    """
    def test_should_return_message(self):
        self.assertEqual(template_error('error'), '[error]')


class LibIsLiteralTestCase(CubaneTestCase):
    """
    cubane.lib.templatetags.is_literal()
    """
    def test_should_return_true(self):
        self.assertEqual(is_literal('"test"'), True)


    def test_should_return_false(self):
        self.assertEqual(is_literal('test'), False)


class LibLiteralTestCase(CubaneTestCase):
    """
    cubane.lib.templatetags.literal()
    """
    def test_should_return_literal(self):
        self.assertEqual(literal('p', 'class', '"value"'), 'value')


    def test_should_raise_exception(self):
        self.assertRaises(TemplateSyntaxError, literal, 'p', 'class', 'value')


class LibValueOrLiteralTestCase(CubaneTestCase):
    """
    cubane.lib.templatetags.value_or_literal()
    """
    def test_should_return_none(self):
        self.assertEqual(value_or_literal(None, None), None)


    def test_should_return_literal(self):
        self.assertEqual(value_or_literal('"test"', None), 'test')


    def test_should_return_variable(self):
        c = Context({'test': 1})
        self.assertEqual(value_or_literal('test', c), 1)


    def test_should_return_none_if_variable_does_not_exist(self):
        c = Context({'test': 1})
        self.assertEqual(value_or_literal('name', c), None)


class LibValueOrNoneTestCase(CubaneTestCase):
    """
    cubane.lib.templatetags.value_or_none()
    """
    def test_should_return_none(self):
        c = Context({'name': 'value'})
        self.assertEqual(value_or_none(None, c), None)
        self.assertEqual(value_or_none('test', c), None)


    def test_should_return_value(self):
        c = Context({'name': 'value'})
        self.assertEqual(value_or_none('name', c), 'value')


class LibValueOrDefaultTestCase(CubaneTestCase):
    """
    cubane.lib.templatetags.value_or_default()
    """
    def test_should_return_default(self):
        c = Context({'name': 'value'})
        self.assertEqual(value_or_default(None, c, False), False)
        self.assertEqual(value_or_default('test', c, False), False)


    def test_should_return_value(self):
        c = Context({'name': 'value'})
        self.assertEqual(value_or_default('name', c, False), 'value')


class LibHTMLTagTestCase(CubaneTestCase):
    """
    cubane.lib.templatetags.htmltag()
    """
    def test_should_return_html_tag(self):
        self.assertEqual(htmltag('p', {'class': 'test'}, 'test'), '<p class="test">test</p>')