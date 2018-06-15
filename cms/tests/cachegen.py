# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.core.management import call_command
from cubane.tests.base import CubaneTestCase
from cubane.cms.tests.views import CMSViewsCMSBaseTestCase
from cubane.cms.views import get_cms, fake_request
from cubane.cms.models import Page
from cubane.testapp.models import TestModel, Settings
from freezegun import freeze_time
from datetime import datetime
import os
import shutil


class CMSCacheGenMaterialiseTemplateContextTestCase(CubaneTestCase):
    """
    cubane.lib.templatetags.materialise_template_context()
    """
    @classmethod
    def setUpClass(cls):
        cls.cms = get_cms()
        cls.generator = cls.cms.get_cache_generator()
        cls.a = TestModel(title='a')
        cls.a.save()


    @classmethod
    def tearDownClass(cls):
        cls.a.delete()


    def test_should_return_empty_dict_for_none(self):
        self.assertEqual({}, self.generator.materialise_template_context(None))


    def test_should_ignore_if_not_dict(self):
        self.assertEqual('not a dict', self.generator.materialise_template_context('not a dict'))


    def test_should_materialise_query_set_member(self):
        d = {
            'objects': TestModel.objects.all()
        }
        self.generator.materialise_template_context(d)
        self.assertIsInstance(d.get('objects'), list)


    def test_should_materialise_nested_queryset_members(self):
        d = {
            'info': {
                'objects': TestModel.objects.all()
            }
        }
        self.generator.materialise_template_context(d)
        self.assertIsInstance(d.get('info').get('objects'), list)


class CMSCacheGenPublishTestCase(CMSViewsCMSBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(CMSCacheGenPublishTestCase, cls).setUpClass()


    def setUp(self):
        super(CMSCacheGenPublishTestCase, self).setUp()
        self.cms = get_cms()
        self.generator = self.cms.get_cache_generator()
        self._delete_public_html()


    def _delete_public_html(self):
        path = settings.PUBLIC_HTML_ROOT
        if os.path.exists(path):
            shutil.rmtree(path)


    def test_should_cache_pages(self):
        cache_items, cache_size, _ = self.cms.publish(True)
        self.assertEqual(cache_items, 1, 'There is only one page.')
        self.assertEqual(cache_size > 0, True, 'Size of cache should be more than zero.')


    def test_should_cache_child_pages(self):
        settings = self.set_settings_vars({
            'paging_enabled': True,
            'paging_child_pages': ['blog_blogpost'],
            'page_size': 4
        })
        self.page.entity_type = 'BlogPost'
        self.page.save()

        cache_items, cache_size, _ = self.cms.publish(True)
        self.assertEqual(cache_items, 2, 'There is one page and one child page.')
        self.assertEqual(cache_size > 0, True, 'Size of cache should be more than zero.')


    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_should_cache_contact_page_if_csrf_is_off(self):
        settings = self.set_settings_vars({
            'contact_page': self.page
        })
        cache_items, cache_size, _ = self.cms.publish(True)
        self.assertEqual(cache_items, 1, 'There is one contact us page which should be cached because CSRF is turned off.')


    @override_settings(MIDDLEWARE_CLASSES=['django.middleware.csrf.CsrfViewMiddleware'])
    def test_should_not_cache_contact_page_if_csrf_is_on(self):
        settings = self.set_settings_vars({
            'contact_page': self.page
        })
        cache_items, cache_size, _ = self.cms.publish(True)
        self.assertEqual(cache_items, 0, 'There is one contact us page, but it should not be cached due to CSRF being turned on.')


    def test_should_not_publish_child_pages_without_page_reference(self):
        self.page.entity_type = 'BlogPost'
        self.page.save()
        child_page = self.create_child_page(2)
        child_page.page = None
        child_page.save()

        # should not raise ChildPageWithoutParentError()
        self.cms.publish(True)


    def test_should_not_publish_child_page_if_page_does_not_support_child_pages(self):
        self.page.entity_type = 'BlogPost'
        self.page.save()
        child_page = self.create_child_page(2, page=self.page)

        abandoned_page = self.create_page('Abandoned Page', entity_type=None)
        abandoned_child = self.create_child_page(3, page=abandoned_page)

        # should not raise Http404()
        self.cms.publish(True)


    def test_should_generate_cache_for_pagination(self):
        settings = self.set_settings_vars({
            'paging_enabled': True,
            'paging_child_pages': ['blog_blogpost'],
            'page_size': 2
        })
        self.page.entity_type = 'BlogPost'
        self.page.save()
        child_page_one = self.create_child_page(2)
        child_page_two = self.create_child_page(3)
        child_page_three = self.create_child_page(4)
        cache_items, cache_size, _ = self.cms.publish(True)
        self.assertEqual(cache_items, 6, 'There should be 6 cache files as there is pagination.')
        self.assertEqual(cache_size >= 0, True)


    def test_should_determine_updated_on_from_page(self):
        [m.delete() for m in TestModel.objects.all()]
        [s.delete() for s in Settings.objects.all()]
        page = self._create_test_page('Foo', updated_on='2016-09-13')

        try:
            self.assertEqual(datetime(2016, 9, 13), self.cms.render_page(page, cache_generator=self.generator).mtime)
        finally:
            page.delete()


    def test_should_determine_updated_on_from_template_context(self):
        [m.delete() for m in TestModel.objects.all()]
        [s.delete() for s in Settings.objects.all()]
        page = self._create_test_page('Foo', updated_on='2016-09-13')
        a = self._create_test_model('a', updated_on='2016-09-14')
        try:
            self.assertEqual(datetime(2016, 9, 14), self.cms.render_page(page, cache_generator=self.generator).mtime)
        finally:
            page.delete()
            a.delete()


    def test_should_determine_updated_on_from_child_pages(self):
        [m.delete() for m in TestModel.objects.all()]
        [s.delete() for s in Settings.objects.all()]
        page = self._create_test_page('Foo', entity_type='BlogPost', updated_on='2016-09-13')
        child = self._create_test_child_page(1, page=page, updated_on='2016-09-15')

        a = self._create_test_model('a', updated_on='2016-09-14')
        try:
            cms = get_cms()
            self.assertEqual(datetime(2016, 9, 15), self.cms.render_page(page, cache_generator=self.generator).mtime)
        finally:
            page.delete()
            child.delete()


    def test_should_not_cache_disabled_page(self):
        self.page.disabled = True
        self.page.save()
        try:
            cache_items, cache_size, _ = self.cms.publish(True)
            self.assertEqual(0, cache_items)
            self.assertEqual(0, cache_size)
        finally:
            self.page.disabled = False
            self.page.save()


    def test_should_not_cache_page_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(Page)
        try:
            cache_items, cache_size, _ = self.cms.publish(True)
            self.assertEqual(0, cache_items)
            self.assertEqual(0, cache_size)
        finally:
            self.restore_filter_visibility(Page, _filter_visibility)


    def test_should_not_cache_disabled_child_pages(self):
        self.page.entity_type = 'BlogPost'
        self.page.save()
        self.child_page.disabled = True
        self.child_page.save()

        cache_items, cache_size, _ = self.cms.publish(True)
        self.assertEqual(1, cache_items)
        self.assertTrue(cache_size > 0)


    def _create_test_page(self, title, updated_on, entity_type=None):
        freezer = freeze_time(updated_on)
        freezer.start()
        result = self.create_page(title, entity_type=entity_type)
        freezer.stop()
        return result


    def _create_test_model(self, title, updated_on):
        freezer = freeze_time(updated_on)
        freezer.start()
        m = TestModel(title=title)
        m.save()
        freezer.stop()
        return m


    def _create_test_child_page(self, number, page, updated_on):
        freezer = freeze_time(updated_on)
        freezer.start()
        child = self.create_child_page(number, page)
        freezer.stop()
        return child