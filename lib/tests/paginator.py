# coding=UTF-8
from __future__ import unicode_literals
from django.http import HttpRequest
from django.http import Http404
from django.test import RequestFactory
from django.http.request import QueryDict
from cubane.tests.base import CubaneTestCase
from cubane.lib.paginator import VIEW_ALL_LABEL
from cubane.lib.paginator import create_paginator
from cubane.testapp.models import TestModel


class CubanepaginatorCreateTestCase(CubaneTestCase):
    """
    cubane.lib.paginator.create_paginator
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

        for i in range(1, 10):
            obj = TestModel()
            obj.title = '%d' % i
            obj.save()


    def tearDown(self):
        [obj.delete() for obj in TestModel.objects.all()]


    def test_should_create_default_paginator_for_page_1(self):
        p = create_paginator(self.request, TestModel.objects.all().order_by('title'), page=1, page_size=5)

        self.assertEqual(p.count(), 5)
        self.assertEqual(p.number, 1)
        self.assertEqual(p.paginator.num_pages, 2)
        self.assertFalse(p.paginator.view_all)
        self.assertEqual(p.paginator.view_all_label, VIEW_ALL_LABEL)
        self.assertEqual(p.pages, [{u'page': 1, u'url': u'/'}, {u'page': 2, u'url': u'/page-2/'}])
        self.assertEqual(p.prev_url, None)
        self.assertEqual(p.next_url, '/page-2/')


    def test_should_create_paginator_for_page_2(self):
        p = create_paginator(self.request, TestModel.objects.all().order_by('title'), page=2, page_size=5)

        self.assertEqual(p.count(), 4)
        self.assertEqual(p.number, 2)
        self.assertEqual(p.paginator.num_pages, 2)
        self.assertFalse(p.paginator.view_all)
        self.assertEqual(p.paginator.view_all_label, VIEW_ALL_LABEL)
        self.assertEqual(p.pages, [{u'page': 1, u'url': u'/'}, {u'page': 2, u'url': u'/page-2/'}])
        self.assertEqual(p.prev_url, '/')
        self.assertEqual(p.next_url, None)


    def test_should_create_paginator_for_all(self):
        self.request = self.factory.get('/', {'all': '1'})
        p = create_paginator(self.request, TestModel.objects.all().order_by('title'), page=1, page_size=5)

        self.assertEqual(p.count(), 9)
        self.assertEqual(p.number, 1)
        self.assertEqual(p.paginator.num_pages, 1)
        self.assertTrue(p.paginator.view_all)
        self.assertEqual(p.paginator.view_all_label, 'View 10')
        self.assertEqual(p.pages, [{'page': 1, 'url': '/all-page-1/'}])
        self.assertEqual(p.prev_url, None)
        self.assertEqual(p.next_url, None)


    def test_should_create_paginator_with_max_page_size_lower_than_total(self):
        p = create_paginator(self.request, TestModel.objects.all().order_by('title'), page=1, page_size=5, min_page_size=5, max_page_size=8)

        self.assertEqual(p.count(), 5)
        self.assertEqual(p.number, 1)
        self.assertEqual(p.paginator.num_pages, 2)
        self.assertFalse(p.paginator.view_all)
        self.assertEqual(p.paginator.view_all_label, 'View 8')
        self.assertEqual(p.pages, [{u'page': 1, u'url': u'/'}, {u'page': 2, u'url': u'/page-2/'}])
        self.assertEqual(p.prev_url, None)
        self.assertEqual(p.next_url, '/page-2/')


    def test_should_create_paginator_for_specific_page(self):
        self.request = self.factory.get('/', {'page': '2'})
        p = create_paginator(self.request, TestModel.objects.all().order_by('title'), page_size=5)

        self.assertEqual(p.count(), 4)
        self.assertEqual(p.number, 2)
        self.assertEqual(p.paginator.num_pages, 2)
        self.assertFalse(p.paginator.view_all)


    def test_should_obtain_base_path_from_request_for_specific_page(self):
        self.request = self.factory.get('/test/page-2/', {'foo': 'bar'})
        p = create_paginator(self.request, TestModel.objects.all().order_by('title'), page_size=5)
        self.assertEqual(p.count(), 4)
        self.assertEqual(p.number, 2)
        self.assertEqual(p.paginator.num_pages, 2)
        self.assertFalse(p.paginator.view_all)
        self.assertEqual(p.prev_url, '/test/?foo=bar')
        self.assertEqual(p.next_url, None)


    def test_should_obtain_base_path_from_request_for_all_pages(self):
        self.request = self.factory.get('/test/all-page-1/', {'page': '1', 'all': '1'})
        p = create_paginator(self.request, TestModel.objects.all().order_by('title'), page_size=5)
        self.assertEqual(p.count(), 9)
        self.assertEqual(p.number, 1)
        self.assertEqual(p.paginator.num_pages, 1)
        self.assertTrue(p.paginator.view_all)
        self.assertEqual(p.prev_url, None)
        self.assertEqual(p.next_url, None)


    def test_invalid_page_number_request(self):
        self.request = self.factory.get('/', {'page': 'NotANumber'})
        with self.assertRaises(Http404):
            create_paginator(self.request, TestModel.objects.all().order_by('title'), page_size=5)


    def test_invalid_page_number(self):
        with self.assertRaises(Http404):
            create_paginator(self.request, TestModel.objects.all().order_by('title'), page=10, page_size=5)