# coding=UTF-8
from __future__ import unicode_literals
from django import template
from django import forms
from django.template import Context
from django.test import override_settings
from django.template.backends.django import Template
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.form_tags import *
from mock.mock import Mock, patch
from cubane.forms import SectionField


class FormMock(forms.Form):
    message = forms.CharField()


class FormTagsFormTestCase(CubaneTestCase):
    """
    cubane.templatetags.form_tags.form()
    """
    def setUp(self):
        self.parser = Mock()
        self.token = Mock(methods=['split_contents'])


    def test_should_return_form_node(self):
        self.token.split_contents.return_value = ['form', 'form_form', 'utf8']
        self.assertIsInstance(form(self.parser, self.token), FormNode)


    def test_should_set_form(self):
        self.token.split_contents.return_value = ['form', 'form_form']
        form_node = form(self.parser, self.token)
        self.assertEqual(form_node.form, 'form_form')


    def test_should_set_enctype(self):
        self.token.split_contents.return_value = ['form', 'form_form', 'utf8']
        form_node = form(self.parser, self.token)
        self.assertEqual(form_node.enctype, 'utf8')


    def test_should_raise_exception(self):
        self.token.split_contents.return_value = ['form', 'form_form', 'utf8', 'test']
        self.assertRaises(template.TemplateSyntaxError, form, self.parser, self.token)


    def test_shuld_set_default_values(self):
        self.token.split_contents.return_value = ['form']
        form_node = form(self.parser, self.token)
        self.assertEqual(form_node.form, 'form')
        self.assertEqual(form_node.enctype, None)


class FormTagsFilterFormTestCase(CubaneTestCase):
    """
    cubane.templatetags.form_tags.filter_form()
    """
    def setUp(self):
        self.parser = Mock()
        self.token = Mock(methods=['split_contents'])


    def test_should_return_filter_form_node(self):
        self.token.split_contents.return_value = ['filter_form', 'form']
        self.assertIsInstance(filter_form(self.parser, self.token), FilterFormNode)


    def test_should_set_default(self):
        self.token.split_contents.return_value = ['filter_form']
        filter_form_node = filter_form(self.parser, self.token)
        self.assertEqual(filter_form_node.form, 'filter_form')


    def test_should_set_form(self):
        self.token.split_contents.return_value = ['filter_form', 'form']
        filter_form_node = filter_form(self.parser, self.token)
        self.assertEqual(filter_form_node.form, 'form')


    def test_should_raise_exception(self):
        self.token.split_contents.return_value = ['filter_form', 'form', 'test']
        self.assertRaises(template.TemplateSyntaxError, filter_form, self.parser, self.token)


class FormTagsFieldsPerRowTestCase(CubaneTestCase):
    """
    cubane.templatetags.form_tags.fields_per_row()
    """
    def setUp(self):
        self.fields = []
        for x in range(14):
            if x % 5 == 0:
                self.fields.append(Mock(field=SectionField()))
            else:
                self.fields.append(Mock(field='my_field'))


    def test_should_create_rows(self):
        rows = fields_per_row(self.fields)
        self.assertEqual(len(rows), 2)


class FormTagsFormNodeTestCase(CubaneTestCase):
    """
    cubane.templatetags.form_tags.FormNode.get_template()
    """
    def setUp(self):
        self.parser = Mock()
        self.token = Mock(methods=['split_contents'])


    def test_should_return_template(self):
        self.token.split_contents.return_value = ['form', 'form', 'utf8']
        form_node = form(self.parser, self.token)
        self.assertIsInstance(form_node.get_template(), Template)


    def test_should_render_context(self):
        fake_form = FormMock()
        self.token.split_contents.return_value = ['form', 'form', 'utf8']
        form_node = form(self.parser, self.token)
        self.assertTrue(True if 'id_message' in form_node.render(Context({'form': fake_form})) else False)


    def test_should_return_empty_string(self):
        self.token.split_contents.return_value = ['form', 'form', 'utf8']
        form_node = form(self.parser, self.token)
        self.assertEqual(form_node.render({}), '')


class FormTagsAutoCsrfTokenNodeTestCase(CubaneTestCase):
    """
    cubane.templatetags.form_tags.AutoCsrfTokenNode()
    """
    def test_should_render_csrf_tag_if_csrf_middleware_is_loaded(self):
        self.assertEqual(
            '<input type=\'hidden\' name=\'csrfmiddlewaretoken\' value=\'foo\' />',
            AutoCsrfTokenNode().render({'csrf_token': 'foo'})
        )


    @override_settings()
    def test_should_render_empty_string_if_csrf_token_is_not_loaded(self):
        settings.MIDDLEWARE_CLASSES = filter(
            lambda x: x != 'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE_CLASSES
        )
        self.assertEqual(
            '',
            AutoCsrfTokenNode().render({'csrf_token': 'foo'})
        )


class FormTagsFieldTypeTestCase(CubaneTestCase):
    """
    cubane.templatetags.form_tags.field_type()
    """
    def test_should_return_field_type(self):
        fake_form = FormMock()
        self.assertEqual(field_type(fake_form['message']), 'CharField')

