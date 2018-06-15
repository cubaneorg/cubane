# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.template.defaultfilters import slugify
from django.db.models.query import QuerySet
from django.db.models.fields import FieldDoesNotExist
from cubane.testapp.models import TestGroupedModelA, TestDirectoryContent, TestDirectoryCategory
from cubane.tests.base import CubaneTestCase
from cubane.cms.tests.base import CMSTestBase
from cubane.cms.views import get_cms
from cubane.cms.models import Page, MediaGallery
from cubane.media.models import Media
from cubane.directory.models import DirectoryTag
from cubane.blog.models import BlogPost
from cubane.testapp.models import TestModel, Settings
from mock import Mock
import mock


@CubaneTestCase.complex()
class CMSScriptingTestCase(CMSTestBase):
    def testDown(self):
        cms = get_cms()
        cms.delete_content()


    def test_delete_content_should_delete_all_content(self):
        cms = get_cms()
        cms.delete_content()
        models = [Page, Media, BlogPost, TestGroupedModelA, DirectoryTag, TestDirectoryContent, TestDirectoryCategory]
        for model in models:
            m = model()
            m.save()

        cms.delete_content()
        for model in models:
            self.assertEqual(model.objects.all().count(), 0)


    def test_create_object_should_return_instance(self):
        cms = get_cms()
        self.assertEqual(Page.objects.all().count(), 0)
        cms.create_object('Page', {'title': 'Page 1', 'slug': 'page-1'})
        self.assertEqual(Page.objects.all().count(), 1)


    def test_create_object_should_raises_error_for_unknown_model(self):
        cms = get_cms()
        with self.assertRaisesRegexp(ValueError, 'Unknown model name'):
            cms.create_object('FakeModel', {'title': 'Page 1', 'slug': 'page-1'})


    def test_create_object_should_raises_error_for_missing_slug(self):
        cms = get_cms()
        with self.assertRaisesRegexp(ValueError, 'slug: This field is required'):
            cms.create_object('Page', {'title': 'Page 1'})


    def test_create_object_should_raise_error_for_missing_get_form_method(self):
        cms = get_cms()
        with self.assertRaisesRegexp(ValueError, 'Unable to call \'get_form\' class method on model'):
            cms.create_object('TestGroupedModelA', {})


    @mock.patch('cubane.cms.models.Page.get_form')
    def test_create_object_should_raise_error_when_unable_to_create_form_instance(self, get_form):
        get_form.return_value = 'not a form'

        cms = get_cms()
        with self.assertRaisesRegexp(ValueError, 'Unable to create a new instance of the model form'):
            cms.create_object('Page', {'title': 'Page', 'slug': 'page'})


    @mock.patch('cubane.cms.models.Page.get_form')
    def test_create_object_should_raise_error_if_configure_method_has_not_been_implemented_on_form(self, get_form):
        class Form(object):
            def __init__(self, *args, **kwargs):
                pass
        get_form.return_value = Form

        cms = get_cms()
        with self.assertRaisesRegexp(NotImplementedError, 'must implement configure'):
            cms.create_object('Page', {'title': 'Page', 'slug': 'page'})


    def test_create_object_should_ignore_missing_seq_field(self):
        cms = get_cms()
        def _get_seq_model_field(cms):
            raise FieldDoesNotExist()
        cms.get_seq_model_field = _get_seq_model_field
        cms.create_object('Page', {'title': 'Page', 'slug': 'page'})


    def test_create_media_from_file_should_read_image_from_disk(self):
        cms = get_cms()
        filename = self.get_test_image_path('test.jpg')
        media = cms.create_media_from_file(filename, 'Test', 'testimage.jpg')
        self.assertIsNotNone(media.pk)
        self.assertEqual('Test', media.caption)
        self.assertEqual('test.jpg', media.filename)
        self.assertEqual([512, 512], [media.width, media.height])


    def test_create_media_from_url_should_download_file_from_url(self):
        cms = get_cms()
        filename = self.get_test_image_path('test.jpg')
        media = cms.create_media_from_url('http://sipi.usc.edu/database/preview/textures/1.1.01.png', 'Test', 'test.jpg')
        self.assertEqual('Test', media.caption)
        self.assertEqual('test.jpg', media.filename)
        self.assertEqual([200, 200], [media.width, media.height])


    def test_add_media_to_gallery_should_create_media_gallery(self):
        cms = get_cms()
        p = self.create_page('Page')
        m = Media()
        m.save()
        self.assertEqual(len(MediaGallery.objects.filter(target_id=p.pk)), 0)
        cms.add_media_to_gallery(p, m)
        self.assertEqual(len(MediaGallery.objects.filter(target_id=p.pk)), 1)