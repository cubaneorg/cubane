# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.client import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.cms.views import get_cms
from cubane.directory import DirectoryOrder
from cubane.testapp.models import TestContentAggregator
from cubane.testapp.models import TestDirectoryContent


class TestDirectoryPageContextExtensions(CubaneTestCase):
    def test_should_inject_aggregated_pages(self):
        cms = get_cms()
        factory = RequestFactory()
        request = factory.get('/')
        page = TestContentAggregator.objects.create(
            title='Cromer',
            slug='cromer',
            tags=['cromer'],
            include_tags_1=['cromer'],
            order_mode=DirectoryOrder.ORDER_TITLE
        )
        a = TestDirectoryContent.objects.create(title='Hotel A', tags=['cromer'])
        b = TestDirectoryContent.objects.create(title='Hotel B', tags=['cromer'])
        try:
            c = cms.get_template_context(request, page=page)
            self.assertEqual([a, b], c.get('aggregated_pages'))
        finally:
            b.delete()
            a.delete()
            page.delete()