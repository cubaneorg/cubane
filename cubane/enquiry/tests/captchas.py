# coding=UTF-8
from __future__ import unicode_literals
from django.test.utils import override_settings
from django import forms
from cubane.tests.base import CubaneTestCase
from cubane.enquiry.captchas import *
from mock import MagicMock, patch


class CaptchaForm(forms.Form):
    captcha = forms.CharField(max_length=255)


class EnquiryRecaptchaWidgetTestCase(CubaneTestCase):
    @override_settings(RECAPTCHA_PUBLIC_KEY='foo')
    def test_should_render_javascript_snippet_for_captcha(self):
        self.assertIn(
            'http://www.google.com/recaptcha/api/challenge?k=foo',
            RecaptchaWidget().render()
        )


class EnquiryNewRecaptchaWidgetTestCase(CubaneTestCase):
    @override_settings(CAPTCHA_SITE_KEY='foo')
    def test_should_render_javascript_snippet_for_captcha(self):
        self.assertEqual(
            '<div class="g-recaptcha" data-sitekey="foo" ></div>',
            NewRecaptchaWidget().render()
        )


class EnquiryHashWidgetTestCase(CubaneTestCase):
    @override_settings(CAPTCHA_SITE_KEY='foo')
    def test_should_render_empty_string(self):
        self.assertEqual(
            '',
            HashWidget().render()
        )


class EnquiryInnershedCaptchaWidgetTestCase(CubaneTestCase):
    @override_settings(CAPTCHA_PLACEHOLDER='foo')
    def test_should_render_javascript_snippet_for_captcha_with_placeholder(self):
        self.assertEqual(
            '<input id="id_captcha" maxlength="255" name="captcha" placeholder="foo" type="text">',
            InnershedCaptchaWidget().render()
        )


    @override_settings(CAPTCHA_PLACEHOLDER=None)
    def test_should_render_javascript_snippet_for_captcha_without_placeholder(self):
        self.assertEqual(
            '<input id="id_captcha" maxlength="255" name="captcha" type="text">',
            InnershedCaptchaWidget().render()
        )


class EnquiryGetCaptchaWidget(CubaneTestCase):
    @override_settings(CAPTCHA='recaptcha')
    def test_should_return_recaptcha_wideget(self):
        field = get_captcha_widget()
        self.assertIsInstance(field, forms.CharField)
        self.assertIsInstance(field.widget, RecaptchaWidget)


    @override_settings(CAPTCHA='innershed_captcha')
    def test_should_return_innershed_wideget(self):
        field = get_captcha_widget()
        self.assertIsInstance(field, forms.CharField)
        self.assertIsInstance(field.widget, InnershedCaptchaWidget)


    @override_settings(CAPTCHA='new_recaptcha')
    def test_should_return_new_captcha_wideget(self):
        field = get_captcha_widget()
        self.assertIsInstance(field, forms.CharField)
        self.assertIsInstance(field.widget, NewRecaptchaWidget)


    @override_settings(CAPTCHA='does-not-exist')
    def test_should_return_empty_string_for_unknown_captcha_wideget(self):
        self.assertEqual('', get_captcha_widget())


class EnquiryCleanCaptchaDataTestCase(CubaneTestCase):
    def setUp(self):
        self.form = CaptchaForm()
        self.form._errors = {}


    @override_settings(CAPTCHA='innershed_captcha')
    def test_should_raise_from_error_if_captcha_value_is_not_present(self):
        clean_captcha_data({}, self.form)
        self.assertFormFieldError(self.form, 'captcha', 'Please enter the captcha.')


    @override_settings(CAPTCHA='innershed_captcha')
    def test_should_raise_from_error_if_captcha_hash_is_missing(self):
        clean_captcha_data({'captcha': 'foo'}, self.form)
        self.assertFormFieldError(self.form, 'captcha', 'Captcha hash argument is missing.')


    @override_settings(CAPTCHA='innershed_captcha')
    @patch('requests.get')
    def test_should_raise_from_error_if_captcha_is_invalid(self, get):
        get.return_value = MagicMock(text='invalid')
        clean_captcha_data({'captcha': 'foo', 'captcha_hash': 'bar'}, self.form)
        self.assertFormFieldError(self.form, 'captcha', 'Please enter the correct captcha.')


    @override_settings(CAPTCHA='innershed_captcha')
    @patch('requests.get')
    def test_should_not_raise_from_error_if_captcha_is_valid(self, get):
        get.return_value = MagicMock(text='valid')
        clean_captcha_data({'captcha': 'foo', 'captcha_hash': 'bar'}, self.form)
        self.assertEqual({}, self.form._errors)


class EnquiryIsCaptchaWidgetTestCase(CubaneTestCase):
    def test_should_return_true_for_valid_captcha_widget(self):
        for widget in CAPTCHA_WIDGETS:
            self.assertTrue(is_captcha_widget(widget()))


    def test_should_return_false_for_invalid_captcha_widget(self):
        self.assertFalse(is_captcha_widget('not-a-cpatcha-widget'))