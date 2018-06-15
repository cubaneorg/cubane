# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.core import mail
from django.core.mail import send_mail
from cubane.tests.base import CubaneTestCase
from cubane.lib.mail import send_exception_email
from cubane.lib.mail import cubane_send_mail
from cubane.lib.mail import cubane_send_mail_template
from cubane.lib.mail import cubane_send_cms_mail
from cubane.lib.mail import cubane_send_cms_enquiry_mail
from cubane.lib.mail import cubane_send_shop_mail
from cubane.lib.mail import get_ordered_list_of_fields
from cubane.lib.mail import get_decoded_email_body
from cubane.cms.models import Page
from cubane.testapp.models import Settings
import re
import os


@CubaneTestCase.complex()
class LibMailBaseTestCase(CubaneTestCase):
    def tearDown(self):
        [p.delete() for p in Page.objects.all()]
        [s.delete() for s in Settings.objects.all()]


@CubaneTestCase.complex()
class LibSendExceptionEmailTestCase(LibMailBaseTestCase):
    """
    cubane.lib.mail.send_exception_email
    """
    def test_should_send_mail(self):
        try:
            b = 0 / 0
        except:
            send_exception_email()

        m = self.get_latest_email()
        self.assertTrue('integer division or modulo by zero' in m.subject)
        self.assertTrue('Exception Value: integer division or modulo by zero' in m.message().as_string())


@CubaneTestCase.complex()
class LibMailCubaneSendMailTestCase(LibMailBaseTestCase):
    """
    cubane.lib.mail.cubane_send_mail
    """
    def test_should_send_email_to_outbox(self):
        cubane_send_mail('test@innershed.com', 'Test', '<h1>Test</h1>')

        m = self.get_latest_email()
        self.assertTrue('test@innershed.com' in m.to, 'to address not found')
        self.assertEqual(m.subject, 'Test')
        self.assertTrue('<h1>Test</h1>' in m.message().as_string())


    def test_should_contain_reply_to_from_cms_settings(self):
        s = Settings()
        s.enquiry_reply = 'noreply@innershed.com'
        s.save()

        cubane_send_mail('test@innershed.com', 'Test', '<h1>Test</h1>')

        m = self.get_latest_email()
        self.assertTrue(m.extra_headers.get('Reply-To'), 'noreply@innershed.com')


    def test_should_add_single_attachement(self):
        filename = os.path.join(settings.BASE_PATH, 'templates', 'testapp', 'attachments', 'a.txt')
        cubane_send_mail('test@innershed.com', 'Test', '<h1>Test</h1>', filename)

        m = self.get_latest_email()
        self.assertTrue('test@innershed.com' in m.to, 'to address not found')
        self.assertEqual(m.subject, 'Test')
        self.assertTrue('<h1>Test</h1>' in m.message().as_string())
        self.assertEqual(1, len(m.attachments))

        # attachment
        filename, content, _ = m.attachments[0]
        self.assertEqual('a.txt', filename)
        self.assertEqual('This is an email attachment.', content)


    def test_should_add_multiple_attachments(self):
        filename_a = os.path.join(settings.BASE_PATH, 'templates', 'testapp', 'attachments', 'a.txt')
        filename_b = os.path.join(settings.BASE_PATH, 'templates', 'testapp', 'attachments', 'b.txt')
        filenames = [filename_a, filename_b]
        cubane_send_mail('test@innershed.com', 'Test', '<h1>Test</h1>', filenames)

        m = self.get_latest_email()
        self.assertTrue('test@innershed.com' in m.to, 'to address not found')
        self.assertEqual(m.subject, 'Test')
        self.assertTrue('<h1>Test</h1>' in m.message().as_string())
        self.assertEqual(2, len(m.attachments))

        # attachment a
        filename, content, _ = m.attachments[0]
        self.assertEqual('a.txt', filename)
        self.assertEqual('This is an email attachment.', content)

        # attachment b
        filename, content, _ = m.attachments[1]
        self.assertEqual('b.txt', filename)
        self.assertEqual('This is another email attachment.', content)


    def test_should_raise_exception_if_attachment_file_does_not_exist(self):
        with self.assertRaisesRegexp(IOError, 'No such file or directory'):
            cubane_send_mail('test@innershed.com', 'Test', '<h1>Test</h1>', 'does-not-exist')


    @override_settings(INSTALLED_APPS=[])
    def test_requires_cubane_cms_module(self):
        with self.assertRaises(ValueError):
            cubane_send_mail('test@innershed.com', 'Test', '<h1>Test</h1>')


@CubaneTestCase.complex()
class LibMailCubaneSendMailTemplateTestCase(LibMailBaseTestCase):
    """
    cubane.lib.mail.cubane_send_mail_template
    """
    def test_should_run_template_and_dispatch_email(self):
        cubane_send_mail_template(None, 'test@innershed.com', 'Test', 'testapp/mail/testmail.html', {
            'content': 'Test'
        })

        m = self.get_latest_email()
        self.assertTrue('test@innershed.com' in m.to, 'to address not found')
        self.assertEqual(m.subject, 'Test')
        self.assertTrue('<h1>Test</h1>' in m.message().as_string())


@CubaneTestCase.complex()
class LibMailCubaneSendCmsMailTestCase(LibMailBaseTestCase):
    """
    cubane.lib.mail.cubane_send_cms_mail
    """
    def test_should_render_cms_page_and_dispatch_email(self):
        page = Page()
        page.title = 'Test Page'
        page.slug = 'test'
        page.template = 'testapp/mail/enquiry_visitor.html'
        page.set_slot_content('content', '<h1>Test</h1>')
        page.save()

        cubane_send_cms_mail(None, 'test@innershed.com', 'Test', page)

        m = self.get_latest_email()
        self.assertTrue('test@innershed.com' in m.to, 'to address not found')
        self.assertEqual(m.subject, 'Test')
        self.assertTrue('<html><head><title>' in m.message().as_string())
        self.assertTrue('<h1>Test</h1>' in m.message().as_string())


    @override_settings(INSTALLED_APPS=[])
    def test_requires_cubane_cms_module(self):
        with self.assertRaisesRegexp(ValueError, 'cubane.cms required for sending cms page emails.'):
            cubane_send_cms_mail(None, 'test@innershed.com', 'Test', Page())


@CubaneTestCase.complex()
class LibMailCubaneSendCmsEnquiryMailTestCase(LibMailBaseTestCase):
    """
    cubane.lib.mail.cubane_send_cms_enquiry_mail
    """
    def test_should_render_cms_page_and_dispatch_email(self):
        page = Page()
        page.title = 'Test Page'
        page.slug = 'test'
        page.template = 'testapp/mail/enquiry_visitor.html'
        page.set_slot_content('content', '<h1>Test</h1>')
        page.save()

        s = Settings()
        s.enquiry_template = page
        s.save()

        cubane_send_cms_enquiry_mail(None, 'test@innershed.com', 'Test')

        m = self.get_latest_email()
        self.assertTrue('test@innershed.com' in m.to, 'to address not found')
        self.assertEqual(m.subject, 'Test')
        self.assertTrue('<html><head><title>' in m.message().as_string())
        self.assertTrue('<h1>Test</h1>' in m.message().as_string())


    @override_settings(INSTALLED_APPS=[])
    def test_requires_cubane_cms_module(self):
        with self.assertRaisesRegexp(ValueError, 'cubane.cms required for sending cms page emails.'):
            cubane_send_cms_enquiry_mail(None, 'test@innershed.com', 'Test')


@CubaneTestCase.complex()
class LibMailCubaneSendShopMailTestCase(LibMailBaseTestCase):
    """
    cubane.lib.mail.cubane_send_shop_mail
    """
    def test_should_render_cms_page_and_dispatch_email(self):
        page = Page()
        page.title = 'Test Page'
        page.slug = 'test'
        page.template = 'testapp/mail/enquiry_visitor.html'
        page.set_slot_content('content', '<h1>Test</h1>')
        page.save()

        settings = Settings()
        settings.shop_email_template = page
        settings.save()

        cubane_send_shop_mail(None, 'test@innershed.com', 'Test')

        m = self.get_latest_email()
        self.assertTrue('test@innershed.com' in m.to, 'to address not found')
        self.assertEqual(m.subject, 'Test')
        self.assertTrue('<html><head><title>' in m.message().as_string())
        self.assertTrue('<h1>Test</h1>' in m.message().as_string())


    @override_settings(INSTALLED_APPS=[])
    def test_requires_ishop_module(self):
        with self.assertRaisesRegexp(ValueError, 'cubane.ishop required for sending shop page emails.'):
            cubane_send_shop_mail(None, 'test@innershed.com', 'Test')


@CubaneTestCase.complex()
class LibMailCubaneGetOrderedListOfFieldsTestCase(LibMailBaseTestCase):
    """
    cubane.lib.mail.get_ordered_list_of_fields
    """
    def test_should_return_ordered_list_of_given_fields(self):
        d = {
            'foo': 'Bar',
            '_foo': '_Bar',
            'foo_bar': 'Foo and Bar',
            'numbers': [1, 2, 3]
        }
        for item in get_ordered_list_of_fields(d, d.items()):
            name = item.get('name')
            if name == 'foo':
                self.assertFalse(item.get('list'))
                self.assertEqual(item.get('value'), 'Bar')
                self.assertEqual(item.get('title'), 'Foo')
            elif name == '_foo':
                self.assertTrue(False, 'Field starting with _ should not appear in field list.')
            elif name == 'foo_bar':
                self.assertFalse(item.get('list'))
                self.assertEqual(item.get('value'), 'Foo and Bar')
                self.assertEqual(item.get('title'), 'Foo Bar')
            elif name == 'numbers':
                self.assertTrue(item.get('list'))
                self.assertEqual(item.get('value'), [1, 2, 3])
                self.assertEqual(item.get('title'), 'Numbers')
            else:
                self.assertTrue(False, 'Unknown field name: %s' % name)


@CubaneTestCase.complex()
class LibMailGetDecodedEmailBodyTestCase(LibMailBaseTestCase):
    """
    cubane.lib.mail.get_decoded_email_body
    """
    def test_should_decode_utf8_multipart(self):
        cubane_send_mail('test@innershed.com', 'Test', '<h1>Test</h1>')

        m = self.get_latest_email()
        text = get_decoded_email_body(m.message().as_string())
        self.assertEqual(text, '<h1>Test</h1>')

        try:
            text.decode('utf-8')
        except UnicodeError:
            self.assertTrue(False, 'decoded email message body is not UTF-8 encoded byte string.')


    def test_ignore_encoding_if_no_encoding_is_known_for_part(self):
        cubane_send_mail('test@innershed.com', 'Test', '<h1>Test</h1>')
        m = self.get_latest_email()
        raw_message = m.message().as_string()
        raw_message = re.sub(r'text\/plain; charset\="utf-8"', '', raw_message)

        text = get_decoded_email_body(raw_message)
        self.assertEqual(text, '<h1>Test</h1>')

        try:
            text.decode('utf-8')
        except UnicodeError:
            self.assertTrue(False, 'decoded email message body is not UTF-8 encoded byte string.')


    def test_should_decode_utf8_plain(self):
        send_mail('Test', 'Test Message', 'noreply@innershed.com', ['test@innershed.com'])

        m = self.get_latest_email()
        text = get_decoded_email_body(m.message().as_string())
        self.assertEqual(text, 'Test Message')

        try:
            text.decode('utf-8')
        except UnicodeError:
            self.assertTrue(False, 'decoded email message body is not UTF-8 encoded byte string.')
