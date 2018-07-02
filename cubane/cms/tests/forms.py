# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test import RequestFactory
from django.test.utils import override_settings
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.cache import SessionStore
from cubane.tests.base import CubaneTestCase
from cubane.blog.models import BlogPost
from cubane.blog.forms import BlogPostForm
from cubane.cms.forms import *
from cubane.cms.views import fake_request, get_cms_settings, get_settings_model
from cubane.cms.models import Page
from cubane.testapp.models import Settings, CustomChildPage
from cubane.testapp.forms import SettingsForm, CustomPageForm, CustomChildPageForm
import datetime
import mock


class CmsFormsTestCase(CubaneTestCase):
    def tearDown(self):
        BlogPost.objects.all().delete()
        Page.objects.all().delete()


    def create_page(self, title, template='testapp/page.html', nav='header', entity_type=None, seq=0, legacy_url=None, identifier=None, parent=None):
        p = Page(
            title=title,
            slug=slugify(title),
            template=template,
            _nav=nav,
            entity_type=entity_type,
            seq=seq,
            legacy_url=legacy_url,
            identifier=identifier,
            parent=parent
        )
        p.save()
        return p


    def create_child_page(self, number, page=None):
        if page == None:
            page = self.page
        c = BlogPost(
            title='Child Page %s' % number,
            slug=slugify('Child Page %s' % number),
            template='testapp/page.html',
            page=page,
            seq=number
        )
        c.save()
        return c


    def create_settings_with_homepage(self, page):
        settings = get_settings_model()()
        settings.homepage = page
        settings.save()
        page.is_homepage = True
        page.save()
        return settings


    def _create_settings_data(self, settings=None, additional_data={}):
        data = {
            'contact_page': self.contact_page.pk,
            'homepage': self.homepage.pk,
            'default_404': self.default_404.pk,
            'default_encoding': 'utf_8',
            'name': 'Name',
            'address1': 'Address 1',
            'city': 'Norwich',
            'county': 'Norfolk',
            'country': 'GB',
            'order_mode': 2,
            'enquiry_email': 'info@foo.com',
            'enquiry_from': 'website@foo.com',
            'enquiry_reply': 'info@foo.com',
            'max_products_per_page': 100,
            'order_id': 'numeric',
            'max_quantity': 10,
            'mail_from_address': 'website@foo.com',
            'mail_notify_address': 'info@foo.com',
            'related_products_to_show': 5,
            'products_per_page': 9,
            '_cubane_instance_checksum': settings.get_checksum() if settings else None
        }
        data.update(additional_data)
        return data


class CmsFormsBrowseCmsModelFieldTestCase(CubaneTestCase):
    def test_browse_cms_model_field(self):
        field = BrowseCmsModelField(model=Page)
        self.assertEqual(Page, field.queryset.model)
        self.assertEqual(Page._meta.verbose_name_plural, field.name)


class CmsFormLegacyUrlTestCase(CubaneTestCase):
    def setUp(self):
        self.request = fake_request(path='')


    def _getLegacyPath(self, url):
        form = PageForm({
            'slug': 'slug',
            'template': 'testapp/page.html',
            'title': 'title',
            'identifier': None,
            'legacy_url': url,
            '_cubane_instance_checksum': None
        })

        form.configure(self.request, None, False)
        form.is_valid()

        return form.cleaned_data.get('legacy_url')


    def test_should_return_empty_string_or_none_if_path_is_not_presented(self):
        self.assertNoneOrEmpty(self._getLegacyPath(None))
        self.assertNoneOrEmpty(self._getLegacyPath(''))


    def test_should_return_path(self):
        self.assertEqual('/path', self._getLegacyPath('/path'))


    def test_should_return_path_without_domain(self):
        self.assertEqual('/path', self._getLegacyPath('http://test.com/path'))


    def test_should_return_path_without_port_number(self):
        self.assertEqual('/path', self._getLegacyPath('http://test.com:81/path'))


    def test_should_return_path_with_query_string(self):
        self.assertEqual('/path?test=1&test=2', self._getLegacyPath('http://test.com/path?test=1&test=2'))


    def test_should_return_path_without_fragments(self):
        self.assertEqual('/path/?test=1&test=2', self._getLegacyPath('/path/?test=1&test=2#fragment'))
        self.assertEqual('/path/', self._getLegacyPath('/path/#test'))


@CubaneTestCase.complex()
class CmsFormsMetaPreviewWidgetTestCase(CmsFormsTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.page = self.create_page('Page')


    def test_meta_preview_widget_returns_html(self):
        widget = MetaPreviewWidget()
        form = CustomPageForm()
        form.configure(self.request, instance=self.page, edit=True)
        widget.attrs = {'form': form}
        rendered_widget = widget.render('_meta_title', 'Title')
        self.assertIn('class="meta-preview"', rendered_widget)
        self.assertIn('Page', rendered_widget)


    def test_meta_preview_widget_should_remove_admin_prefix(self):
        widget = MetaPreviewWidget()
        form = CustomPageForm()
        form.configure(self.request, instance=self.page, edit=True)
        widget.attrs = {'form': form, 'path': '/admin/pages/edit/?pk=1'}
        rendered_widget = widget.render('_meta_title', 'Title')
        self.assertIn('class="meta-preview"', rendered_widget)
        self.assertIn('Page', rendered_widget)


    def test_meta_preview_widget_with_child_page(self):
        child_page = self.create_child_page(1)
        widget = MetaPreviewWidget()
        form = CustomChildPageForm()
        form.configure(self.request, instance=child_page, edit=True)
        widget.attrs = {'form': form}
        rendered_widget = widget.render('_meta_title', 'Title')
        try:
            self.assertIn('class="meta-preview"', rendered_widget)
            self.assertIn('Page', rendered_widget)
        finally:
            child_page.delete()


    def test_meta_preview_widget_with_child_page_not_linked(self):
        child_page = self.create_child_page(1)
        child_page.page = None
        child_page.save()
        widget = MetaPreviewWidget()
        form = CustomChildPageForm()
        form.configure(self.request, instance=child_page, edit=True)
        widget.attrs = {'form': form}
        rendered_widget = widget.render('_meta_title', 'Title')
        try:
            self.assertIn('class="meta-preview"', rendered_widget)
            self.assertIn('Page', rendered_widget)
        finally:
            child_page.delete()


@CubaneTestCase.complex()
class CmsPageFormBaseTestCase(CmsFormsTestCase):
    def setUp(self):
        self.page = self.create_page('Page', entity_type='BlogPost', identifier='blog')


    def test_clean_slug_should_be_valid_when_editing_an_existing_page(self):
        form = self._create_form(self.page, edit=True)
        self.assertTrue(form.is_valid())


    def test_should_raise_error_when_slug_collides_with_other_page(self):
        form = self._create_form(edit=False)
        self.assertFalse(form.is_valid())
        self.assertEqual({'slug': [PageForm.ERROR_SLUG_COLLISION]}, form.errors)


    def test_should_raise_error_when_slug_has_not_changed_on_duplication(self):
        form = self._create_form(self.page, is_duplicate=True)
        self.assertFalse(form.is_valid())
        self.assertEqual({'slug': [PageForm.ERROR_SLUG_COLLISION]}, form.errors)


    def test_should_raise_error_when_slug_collides_with_child_page_attached_to_homepage(self):
        child_page = self.create_child_page(1, self.page)
        settings = self.create_settings_with_homepage(self.page)
        form = self._create_form(edit=False, slug='child-page-1')
        self.assertFalse(form.is_valid())
        self.assertEqual({'slug': [PageForm.ERROR_SLUG_COLLISION]}, form.errors)
        settings.delete()


    def test_should_raise_error_when_slug_collides_with_reserved_name(self):
        form = self._create_form(self.page, edit=True, slug='admin')
        self.assertFalse(form.is_valid())
        self.assertEqual({'slug': [PageForm.ERROR_SLUG_SYSTEM_NAME]}, form.errors)


    def test_should_raise_error_when_identifier_has_invalid_format(self):
        form = self._create_form(self.page, edit=True, identifier='3NotCorrectIdentifierFormat')
        self.assertFalse(form.is_valid())
        self.assertEqual({'identifier': [PageForm.ERROR_IDENTIFIER_INVALID_FORMAT]}, form.errors)


    def test_should_raise_error_when_identifier_collides_with_existing_page(self):
        form = self._create_form(slug='test', edit=False, identifier='blog')
        self.assertFalse(form.is_valid())
        self.assertEqual({'identifier': [PageForm.ERROR_IDENTIFIER_COLLISION]}, form.errors)


    @override_settings(PAGE_HIERARCHY=False)
    def test_should_hide_parent_page_field_if_no_hierarchy_is_enabled(self):
        form = self._create_form(slug='test', edit=False)
        self.assertFalse('parent' in form.fields)


    @override_settings(PAGE_HIERARCHY=True)
    def test_should_show_parent_page_field_if_hierarchy_is_enabled(self):
        form = self._create_form(slug='test', edit=False)
        self.assertTrue('parent' in form.fields)


    def _create_form(self, page=None, edit=False, is_duplicate=False, slug='page', identifier=None):
        form = PageForm({
            'slug': slug,
            'template': 'testapp/page.html',
            'title': 'Page 1',
            'identifier': identifier,
            '_cubane_instance_checksum': page.get_checksum() if page else None
        })
        request = fake_request(path='')
        form.is_duplicate = is_duplicate
        form.configure(request, page, edit=edit)
        return form


@CubaneTestCase.complex()
class CmsChildPageFormTestCase(CmsFormsTestCase):
    def setUp(self):
        self.page = self.create_page('Page', entity_type='BlogPost')
        self.child_page = self.create_child_page('1', self.page)


    def test_child_page_form_is_valid(self):
        form = self._create_form(self.child_page, self.page, edit=True)
        self.assertTrue(form.is_valid())


    def test_should_raise_error_when_creating_a_child_page_for_the_same_page_with_colliding_slug(self):
        form = self._create_form(page=self.page, edit=False)
        self.assertFalse(form.is_valid())
        self.assertEqual({'slug': [PageForm.ERROR_SLUG_COLLISION]}, form.errors)


    def test_should_raise_error_when_colliding_with_page_as_child_page_of_homepage(self):
        settings = self.create_settings_with_homepage(self.page)
        another_page = self.create_page('Another Page')
        form = self._create_form(page=self.page, edit=False, slug='another-page')
        self.assertFalse(form.is_valid())
        self.assertEqual({'slug': [PageForm.ERROR_SLUG_COLLISION]}, form.errors)
        settings.delete()


    def test_should_raise_error_when_slug_collides_with_reserved_name_for_child_page_of_homepage(self):
        settings = self.create_settings_with_homepage(self.page)
        form = self._create_form(page=self.page, edit=False, slug='admin')
        self.assertFalse(form.is_valid())
        self.assertEqual({'slug': [PageForm.ERROR_SLUG_SYSTEM_NAME]}, form.errors)
        settings.delete()


    def _create_form(self, child_page=None, page=None, edit=False, is_duplicate=False, slug='child-page-1', title='Child Page 1', template='testapp/page.html'):
        form = BlogPostForm({
            'page': page.pk if page else None,
            '_cubane_instance_checksum': child_page.get_checksum() if child_page else None,
            'slug': slug,
            'template': template,
            'title': title
        })
        request = fake_request(path='')
        form.is_duplicate = is_duplicate
        form.configure(request, child_page, edit=edit)
        return form


class CmsSettingsFormTestCaseBase(CmsFormsTestCase):
    def setUp(self):
        self.homepage = self.create_page('Home')
        self.contact_page = self.create_page('Contact')
        self.default_404 = self.create_page('Page Not Found')


    def tearDown(self):
        super(CmsSettingsFormTestCaseBase, self).tearDown()
        [s.delete() for s in Settings.objects.all()]


@CubaneTestCase.complex()
@override_settings(CMS_TEST_SPF=False)
class CmsSettingsFormTestCase(CmsSettingsFormTestCaseBase):
    def test_settings_form(self):
        s = Settings()
        s.save()
        form = SettingsForm(self._create_settings_data(s))
        request = fake_request(path='')
        form.configure(request, s, edit=True)
        self.assertTrue(form.is_valid())


    @mock.patch('cubane.cms.models.get_child_page_model_choices')
    def test_settings_form_without_child_page_choices_should_remove_pagination_fields(self, get_child_page_model_choices):
        get_child_page_model_choices.return_value = []

        form = SettingsForm(self._create_settings_data())
        request = fake_request(path='')
        form.configure(request, None, edit=False)
        self.assertFalse(form.has_tab('Pagination'))
        self.assertIsNone(form.fields.get('page_size'))
        self.assertIsNone(form.fields.get('max_page_size'))


    @override_settings(INSTALLED_APPS=[])
    def test_settings_form_should_hide_directory_settings_if_no_directory_is_used(self):
        form = SettingsForm(self._create_settings_data())
        request = fake_request(path='')
        form.configure(request, None, edit=False)
        self.assertFalse(form.has_tab('Directory'))
        self.assertIsNone(form.fields.get('order_mode'))


    def test_settings_form_should_parse_page_size_as_integer(self):
        s = Settings()
        s.save()
        form = SettingsForm(self._create_settings_data(s, {
            'page_size': '10',
            'max_page_size': '100'
        }))
        request = fake_request(path='')
        form.configure(request, s, edit=True)
        self.assertTrue(form.is_valid())
        self.assertEqual(10, form.cleaned_data.get('page_size'))
        self.assertEqual(100, form.cleaned_data.get('max_page_size'))


    def test_settings_form_should_fail_if_max_page_size_it_lower_than_page_size(self):
        s = Settings()
        s.save()
        form = SettingsForm(self._create_settings_data(s, {
            'page_size': '10',
            'max_page_size': '5'
        }))
        request = fake_request(path='')
        form.configure(request, s, edit=True)
        self.assertFalse(form.is_valid())
        self.assertEqual({'max_page_size': ['Max. page size needs to be at least the page size of 10.']}, form.errors)


    def test_settings_form_should_raise_error_if_opening_time_specified_without_closing_time(self):
        form = SettingsForm(self._create_settings_data(None, {
            'monday_start': datetime.time()
        }))
        request = fake_request(path='')
        form.configure(request, None, edit=False)
        self.assertFalse(form.is_valid())
        self.assertEqual({'monday_close': [SettingsForm.ERROR_CLOSING_TIME_REQUIRED]}, form.errors)


    def test_settings_form_should_raise_error_if_closing_time_specified_without_opening_time(self):
        form = SettingsForm(self._create_settings_data(None, {
            'monday_close': datetime.time()
        }))
        request = fake_request(path='')
        form.configure(request, None, edit=False)
        self.assertFalse(form.is_valid())
        self.assertEqual({'monday_start': [SettingsForm.ERROR_OPENING_TIME_REQUIRED]}, form.errors)


    def test_settings_form_should_raise_error_if_closing_time_is_before_opening_time(self):
        form = SettingsForm(self._create_settings_data(None, {
            'monday_start': datetime.time(17, 0, 0),
            'monday_close': datetime.time(9, 0, 0)
        }))
        request = fake_request(path='')
        form.configure(request, None, edit=False)
        self.assertFalse(form.is_valid())
        self.assertEqual({'monday_start': [SettingsForm.ERROR_OPENING_TIME_MUST_COME_BEFORE_CLOSING_TIME]}, form.errors)


    def test_settings_form_should_raise_error_if_enquiry_email_and_reply_to_address_are_the_same(self):
        s = Settings()
        s.save()
        form = SettingsForm(self._create_settings_data(s, {
            'enquiry_email': 'foo@bar.com',
            'enquiry_from': 'foo@bar.com',
            'enquiry_reply': 'foo@bar.com'
        }))
        request = fake_request(path='')
        form.configure(request, s, edit=True)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'enquiry_from', SettingsForm.ERROR_FROM_EMAIL_CANNOT_BE_THE_SAME_AS_ENQUIRY_EMAIL)


@CubaneTestCase.complex()
@override_settings(CMS_TEST_SPF=True)
class CmsSettingsFormWithSPFValidationTestCase(CmsSettingsFormTestCaseBase):
    EXPECTED_SPF_ERROR_MSG = 'SPF check did not pass.'


    def test_should_raise_error_if_spf_check_fails(self):
        _, form = self._create_spf_test_form()
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(
            form,
            'enquiry_from',
            self.EXPECTED_SPF_ERROR_MSG
        )


    @override_settings(DEBUG=True)
    def test_should_soft_fail_if_spf_check_fails_in_debug(self):
        request, form = self._create_spf_test_form()
        self.assertTrue(form.is_valid())
        self.assertMessage(request, self.EXPECTED_SPF_ERROR_MSG)


    def _create_spf_test_form(self):
        s = Settings()
        s.save()
        form = SettingsForm(self._create_settings_data(s, {
            'enquiry_email': 'foo@gmail.com',
            'enquiry_from': 'website@gmail.com',
            'enquiry_reply': 'foo@gmail.com'
        }))
        factory = RequestFactory()
        request = factory.post('/')
        request.session = SessionStore()
        request._messages = FallbackStorage(request)
        form.configure(request, s, edit=True)
        return (request, form)