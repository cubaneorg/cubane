# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db.models.query import QuerySet
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.template.defaultfilters import slugify
from cubane.tests.base import CubaneTestCase
from cubane.cms.views import fake_request
from cubane.testapp.models import CustomPage
from cubane.backend.api import *


class BackendApiViewTestCase(CubaneTestCase):
    def test_cms_api_view_links_returns_dict(self):
        view = BackendApiView()
        request = self._get_request()
        links = view.links(request)
        self.assertIsInstance(links, dict)
        self.assertIsInstance(links.get('items'), list)


    def test_cms_api_view_images_returns_queryset(self):
        view = BackendApiView()
        request = self._get_request()
        images = view.images(request)
        self.assertIsInstance(images, QuerySet)


    @override_settings()
    def test_cms_api_view_links_gets_custom_pages(self):
        settings.CMS_PAGE_MODEL = 'cubane.testapp.models.CustomPage'
        page = self.create_page('Page')
        view = BackendApiView()
        request = self._get_request()
        links = view.links(request)
        pages = filter(lambda x: x.get('type') == 'CustomPage', links.get('items'))[0]
        self.assertEqual(pages.get('title'), 'Custom Pages')
        self.assertEqual(len(pages.get('links')), 1)


    @override_settings()
    def test_cms_api_view_links_should_not_return_pages_if_cms_is_not_installed(self):
        settings.INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if app != 'cubane.cms']
        page = self.create_page('Page')
        view = BackendApiView()
        request = self._get_request()
        links = view.links(request)
        pages = filter(lambda x: x.get('type') == 'CustomPage', links.get('items'))
        self.assertEqual(0, len(pages))


    @override_settings()
    def test_cms_api_view_links_should_not_return_media_if_app_is_not_installed(self):
        settings.INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if app != 'cubane.media']
        view = BackendApiView()
        request = self._get_request()
        links = view.links(request)
        pages = filter(lambda x: x.get('type') == 'Media', links.get('items'))
        self.assertEqual(0, len(pages))


    @override_settings()
    def test_cms_api_view_images_returns_empty_list(self):
        settings.INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if app != 'cubane.media']
        view = BackendApiView()
        request = self._get_request()
        images = view.images(request)
        self.assertIsInstance(images, list)


    def create_page(self, title, template='testapp/page.html', nav='header', entity_type=None, seq=0, legacy_url=None, identifier=None, parent=None):
        p = CustomPage(
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


    def _get_request(self):
        request = fake_request(path='/')
        request.user = User(is_staff=True, is_superuser=True)
        return request