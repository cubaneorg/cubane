# coding=UTF-8
from __future__ import unicode_literals
from django.test.utils import override_settings
from django.test.client import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.cms.views import get_cms
from cubane.directory import DirectoryOrder
from cubane.directory.nav import DirectoryNavigationExtensions
from cubane.testapp.models import CustomDirectoryPage, TestDirectoryContent


class TestDirectoryNavInitTestCase(CubaneTestCase):
    def test_should_have_empty_aggregation_cahce(self):
        nav = DirectoryNavigationExtensions()
        self.assertEqual({}, nav.agg_cache)


@override_settings(CMS_PAGE_MODEL = 'cubane.testapp.models.CustomDirectoryPage')
class TestDirectoryNavGetNavItemTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDirectoryNavGetNavItemTestCase, cls).setUpClass()
        cls.page = CustomDirectoryPage(title='Cromer', nav_include_tags=['cromer'], nav_order_mode=DirectoryOrder.ORDER_TITLE, _nav='header')
        cls.a = TestDirectoryContent(title='Hotel A', tags=['cromer', 'hotel'])
        cls.b = TestDirectoryContent(title='Hotel B', tags=['cromer', 'hotel'])
        cls.page.save()
        cls.a.save()
        cls.b.save()
        cls.factory = RequestFactory()


    @classmethod
    def tearDownClass(cls):
        cls.b.delete()
        cls.a.delete()
        cls.page.delete()
        super(TestDirectoryNavGetNavItemTestCase, cls).tearDownClass()


    def test_should_inject_aggregated_content_for_nav_item(self):
        cms = get_cms()
        context = cms.get_page_context(self.factory.get('/cromer/'), page=self.page, view=cms)
        nav_item = context.get_template_context().get('nav').get('header')[0]
        items = [item.get('page_title') for item in nav_item.get('aggregated_pages')()]
        self.assertEqual(['Hotel A', 'Hotel B'], items)


    def test_should_not_inject_disabled_content_for_nav_item(self):
        try:
            self.a.disabled = True
            self.a.save()

            cms = get_cms()
            context = cms.get_page_context(self.factory.get('/cromer/'), page=self.page, view=cms)
            nav_item = context.get_template_context().get('nav').get('header')[0]
            items = [item.get('page_title') for item in nav_item.get('aggregated_pages')()]
            self.assertEqual(['Hotel B'], items)
        finally:
            self.a.disabled = False
            self.a.save()


    def test_should_not_inject_content_for_nav_item_with_custom_visibility_checks(self):
        _filter_visibility = self.patch_filter_visibility(TestDirectoryContent)
        try:
            cms = get_cms()
            context = cms.get_page_context(self.factory.get('/cromer/'), page=self.page, view=cms)
            nav_item = context.get_template_context().get('nav').get('header')[0]
            items = [item.get('page_title') for item in nav_item.get('aggregated_pages')()]
            self.assertEqual([], items)
        finally:
            self.restore_filter_visibility(TestDirectoryContent, _filter_visibility)