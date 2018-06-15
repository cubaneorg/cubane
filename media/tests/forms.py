# coding=UTF-8
from __future__ import unicode_literals
from django.test import RequestFactory
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.media.models import MediaFolder
from cubane.media.forms import *


class MediaFormsBrowseMediaFolderFieldTestCase(CubaneTestCase):
    def test_browse_media_folder_field(self):
        field = BrowseMediaFolderField()
        self.assertEqual(MediaFolder, field.queryset.model)
        self.assertEqual(MediaFolder._meta.verbose_name_plural, field.name)


class MediaFormsMediaFolderFormTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(MediaFormsMediaFolderFormTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.post('/')
        cls.parent = MediaFolder.objects.create(title='Parent')
        cls.child = MediaFolder.objects.create(title='Child', parent=cls.parent)


    @classmethod
    def tearDownClass(cls):
        cls.child.delete()
        cls.parent.delete()
        super(MediaFormsMediaFolderFormTestCase, cls).tearDownClass()


    def test_should_validate_with_empty_parent(self):
        form = MediaFolderForm({'title': 'Foo', 'parent': None})
        self.assertTrue(form.is_valid())


    def test_should_fail_if_parent_is_the_node(self):
        form = MediaFolderForm({'title': 'Foo', 'parent': self.parent.pk})
        form.configure(self.request, self.parent, edit=True)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'parent', MediaFolderForm.ERROR_ITSELF_AS_PARENT)


    def test_should_fail_if_parent_is_child_of_the_node(self):
        form = MediaFolderForm({'title': 'Foo', 'parent': self.child.pk})
        form.configure(self.request, self.parent, edit=True)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'parent', MediaFolderForm.ERROR_PARENT_AS_CHILD)


class MediaFormsMediaFormTestCase(CubaneTestCase):
    @override_settings(IMAGE_CREDITS=True)
    def test_should_contain_media_credit_field_if_turned_on(self):
        form = self._create_form()
        self.assertIsNotNone(form.fields.get('credits'))


    @override_settings(IMAGE_CREDITS=False)
    def test_should_not_contain_media_credit_field_if_turned_off(self):
        form = self._create_form()
        self.assertIsNone(form.fields.get('credits'))


    @override_settings(IMAGE_EXTRA_TITLE=True)
    def test_should_contain_extra_title_field_if_turned_on(self):
        form = self._create_form()
        self.assertIsNotNone(form.fields.get('extra_image_title'))


    @override_settings(IMAGE_EXTRA_TITLE=False)
    def test_should_not_contain_extra_title_field_if_turned_off(self):
        form = self._create_form()
        self.assertIsNone(form.fields.get('extra_image_title'))


    def test_should_validate_media_formats_for_images(self):
        form = self._create_form(is_image=True)
        self.assertEqual(MediaForm.IMAGE_EXT, form.fields['media'].ext)


    def test_should_validate_document_formats_for_documents(self):
        form = self._create_form(is_image=False)
        self.assertEqual(MediaForm.DOCUMENT_EXT, form.fields['media'].ext)


    def test_should_require_file_upload_field_when_creating_new_instance(self):
        form = self._create_form(edit=False)
        self.assertTrue(form.fields['media'].required)


    def test_should_not_require_file_upload_field_when_editing_exiting_instance(self):
        form = self._create_form(edit=True)
        self.assertFalse(form.fields['media'].required)


    def _create_form(self, edit=False, is_image=True):
        form = MediaForm()
        factory = RequestFactory()
        request = factory.get('/')
        request.is_image = is_image

        form.configure(request, Media(), edit)
        return form


class MediaFormsMultiMediaFormTestCase(CubaneTestCase):
    def test_should_validate_media_formats_for_images(self):
        form = self._create_form(is_image=True)
        self.assertEqual(MediaForm.IMAGE_EXT, form.fields['media'].ext)


    def test_should_validate_document_formats_for_documents(self):
        form = self._create_form(is_image=False)
        self.assertEqual(MediaForm.DOCUMENT_EXT, form.fields['media'].ext)


    def _create_form(self, is_image=True):
        form = MultiMediaForm()
        factory = RequestFactory()
        request = factory.get('/')
        request.is_image = is_image

        form.configure(request)
        return form


class MediaFormsBrowseMediaFieldTestCase(CubaneTestCase):
    def test_browse_images(self):
        field = BrowseMediaField(images=True)
        self.assertEqual(Media, field.queryset.model)
        self.assertEqual('Images', field.name)


    def test_browse_documents(self):
        field = BrowseMediaField(images=False)
        self.assertEqual(Media, field.queryset.model)
        self.assertEqual('Documents', field.name)


class MediaFormsBrowseImageFieldTestCase(CubaneTestCase):
    def test_browse_images(self):
        self.assertEqual('Images', BrowseImagesSelectField().name)


class MediaFormsBrowseDocumentsFieldTestCase(CubaneTestCase):
    def test_browse_documents(self):
        self.assertEqual('Documents', BrowseDocumentsField().name)