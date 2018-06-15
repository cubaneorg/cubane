# coding=UTF-8
from __future__ import unicode_literals
from django.http import HttpResponseRedirect
from django.test.utils import override_settings
from django.test.client import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.enquiry.views import *
from cubane.testapp.models import Settings, Enquiry
from cubane.testapp.forms import EnquiryForm, CustomEnquiryForm
from mock import patch
import cStringIO


class EnquiryViewsGetEnquiryModelTestCase(CubaneTestCase):
    EXCEPTION_MSG = 'to be set to the full path of the model class'


    def test_should_returns_enquiry_model_class(self):
        self.assertEqual(get_enquiry_model(), Enquiry)


    @override_settings(ENQUIRY_MODEL='')
    def test_should_raise_exception_if_enquiry_model_is_not_defined(self):
        del settings.ENQUIRY_MODEL
        with self.assertRaisesRegexp(ValueError, self.EXCEPTION_MSG):
            get_enquiry_model()


    @override_settings(ENQUIRY_MODEL='does_not_exist')
    def test_should_raise_exception_if_enquiry_model_does_not_exist(self):
        with self.assertRaisesRegexp(ValueError, self.EXCEPTION_MSG):
            get_enquiry_model()


class EnquiryViewsCreateBlankEnquiryFormTestCase(CubaneTestCase):
    def test_should_create_form_for_given_model_with_no_initial_data_and_backend_fields_removed(self):
        form = create_blank_enquiry_form(Enquiry)
        self.assertIsInstance(form, EnquiryForm)
        self.assertEqual({}, form.initial)
        self.assertIsNone(form.fields.get('closed'))


    def test_should_create_form_of_given_type(self):
        form = create_blank_enquiry_form(Enquiry, CustomEnquiryForm)
        self.assertIsInstance(form, CustomEnquiryForm)
        self.assertEqual({}, form.initial)
        self.assertIsNone(form.fields.get('closed'))
        self.assertIsNotNone(form.fields.get('enquiry_title'))


class EnquiryViewsRemoveBackendFieldsTestCase(CubaneTestCase):
    def test_should_remove_backend_fields_from_form(self):
        form = EnquiryForm()
        for fieldname in BACKEND_FORM_FIELD_NAMES:
            self.assertIsNotNone(form.fields.get(fieldname), fieldname)

        remove_backend_fields(form)

        for fieldname in BACKEND_FORM_FIELD_NAMES:
            self.assertIsNone(form.fields.get(fieldname), fieldname)


    def test_should_remove_tabs(self):
        form = EnquiryForm()
        self.assertTrue(len(form._tabs) > 0)

        remove_backend_fields(form)

        self.assertEqual([], form._tabs)


class EnquiryViewsValidateCaptchaTestCase(CubaneTestCase):
    @override_settings(CAPTCHA_SECRET_KEY='foo')
    @patch('urllib2.urlopen')
    def test_should_return_true_if_captcha_is_valid(self, urlopen):
        self._assert_captcha(urlopen, success=True)


    @override_settings(CAPTCHA_SECRET_KEY='foo')
    @patch('urllib2.urlopen')
    def test_should_return_false_if_captcha_is_not_valid(self, urlopen):
        self._assert_captcha(urlopen, success=False)


    def _assert_captcha(self, urlopen, success):
        response = cStringIO.StringIO()
        response.write('{"success": %s}' % ('true' if success else 'false'))
        response.seek(0)
        urlopen.return_value = response

        factory = RequestFactory()
        request = factory.post('/', {'g-recaptcha-response': 'bar'})

        self.assertEqual(success, validate_captcha(request))
        urlopen.assert_called_with('https://www.google.com/recaptcha/api/siteverify?secret=foo&response=bar')


class EnquiryViewsDefaultEnquiryFormTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(EnquiryViewsDefaultEnquiryFormTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')


    def test_should_create_default_enquiry_form(self):
        context = default_enquiry_form(self.request, None, {}, Enquiry)
        self.assertIsInstance(context.get('enquiry_form'), EnquiryForm)


    def test_should_create_given_enquiry_form_instance(self):
        context = default_enquiry_form(self.request, None, {}, Enquiry, CustomEnquiryForm)
        self.assertIsInstance(context.get('enquiry_form'), CustomEnquiryForm)


    @override_settings(INSTALLED_APPS=[])
    def test_should_raise_if_cms_is_not_installed(self):
        with self.assertRaisesRegexp(ValueError, 'required for sending cms page emails'):
            default_enquiry_form(self.request, None, {}, Enquiry)


    @override_settings(ENQUIRY_CLIENT_TEMPLATE=None)
    def test_should_raise_if_cms_enquiry_template_is_not_setup(self):
        del settings.ENQUIRY_CLIENT_TEMPLATE
        with self.assertRaisesRegexp(ValueError, 'is required in settings for sending emails to clients'):
            default_enquiry_form(self.request, None, {}, Enquiry)


    def test_should_setup_form_initials_via_get_arguments(self):
        initial = {'email': 'foo@bar.com'}
        context = default_enquiry_form(self.factory.get('/', initial), None, {}, Enquiry)
        self.assertEqual(initial, context.get('enquiry_form').initial)


    @patch('cubane.enquiry.views.remove_backend_fields')
    def test_should_remove_backend_fields(self, remove_backend_fields):
        default_enquiry_form(self.request, None, {}, Enquiry)
        self.assertTrue(remove_backend_fields.called)


    @patch('cubane.enquiry.views.validate_captcha')
    def test_should_validate_on_post(self, validate_captcha):
        validate_captcha.return_value = True

        data = {
            'email': 'foo@bar.com'
        }
        context = default_enquiry_form(self.make_request('post', '/', data), None, {}, Enquiry)
        self.assertNotEqual({}, context.get('enquiry_form').errors)


    @patch('cubane.enquiry.views.validate_captcha')
    def test_should_validate_on_post_ajax(self, validate_captcha):
        validate_captcha.return_value = True

        data = {
            'first_name': 'Foo',
            'last_name': 'Bar',
            'contact_email': True,
            'email': 'foo@bar.com'
        }
        response = default_enquiry_form(self.make_request('post', '/', data, ajax=True), None, {}, Enquiry)
        self.assertEqual(
            '{"errors":{"message":["This field is required."]},"success":false}',
            response.content
        )


    @patch('cubane.enquiry.views.validate_captcha')
    def test_should_present_message_if_captcha_failed(self, validate_captcha):
        validate_captcha.return_value = False
        request, response = self._create_form()
        self.assertEqual({}, response.get('enquiry_form').errors)
        self.assertMessage(request, 'Please tick the checkbox at the bottom of the form to prevent SPAM.')


    @patch('cubane.enquiry.views.validate_captcha')
    def test_should_present_message_if_enquiry_email_not_configured(self, validate_captcha):
        validate_captcha.return_value = True
        request, response = self._create_form()
        self.assertMessage(
            request,
            'Our enquiry form isn\'t working at the moment because we don\'t have an email address yet.'
        )


    @patch('cubane.enquiry.views.validate_captcha')
    def test_should_return_ajax_message_if_enquiry_email_not_configured(self, validate_captcha):
        validate_captcha.return_value = True
        request, response = self._create_form(ajax=True)
        self.assertEqual(
            '{"errors":{"__all__":["Our enquiry form isn\'t working at the moment because we don\'t have an email address yet. Please use other means of contacting us."]},"success":false}',
            response.content
        )


    @patch('cubane.enquiry.views.validate_captcha')
    def test_form_submitted_successfully_with_valid_captcha(self, validate_captcha):
        settings = Settings.objects.create(enquiry_email='foo@bar.com')

        try:
            validate_captcha.return_value = True
            request, response = self._create_form()

            # page redirect and system success message
            self.assertIsInstance(response, HttpResponseRedirect)
            self.assertMessage(request, 'Thank you for your enquiry. We will contact you shortly.')
        finally:
            settings.delete()


    @patch('cubane.enquiry.views.validate_captcha')
    def test_ajax_form_submitted_successfully_with_valid_captcha(self, validate_captcha):
        settings = Settings.objects.create(enquiry_email='foo@bar.com')

        try:
            validate_captcha.return_value = True
            request, response = self._create_form(ajax=True)

            # page redirect and system success message
            self.assertEqual(
                '{"success":true}',
                response.content
            )
        finally:
            settings.delete()


    def _create_form(self, data={}, ajax=False):
        formdata = {
            'first_name': 'Foo',
            'last_name': 'Bar',
            'email': 'foo@bar.com',
            'contact_email': True,
            'message': 'Test'
        }
        formdata.update(data)
        request = self.make_request('post', '/', formdata, ajax)
        return request, default_enquiry_form(request, None, {}, Enquiry)


class EnquiryViewTestCase(CubaneTestCase):
    def test_enquiry_view_should_list_enquiries_order_by_date_decending(self):
        view = EnquiryView()
        queryset = view._get_objects(request=None)
        self.assertEqual(Enquiry, queryset.model)
        self.assertEqual(['-created_on'], queryset.query.order_by)