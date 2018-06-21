# coding=UTF-8
from __future__ import unicode_literals
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.testapp.models import Enquiry
from cubane.enquiry.forms import *
from mock import patch


class TestSimpleEnquiryForm(SimpleEnquiryForm):
    class Meta:
        model = Enquiry
        fields = '__all__'


class TestAdvancedEnquiryForm(AdvancedEnquiryForm):
    class Meta:
        model = Enquiry
        fields = '__all__'


class SimpleEnquiryFormTestCase(CubaneTestCase):
    @override_settings(CAPTCHA_SECRET_KEY=None, CAPTCHA='new_captcha')
    @patch('cubane.enquiry.captchas.clean_captcha_data')
    def test_should_clean_captcha_data(self, clean_captcha_data):
        del settings.CAPTCHA_SECRET_KEY
        form = TestSimpleEnquiryForm({
            'first_name': 'Foo',
            'last_name': 'Bar',
            'email': 'foo@bar.com',
            'message': 'Test'
        })
        self.assertTrue(form.is_valid())
        self.assertTrue(clean_captcha_data.called)


class AdvancedEnquiryFormTestCase(CubaneTestCase):
    def test_should_raise_form_error_if_no_contact_information_is_given(self):
        form = self._create_form()
        self.assertFalse(form.is_valid())
        self.assertFormError(form, AdvancedEnquiryForm.FORM_ERROR_NO_CONTACT_INFO)


    def test_should_raise_form_error_if_contact_via_telephone_without_number(self):
        form = self._create_form({'contact_tel': True})
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'tel', AdvancedEnquiryForm.FORM_ERROR_TELEPHONE_REQUIRED)


    def test_should_raise_form_error_if_contact_via_mobile_without_number(self):
        form = self._create_form({'contact_mobile': True})
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'mobile', AdvancedEnquiryForm.FORM_ERROR_MOBILE_REQUIRED)


    def test_contact_via_email_should_succeed(self):
        form = self._create_form({'contact_email': True})
        self.assertTrue(form.is_valid())


    def test_contact_via_telephone_should_succeed(self):
        form = self._create_form({'contact_tel': True, 'tel': '12345678'})
        self.assertTrue(form.is_valid())


    def test_contact_via_mobile_should_succeed(self):
        form = self._create_form({'contact_mobile': True, 'mobile': '12345678'})
        self.assertTrue(form.is_valid())


    @override_settings(CAPTCHA_SECRET_KEY=None, CAPTCHA='new_captcha')
    @patch('cubane.enquiry.captchas.clean_captcha_data')
    def test_should_clean_captcha_data(self, clean_captcha_data):
        del settings.CAPTCHA_SECRET_KEY
        form = self._create_form({'contact_email': True})
        self.assertTrue(form.is_valid())
        self.assertTrue(clean_captcha_data.called)


    def _create_form(self, data={}):
        context = {
            'first_name': 'Foo',
            'last_name': 'Bar',
            'email': 'foo@bar.com',
            'message': 'Test'
        }
        context.update(data)
        return TestAdvancedEnquiryForm(context)