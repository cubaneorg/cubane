# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.template.defaultfilters import slugify
from django.utils.safestring import SafeText
from cubane.tests.base import CubaneTestCase
from cubane.directory.models import *
from cubane.directory.forms import *
from cubane.testapp.models import TestDirectoryContent
from cubane.testapp.models import TestDirectoryCategory
from cubane.testapp.models import TestDirectoryContentWithBackendSections
from cubane.testapp.models import TestContentAggregator
from cubane.testapp.models import TestDirectoryContentEntity
from cubane.testapp.models import TestDirectoryEntity
from mock import patch


class CMSDirectoryModelsTestCase(CubaneTestCase):
    def _get_sections(self, model):
        for section, name in TestDirectoryContentWithBackendSections.BACKEND_SECTION_CHOICES:
            yield (section, slugify(name))


class CMSDirectoryModelsDirectoryTagTestCase(CMSDirectoryModelsTestCase):
    def setUp(self):
        self.a = DirectoryTag(title='a')
        self.a.save()

        self.page = TestDirectoryContent()
        self.page.tags = ['a', 'b']
        self.page.save()


    def tearDown(self):
        if self.a.pk: self.a.delete()
        self.page.delete()


    def test_get_form_should_return_default_form(self):
        self.assertTrue(issubclass(self.a.get_form(), DirectoryTagForm))


    def test_delete_should_remove_tag_from_model(self):
        self.a.delete()
        page = TestDirectoryContent.objects.get(pk=self.page.pk)
        self.assertEqual(['b'], page.tags)


    def test_renaming_tag_should_update_references(self):
        self.a.title = 'c'
        self.a.save()
        page = TestDirectoryContent.objects.get(pk=self.page.pk)
        self.assertEqual(['b', 'c'], page.tags)


class CMSDirectoryModelsDirectoryContentAggregatorTestCase(CMSDirectoryModelsTestCase):
    def test_get_include_tags_should_return_all_inclusion_tags(self):
        c = TestDirectoryCategory(
            title='Test',
            include_tags_1=['a1', 'b1'],
            include_tags_2=['a2', 'b2'],
            include_tags_3=['a3', 'b3'],
            include_tags_4=['a4', 'b4'],
            include_tags_5=['a5', 'b5'],
            include_tags_6=['a6', 'b6']
        )
        c.save()
        self.assertEqual([
            ['a1', 'b1'],
            ['a2', 'b2'],
            ['a3', 'b3'],
            ['a4', 'b4'],
            ['a5', 'b5'],
            ['a6', 'b6']
        ], c.get_include_tags())


class CMSDirectoryModelsDirectoryContentBaseManagerTestCase(CMSDirectoryModelsTestCase):
    @classmethod
    def setUpClass(cls):
        super(CMSDirectoryModelsDirectoryContentBaseManagerTestCase, cls).setUpClass()
        cls.a = TestDirectoryContent(title='a', tags=['a', 'b'])
        cls.b = TestDirectoryContent(title='b', tags=['b', 'c'])
        cls.c = TestDirectoryContent(title='c', tags=['c'], ptags=['d'])
        cls.d = TestDirectoryContent(title='d', tags=['e'])
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
        super(CMSDirectoryModelsDirectoryContentBaseManagerTestCase, cls).tearDownClass()


    def test_filter_by_tags_should_include_content_by_include_tags_union(self):
        self._assert_filter_by_tags([self.a, self.b, self.c], [['a'], ['b'], ['c']], [], [False, False, False])


    def test_filter_by_tags_should_include_content_by_priority_tags(self):
        self._assert_filter_by_tags([self.a, self.b, self.c], [['a'], ['b'], ['d']], [], [False, False, True])


    def test_filter_by_tags_should_include_content_by_include_matching_per_group(self):
        self._assert_filter_by_tags([self.a], [['a', 'b']])


    def test_filter_by_tags_should_exclude_content(self):
        self._assert_filter_by_tags([self.c], [['a'], ['b'], ['c']], ['b'])


    def test_filter_by_tags_should_exclude_content_even_for_priority_tags(self):
        self._assert_filter_by_tags([self.a, self.b], [['b'], ['d']], ['d'])


    def test_filter_by_tags_should_aggregate_no_content_for_empty_inclusion_tags(self):
        self._assert_filter_by_tags([], [])


    def test_filter_by_tags_from_page_should_take_inclusion_tags_from_page(self):
        category = TestDirectoryCategory(
            title='Test',
            include_tags_1=['a'],
            include_tags_2=['b'],
            include_tags_3=['c'],
            exclude_tags=['b']
        )
        items = TestDirectoryContent.objects.filter_by_tags_from_page(category)
        self._assert_filter_by_tags_for_items(items, [self.c])


    def _assert_filter_by_tags(self, expected_pages, include_tags, exclude_tags=[], priority=[]):
        items = TestDirectoryContent.objects.filter_by_tags(include_tags, exclude_tags)
        self._assert_filter_by_tags_for_items(items, expected_pages, priority)


    def _assert_filter_by_tags_for_items(self, items, expected_pages, priority=[]):
        actual = [p.title for p in items]
        expected = [p.title for p in expected_pages]
        self.assertEqual(expected, actual)

        if len(priority) > 0:
            actual_priority = [p.priority for p in items]
            self.assertEqual(priority, actual_priority)


class CMSDirectoryModelsDirectoryContentMixinTestCase(CMSDirectoryModelsTestCase):
    def test_get_directory_content_type_slugs_should_return_default_slug_for_backend_if_no_backend_sections_are_used(self):
        self.assertEqual([
            (None, None, 'test-directory-content')
        ], TestDirectoryContent.get_directory_content_type_slugs())


    def test_get_directory_content_type_slugs_should_return_backend_sections_if_present(self):
        self.assertEqual([
            ('backend_section', 1, 'a'),
            ('backend_section', 2, 'b')
        ], TestDirectoryContentWithBackendSections.get_directory_content_type_slugs())


    def test_get_directory_content_type_slug_should_return_default_slug_if_backend_sections_are_not_used(self):
        self.assertEqual(
            'test-directory-content',
            TestDirectoryContent().get_directory_content_type_slug()
        )


    def test_get_directory_content_type_slug_should_return_slug_based_on_backend_sections_if_used(self):
        for section, slug in self._get_sections(TestDirectoryContentWithBackendSections):
            self.assertEqual(
                slug,
                TestDirectoryContentWithBackendSections(backend_section=section).get_directory_content_type_slug()
            )


    def test_unique_pk_should_return_pk_with_content_type_slug_without_backend_sections(self):
        self.assertEqual('1-directory-content', TestDirectoryContent(id=1).unique_pk)


    def test_unique_pk_should_return_pk_with_content_type_slug_without_backend_sections(self):
        for section, slug in self._get_sections(TestDirectoryContentWithBackendSections):
            self.assertEqual('1-%s' % slug, TestDirectoryContentWithBackendSections(id=1, backend_section=section).unique_pk)


    def test_tags_set_should_return_tags_and_priority_tags(self):
        self.assertEqual(set(['a', 'b']), TestDirectoryContent(tags=['a', 'b']).tags_set)
        self.assertEqual(set(['a', 'b']), TestDirectoryContent(ptags=['a', 'b']).tags_set)
        self.assertEqual(set(['a', 'b', 'c']), TestDirectoryContent(tags=['a', 'b'], ptags=['c']).tags_set)
        self.assertEqual(set(['a', 'b']), TestDirectoryContent(tags=['a', 'b'], ptags=['b']).tags_set)


    def test_nav_title_should_return_nav_title_if_present(self):
        nav_title = TestDirectoryContent(_nav_title='Test').nav_title
        self.assertEqual('Test', nav_title)
        self.assertIsInstance(nav_title, SafeText)


    def test_nav_title_should_substitute_underscore_with_non_breakable_spaces(self):
        self.assertEqual('Hello&nbsp;World', TestDirectoryContent(_nav_title='Hello_World').nav_title)


    def test_nav_title_should_return_default_title_if_no_nav_title_is_available(self):
        self.assertEqual('Test', TestDirectoryContent(title='Test').nav_title)


    def test_breakable_nav_title_should_return_nav_title_ignoring_underscore(self):
        self.assertEqual('Hello World', TestDirectoryContent(_nav_title='Hello_World').breakable_nav_title)


    def test_breakable_nav_title_should_return_title_ignoring_underscore(self):
        self.assertEqual('Hello World', TestDirectoryContent(title='Hello_World').breakable_nav_title)


    def test_has_nav_title_should_return_true_if_nav_title_is_present(self):
        self.assertTrue(TestDirectoryContent(_nav_title='Test').has_nav_title)
        self.assertFalse(TestDirectoryContent().has_nav_title)


    def test_matches_tags_should_return_true_if_at_least_one_tag_is_matched(self):
        self._assert_matches_tags(set(['a']), True)
        self._assert_matches_tags(set(['b']), True)
        self._assert_matches_tags(set(['c']), True)
        self._assert_matches_tags(set(['x', 'y', 'a']), True)
        self._assert_matches_tags(set(['x']), False)
        self._assert_matches_tags(set(['x', 'y']), False)
        self._assert_matches_tags(set(), False)


    def test_matches_inclusion_tags_should_return_true_if_at_least_one_tag_is_matched_but_no_exclusion_tag_is_matched(self):
        self._assert_matches_inclusion_tags(['a'], [], True)
        self._assert_matches_inclusion_tags(['b'], [], True)
        self._assert_matches_inclusion_tags(['c'], [], True)
        self._assert_matches_inclusion_tags(['x', 'y', 'a'], [], True)
        self._assert_matches_inclusion_tags(['x'], [], False)
        self._assert_matches_inclusion_tags(['x', 'y'], [], False)
        self._assert_matches_inclusion_tags(['a'], ['a'], False)
        self._assert_matches_inclusion_tags(['a'], ['b'], False)
        self._assert_matches_inclusion_tags(['a'], ['c'], False)
        self._assert_matches_inclusion_tags(['a'], ['x'], True)


    def _assert_matches_tags(self, tags, expected_result):
        self.assertEqual(
            expected_result,
            TestDirectoryContent(tags=['a', 'b'], ptags=['c']).matches_tags(tags)
        )


    def _assert_matches_inclusion_tags(self, include_tags, exclude_tags, expected_result):
        self.assertEqual(
            expected_result,
            TestDirectoryContent(tags=['a', 'b'], ptags=['c']).matches_inclusion_tags(include_tags, exclude_tags)
        )


class CMSDirectoryModelsDirectoryContentBaseTestCase(CMSDirectoryModelsTestCase):
    def test_slug_with_id_should_return_slug_with_id(self):
        self.assertEqual('test-1', TestDirectoryContent(id=1, slug='test').slug_with_id)


    def test_slug_with_id_should_return_slug_if_id_is_none(self):
        self.assertEqual('test', TestDirectoryContent(slug='test').slug_with_id)


    def test_get_filepath_should_return_path_to_cache_file_for_content_without_backend_section(self):
        self.assertEqual('test-directory-content/test-1/index.html', TestDirectoryContent(id=1, slug='test').get_filepath())


    def test_get_filepath_should_return_path_to_cache_file_for_content_with_backend_section(self):
        for section, slug in self._get_sections(TestDirectoryContentWithBackendSections):
            self.assertEqual('%s/test-1/index.html' % slug, TestDirectoryContentWithBackendSections(id=1, slug='test', backend_section=section).get_filepath())


    def test_get_fullslug_should_return_full_slug_to_page_for_content_without_backend_section(self):
        self.assertEqual('/test-directory-content/test-1/', TestDirectoryContent(id=1, slug='test').get_fullslug())


    def test_get_fullslug_should_return_full_slug_to_page_for_content_with_backend_section(self):
        for section, slug in self._get_sections(TestDirectoryContentWithBackendSections):
            self.assertEqual('/%s/test-1/' % slug, TestDirectoryContentWithBackendSections(id=1, slug='test', backend_section=section).get_fullslug())


    def test_url_should_return_absolute_url(self):
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/test-directory-content/test-1/',
            TestDirectoryContent(id=1, slug='test').url
        )


class CMSDirectoryModelsDirectoryContentAndAggregatorTestCase(CMSDirectoryModelsTestCase):
    def test_get_cascading_tags_with_cascading_turned_on(self):
        # this page defines its content as wroxham and then aggregates content
        # that is tagged as wroxham AND boating.
        # Since tags are cascading, the resulting CASCADING tag should be
        # boating, so that boating is eliminated from the result.
        page = TestContentAggregator(tags=['wroxham'], include_tags_1=['wroxham', 'boating'], cascade_tags=True)
        self.assertEqual(set(['boating']), page.get_cascading_tags())


    def test_get_cascading_tags_should_return_empty_set_if_cascading_is_turned_off(self):
        page = TestContentAggregator(tags=['wroxham'], include_tags_1=['wroxham', 'boating'], cascade_tags=False)
        self.assertEqual(set(), page.get_cascading_tags())


class CMSDirectoryModelsDirectoryContentEntityManagerTestCase(CMSDirectoryModelsTestCase):
    def test_should_always_fetch_related_images(self):
        self.assertEqual(['image'], TestDirectoryContentEntity.objects.all().query.select_related.keys())


class CMSDirectoryModelsDirectoryContentEntityTestCase(CMSDirectoryModelsTestCase):
    def test_is_entity_should_return_true(self):
        self.assertTrue(TestDirectoryContentEntity().is_entity)


class CMSDirectoryModelsDirectoryEntityManagerTestCase(CMSDirectoryModelsTestCase):
    def test_should_always_fetch_related_images(self):
        self.assertEqual(['image'], TestDirectoryEntity.objects.all().query.select_related.keys())


class CMSDirectoryModelsDirectoryEntityTestCase(CMSDirectoryModelsTestCase):
    def test_should_return_none_if_no_backend_group_is_defined(self):
        self.assertIsNone(TestDirectoryEntity.get_backend_section_group())


    def test_should_return_backend_group_if_defined(self):
        try:
            class Listing:
                group = 'foo'
            TestDirectoryEntity.Listing = Listing
            self.assertEqual('foo', TestDirectoryEntity.get_backend_section_group())
        finally:
            delattr(TestDirectoryEntity, 'Listing')


class CMSDirectoryModelsCacheInvalidationDirectoryEntityTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(CMSDirectoryModelsCacheInvalidationDirectoryEntityTestCase, cls).setUpClass()
        cls.model = TestDirectoryEntity


    @patch('cubane.cms.views.CMS.invalidate')
    def test_create_directory_entity_should_invalidate_cache(self, invalidate):
        try:
            entity = self.model.objects.create()
            self.assertTrue(invalidate.called)
        finally:
            entity.delete()


    @patch('cubane.cms.views.CMS.invalidate')
    def test_update_directory_entity_should_invalidate_cache(self, invalidate):
        entity = self.model.objects.create()
        try:
            entity.seq = 99
            entity.save()
            self.assertTrue(invalidate.called)
        finally:
            entity.delete()


    @patch('cubane.cms.views.CMS.invalidate')
    def test_delete_directory_entity_should_invalidate_cache(self, invalidate):
        entity = self.model.objects.create()
        entity.delete()
        self.assertTrue(invalidate.called)


class CMSDirectoryModelsCacheInvalidationDirectoryCategoryTestCase(CMSDirectoryModelsCacheInvalidationDirectoryEntityTestCase):
    @classmethod
    def setUpClass(cls):
        super(CMSDirectoryModelsCacheInvalidationDirectoryCategoryTestCase, cls).setUpClass()
        cls.model = TestDirectoryCategory