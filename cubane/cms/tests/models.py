# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.utils.safestring import SafeText
from django.contrib.contenttypes.models import ContentType
from cubane.tests.base import CubaneTestCase
from cubane.cms.models import ChildPageWithoutParentError
from cubane.cms.models import PageBase, Page, MediaGallery, SettingsBase
from cubane.cms.models import get_child_page_models
from cubane.cms.models import get_child_page_model_choices
from cubane.media.models import Media
from cubane.testapp.models import CustomChildPage
from cubane.testapp.models import TestModel
from cubane.testapp.models import Settings
from cubane.testapp.models import TestDirectoryChildPageAggregator
from cubane.blog.models import BlogPost
from datetime import datetime


class CMSModelsEditableContentMixinTestCase(CubaneTestCase):
    def setUp(self):
        self.page = Page()


    def test_set_and_get_data(self):
        self.assertIsNone(self.page._data)
        self.page.set_data('Hello World')
        self.assertIsNotNone(self.page._data)
        self.assertEqual('Hello World', self.page.get_data())


    def test_set_and_get_slot_content(self):
        self.assertIsNone(self.page._data)
        self.page.set_slot_content('content', '<h1>Test</h1>')
        self.page.set_slot_content('introduction', '<h1>Introduction</h1>')
        self.assertIsNotNone(self.page._data)
        self.assertEqual('<h1>Test</h1>', self.page.get_slot_content('content'))
        self.assertEqual('<h1>Introduction</h1>', self.page.get_slot_content('introduction'))


    def test_get_slot_content_should_return_empty_for_empty_data(self):
        self.assertIsNone(self.page._data)
        self.assertEqual('', self.page.get_slot_content('content'))


    def test_get_slot_content_should_return_empty_for_non_existing_slot(self):
        self.page.set_data({'does-not-exist': 'Foo'})
        self.assertEqual('', self.page.get_slot_content('does-not-exist'))


    def test_set_slot_content_should_not_allow_setting_content_for_slot_that_does_not_exist(self):
        self.page.set_slot_content('does-not-exist', 'Foo')
        self.assertEqual({}, self.page.get_data())


    @override_settings(CMS_SLOTNAMES=['a', 'b'])
    def test_get_combined_slot_content_should_return_content_of_multiple_slots_combined(self):
        self.page.set_slot_content('a', 'Foo')
        self.page.set_slot_content('b', 'Bar')
        self.assertEqual('Foo Bar', self.page.get_combined_slot_content(['a', 'b']))


    @override_settings(CMS_SLOTNAMES=['a', 'b'])
    def test_get_combined_slot_content_should_ignore_empty_slot(self):
        self.page.set_slot_content('a', 'Foo')
        self.assertEqual('Foo', self.page.get_combined_slot_content(['a', 'b']))


    def test_slotnames_with_content(self):
        self.page.set_slot_content('content', '<h1>Test</h1>')
        self.page.set_slot_content('introduction', '<h1>Introduction</h1>')
        self.assertEqual(['content', 'introduction'], self.page.slotnames_with_content())


    def test_slotnames_with_content_with_empty_data(self):
        self.assertIsNone(self.page._data)
        self.assertEqual([], self.page.slotnames_with_content())


    def test_content_by_slot(self):
        self.page.set_slot_content('content', '<h1>Test</h1>')
        self.page.set_slot_content('introduction', '<h1>Introduction</h1>')
        self.assertEqual({
            'content':      '<h1>Test</h1>',
            'introduction': '<h1>Introduction</h1>'
        }, self.page.content_by_slot())


    def test_content_by_slot_with_image_rewrite(self):
        self.page.set_slot_content('content', '<img data-cubane-media-id="1"/>')
        images = {
            1: Media(id=1, caption='Test')
        }
        html = self.page.content_by_slot(images).get('content')
        self.assertIn('class="lazy-load-shape-original"', html)
        self.assertIn('style="padding-bottom:100.0%;"', html)
        self.assertIn('data-shape="original"', html)
        self.assertIn('data-path="/0/1/"', html)
        self.assertIn('data-blank="0"', html)
        self.assertIn('data-sizes="xx-small"', html);
        self.assertIn('<img src="http://www.testapp.cubane.innershed.com/media/shapes/original/xx-small/0/1/" alt="Test" title="Test">', html)


    def test_content_by_slot_with_empty_data(self):
        self.assertIsNone(self.page._data)
        self.assertEqual({}, self.page.content_by_slot())


class CMSModelsExcerptMixinTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(CMSModelsExcerptMixinTestCase, cls).setUpClass()
        cls.page = Page()
        cls.page.set_slot_content('content', '<p>Any <em>intelligent</em> fool can make things <b>bigger</b>, more complex, and more violent. It takes a touch of <em>genius</em> - <span class="highlight">and a lot of courage</span> - to move in the opposite direction.</p>')


    @override_settings(CMS_NO_AUTO_EXCERPT=False)
    def test_auto_excerpt(self):
        self.assertEqual(
            'Any intelligent fool can make things bigger, more complex, and more violent. It takes a touch of genius - and a lot of courage - to move in the opposite direction.',
            self.page.excerpt
        )


    @override_settings(CMS_NO_AUTO_EXCERPT=False)
    def test_auto_excerpt_shorten(self):
        self.assertEqual(
            'Any intelligent fool...',
            self.page.get_excerpt(20)
        )


    @override_settings(CMS_NO_AUTO_EXCERPT=True)
    def test_auto_excerpt_turned_off_should_return_empty(self):
        self.assertEqual('', self.page.excerpt)


    def test_excerpt_override(self):
        self.page._excerpt = 'I am convinced that He (God) does not play dice.'
        self.assertEqual('I am convinced that...', self.page.get_excerpt(20))
        self.page._excerpt = None


class CMSModelsPageBaseTestCase(CubaneTestCase):
    def setUp(self):
        self.page = PageBase()


    def test_get_form(self):
        from cubane.cms.forms import PageForm
        self.assertTrue(issubclass(self.page.get_form(), PageForm))


    def test_html_title_should_return_empty_string_if_title_not_defined(self):
        self.page.title = None
        self.assertEqual('', self.page.html_title)


    def test_html_title_should_return_title_replacing_underline_with_nbsp(self):
        self.page.title = 'Hello_World'
        self.assertEqual('Hello&nbsp;World', self.page.html_title)
        self.assertIsInstance(self.page.html_title, SafeText)


    def test_text_title_should_return_empty_string_if_title_not_defined(self):
        self.page.title = None
        self.assertEqual('', self.page.text_title)


    def test_text_title_should_return_title_replacing_underline_with_spaces(self):
        self.page.title = 'Hello_World'
        self.assertEqual('Hello World', self.page.text_title)


    def test_url_property_should_return_absolute_url(self):
        self.page.slug = 'test-page'
        self.assertEqual(self.page.get_absolute_url(), self.page.url)


    def test_get_absolute_url_should_reflect_slug(self):
        self.page.slug = 'test-page'
        self.assertEqual('http://www.testapp.cubane.innershed.com/test-page/', self.page.get_absolute_url())


    def test_get_filepath_should_return_path_to_cache_for_empty_slug(self):
        self.assertEqual('index.html', self.page.get_filepath())


    def test_get_filepath_should_return_path_to_cache_with_slug_prefix(self):
        self.page.slug = 'test-page'
        self.assertEqual('test-page/index.html', self.page.get_filepath())


    def test_get_slug_should_return_slug(self):
        self.page.slug = 'test-page'
        self.assertEqual(self.page.slug, self.page.get_slug())


    def test_get_fullslug_should_return_slug_with_slashes(self):
        self.page.slug = 'test-page'
        self.assertEqual('/test-page/', self.page.get_fullslug())


    def test_get_fullslug_should_return_single_slash_if_slug_is_empty(self):
        self.page.slug = ''
        self.assertEqual('/', self.page.get_fullslug())


    def test_unicode_should_return_title(self):
        self.page.title = 'Hello World'
        self.assertEqual(self.page.title, unicode(self.page))


class CMSModelsPageAbstractTestCase(CubaneTestCase):
    def setUp(self):
        self.page = Page()


    def test_get_nav_should_return_list_of_navigation_section_assigned(self):
        self.page.set_nav(['a', 'b'])
        self.assertEqual(['a', 'b'], self.page.get_nav())


    def test_get_nav_should_return_empty_list_if_no_navigation_is_assigned(self):
        self.assertEqual([], self.page.get_nav())


    def test_set_nav_should_clear_property_for_empty_list(self):
        self.page.set_nav(['a', 'b'])
        self.assertIsNotNone(self.page._nav)
        self.page.set_nav([])
        self.assertIsNone(self.page._nav)


    def test_get_nav_property(self):
        self.page.nav = ['a', 'b']
        self.assertEqual(['a', 'b'], self.page.nav)


    def test_get_entity_model_should_return_model_of_entity_used_for_child_pages_for_this_page(self):
        self.page.entity_type = 'CustomChildPage'
        self.assertTrue(issubclass(self.page.get_entity_model(), CustomChildPage))


    def test_get_entity_model_not_found(self):
        self.page.entity_type = 'DoesNotExist'
        self.assertIsNone(self.page.get_entity_model())


    def test_get_filepath_should_return_path_to_cache_for_empty_slug(self):
        self.assertEqual('index.html', self.page.get_filepath())


    def test_get_filepath_should_return_path_to_cache_with_slug_prefix(self):
        self.page.slug = 'test-page'
        self.assertEqual('test-page/index.html', self.page.get_filepath())


    def test_get_filepath_for_homepage_should_return_path_to_cache(self):
        self.page.is_homepage = True
        self.assertEqual('index.html', self.page.get_filepath())


    def test_get_filepath_for_homepage_should_ignore_slug(self):
        self.page.is_homepage = True
        self.page.slug = 'test-page'
        self.assertEqual('index.html', self.page.get_filepath())


    def test_get_slug_should_be_empty_for_homepage(self):
        self.page.is_homepage = True
        self.page.slug = 'test-page'
        self.assertEqual('', self.page.get_slug())


    def test_get_slug_should_return_slug_for_page_other_than_homepage(self):
        self.page.is_homepage = False
        self.page.slug = 'test-page'
        self.assertEqual('test-page', self.page.get_slug())


    def test_get_fullslug_for_homepage_should_be_slash_ignoring_slug(self):
        self.page.is_homepage = True
        self.page.slug = 'test-page'
        self.assertEqual('', self.page.get_fullslug())


    def test_get_fullslug_for_page_should_contain_slug_with_slashes(self):
        self.page.is_homepage = False
        self.page.slug = 'test-page'
        self.assertEqual('/test-page/', self.page.get_fullslug())


    def test_get_absolute_url_should_return_root_url_for_homepage(self):
        self.page.is_homepage = True
        self.page.slug = 'test-page'
        self.assertEqual('http://www.testapp.cubane.innershed.com/', self.page.get_absolute_url())


    @override_settings(APPEND_SLASH=True)
    def test_get_absolute_url_should_return_full_slug_ending_with_slash_with_append_slash_option(self):
        self.page.is_homepage = False
        self.page.slug = 'test-page'
        self.assertEqual('http://www.testapp.cubane.innershed.com/test-page/', self.page.get_absolute_url())


    @override_settings(APPEND_SLASH=False)
    def test_get_absolute_url_should_return_full_slug_ending_with_slash_without_append_slash_option(self):
        self.page.is_homepage = False
        self.page.slug = 'test-page'
        self.assertEqual('http://www.testapp.cubane.innershed.com/test-page', self.page.get_absolute_url())


class CMSModelsPageTestCase(CubaneTestCase):
    def setUp(self):
        self.page = Page()


    def test_get_backend_section_group_should_return_none_if_not_set(self):
        self.assertFalse(hasattr(Page.Listing, 'group'))
        self.assertIsNone(self.page.get_backend_section_group())


    def test_get_backend_section_group_should_return_group_name(self):
        Page.Listing.group = 'testgroup'
        self.assertEqual(Page.Listing.group, self.page.get_backend_section_group())
        delattr(Page.Listing, 'group')


    def test_save_should_auto_generate_slug_if_no_slug_is_present(self):
        self.page.title = 'Hello World'
        self.page.save()
        self.assertEqual('hello-world', self.page.slug)
        self.page.delete()


    def test_save_should_not_auto_generate_slug_if_slug_is_present(self):
        self.page.title = 'Hello World'
        self.page.slug = 'already-present'
        self.page.save()
        self.assertEqual('already-present', self.page.slug)
        self.page.delete()


    def test_gallery_property_should_return_attached_media_in_seq(self):
        self.page.title = 'Test'
        self.page.save()

        content_type = ContentType.objects.get_for_model(self.page.__class__)
        names = ['c', 'b', 'a']
        for seq, name in enumerate(names, start=1):
            m = Media(caption=name)
            m.save()

            mg = MediaGallery()
            mg.media = m
            mg.content_type = content_type
            mg.target_id = self.page.pk
            mg.seq = seq
            mg.save()

        self.assertEqual(names, [m.caption for m in self.page.gallery])

        [mg.delete() for mg in MediaGallery.objects.all()]
        [m.delete() for m in Media.objects.all()]
        self.page.delete()


    def test_to_dict(self):
        self.page.id = 1
        self.page.title = 'Hello World'
        self.page.slug = 'hello-world'

        self.assertEqual({
            'foo': 'bar',
            'title': 'Hello World',
            'url': 'http://www.testapp.cubane.innershed.com/hello-world/',
            'url_path': '/hello-world/',
            'slug': 'hello-world',
            'id': 1
        }, self.page.to_dict({'foo': 'bar'}))


class CMSModelsChildPageTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(CMSModelsChildPageTestCase, cls).setUpClass()
        cls.homepage = Page(is_homepage=True, title='Homepage')
        cls.homepage.save()

        cls.homechild = CustomChildPage(title='Home Child', page=cls.homepage)
        cls.homechild.save()

        cls.page = Page(title='Page', entity_type='CustomChildPage')
        cls.page.save()

        cls.child = CustomChildPage(title='Child', page=cls.page)
        cls.child.save()


    @classmethod
    def tearDownClass(cls):
        cls.child.delete()
        cls.homechild.delete()

        cls.page.delete()
        cls.homepage.delete()
        super(CMSModelsChildPageTestCase, cls).tearDownClass()


    def test_get_form_should_return_default_entity_form(self):
        from cubane.cms.forms import ChildPageForm
        self.assertTrue(issubclass(self.child.get_form(), ChildPageForm))


    def test_get_filepath_for_homepage_child_should_obmit_slug_of_parent_page(self):
        self.assertEqual('home-child/index.html', self.homechild.get_filepath())


    def test_get_filepath_for_ordinary_child_should_contain_slug_of_parent_page(self):
        self.assertEqual('page/child/index.html', self.child.get_filepath())


    def test_get_filepath_for_child_page_without_parent_should_raise_exception(self):
        page = self.child.page
        self.child.page = None
        try:
            with self.assertRaises(ChildPageWithoutParentError):
                self.child.get_filepath()
        finally:
            self.child.page = page


    def test_get_slug_simply_returns_slug(self):
        self.assertEqual('home-child', self.homechild.get_slug())
        self.assertEqual('child', self.child.get_slug())


    def test_get_fullslug_for_homepage_child_should_obmit_slug_of_parent_page(self):
        self.assertEqual('/home-child/', self.homechild.get_fullslug())


    def test_get_fullslug_for_ordinary_child_page_should_contain_slug_of_parent_page(self):
        self.assertEqual('/page/child/', self.child.get_fullslug())


    def test_get_fullslug_for_child_page_without_parent_should_raise_exception(self):
        page = self.child.page
        self.child.page = None
        try:
            with self.assertRaises(ChildPageWithoutParentError):
                self.child.get_fullslug()
        finally:
            self.child.page = page


    def test_get_fullslug_for_childpage_without_slug_should_fallback_to_parent_page_slug(self):
        slug = self.child.slug
        self.child.slug = None

        self.assertEqual('/page/', self.child.get_fullslug())

        self.child.slug = slug


    def test_child_pages_dont_have_identifiers(self):
        with self.assertRaises(AttributeError):
            self.child.identifier = 'test'
        self.assertIsNone(self.child.identifier)


    @override_settings(APPEND_SLASH=True)
    def test_get_absolute_url_for_homepage_child_should_obmit_slug_of_parent_page_with_append_slash(self):
        self.assertEqual('http://www.testapp.cubane.innershed.com/home-child/', self.homechild.get_absolute_url())


    @override_settings(APPEND_SLASH=True)
    def test_get_absolute_url_for_ordinary_child_should_contain_slug_of_parent_page_with_append_slash(self):
        self.assertEqual('http://www.testapp.cubane.innershed.com/page/child/', self.child.get_absolute_url())


    @override_settings(APPEND_SLASH=False)
    def test_get_absolute_url_for_homepage_child_should_obmit_slug_of_parent_page_without_append_slash(self):
        self.assertEqual('http://www.testapp.cubane.innershed.com/home-child', self.homechild.get_absolute_url())


    @override_settings(APPEND_SLASH=False)
    def test_get_absolute_url_for_ordinary_child_should_contain_slug_of_parent_page_without_append_slash(self):
        self.assertEqual('http://www.testapp.cubane.innershed.com/page/child', self.child.get_absolute_url())


class CMSModelsEntityTestCase(CubaneTestCase):
    def setUp(self):
        self.entity = TestModel()


    def test_get_backend_section_group_should_return_none_if_not_set(self):
        self.assertFalse(hasattr(TestModel.Listing, 'group'))
        self.assertIsNone(self.entity.get_backend_section_group())


    def test_get_backend_section_group_should_return_group_name(self):
        TestModel.Listing.group = 'testgroup'
        self.assertEqual(TestModel.Listing.group, self.entity.get_backend_section_group())
        delattr(TestModel.Listing, 'group')


class CMSModelsDefaultPagesSettingsMixinTestCase(CubaneTestCase):
    def setUp(self):
        self.settings = Settings()


    def test_get_default_pages_pks_should_be_empty_by_default(self):
        self.assertEqual([], self.settings.get_default_pages_pks())


    def test_get_default_pages_pks_should_return_pks_for_default_pages_as_list(self):
        home = Page()
        contact = Page()
        _404 = Page()
        enquiry = Page()

        home.save()
        contact.save()
        _404.save()
        enquiry.save()

        self.settings.homepage = home
        self.settings.contact_page = contact
        self.settings.default_404 = _404
        self.settings.enquiry_template = enquiry

        self.assertEqual([
            home.pk,
            contact.pk,
            _404.pk,
            enquiry.pk
        ], self.settings.get_default_pages_pks())

        home.delete()
        contact.delete()
        _404.delete()
        enquiry.delete()


    def test_get_default_pages_pks_should_return_pks_for_default_pages_as_list_abmitting_not_assigned_pages(self):
        contact = Page()
        enquiry = Page()

        contact.save()
        enquiry.save()

        self.settings.contact_page = contact
        self.settings.enquiry_template = enquiry

        self.assertEqual([
            contact.pk,
            enquiry.pk
        ], self.settings.get_default_pages_pks())

        contact.delete()
        enquiry.delete()


class CMSModelsSocialMediaSettingsMixinTestCase(CubaneTestCase):
    def test_has_social_media_should_be_false_if_no_social_media_assigned(self):
        s = Settings()
        self.assertFalse(s.has_social_media)


    def test_has_social_media_should_be_true_if_at_least_one_social_media_is_assigned(self):
        settings = Settings()
        for attr, _ in settings.social_links:
            s = Settings()
            setattr(s, attr, 'social-media-url')
            self.assertTrue(s.has_social_media)


class CMSModelsPaginationSettingsMixinTestCase(CubaneTestCase):
    def setUp(self):
        self.settings = Settings()
        self.settings.paging_enabled = True
        self.settings.paging_child_pages = 'testapp_customchildpage'


    def test_pagination_should_be_enabled_if_enabled_in_general_and_child_page_is_enabled(self):
        self.assertTrue(self.settings.paging_enabled_for(CustomChildPage))


    def test_pagination_should_be_disabled_if_disabled_in_general(self):
        self.settings.paging_enabled = False
        self.assertFalse(self.settings.paging_enabled_for(CustomChildPage))


    def test_pagination_should_be_disabled_if_child_page_not_enabled(self):
        self.settings.paging_child_pages = None
        self.assertFalse(self.settings.paging_enabled_for(CustomChildPage))


class CMSModelsOpeningTimesSettingsMixinTestCase(CubaneTestCase):
    def setUp(self):
        self.settings = Settings()


    def test_weekday_names(self):
        self.assertEqual([
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'friday',
            'saturday',
            'sunday'
        ], self.settings.full_week_days)


    def test_set_opening_time_with_invalid_day_should_return_false(self):
        self.assertFalse(self.settings.set_opening_time('does-not_exist', 'start', '09:00'))


    def test_set_opening_time_with_invalid_bound_should_return_false(self):
        self.assertFalse(self.settings.set_opening_time('friday', 'does-not-exist', '09:00'))


    def test_set_opening_time_with_invalid_value_should_return_false(self):
        self.assertFalse(self.settings.set_opening_time('friday', 'start', 15))


    def test_opening_times_should_return_all_opening_times(self):
        self.settings.set_opening_times(self.settings.week_days, '09:00', '17:00')
        self.settings.set_opening_times(self.settings.weekend_days, '10:00', '16:00')
        self.assertEqual([
            ('monday',    datetime(1900, 1, 1,  9, 0), datetime(1900, 1, 1, 17, 0)),
            ('tuesday',   datetime(1900, 1, 1,  9, 0), datetime(1900, 1, 1, 17, 0)),
            ('wednesday', datetime(1900, 1, 1,  9, 0), datetime(1900, 1, 1, 17, 0)),
            ('thursday',  datetime(1900, 1, 1,  9, 0), datetime(1900, 1, 1, 17, 0)),
            ('friday',    datetime(1900, 1, 1,  9, 0), datetime(1900, 1, 1, 17, 0)),
            ('saturday',  datetime(1900, 1, 1, 10, 0), datetime(1900, 1, 1, 16, 0)),
            ('sunday',    datetime(1900, 1, 1, 10, 0), datetime(1900, 1, 1, 16, 0))
        ], self.settings.opening_times)


    def test_same_opening_times_for_weekdays_should_return_true_if_same_opening_times(self):
        self.settings.set_opening_times(self.settings.full_week_days, '09:00', '17:00')
        self.assertTrue(self.settings.same_opening_times_for_weekdays)


    def test_same_opening_times_for_weekdays_should_return_false_if_not_same_opening_times(self):
        self.settings.set_opening_times(self.settings.week_days, '09:00', '17:00')
        self.settings.set_opening_times('friday', '10:00', '16:00')
        self.assertFalse(self.settings.same_opening_times_for_weekdays)


class CMSModelsSettingsBaseTestCase(CubaneTestCase):
    def test_get_form_should_return_default_settings_form(self):
        from cubane.cms.forms import SettingsForm
        self.assertTrue(issubclass(SettingsBase.get_form(), SettingsForm))


class CMSModelsHelpersTestCase(CubaneTestCase):
    def test_get_child_page_models_should_return_a_list_of_all_known_child_page_models(self):
        self.assertEqual([
            BlogPost,
            CustomChildPage,
            TestDirectoryChildPageAggregator,
        ], get_child_page_models())


    def test_get_child_page_model_choices_should_return_choices_for_all_known_child_page_models(self):
        self.assertEqual([
            ('blog_blogpost',                            'Blog Posts'),
            ('testapp_customchildpage',                  'Custom Child Pages'),
            ('testapp_testdirectorychildpageaggregator', 'Test Directory Child Page Aggregators')
        ], get_child_page_model_choices())