# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.client import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.directory.models import DirectoryTag
from cubane.directory.forms import DirectoryTagForm
from cubane.testapp.forms import TestDirectoryContentForm
from cubane.testapp.forms import TestDirectoryPageAggregatorForm
from cubane.testapp.forms import TestDirectoryContentAggregatorChildPageForm
from cubane.testapp.forms import TestDirectoryContentAndAggregatorForm
from cubane.testapp.forms import TestDirectoryContentEntityForm
from cubane.testapp.forms import TestDirectoryCategoryForm
from cubane.testapp.models import TestDirectoryContent


class DirectoryTagFormTestCase(CubaneTestCase):
    def test_should_succeed_for_valid_tag_title(self):
        form = DirectoryTagForm({
            'title': 'foo'
        })
        self.assertTrue(form.is_valid())


    def test_should_lowercase_tag_title(self):
        form = DirectoryTagForm({
            'title': 'FOO'
        })
        self.assertTrue(form.is_valid())
        self.assertEqual('foo', form.cleaned_data.get('title'))


    def test_should_fail_for_tag_title_with_incorrect_characters(self):
        form = DirectoryTagForm({
            'title': '!@£$%^&'
        })
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'title', 'The tag name contains invalid characters')


class DirectoryContentConfigureTagsAsChoicesTestCase(CubaneTestCase):
    CHOICES = [
        ('bar', 'bar'),
        ('foo', 'foo')
    ]

    TAG_FIELDS = [
        'tags',
        'ptags'
    ]

    INCLUDE_TAG_FIELDS = [
        'include_tags_1',
        'include_tags_2',
        'include_tags_3',
        'include_tags_4',
        'include_tags_5',
        'include_tags_6',
        'exclude_tags'
    ]

    NAV_TAG_FIELDS = [
        'nav_include_tags',
        'nav_exclude_tags'
    ]


    @classmethod
    def setUpClass(cls):
        super(DirectoryContentConfigureTagsAsChoicesTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.post('/')
        cls.foo = DirectoryTag.objects.create(title='foo')
        cls.bar = DirectoryTag.objects.create(title='bar')


    @classmethod
    def tearDownClass(cls):
        cls.foo.delete()
        cls.bar.delete()
        super(DirectoryContentConfigureTagsAsChoicesTestCase, cls).tearDownClass()


    def test_directory_content_base_form_configure_should_load_tags_as_choices(self):
        self._assert_choices(
            TestDirectoryContentForm(),
            self.TAG_FIELDS
        )


    def test_directory_content_entity_form(self):
        self._assert_choices(
            TestDirectoryContentEntityForm(),
            self.TAG_FIELDS
        )


    def test_directory_content_aggregator_page_form_configure_should_load_tags_as_choices(self):
        self._assert_choices(
            TestDirectoryPageAggregatorForm(),
            self.INCLUDE_TAG_FIELDS + self.NAV_TAG_FIELDS
        )


    def test_directory_content_aggregator_child_page_form_configure_should_load_tags_as_choices(self):
        self._assert_choices(
            TestDirectoryContentAggregatorChildPageForm(),
            self.INCLUDE_TAG_FIELDS
        )


    def test_directory_content_and_aggregator_form_configure_should_load_tags_as_choices(self):
        self._assert_choices(
            TestDirectoryContentAndAggregatorForm(),
            self.INCLUDE_TAG_FIELDS
        )


    def test_directory_category_form_configure_should_load_tags_as_choices(self):
        self._assert_choices(
            TestDirectoryCategoryForm(),
            self.INCLUDE_TAG_FIELDS
        )


    def _assert_choices(self, form, fieldnames):
        form.configure(self.request, None, False)
        for fieldname in fieldnames:
            self.assertEqual(self.CHOICES, form.fields.get(fieldname).choices)


class DirectoryContentBaseFormTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(DirectoryContentBaseFormTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.post('/')
        cls.content = TestDirectoryContent.objects.create(title='Foo', slug='foo')


    @classmethod
    def tearDownClass(cls):
        cls.content.delete()
        super(DirectoryContentBaseFormTestCase, cls).tearDownClass()


    def test_should_succeed_for_content_that_does_not_exist_yet(self):
        form = TestDirectoryContentForm({'slug': 'new', 'title': 'New', 'template': 'testapp/page.html'})
        form.configure(self.request, TestDirectoryContent(), False)
        self.assertTrue(form.is_valid())


    def test_should_succeed_for_changing_existing_content(self):
        form = TestDirectoryContentForm({'slug': 'foo', 'title': 'Foo', 'template': 'testapp/page.html', '_cubane_instance_checksum': self.content.get_checksum()})
        form.configure(self.request, self.content, True)
        self.assertTrue(form.is_valid())


    def test_should_fail_for_content_that_already_exists(self):
        form = TestDirectoryContentForm({'slug': 'foo', 'title': 'Foo', 'template': 'testapp/page.html'})
        form.configure(self.request, TestDirectoryContent(), False)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'slug', 'There is already a slug with this name')