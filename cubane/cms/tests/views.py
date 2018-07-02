# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.http.response import HttpResponsePermanentRedirect
from django.test.utils import override_settings
from django.template.context import Context
from django.template.defaultfilters import slugify
from django.db.models.query import QuerySet
from django.test.client import RequestFactory
from django.contrib.auth.models import User
from cubane.tests.base import CubaneTestCase
from cubane.cms.tests.base import CMSTestBase
from cubane.cms.views import *
from cubane.cms.models import Page, MediaGallery
from cubane.directory.models import DirectoryTag
from cubane.blog.models import BlogPost
from cubane.testapp.models import TestModel, Settings
from cubane.testapp.forms import EnquiryForm
from cubane.testapp.models import TestGroupedModelA, TestDirectoryContent, TestDirectoryCategory
from cubane.testapp.views import TestAppCMS
from mock import Mock, patch
from datetime import datetime
import json


def create_fake_request(path='/', cms=None):
    """
    Create a fake request object that is primarily used when calling into the
    CMS from command line.
    """
    factory = RequestFactory()
    request = factory.get(path)
    request.user = User(is_staff=True, is_superuser=True)
    request.cms = cms
    request.settings = cms.settings if cms else None
    request.session = SessionStore()
    return request


class CMSViewsGetCMSTestCase(CubaneTestCase):
    def test_get_cms_should_return_cms_class_instance(self):
        cms = get_cms()
        self.assertIsInstance(cms, self.testapp_cms_class)


    def test_get_cms_should_return_new_instances_every_time(self):
        cms = get_cms()
        self.assertNotEqual(cms, get_cms())


    @override_settings(CMS=None)
    def test_get_cms_should_raise_if_not_configured(self):
        with self.assertRaises(ValueError):
            get_cms(ignore_cache=True)


    @override_settings(CMS='does-not-exist-class-name')
    def test_get_cms_should_raise_if_class_does_not_exist(self):
        with self.assertRaises(ValueError):
            get_cms(ignore_cache=True)


    @property
    def testapp_cms_class(self):
        from cubane.testapp.views import TestAppCMS
        return TestAppCMS


class CMSViewsPageContextSeqTestCase(CMSTestBase):
    @classmethod
    def setUpClass(cls):
        super(CMSViewsPageContextSeqTestCase, cls).setUpClass()
        cls.create_pages()
        cls.cms = get_cms()
        cls.context = cls.cms.get_page_context(create_fake_request(), slug='page-0')
        cls.template_context = cls.context.get_template_context()


    @classmethod
    def tearDownClass(cls):
        Page.objects.all().delete()
        BlogPost.objects.all().delete()
        super(CMSViewsPageContextSeqTestCase, cls).tearDownClass()


    @classmethod
    def create_pages(cls):
        for i in range(0, 2):
            title = 'Page %s' % i
            page = cls.create_page(title, seq=i, entity_type='BlogPost')

        page = Page.objects.get(slug='page-0')
        for i in range(0, 2):
            title = 'Child Page %s' % i
            cls.create_child_page_for_page(page, title, seq=i)


    def test_page_context_gives_correct_seq_for_pages(self):
        page_object_ids = [p.id for p in Page.objects.all().order_by('seq')]
        nav_item_ids = [item.get('id') for item in self.template_context['nav']['header']]
        self.assertEqual(page_object_ids, nav_item_ids)


    def test_page_context_gives_correct_seq_for_child_pages(self):
        child_page_ids = [p.id for p in BlogPost.objects.all().order_by('seq')]
        context_child_page_ids = [p.id for p in self.context.child_pages]
        self.assertEqual(context_child_page_ids, child_page_ids)


    def test_page_context_navigation_has_correct_pages(self):
        nav_items = self.template_context['nav']['header']
        self.assertEqual(len(nav_items), 2)


class CMSViewsPageContextRedirectAppendSlashTestCase(CMSTestBase):
    @classmethod
    def setUpClass(cls):
        super(CMSViewsPageContextRedirectAppendSlashTestCase, cls).setUpClass()
        cls.create_page('Page')


    @classmethod
    def tearDownClass(cls):
        Page.objects.all().delete()
        super(CMSViewsPageContextRedirectAppendSlashTestCase, cls).tearDownClass()


    def test_page_context_redirect_append_slash_should_append_slash(self):
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path='page'), slug='page')
        self.assertEqual(context._redirect_url, 'page/')
        self.assertEqual(context._is_redirect, True)


    def test_page_context_redirect_append_slash_should_pass_for_unresolved_url(self):
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path='testing'), slug='page')
        self.assertEqual(context._redirect_url, 'testing/')
        self.assertEqual(context._is_redirect, True)


    @override_settings(APPEND_SLASH=False)
    def test_page_context_redirect_append_slash_still_appends_slash_if_not_settings_append_slash(self):
        settings.APPEND_SLASH = False
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path='testing'), slug='page')
        self.assertEqual(context._redirect_url, 'testing/')


class CMSViewsPageContextBaseTestCase(CMSTestBase):
    def setUp(self):
        self.page = self.create_page('Page', entity_type='BlogPost')
        self.create_child_pages()
        self.child_page = BlogPost.objects.all()[0]


    def tearDown(cls):
        Page.objects.all().delete()
        BlogPost.objects.all().delete()


    def create_child_pages(self):
        for i in range(0, 10):
            self.create_child_page(i)


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


class CMSViewsPageContextTestCase(CMSViewsPageContextBaseTestCase):
    def test_should_return_context_for_homepage(self):
        self.set_settings_vars({'homepage': self.page})
        factory = RequestFactory()
        request = factory.get('/')
        cms = get_cms()
        context = cms.get_page_context(request, page=self.page)
        self.assertIsInstance(context, PageContext)


    def test_should_return_context_for_page(self):
        factory = RequestFactory()
        request = factory.get('/page')
        cms = get_cms()
        context = cms.get_page_context(request, page=self.page)
        self.assertIsInstance(context, PageContext)


    def test_should_return_context_for_child_page(self):
        factory = RequestFactory()
        request = factory.get('/page/child-page-1')
        cms = get_cms()
        context = cms.get_page_context(request, page=self.child_page)
        self.assertIsInstance(context, PageContext)


    def test_should_return_context_for_child_page_of_homepage(self):
        self.set_settings_vars({'homepage': self.page})
        factory = RequestFactory()
        request = factory.get('/page/child-page-1')
        cms = get_cms()
        context = cms.get_page_context(request, page=self.child_page)
        self.assertIsInstance(context, PageContext)


    def test_context_should_raise_404_for_child_page_without_parent_page(self):
        # deleting a page might leave a child page without its parent.
        # when attempting to render the child (without parent), 404 should be
        # raised (non-preview)...
        child = BlogPost()
        child.slug = 'post'
        child.save()

        factory = RequestFactory()
        request = factory.get('/page/post')
        cms = get_cms()
        with self.assertRaises(Http404):
            context = cms.get_page_context(request, page=child)


    def test_raises_404_if_default_404_page(self):
        page = self.create_page('Page Not Found', seq=1)
        settings = self.set_settings_vars({'default_404': page})
        request = create_fake_request(path='page-not-found/')
        request.settings = settings
        cms = get_cms()
        with self.assertRaises(Http404):
            cms.get_page_context(request, slug='page-not-found/')


    def test_raises_404_if_no_page_or_slug(self):
        def _get_page_context():
            cms = get_cms()
            cms.get_page_context(create_fake_request(path=''))
        self.assertRaises(Http404, _get_page_context)


    def test_raises_404_if_page_with_slug_does_not_exist(self):
        def _get_page_context():
            cms = get_cms()
            cms.get_page_context(create_fake_request(path=''), slug='test-page')
        self.assertRaises(Http404, _get_page_context)


    def test_creates_create_fake_request_if_no_request_given_and_page_given(self):
        cms = get_cms()
        context = cms.get_page_context(None, page=self.page)
        self.assertEqual(context.current_page, self.page)


    def test_allows_non_cms_content(self):
        page = TestModel()
        cms = get_cms()
        context = cms.get_page_context(None, page=page)
        self.assertEqual(page, context.current_page)


    def test_raises_error_for_childpage_on_childpage(self):
        with self.assertRaises(Http404):
            cms = get_cms()
            cms.get_page_context(create_fake_request(path=''), slug='page/child-page/test')


    def test_returns_homepage_if_empty_slug(self):
        self.set_settings_vars({'homepage': self.page})
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path=''), slug='')
        self.assertEqual(context.current_page, self.page)


    def test_should_redirect_if_matches_url_with_slash(self):
        factory = RequestFactory()
        request = factory.get('/non-standard-page')
        cms = get_cms()
        context = cms.get_page_context(request, slug='non-standard-page')
        self.assertTrue(context._is_redirect)
        self.assertEqual('/non-standard-page/', context._redirect_url)


    #
    # get_page_image_ids()
    #
    def test_get_page_image_ids_should_return_empty_list_for_content_that_does_not_contain_image_references(self):
        self.page.set_slot_content('content', '<p>Lorem ipsum</p>')
        self.page.save()
        cms = get_cms()
        media_ids = cms.get_page_context(create_fake_request(path='/'), slug='/page/').get_page_image_ids(self.page)
        self.assertEqual([], media_ids)


    def test_get_page_image_ids_should_return_list_of_image_ids(self):
        request = create_fake_request(path='/')
        self.page.set_slot_content('content', '<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed porttitor pellentesque dolor a sodales. Quisque eu erat in quam rutrum elementum. Fusce convallis sed lectus ut lobortis. Aliquam nec dictum nulla, a maximus nisl. Nulla interdum varius eros eu viverra. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Quisque gravida ut ex vitae pretium.<img src="/media/shapes/original/x-large/0/1/test.jpg" alt="" data-width="1005" data-height="670" data-cubane-lightbox="false" data-cubane-media-id="1" data-cubane-media-size="auto" data-mce-src="/media/shapes/original/x-large/0/1/test.jpg"></p>')
        self.page.save()
        cms = get_cms()
        media_ids = cms.get_page_context(request, slug='/page/').get_page_image_ids(self.page)
        self.assertEqual([1], media_ids)


    def test_get_page_image_ids_should_return_list_of_image_ids_matching_data_ikit_attribbutes_for_legacy_reasons(self):
        request = create_fake_request(path='/')
        self.page.set_slot_content('content', '<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed porttitor pellentesque dolor a sodales. Quisque eu erat in quam rutrum elementum. Fusce convallis sed lectus ut lobortis. Aliquam nec dictum nulla, a maximus nisl. Nulla interdum varius eros eu viverra. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Quisque gravida ut ex vitae pretium.<img src="/media/shapes/original/x-large/0/1/test.jpg" alt="" data-width="1005" data-height="670" data-ikit-lightbox="false" data-ikit-media-id="1" data-cubane-media-size="auto" data-mce-src="/media/shapes/original/x-large/0/1/test.jpg"></p>')
        self.page.save()
        cms = get_cms()
        media_ids = cms.get_page_context(request, slug='/page/').get_page_image_ids(self.page)
        self.assertEqual([1], media_ids)


    #
    # get_page_images()
    #
    def test_get_page_images_should_return_empty_dict_if_no_media_is_used_on_given_page(self):
        request = create_fake_request(path='/')
        image = Media(filename='test.jpg', caption='Test')
        image.save()
        self.page.set_slot_content('content', '<p>Lorem ipsum</p>')
        self.page.save()
        cms = get_cms()
        page_images = cms.get_page_context(request, slug='/page/').get_page_images(self.page, False)
        self.assertEqual({}, page_images)
        image.delete()


    def test_get_page_images_should_return_dict_of_media_instances(self):
        request = create_fake_request(path='/')
        image = Media(filename='test.jpg', caption='Test')
        image.save()
        self.page.set_slot_content('content', '<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed porttitor pellentesque dolor a sodales. Quisque eu erat in quam rutrum elementum. Fusce convallis sed lectus ut lobortis. Aliquam nec dictum nulla, a maximus nisl. Nulla interdum varius eros eu viverra. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Quisque gravida ut ex vitae pretium.<img src="/media/shapes/original/x-large/0/{id}/{caption}" alt="" data-width="1005" data-height="670" data-cubane-lightbox="false" data-cubane-media-id="{id}" data-cubane-media-size="auto" data-mce-src="/media/shapes/original/x-large/0/{id}/{caption}"></p>'.format(id=image.id, caption=image.caption))
        self.page.save()
        cms = get_cms()
        page_images = cms.get_page_context(request, slug='/page/').get_page_images(self.page, False)
        self.assertIsInstance(page_images, dict)
        self.assertEqual(page_images.values()[0], image)
        image.delete()


    #
    #
    #
    def test_returns_context_with_non_standard_cms_page(self):
        request = create_fake_request(path='non-standard-page/')
        cms = get_cms()
        context = cms.get_page_context(request, page='', slug='non-standard-page/')
        self.assertIsInstance(context, PageContext)


    def test_returns_none_for_wrong_default_pages(self):
        c = self.create_child_page(2)
        request = create_fake_request(path='page/')
        cms = get_cms()
        context = cms.get_page_context(request, page=c, slug='page/')
        self.assertEqual(context.get_default_page('home'), None)


class CMSViewsPageContextVisibilityTestCase(CMSViewsPageContextBaseTestCase):
    def test_should_raise_404_if_page_is_disabled(self):
        cms = get_cms()
        self.page.disabled = True
        self.page.save()
        try:
            with self.assertRaisesRegexp(Http404, 'There is no CMS page with the given slug'):
                cms.get_page_context(create_fake_request(path='/page/'), slug='/page/')
        finally:
            self.page.disabled = False
            self.page.save()


    def test_should_raise_404_if_render_specific_page_that_is_disabled(self):
        cms = get_cms()
        self.page.disabled = True
        self.page.save()
        try:
            with self.assertRaisesRegexp(Http404, 'Page is not visible'):
                cms.get_page_context(create_fake_request(path='/page/'), page=self.page)
        finally:
            self.page.disabled = False
            self.page.save()


    def test_should_raise_404_if_filtered_by_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(Page)
        cms = get_cms()
        try:
            with self.assertRaisesRegexp(Http404, 'There is no CMS page with the given slug'):
                cms.get_page_context(create_fake_request(path='/page/'), slug='/page/')
        finally:
            self.restore_filter_visibility(Page, _filter_visibility)


    def test_should_raise_404_if_render_specific_page_with_custom_visibility_checks(self):
        def is_visible():
            return False

        cms = get_cms()
        p = self.create_page('Disabled Page')
        p.is_visible = is_visible
        try:
            with self.assertRaisesRegexp(Http404, 'Page is not visible'):
                cms.get_page_context(create_fake_request(path='/disabled-page/'), page=p)
        finally:
            p.delete()


    def test_should_raise_404_for_legacy_url_of_disabled_page(self):
        p = self.create_page('Legacy Page', disabled=True, legacy_url='legacy.html')
        cms = get_cms()
        try:
            with self.assertRaisesRegexp(Http404, 'There is no CMS page with the given slug'):
                cms.get_page_context(create_fake_request(path='legacy.html'), slug='legacy.html')
        finally:
            p.delete()


    def test_should_raise_404_for_legacy_url_of_page_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(Page)
        cms = get_cms()
        p = self.create_page('Legacy Page', legacy_url='legacy.html')
        try:
            with self.assertRaisesRegexp(Http404, 'There is no CMS page with the given slug'):
                cms.get_page_context(create_fake_request(path='legacy.html'), slug='legacy.html')
        finally:
            p.delete()
            self.restore_filter_visibility(Page, _filter_visibility)


    def test_should_not_include_child_pages_that_are_disabled(self):
        cms = get_cms()
        post = BlogPost.objects.get(slug='child-page-0')
        post.disabled = True
        post.save()
        try:
            context = cms.get_page_context(create_fake_request(path=''), page=self.page)
            child_pages = [item.title for item in context.get_template_context().get('child_pages')]
            self.assertNotIn('Child Page 0', child_pages)
        finally:
            post.disabled = False
            post.save()


    def test_should_not_include_child_pages_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(BlogPost)
        cms = get_cms()
        try:
            context = cms.get_page_context(create_fake_request(path=''), page=self.page)
            child_pages = list(context.get_template_context().get('child_pages'))
            self.assertEqual([], child_pages)
        finally:
            self.restore_filter_visibility(BlogPost, _filter_visibility)


    def test_should_not_include_disabled_page_in_nav(self):
        cms = get_cms()
        p = self.create_page('Disabled Page', disabled=True)
        try:
            context = cms.get_page_context(create_fake_request(path=''), page=self.page)
            items = [item.get('page_title') for item in context.get_template_context().get('nav').get('header')]
            self.assertNotIn('Disabled Page', items)
        finally:
            p.delete()


    def test_should_not_include_page_in_nav_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(Page)
        cms = get_cms()
        try:
            context = cms.get_page_context(create_fake_request(path=''), page=self.page)
            items = context.get_template_context().get('nav').get('header')
            self.assertIsNone(items)
        finally:
            self.restore_filter_visibility(Page, _filter_visibility)


    def test_should_not_provide_disabled_page_via_identifier(self):
        cms = get_cms()
        p = self.create_page('Disabled Page', disabled=True, identifier='foo')
        try:
            context = cms.get_page_context(create_fake_request(path=''), page=self.page)
            page = context.get_template_context().get('pages').get('foo')
            self.assertIsNone(page)
        finally:
            p.delete()


    def test_should_not_provide_page_via_identifier_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(Page)
        cms = get_cms()
        p = self.create_page('Disabled Page', identifier='foo')
        try:
            context = cms.get_page_context(create_fake_request(path=''), page=self.page)
            page = context.get_template_context().get('pages').get('foo')
            self.assertIsNone(page)
        finally:
            p.delete()
            self.restore_filter_visibility(Page, _filter_visibility)


    @override_settings(CMS_NAVIGATION_INCLUDE_CHILD_PAGES=False)
    def test_should_not_include_child_pages_in_nav_if_feature_is_not_enabled(self):
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path=''), page=self.page)
        child_pages = context.get_template_context().get('nav').get('header')[0].get('child_pages')
        self.assertEqual([], child_pages)


    @override_settings(CMS_NAVIGATION_INCLUDE_CHILD_PAGES=True)
    def test_should_not_include_disabled_child_pages_in_nav(self):
        cms = get_cms()
        post = BlogPost.objects.get(slug='child-page-0')
        post.disabled = True
        post.save()
        try:
            context = cms.get_page_context(create_fake_request(path=''), page=self.page)
            child_pages = [item.get('title') for item in context.get_template_context().get('nav').get('header')[0].get('child_pages')]
            self.assertNotIn('Child Page 0', child_pages)
        finally:
            post.disabled = False
            post.save()


    @override_settings(CMS_NAVIGATION_INCLUDE_CHILD_PAGES=True)
    def test_should_not_include_child_pages_in_nav_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(BlogPost)
        cms = get_cms()
        try:
            context = cms.get_page_context(create_fake_request(path=''), page=self.page)
            child_pages = [item.get('title') for item in context.get_template_context().get('nav').get('header')[0].get('child_pages')]
            self.assertEqual([], child_pages)
        finally:
            self.restore_filter_visibility(BlogPost, _filter_visibility)


class CMSViewsPaginationTestCase(CMSViewsPageContextBaseTestCase):
    def test_sets_pagination_correctly(self):
        settings = self._pagination_settings()
        request = create_fake_request(path='page/')
        request.settings = settings
        cms = get_cms()
        context = cms.get_page_context(request, slug='page/page-2')
        self.assertEqual(context.paginator.min_page_size, 4)


    def test_explicit_page_1_url_should_redirect(self):
        settings = self._pagination_settings()
        request = create_fake_request(path='page/')
        request.settings = settings
        cms = get_cms()
        response = cms.page_by_slug(request, slug='page/page-1')
        self.assertIsInstance(response, HttpResponsePermanentRedirect)
        self.assertEqual('http://www.testapp.cubane.innershed.com/page/', response['Location'])


    def test_explicit_page_1_url_should_not_redirect_if_we_view_all(self):
        settings = self._pagination_settings()
        request = create_fake_request(path='page/')
        request.settings = settings
        cms = get_cms()
        response = cms.page_by_slug(request, slug='page/all-page-1')
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(200, response.status_code)


    def test_should_accept_pagination_argument_all(self):
        settings = self._pagination_settings()
        request = create_fake_request(path='page/')
        request.settings = settings
        cms = get_cms()
        context = cms.get_page_context(request, slug='page/all-page-1')
        self.assertTrue(request.paginator_all)


    def test_raises_error_if_page_has_no_children_and_url_suggests_it_does(self):
        p = self.create_page('Page 2', seq=1)
        with self.assertRaises(Http404):
            cms = get_cms()
            cms.get_page_context(create_fake_request(path=''), slug='page-2/test')


    def test_raises_error_if_page_has_no_children_and_url_contains_pagination(self):
        self._pagination_settings()
        request = create_fake_request(path='page-2/')
        request.settings = settings
        p = self.create_page('Page 2', seq=1)
        with self.assertRaises(Http404):
            cms = get_cms()
            cms.get_page_context(request, slug='page-2/page-2')


    def test_raises_error_if_pagination_in_url_but_child_page_not_in_settings(self):
        self._pagination_settings()
        request = create_fake_request(path='page-24/')
        request.settings = settings
        with self.assertRaises(Http404):
            cms = get_cms()
            cms.get_page_context(request, slug='page/page-24')


    def test_should_render_pagination_on_the_first_page(self):
        self._pagination_settings()
        self.page.template = 'cubane/cms/default_template.html'
        self.page.save()
        cms = get_cms()
        self.assertTrue('pagination' in cms.render_page(self.page).content)


    def _pagination_settings(self):
        settings = get_cms_settings()
        settings.name = 'Test Settings'
        settings.paging_enabled = True
        settings.paging_child_pages = ['blog_blogpost']
        settings.page_size = 4
        settings.save()
        return settings


class CMSViewsNavigationTestCase(CMSViewsPageContextBaseTestCase):
    @override_settings(PAGE_HIERARCHY=True)
    def test_sets_active_nav_item_for_parent(self):
        parent = self.create_page('Page 1', seq=1)
        child_page = self.create_page('Page 2', seq=1, parent=parent)
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path=''), page=child_page)
        nav = context.get_template_context().get('nav')
        active_nav_item = self.get_active_nav_item(nav)
        self.assertEqual(active_nav_item.get('id'), child_page.id, 'Active nav item should be the same.')


    def test_has_correct_child_pages_in_nav(self):
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path=''), page=self.page)
        child_pages = [item for item in context.get_template_context().get('nav').get('child_pages')]
        self.assertEqual(len(child_pages), 10, 'There should be 10 child pages')


    def test_puts_pages_with_identifier_in_seperate_list_to_normal_pages(self):
        page = self.create_page('Page with identifier', seq=1, identifier='identifier')
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path=''), page=page)
        pages = context.get_template_context().get('pages')
        self.assertEqual(len(pages), 1, 'Should only be one page with identifier.')
        self.assertEqual(pages.get('identifier').get('id'), page.id, 'Page with identifier should match.')


    def test_does_not_put_page_in_nav_if_set_to_none(self):
        page = self.create_page('Page not in nav', seq=1, nav='')
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path=''), page=page)
        nav = context.get_template_context().get('nav').get('header')
        self.assertEqual(self._is_item_in_nav(page.id, nav), False, 'Page should not be in nav.')


    def _is_item_in_nav(self, item_id, nav):
        for item in nav:
            if item.get('id') == item_id:
                return True
        return False


    def get_active_nav_item(self, nav):
        header_nav = nav.get('header')
        for item in header_nav:
            if item.get('active'):
                return item
            if item.get('active_child'):
                for child in item.get('children'):
                    if child.get('active'):
                        return child
        return None


class CMSViewsGetHomepageTestCase(CMSViewsPageContextBaseTestCase):
    def test_raises_404_if_no_homepage_defined(self):
        with self.assertRaises(Http404):
            cms = get_cms()
            cms.get_page_context(create_fake_request(path='/'), page=self.page).get_homepage_or_404()


    def test_raise_404_if_slug_is_not_a_page_or_child_page_of_homepage(self):
        page = self.create_page('Home Page', seq=1)
        self.set_settings_vars({'homepage': page})
        request = create_fake_request(path='child-page-1')
        request.settings = settings
        with self.assertRaises(Http404):
            cms = get_cms()
            cms.get_page_context(request, slug='child-page-1').get_page_by_slug_or_404('child-page-1')


class CMSViewsGetPageBySlugOr404TestCase(CMSViewsPageContextBaseTestCase):
    def test_should_return_child_page_if_child_page_of_homepage(self):
        self.set_settings_vars({'homepage': self.page})
        request = create_fake_request(path='child-page-1')
        request.settings = settings
        cms = get_cms()
        page = cms.get_page_context(request, slug='child-page-1').get_page_by_slug_or_404('child-page-1')
        self.assertEqual(page, BlogPost.objects.get(slug='child-page-1'), 'Should return child page 1.')


    def test_should_raise_404_if_not_a_child_page_of_homepage(self):
        settings = self.set_settings_vars({'homepage': self.page})
        request = create_fake_request(path='child-page-1')
        request.settings = settings
        page = self.create_page('Page 11', seq=1)
        child_page = self.create_child_page(11, page)
        with self.assertRaises(Http404):
            cms = get_cms()
            cms.get_page_context(request, slug='child-page-11').get_page_by_slug_or_404('child-page-11')


    def test_should_raise_404_if_enquiry_page(self):
        page = self.create_page('Enquiry Page', seq=1)
        settings = self.set_settings_vars({'enquiry_template': page})
        request = create_fake_request(path='enquiry-page')
        request.settings = settings
        with self.assertRaises(Http404):
            cms = get_cms()
            cms.get_page_context(request, slug='enquiry-page').get_page_by_slug_or_404('enquiry-page')


class CMSViewsGetTemplateTestCase(CMSViewsPageContextBaseTestCase):
    def test_should_return_correct_template(self):
        self.page.template = 'testapp/homepage.html'
        cms = get_cms()
        self.assertEqual(cms.get_page_context(create_fake_request(path='page'), page=self.page).get_template(), 'testapp/homepage.html')
        self.assertEqual(cms.get_page_context(create_fake_request(path='child-page-0'), page=self.child_page).get_template(), 'testapp/page.html')


class CMSViewsRenderTestCase(CMSViewsPageContextBaseTestCase):
    def test_page_context_render_should_return_html(self):
        cms = get_cms()
        self.assertEqual(cms.get_page_context(create_fake_request(path='page'), page=self.page).render({})._headers['content-type'][1], 'text/html; charset=utf-8')


class CMSViewsHasIdentifierTestCase(CMSViewsPageContextBaseTestCase):
    def test_should_return_true_if_page_has_identifier(self):
        p = self.create_page('Page 3', seq=1, identifier='new_page')
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path=''), page=p)
        self.assertEqual(context.has_identifier('new_page'), True, 'has_identifier should return True if page has identifier.')
        p2 = self.create_page('Page 4', seq=1)
        context2 = cms.get_page_context(create_fake_request(path=''), page=p2)
        self.assertEqual(context2.has_identifier('new_page'), False, 'has_identifier should return False if page does not have identifier.')


class CMSViewsIsHomepageTestCase(CMSViewsPageContextBaseTestCase):
    def test_is_homepage_gives_correct_value(self):
        page = self.create_page('Home Page', seq=1)
        settings = self.set_settings_vars({'homepage': page})
        request = create_fake_request(path='')
        request.settings = settings
        cms = get_cms()
        context = cms.get_page_context(request, page=self.page)
        home_context = cms.get_page_context(request, page=page)
        self.assertEqual(context.is_homepage(), False)
        self.assertEqual(home_context.is_homepage(), True)


class CMSViewsIsLegacyUrlTestCase(CMSViewsPageContextBaseTestCase):
    def test_redirects_if_legacy_url(self):
        p = self.create_page('Page 3', seq=1, legacy_url='/testing.html')
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path='testing.html'), slug='testing.html')
        self.assertEqual(context._redirect_url, 'http://www.testapp.cubane.innershed.com/page-3/')
        self.assertEqual(context._is_legacy_url, True)


    def test_returns_false_if_page_does_not_have_legacy_url(self):
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path='/'), page=self.page)
        self.assertEqual(context.is_legacy_url(), False, 'Page should not have legacy url.')


    def test_returns_true_if_page_has_legacy_url(self):
        page = self.create_page('Home Page', seq=1, legacy_url='/old-url-path/')
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path='/old-url-path/'), slug='/old-url-path/')
        self.assertEqual(context.is_legacy_url(), True)


class CMSViewsIsAppendSlashTestCase(CMSViewsPageContextBaseTestCase):
    def test_returns_true_if_path_does_not_have_trailing_slash(self):
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path='page-2'), page=self.page)
        self.assertEqual(context.is_redirect(), True)


    def test_returns_false_if_path_has_trailing_slash(self):
        cms = get_cms()
        context = cms.get_page_context(create_fake_request(path='/'), page=self.page)
        self.assertEqual(context.is_redirect(), False)


class CMSViewsCMSBaseTestCase(CMSTestBase):
    def setUp(self):
        self.page = self.create_page('Page')
        self.child_page = self.create_child_page(1)
        self.settings = get_cms_settings()
        self.settings.homepage = self.page
        self.settings.save()
        self.factory = RequestFactory()


    def tearDown(self):
        Settings.objects.all().delete()
        Page.objects.all().delete()
        DirectoryTag.objects.all().delete()
        Media.objects.all().delete()
        BlogPost.objects.all().delete()


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


class CMSViewsCMSTestCase(CMSViewsCMSBaseTestCase):
    @override_settings(CMS_PAGE_MODEL='cubane.testapp.models.CustomPage')
    def test_get_page_model_returns_correct_model(self):
        from cubane.testapp.models import CustomPage
        self.assertEqual(get_cms().get_page_model(), CustomPage)


    def test_create_fake_request_returns_create_fake_request(self):
        self.assertIsInstance(get_cms().fake_request(), HttpRequest)


    def test_create_default_enquiry_form_returns_form_object(self):
        request = create_fake_request(path='')
        cms = get_cms()
        default_enquiry_form = cms.create_default_enquiry_form(request, cms.get_template_context(request), {})
        self.assertIsInstance(default_enquiry_form.get('enquiry_form', None), EnquiryForm)


    def test_create_blank_enquiry_form_returns_enquiry_form(self):
        cms = get_cms()
        blank_enquiry_form = cms.create_blank_enquiry_form()
        self.assertIsInstance(blank_enquiry_form, EnquiryForm)


    def test_on_contact_page_returns_enquiry_form(self):
        request = create_fake_request(path='')
        cms = get_cms()
        on_contact_page = cms.on_contact_page(request, cms.get_template_context(request), {})
        self.assertIsInstance(on_contact_page.get('enquiry_form', None), EnquiryForm)


    def test_dispatch_returns_http_response(self):
        request = create_fake_request(path='')
        cms = get_cms()
        context = cms.get_page_context(request, '')
        self.assertIsInstance(cms.dispatch(request, context), RenderResponse)


    def test_dispatch_returns_permanent_redirect_if_append_slash_in_context(self):
        page = self.create_page('Page 2')
        request = create_fake_request(path='page-2')
        cms = get_cms()
        context = cms.get_page_context(request, 'page-2')
        self.assertIsInstance(cms.dispatch(request, context), HttpResponsePermanentRedirect, 'Dispatch should redirect if context.is_redirect.')


    def test_dispatch_returns_status_code_404_if_context_is_404_page(self):
        page = self.create_page('Page Not Found')
        settings = self.set_settings_vars({'default_404': page})
        request = create_fake_request(path='page-not-found/')
        cms = get_cms()
        context = cms.get_page_context(request, 'page-not-found/', page=page)
        self.assertIsInstance(cms.dispatch(request, context), RenderResponse, 'Dispatch should return RenderResponse.')
        self.assertEqual(cms.dispatch(request, context).status_code, 404, '404 page should return status code 404.')


    def test_page_should_return_response(self):
        cms = get_cms()
        request = create_fake_request(path='page/')
        response = cms.page(request, self.page)
        self.assertEqual(response.status_code, 200, 'Page should return status code of 200 if page exists.')
        self.assertIsInstance(response, HttpResponse, 'Page should return response.')


    def test_default_404_should_return_none_if_no_page_set_in_settings_for_default_404(self):
        cms = get_cms()
        request = create_fake_request(path='/')
        response = cms.default_404(request)
        self.assertEqual(
            response,
            None,
            'default_404 should return None if no default_404 set in settings.'
        )


    def test_default_404_should_return_response_with_404_status_code(self):
        page = self.create_page('Page Not Found')
        settings = self.set_settings_vars({'default_404': page})
        cms = get_cms()
        request = create_fake_request(path='/')
        response = cms.default_404(request)
        self.assertEqual(
            response.status_code,
            404,
            'default_404 should return status code of 404.'
        )


    def test_default_404_should_return_response_even_if_page_is_disabled(self):
        # create disabled 404 page
        page = self.create_page('Page Not Found')
        page.disabled = True
        page.save()

        # setup settings
        settings = self.set_settings_vars({'default_404': page})

        # process 404 default handler
        cms = get_cms()
        request = create_fake_request(path='/')
        response = cms.default_404(request)
        self.assertEqual(
            response.status_code,
            404,
            'default_404 should return status code of 404.'
        )


    def test_render_page_should_return_empty_string_if_not_given_page(self):
        cms = get_cms()
        self.assertEqual(
            cms.render_page(None).content,
            '',
            'render_page should return empty string.'
        )


    def test_render_page_should_return_html_for_given_page(self):
        cms = get_cms()
        self.assertEqual(
            '<!DOCTYPE html>' in cms.render_page(self.page).content,
            True,
            'render_page should return html of page.'
        )


    def test_render_page_should_return_empty_string_for_404(self):
        page = self.create_page('Page Not Found')
        settings = self.set_settings_vars({'default_404': page})
        cms = get_cms()
        self.assertEqual(
            cms.render_page(page).content,
            '',
            'render_page should return empty string for 404 page.'
        )


    def test_invalidate_returns_number_of_files_removed_from_cache(self):
        cms = get_cms()
        cache_items, cache_size, _ = cms.publish(True)
        self.assertEqual(cms.invalidate(), 1, 'CMS invalidate should return 1 as it has removed 1 cache file.')


    def test_get_directory_tags_returns_list(self):
        cms = get_cms()
        d_tag = DirectoryTag()
        d_tag.title = 'tag-test'
        d_tag.save()
        directory_tags = cms.get_directory_tags()
        self.assertIsInstance(directory_tags, list)
        self.assertEqual(len(directory_tags), 1)


    def test_get_directory_tag_choices_returns_list(self):
        cms = get_cms()
        d_tag = DirectoryTag()
        d_tag.title = 'tag-test'
        d_tag.save()
        directory_tag_choices = cms.get_directory_tag_choices()
        self.assertIsInstance(directory_tag_choices, list)
        self.assertEqual(len(directory_tag_choices), 1)


    def test_get_contact_page_url_returns_empty_string_if_no_contact_page_defined(self):
        cms = get_cms()
        request = create_fake_request(path='page/')
        context = cms.get_page_context(request, slug='page/')
        self.assertEqual(cms.get_contact_page_url(context), '')


    def test_get_contact_page_url_returns_url(self):
        settings = self.set_settings_vars({'contact_page': self.page})
        cms = get_cms()
        request = create_fake_request(path='page/')
        context = cms.get_page_context(request, slug='page/')
        self.assertEqual(cms.get_contact_page_url(context), 'http://www.testapp.cubane.innershed.com/page/')


    def test_redirects_legacy_url(self):
        p = self.create_page('Legacy', legacy_url='/legacy.html')
        cms = get_cms()
        request = create_fake_request(path='legacy.html')
        context = cms.get_page_context(request, slug='legacy.html')
        response = cms.dispatch(request, context)
        self.assertIsInstance(response, HttpResponsePermanentRedirect)
        self.assertEqual(response._headers.get('location')[1], 'http://www.testapp.cubane.innershed.com/legacy/')


class CMSViewsCMSPageBySlugTestCase(CMSViewsCMSBaseTestCase):
    def test_should_return_response_for_rendering_page(self):
        response = self._render_page('page/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, HttpResponse)
        self.assertIn('<title>Page</title>', response.content)


    def _render_page(self, slug):
        cms = get_cms()
        request = self.factory.get(slug)
        return cms.page_by_slug(request, slug)


class CMSViewsCMSGetPagesTestCase(CMSViewsCMSBaseTestCase):
    def test_get_pages_returns_queryset_for_pages(self):
        self.assertIsInstance(get_cms().get_pages(), QuerySet)
        self.assertEqual(len(get_cms().get_pages()), 1)


    def test_get_child_page_models_returns_list_of_child_page_models(self):
        self.assertIsInstance(get_cms().get_child_page_models(), list)
        self.assertEqual(len(get_cms().get_child_page_models()), 3)


    def test_get_child_pages_for_model_returns_queryset_for_given_model(self):
        self.assertIsInstance(get_cms().get_child_pages_for_model(BlogPost), QuerySet)
        self.assertEqual(len(get_cms().get_child_pages_for_model(BlogPost)), 1)


    def test_get_child_pages_for_page_returns_queryset_if_given_page_has_child_pages(self):
        page = self.create_page('Page 2', entity_type='BlogPost')
        child_page = self.create_child_page(2, page)
        self.assertIsInstance(get_cms().get_child_pages_for_page(page), QuerySet)
        self.assertEqual(len(get_cms().get_child_pages_for_page(page)), 1)


    def test_get_child_pages_for_page_returns_empty_unicode_if_given_page_has_no_child_pages(self):
        self.assertIsInstance(get_cms().get_child_pages_for_page(self.page), unicode)
        self.assertEqual(get_cms().get_child_pages_for_page(self.page), u'')


    def test_get_homepage_returns_homepage_or_none(self):
        cms = get_cms()
        cms.settings.homepage = None
        self.assertEqual(cms.get_homepage(), None)
        cms.settings.homepage = self.page
        self.assertEqual(cms.get_homepage(), self.page)


class CMSViewsCMSSubmitMailchimpSubscriptionTestCase(CMSViewsCMSBaseTestCase):
    def test_returns_empty_string(self):
        cms = get_cms()
        request = create_fake_request(path='/')
        self.assertRaises(Http404, cms.submit_mailchimp_subscription, request)


    def test_raises_http404(self):
        settings = self.set_settings_vars({
            'mailchimp_api': 'fakeid',
            'mailchimp_list_id': 'fakelistid'
        })
        cms = get_cms()
        request = create_fake_request(path='/')
        with self.assertRaises(Http404):
            cms.submit_mailchimp_subscription(request)


    def test_should_return_html_as_json(self):
        settings = self.set_settings_vars({
            'mailchimp_api': 'fakeid',
            'mailchimp_list_id': 'fakelistid'
        })
        cms = get_cms()
        factory = RequestFactory()
        request = factory.get('mailchimp-subscription-ajax', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = cms.submit_mailchimp_subscription(request)
        self.assertEqual(response._headers.get('content-type')[1], 'text/javascript')
        self.assertEqual('html' in json.loads(response.content), True)


    @patch('mailsnake.MailSnake')
    def test_returns_error_message(self, MailSnake):
        MailSnake().listSubscribe.side_effect = Exception()

        settings = self.set_settings_vars({
            'mailchimp_api': 'fakeid',
            'mailchimp_list_id': 'fakelistid'
        })
        cms = get_cms()
        factory = RequestFactory()
        request = factory.post('mailchimp-subscription-ajax', {
            'mailchimp_subscription__email': 'test@innershed.com'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = cms.submit_mailchimp_subscription(request)
        self.assertEqual('Unfortunately we were unable to process your request. Please try again later' in json.loads(response.content).get('html'), True)


class CMSViewsCMSIsPageHomepageTestCase(CMSViewsCMSBaseTestCase):
    def test_returns_false_when_homepage_is_not_set(self):
        cms = get_cms()
        cms.settings.homepage = None
        self.assertEqual(cms.is_page_homepage(self.page), False)


    def test_returns_true_when_homepage_is_set(self):
        cms = get_cms()
        self.assertEqual(cms.is_page_homepage(self.page), True)


    def test_returns_false_if_not_on_homepage(self):
        cms = get_cms()
        self.assertEqual(cms.is_page_homepage(self.child_page), False)


class CMSViewsCMSRenderPageWithoutDispatchTestCase(CMSViewsCMSBaseTestCase):
    def test_returns_empty_string_if_no_page_given(self):
        cms = get_cms()
        self.assertEqual(cms.render_page_without_dispatch(None), '')


    def test_returns_html_content_for_page(self):
        cms = get_cms()
        content = cms.render_page_without_dispatch(self.page)
        self.assertIsInstance(content, str)
        self.assertEqual('<!DOCTYPE html>' in content, True)


class CMSViewsCMSRenderEnquiryTemplateTestCase():
    def test_render_enquiry_template_returns_empty_string_if_not_enquiry_page_defined(self):
        cms = get_cms()
        request = create_fake_request(path='/')
        content = cms.render_enquiry_template(request)
        self.assertEqual(content, '')


    def test_render_enquiry_template_returns_html_for_settings_page(self):
        page = self.create_page('Contact Us')
        settings = self.set_settings_vars({'enquiry_template': page})
        cms = get_cms()
        request = create_fake_request(path='/')
        content = cms.render_enquiry_template(request)
        self.assertEqual('<!DOCTYPE html>' in content, True)


class CMSViewsPageContentView(CMSTestBase):
    def test_get_objects_returns_empty_queryset_if_no_pages(self):
        view = PageContentView(Page)
        request = create_fake_request(path='/')
        self.assertEqual(len(view._get_objects(request)), 0, 'Empty queryset should be returned.')


    def test_get_objects_returns_queryset(self):
        p = self.create_page('Page')
        view = PageContentView(Page)
        request = create_fake_request(path='/')
        self.assertEqual(len(view._get_objects(request)), 1, 'Queryset with one page should be returned.')


    def test_preview_returns_http_response(self):
        view = PageContentView(Page)
        request = create_fake_request(path='/')
        self.assertIsInstance(view.preview(request), HttpResponse)


    def test_preview_returns(self):
        view = PageContentView(BlogPost)
        request = create_fake_request(path='/')
        self.assertIsInstance(view.preview(request), HttpResponse)


    def test_preview_should_render_preview_even_if_child_page_has_no_page(self):
        # create child page without a page, which might happen if someone
        # deleted the corresponding page. Rendering the child page in preview
        # mode should still work.
        child = BlogPost()
        child.save()

        view = PageContentView(BlogPost)
        request = create_fake_request(path='/')
        view.preview(request, pk=child.pk)


    def test_form_initial_adds_gallery_images_to_initial(self):
        view = PageContentView(Page)
        request = create_fake_request(path='/')
        page = self.create_page('Page')
        page_initial = page.to_dict()
        self.assertEqual('_gallery_images' not in page_initial, True, 'Should not have _gallery_images in page initial.')
        view.form_initial(request, page_initial, page, False)
        self.assertEqual('_gallery_images' in page_initial, True, 'Should have _gallery_images in.')


    def test_before_save_should_set_slot_content(self):
        view = PageContentView(Page)
        factory = RequestFactory()
        request = factory.post('/', {'slot_content': 'Hello World!'})
        page = self.create_page('Page')
        view.before_save(request, None, page, False)
        self.assertEqual(page.get_data().get('content'), 'Hello World!')


    def test_preview_should_return_response(self):
        page = self.create_page('Page')
        view = PageContentView(Page)
        request = create_fake_request(path='/')
        response = view.preview(request, page.pk)
        self.assertEqual(type(response), HttpResponse, 'Preview should return response for page with given pk.')
        self.assertEqual(response.status_code, 200, 'Response should have status code 200.')


    def test_after_save_should_raise_error(self):
        view = PageContentView(Page)
        request = create_fake_request(path='/')
        page = self.create_page('Page')
        with self.assertRaises(AttributeError):
            view.after_save(request, None, page, False)


    def test_after_save_sets_gallery(self):
        view = PageContentView(Page)
        request = self.make_request('get', '/')
        page = self.create_page('Page')
        cms = get_cms()
        image = Media(filename='test.jpg', caption='Test')
        image.save()
        view.after_save(request, {'_gallery_images': [image]}, page, False)
        self.assertEqual(len(page.gallery), 1)


    @override_settings(PAGE_HIERARCHY=True)
    def test_PAGE_HIERARCHY_sets_folder_model(self):
        settings.PAGE_HIERARCHY = True
        view = PageContentView(Page)


class CMSViewsContentView(CMSTestBase):
    def test_get_objects_returns_queryset(self):
        page = self.create_page('Page')
        c = ContentView(Page)
        request = create_fake_request(path='/')
        objects = c._get_objects(request)
        self.assertEqual(objects.count(), 1)


class CMSViewsSettingsView(CMSTestBase):
    def test_before_save_sets_homepage(self):
        page = self.create_page('Page')
        v = SettingsView()
        s = Settings()
        s.homepage = page
        s.save()
        request = create_fake_request(path='/')
        v.before_save(request, {'homepage': page}, s, False)
        self.assertEqual(page.is_homepage, True)


    def test_get_objects_returns_settings_instance(self):
        v = SettingsView()
        s = Settings()
        s.name = 'Foo'
        s.save()
        request = create_fake_request(path='/')
        instance = v._get_object(request)
        self.assertIsInstance(instance, Settings)


    def test_get_objects_returns_none(self):
        v = SettingsView()
        request = create_fake_request(path='/')
        instance = v._get_object(request)
        self.assertEqual(instance, None)


class CMSViewsGetSettingsModelTestCase(CubaneTestCase):
    def test_get_settings_model_returns_correct_model(self):
        from cubane.testapp.models import Settings
        self.assertEqual(get_settings_model(), Settings)


    @override_settings(CMS_SETTINGS_MODEL=None)
    def test_get_settings_model_raises_error_settings_not_defined(self):
        del settings.CMS_SETTINGS_MODEL
        def _get_settings_model():
            get_settings_model()
        self.assertRaises(ValueError, _get_settings_model)


class CMSViewGetPageModelTestCase(CubaneTestCase):
    @override_settings(CMS_PAGE_MODEL='cubane.testapp.models.CustomPage')
    def test_get_page_model_returns_correct_model_if_custom_model_defined(self):
        from cubane.testapp.models import CustomPage
        self.assertEqual(get_page_model(), CustomPage)


    def test_get_page_model_returns_page_if_not_defined_in_settings(self):
        from cubane.cms.models import Page
        self.assertEqual(get_page_model(), Page)


class CMSViewOnRenderContentPipelinePatcher(CubaneTestCase):
    def setUp(self):
        factory = RequestFactory()
        self.request = factory.get('/')
        self.cms = TestAppCMS()


    def test_should_replace_registered_snippet(self):
        self.cms.map_content('FOO', 'BAR')
        result = self.cms.on_render_content_pipeline(self.request, 'Hello {FOO}', {})
        self.assertEqual('Hello BAR', result)


    def test_should_replace_registered_snippet_with_template_code(self):
        self.cms.map_content('FOO', '{{ subject }}')
        result = self.cms.on_render_content_pipeline(self.request, 'Hello {FOO}', {'subject': 'BAR'})
        self.assertEqual('Hello BAR', result)


    def test_should_replace_registered_snippet_with_template_code_using_template_context(self):
        self.cms.map_content('FOO', '{{ subject }}')
        result = self.cms.on_render_content_pipeline(self.request, 'Hello {FOO}', Context({'subject': 'BAR'}))
        self.assertEqual('Hello BAR', result)


class CMSViewGetSitemapTestCase(CubaneTestCase):
    def setUp(self):
        self.cms = get_cms()
        self.sitemap = self.cms.get_sitemaps()


    def tearDown(self):
        [s.delete() for s in Settings.objects.all()]
        [p.delete() for p in Page.objects.all()]


    def test_should_publish_homepage(self):
        page = Page.objects.create(title='Page', is_homepage=True)
        settings = Settings.objects.create(
            homepage=page
        )

        # one homepage, /
        homepage = self.sitemap.get('homepage').items()
        self.assertEqual(1, len(homepage))
        self.assertEqual('http://www.testapp.cubane.innershed.com/', homepage[0].url)

        # homepage does not appear as normal page
        pages = list(self.sitemap.get('pages').items())
        self.assertEqual(0, len(pages))


    def test_should_not_publish_homepage_if_not_configured_in_settings(self):
        homepage = self.sitemap.get('homepage').items()
        self.assertEqual(0, len(homepage))


    def test_should_not_publish_disabled_homepage(self):
        page = Page.objects.create(title='Page', disabled=True)
        settings = Settings.objects.create(
            homepage=page
        )
        homepage = self.sitemap.get('homepage').items()
        self.assertEqual(0, len(homepage))


    def test_should_not_publish_homepage_with_custom_visibility(self):
        def is_visible(page):
            return False

        page = Page.objects.create(title='Page')
        _is_visible = Page.is_visible
        Page.is_visible = is_visible
        settings = Settings.objects.create(
            homepage=page
        )

        try:
            homepage = self.sitemap.get('homepage').items()
            self.assertEqual(0, len(homepage))
        finally:
            Page.is_visible = _is_visible


    def test_should_publish_page(self):
        page = Page.objects.create(title='Page')
        pages = list(self.sitemap.get('pages').items())
        self.assertEqual(1, len(pages))
        self.assertEqual('Page', pages[0].title)


    def test_should_not_publish_disabled_page(self):
        page = Page.objects.create(title='Page', disabled=True)
        pages = list(self.sitemap.get('pages').items())
        self.assertEqual(0, len(pages))


    def test_should_not_publish_page_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(Page)
        try:
            page = Page.objects.create(title='Page')
            pages = list(self.sitemap.get('pages').items())
            self.assertEqual(0, len(pages))
        finally:
            self.restore_filter_visibility(Page, _filter_visibility)


    def test_should_publish_child_pages(self):
        page = Page.objects.create(title='Page', entity_type='BlogPost')
        post = BlogPost.objects.create(title='Post', page=page)

        # one page
        pages = list(self.sitemap.get('pages').items())
        self.assertEqual(1, len(pages))
        self.assertEqual('Page', pages[0].title)

        # one post
        posts = list(self.sitemap.get('blog-post').items())
        self.assertEqual(1, len(posts))
        self.assertEqual('Post', posts[0].title)


    def test_should_not_publish_disabled_child_page(self):
        page = Page.objects.create(title='Page', entity_type='BlogPost')
        post = BlogPost.objects.create(title='Post', page=page, disabled=True)
        posts = list(self.sitemap.get('blog-post').items())
        self.assertEqual(0, len(posts))


    def test_should_not_publish_child_page_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(BlogPost)
        try:
            page = Page.objects.create(title='Page', entity_type='BlogPost')
            post = BlogPost.objects.create(title='Post', page=page)
            posts = list(self.sitemap.get('blog-post').items())
            self.assertEqual(0, len(posts))
        finally:
            self.restore_filter_visibility(BlogPost, _filter_visibility)


    def test_should_not_contain_custom_sitemap_entries_if_we_did_not_generate_custom_entries(self):
        items = self.sitemap.get('custom').items()
        self.assertEqual(0, len(items))


    def test_should_contain_custom_sitemap_entries_after_adding_custom_entries(self):
        # patch on custom sitemap handler
        def on_custom_sitemap(sitemap):
            sitemap.add('test_non_standard_cms_page')
        f = self.cms.on_custom_sitemap
        self.cms.on_custom_sitemap = on_custom_sitemap

        try:
            items = self.sitemap.get('custom').items()
            self.assertEqual(1, len(items))
            self.assertEqual('http://www.testapp.cubane.innershed.com/non-standard-page/', items[0].url)
        finally:
            self.cms.on_custom_sitemap = f