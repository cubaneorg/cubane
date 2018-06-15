# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.cms.views import get_cms
from cubane.backend.views import BackendSection
from cubane.directory import DirectoryOrder
from cubane.directory.models import DirectoryTag
from cubane.testapp.models import CustomDirectoryPage
from cubane.testapp.models import TestDirectoryCategory
from cubane.testapp.models import TestDirectoryContent
from cubane.testapp.models import TestDirectoryContentWithBackendSections
from cubane.testapp.models import TestContentAggregator
from cubane.testapp.models import TestDirectoryContentEntity
from cubane.directory.views import get_directory_content_backend_sections
from cubane.directory.views import DirectoryBackendSection
from cubane.directory.views import DirectoryTagsView
from cubane.directory.views import DirectoryCategoryView
from cubane.directory.views import DirectoryContentView
from cubane.directory.views import content
from mock import patch, MagicMock


class TestDirectoryViewsGetDirectoryContentBackendSectionsTestCase(CubaneTestCase):
    def test_should_return_list_of_directory_sub_sections_for_directory_models(self):
        section = BackendSection()
        self.assertEqual(
            ['A', 'B', 'Test Content Aggregators', 'Test Directory Content', 'Test Directory Content Entities'],
            [s.title for s in get_directory_content_backend_sections(section)]
        )


class TestDirectoryBackendSectionTestCase(CubaneTestCase):
    def test_should_contain_directory_related_sections_categories_and_entities_but_no_model_sections(self):
        self.assertEqual(
            ['Tags', 'Test Directory Categories', 'Test Directory Entities'],
            [s.title for s in DirectoryBackendSection().sections]
        )


class TestDirectoryTestCaseBase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDirectoryTestCaseBase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')
        cls.request.user = User(is_staff=True, is_superuser=True)


class TestDirectoryTagsViewTestCase(TestDirectoryTestCaseBase):
    def setUp(self):
        self.tag = DirectoryTag.objects.create(title='foo')


    def tearDown(self):
        self.tag.delete()


    def test_should_return_all_tags(self):
        view = DirectoryTagsView()
        self.assertEqual(
            ['foo'],
            [tag.title for tag in view._get_objects(self.request)]
        )


class TestDirectoryCategoryViewTestCase(TestDirectoryTestCaseBase):
    def setUp(self):
        self.category = TestDirectoryCategory.objects.create(title='foo')


    def tearDown(self):
        self.category.delete()


    def test_should_return_all_categories(self):
        view = DirectoryCategoryView('slug', TestDirectoryCategory)
        self.assertEqual(
            ['foo'],
            [c.title for c in view._get_objects(self.request)]
        )


class TestDirectoryContentViewTestCase(TestDirectoryTestCaseBase):
    def setUp(self):
        self.page = TestDirectoryContent.objects.create(title='Foo')
        self.view = DirectoryContentView('Test', None, None, TestDirectoryContent)


    def tearDown(self):
        self.page.delete()


    def test_should_return_all_content_items(self):
        self.assertEqual(
            ['Foo'],
            [p.title for p in self.view._get_objects(self.request)]
        )


    def test_should_return_content_items_matching_attr(self):
        bar = TestDirectoryContent.objects.create(title='Bar')
        try:
            view = DirectoryContentView('Test', 'title', 'Bar', TestDirectoryContent)
            self.assertEqual(
                ['Bar'],
                [p.title for p in view._get_objects(self.request)]
            )
        finally:
            bar.delete()


    def test_should_render_preview_content_for_existing_page(self):
        response = self.view.preview(self.request, pk=self.page.pk)
        self.assertEqual(200, response.status_code)
        self.assertIn('<title>Foo</title>', response.content)


    def test_should_render_preview_content_for_new_page(self):
        response = self.view.preview(self.request)
        self.assertEqual(200, response.status_code)
        self.assertIn('<title></title>', response.content)


    def test_should_render_preview_with_given_template(self):
        response = self.view.preview(self.factory.get('/', {'template': 'testapp/test.html'}))
        self.assertEqual(200, response.status_code)
        self.assertEqual('Test', response.content)


    def test_should_render_preview_ignoring_given_template_if_not_valid(self):
        response = self.view.preview(self.factory.get('/', {'template': 'does-not-exist'}))
        self.assertEqual(200, response.status_code)
        self.assertIn('<title></title>', response.content)


    def test_should_foo_for_non_existing_page(self):
        with self.assertRaisesRegexp(Http404, 'Unknown primary key'):
            self.view.preview(self.request, pk=9999)


@override_settings(CMS_PAGE_MODEL = 'cubane.testapp.models.CustomDirectoryPage')
class TestDirectoryCMSExtensionsCacheTestCase(CubaneTestCase):
    def test_should_cache_aggregator_page(self):
        page = CustomDirectoryPage(title='Cromer')
        page.save()
        try:
            cms = get_cms()
            cache_items, _, _ = cms.publish()
            self.assertEqual(1, cache_items)
        finally:
            page.delete()


    def test_should_not_cache_disabled_aggregator_page(self):
        page = CustomDirectoryPage(title='Cromer', disabled=True)
        page.save()
        try:
            cms = get_cms()
            cache_items, _, _ = cms.publish()
            self.assertEqual(0, cache_items)
        finally:
            page.delete()


    def test_should_not_cache_aggregator_page_with_custom_visibility_checks(self):
        page = CustomDirectoryPage(title='Cromer')
        page.save()
        _filter_visibility = self.patch_filter_visibility(CustomDirectoryPage)
        try:
            cms = get_cms()
            cache_items, _, _ = cms.publish()
            self.assertEqual(0, cache_items)
        finally:
            page.delete()
            self.restore_filter_visibility(CustomDirectoryPage, _filter_visibility)


    def test_should_cache_directory_content(self):
        content = TestDirectoryContent(title='Hotel A')
        content.save()
        try:
            cms = get_cms()
            cache_items, _, _ = cms.publish()
            self.assertEqual(1, cache_items)
        finally:
            content.delete()


    def test_should_not_cache_disabled_directory_content(self):
        content = TestDirectoryContent(title='Hotel A', disabled=True)
        content.save()
        try:
            cms = get_cms()
            cache_items, _, _ = cms.publish()
            self.assertEqual(0, cache_items)
        finally:
            content.delete()


    def test_should_not_cache_directory_content_with_custom_visibility_checks(self):
        content = TestDirectoryContent(title='Hotel A')
        content.save()
        _filter_visibility = self.patch_filter_visibility(TestDirectoryContent)
        try:
            cms = get_cms()
            cache_items, _, _ = cms.publish(True)
            self.assertEqual(0, cache_items)
        finally:
            content.delete()
            self.restore_filter_visibility(TestDirectoryContent, _filter_visibility)


class TestDirectoryCMSExtensionsSitemapTestCase(CubaneTestCase):
    def setUp(self):
        self.cms = get_cms()
        self.sitemap = self.cms.get_sitemaps()


    def tearDown(self):
        [p.delete() for p in TestDirectoryContent.objects.all()]


    def test_should_publish_directory_content(self):
        content = TestDirectoryContent.objects.create(title='Content')
        items = list(self.sitemap.get('test-directory-content').items())
        self.assertEqual(1, len(items))
        self.assertEqual('Content', items[0].title)


    def test_should_not_publish_disabled_directory_content(self):
        content = TestDirectoryContent.objects.create(title='Content', disabled=True)
        items = list(self.sitemap.get('test-directory-content').items())
        self.assertEqual(0, len(items))


    def test_should_not_publish_directory_content_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(TestDirectoryContent)
        try:
            content = TestDirectoryContent.objects.create(title='Content')
            items = list(self.sitemap.get('test-directory-content').items())
            self.assertEqual(0, len(items))
        finally:
            self.restore_filter_visibility(TestDirectoryContent, _filter_visibility)


class DirectoryCMSExtensionTestCaseBase(CubaneTestCase):
    def setUp(self):
        self.cms = get_cms()


    def _get_pages(self, include_tags, exclude_tags=[], order=DirectoryOrder.ORDER_TITLE, max_items=None, navigation=False):
        pages = self.cms.get_aggregated_pages(include_tags, exclude_tags, order, max_items, navigation)
        return [p.title for p in pages]


class DirectoryCMSExtensionGetDirctoryTagsTestCase(DirectoryCMSExtensionTestCaseBase):
    """
    cubane.directory.views.CMSExtensions.get_directory_tags()
    """
    def test_should_return_empty_list_if_no_directory_tags_are_defined(self):
        self.assertEqual([], self.cms.get_directory_tags())


    def test_should_return_list_of_directory_tags(self):
        a = DirectoryTag.objects.create(title='a')
        b = DirectoryTag.objects.create(title='b')
        try:
            self.assertEqual([a, b], self.cms.get_directory_tags())
        finally:
            b.delete()
            a.delete()


class DirectoryCMSExtensionGetDirectoryTagChoicesTestCase(DirectoryCMSExtensionTestCaseBase):
    """
    cubane.directory.views.CMSExtensions.get_directory_tag_choices()
    """
    def test_should_return_empty_list_if_no_directory_tags_are_defined(self):
        self.assertEqual([], self.cms.get_directory_tag_choices())


    def test_should_return_list_of_choices_for_all_directory_tags(self):
        a = DirectoryTag.objects.create(title='a')
        b = DirectoryTag.objects.create(title='b')
        try:
            self.assertEqual(
                [('a', 'a'), ('b', 'b')],
                self.cms.get_directory_tag_choices()
            )
        finally:
            b.delete()
            a.delete()


class DirectoryCMSExtensionGetDirectoryCategoryModelsTestCase(DirectoryCMSExtensionTestCaseBase):
    """
    cubane.directory.views.CMSExtensions.get_directory_category_models()
    """
    def test_should_return_aggregatable_content_models(self):
        self.assertEqual([
            TestDirectoryCategory
        ], self.cms.get_directory_category_models())


class DirectoryCMSExtensionGetDirectoryModelsTestCase(DirectoryCMSExtensionTestCaseBase):
    """
    cubane.directory.views.CMSExtensions.get_directory_models()
    """
    def test_should_return_aggregatable_content_models(self):
        self.assertEqual([
            TestDirectoryContent,
            TestDirectoryContentWithBackendSections,
            TestContentAggregator
        ], self.cms.get_directory_models())


class DirectoryCMSExtensionGetAggregatedPagesTestCase(DirectoryCMSExtensionTestCaseBase):
    @classmethod
    def setUpClass(cls):
        super(DirectoryCMSExtensionGetAggregatedPagesTestCase, cls).setUpClass()
        cls.a = TestDirectoryContent(title='a', seq=4, tags=['a', 'b'])
        cls.b = TestDirectoryContent(title='b', seq=3, tags=['b', 'c'])
        cls.c = TestDirectoryContent(title='c', seq=2, tags=['c'], ptags=['d'])
        cls.d = TestDirectoryContent(title='d', seq=1, tags=['e'])
        cls.a.save()
        cls.b.save()
        cls.c.save()
        cls.d.save()


    @classmethod
    def tearDownClass(cls):
        cls.a.delete()
        cls.b.delete()
        cls.c.delete()
        cls.d.delete()
        super(DirectoryCMSExtensionGetAggregatedPagesTestCase, cls).tearDownClass()


    def setUp(self):
        super(DirectoryCMSExtensionGetAggregatedPagesTestCase, self).setUp()
        self.cms.settings.order_mode=DirectoryOrder.ORDER_SEQ
        self.cms.settings.save()


    def test_should_return_content_pages_based_on_include_tags(self):
        self.assertEqual(['a', 'b'], self._get_pages(['b']))


    def test_should_join_multiple_sets_of_include_tags(self):
        self.assertEqual(['a', 'b'], self._get_pages([['a'], ['b', 'c']]))


    def test_should_not_respect_priority_tags_if_found_through_regular_tag(self):
        self.assertEqual(['a', 'b', 'c'], self._get_pages([['b'], ['c']]))


    def test_should_respect_priority_tags_if_found_through_priority_tag(self):
        self.assertEqual(['c', 'a', 'b'], self._get_pages([['b'], ['d']]))


    def test_should_respect_exclude_tags_for_tag_searched_against(self):
        self.assertEqual(['b', 'c'], self._get_pages([['a'], ['c']], ['a']))


    def test_should_respect_exclude_tags_for_tag_not_searched_against(self):
        self.assertEqual(['a'], self._get_pages([['b'], ['d']], ['c']))


    def test_should_respect_exclude_tags_for_priority_tag(self):
        self.assertEqual(['a', 'b'], self._get_pages([['b'], ['d']], ['d']))


    def test_should_fallback_to_settings_order_if_no_specific_order_is_specified(self):
        self.assertEqual(['b', 'a'], self._get_pages(['b'], [], DirectoryOrder.ORDER_DEFAULT))


    def test_should_order_by_seq(self):
        self.assertEqual(['b', 'a'], self._get_pages(['b'], [], DirectoryOrder.ORDER_SEQ))


    def test_should_order_by_title(self):
        self.assertEqual(['a', 'b'], self._get_pages(['b'], [], DirectoryOrder.ORDER_TITLE))


    def test_should_order_by_date(self):
        self.assertEqual(['b', 'a'], self._get_pages(['b'], [], DirectoryOrder.ORDER_DATE))


    @patch('random.randint')
    def test_should_order_by_random_order(self, randint):
        self.seq = 100
        def random_order(min, max):
            self.seq -= 1
            return self.seq
        randint.side_effect = random_order

        self.assertEqual(
            ['d', 'c', 'b', 'a'],
            self._get_pages([['b'], ['c'], ['e']], [], DirectoryOrder.ORDER_RANDOM)
        )


    def test_should_restrict_max_number_of_results_if_provided(self):
        self.assertEqual(
            ['a', 'b'],
            self._get_pages([['b'], ['c'], ['e']], [], DirectoryOrder.ORDER_TITLE, 2)
        )


    def test_should_not_aggregate_disabled_content(self):
        try:
            self.a.disabled = True
            self.a.save()
            self.assertEqual(['b'], self._get_pages(['b']))
        finally:
            self.a.disabled = False
            self.a.save()


    def test_should_not_aggregate_content_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(TestDirectoryContent)
        try:
            self.assertEqual([], self._get_pages(['b']))
        finally:
            self.restore_filter_visibility(TestDirectoryContent, _filter_visibility)


class DirectoryCMSExtensionMixedDirectoryContentTestCaseBase(DirectoryCMSExtensionTestCaseBase):
    def _setup(self, cascade_tags):
        self.a = TestContentAggregator(title='Cromer', tags=['cromer'], include_tags_1=['cromer'])
        self.b = TestContentAggregator(title='Cromer Hotels', tags=['cromer'], include_tags_1=['cromer', 'hotel'], cascade_tags=cascade_tags)
        self.c = TestDirectoryContent(title='Hotel A', tags=['cromer', 'hotel'])
        self.d = TestDirectoryContent(title='Hotel B', tags=['cromer', 'hotel'])
        self.a.save()
        self.b.save()
        self.c.save()
        self.d.save()
        self.cms.settings.order_mode=DirectoryOrder.ORDER_TITLE


    def tearDown(self):
        self.a.delete()
        self.b.delete()
        self.c.delete()
        self.d.delete()


class DirectoryCMSExtensionGetAggregatedPagesWithoutCascadeTestCase(DirectoryCMSExtensionMixedDirectoryContentTestCaseBase):
    def setUp(self):
        super(DirectoryCMSExtensionGetAggregatedPagesWithoutCascadeTestCase, self).setUp()
        self._setup(cascade_tags=False)


    def test_should_respect_cascade(self):
        self.assertEqual(['Cromer', 'Cromer Hotels', 'Hotel A', 'Hotel B'], self._get_pages(['cromer']))


class DirectoryCMSExtensionGetAggregatedPagesShouldRespectCascadeTestCase(DirectoryCMSExtensionMixedDirectoryContentTestCaseBase):
    def setUp(self):
        super(DirectoryCMSExtensionGetAggregatedPagesShouldRespectCascadeTestCase, self).setUp()
        self._setup(cascade_tags=True)


    def test_should_respect_cascade(self):
        self.assertEqual(['Cromer', 'Cromer Hotels'], self._get_pages(['cromer']))


class DirectoryCMSExtensionGetAggregatedPagesAdditionalTestCase(DirectoryCMSExtensionTestCaseBase):
    def test_should_deliver_result_from_cache(self):
        a = TestDirectoryContent(title='a', tags=['a', 'b'])
        b = TestDirectoryContent(title='b', tags=['b', 'c'])
        a.save()
        b.save()

        self.assertEqual(['a', 'b'], self._get_pages(['b']))

        # delete objects, they should now come from cache
        a.delete()
        b.delete()
        self.assertEqual(['a', 'b'], self._get_pages(['b']))


class DirectoryCMSExtensionGetAggregatedPagesNavigationTestCase(DirectoryCMSExtensionTestCaseBase):
    def setUp(self):
        super(DirectoryCMSExtensionGetAggregatedPagesNavigationTestCase, self).setUp()
        self.a = TestDirectoryContent(title='a', tags=['a', 'b'])
        self.b = TestDirectoryContent(title='b', tags=['b', 'c'])
        self.c = TestDirectoryContentEntity(title='c', tags=['b', 'd'])
        self.a.save()
        self.b.save()
        self.c.save()


    def tearDown(self):
        self.a.delete()
        self.b.delete()
        self.c.delete()


    def test_should_exclude_content_entities_for_navigation(self):
        self.assertEqual(
            ['a', 'b'],
            self._get_pages(['b'], order=DirectoryOrder.ORDER_TITLE, navigation=True)
        )


    def test_should_include_content_entities_for_none_navigation(self):
        self.assertEqual(
            ['a', 'b', 'c'],
            self._get_pages(['b'], order=DirectoryOrder.ORDER_TITLE, navigation=False)
        )


class DirectoryCMSExtensionGetAggregatedPagesForPageTestCase(DirectoryCMSExtensionMixedDirectoryContentTestCaseBase):
    def setUp(self):
        super(DirectoryCMSExtensionGetAggregatedPagesForPageTestCase, self).setUp()
        self._setup(cascade_tags=True)


    def test_should_return_aggregated_pages_for_given_page_with_cascade(self):
        pages = [p.title for p in self.cms.get_aggregated_pages_for_page(self.b)]
        self.assertEqual(['Hotel A', 'Hotel B'], pages)


class TestDirectoryContentRequestHandlerTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDirectoryContentRequestHandlerTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')
        cls.model = TestDirectoryContent
        cls.page = cls.model.objects.create(title='Foo', slug='foo')


    @classmethod
    def tearDownClass(cls):
        cls.page.delete()
        super(TestDirectoryContentRequestHandlerTestCase, cls).tearDownClass()


    def test_should_render_content_based_on_slug(self):
        response = content(self.request, self.page.pk, self.page.slug, self.model)
        self.assertEqual(200, response.status_code)
        self.assertIn('<title>Foo</title>', response.content)


    def test_should_respect_attribute_condition(self):
        response = content(self.request, self.page.pk, self.page.slug, self.model, 'title', 'Foo')
        self.assertEqual(200, response.status_code)
        self.assertIn('<title>Foo</title>', response.content)


    def test_should_raise_404_if_attribute_condition_does_not_match(self):
        with self.assertRaisesRegexp(Http404, 'Unknown primary key or page is disabled'):
            content(self.request, self.page.pk, self.page.slug, self.model, 'title', 'Does Not Exist')


    def test_should_raise_404_if_pk_is_unknown(self):
        with self.assertRaisesRegexp(Http404, 'Unknown primary key or page is disabled'):
            content(self.request, 9999, self.page.slug, self.model)


    def test_should_redirect_if_slug_does_not_match(self):
        response = content(self.request, self.page.pk, 'bar', self.model)
        self.assertEqual(301, response.status_code)
        self.assertEqual('/test-directory-content/foo-%d/' % self.page.pk, response.get('Location'))


    def test_should_raise_404_if_page_is_disabled(self):
        try:
            self.page.disabled = True
            self.page.save()

            # should raise 404 with matching slug
            with self.assertRaisesRegexp(Http404, 'Unknown primary key or page is disabled'):
                content(self.request, self.page.pk, self.page.slug, self.model)

            # should raise 404 with non-matching slug
            with self.assertRaisesRegexp(Http404, 'Unknown primary key or page is disabled'):
                content(self.request, self.page.pk, 'slug-does-not_match', self.model)
        finally:
            self.page.disabled = False
            self.page.save()


    def test_should_raise_404_if_filtered_by_custom_visibility_checks(self):
        def filter_visibility(cls, objects, visibility_filter_args={}):
            return objects.filter(title='Bar')
        _filter_visibility = self.model.filter_visibility
        self.model.filter_visibility = classmethod(filter_visibility)

        try:
            # should raise 404, since not visible
            with self.assertRaisesRegexp(Http404, 'Unknown primary key or page is disabled'):
                content(self.request, self.page.pk, self.page.slug, self.model)
        finally:
            self.model.filter_visibility = _filter_visibility