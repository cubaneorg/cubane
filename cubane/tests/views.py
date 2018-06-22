# coding=UTF-8
from __future__ import unicode_literals
from django.http import HttpResponse, QueryDict
from django import forms
from django.db import models
from django.template import engines
from django.contrib.sessions.backends.cache import SessionStore
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db.models.fields import FieldDoesNotExist
from django.test.client import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.decorators import identity
from cubane.views import *
from cubane.models import Country
from cubane.cms.models import Page
from cubane.cms.views import get_cms, PageContentView, ContentView, SettingsView
from cubane.media.views import FolderView, MediaView, ImageView
from cubane.ishop.apps.merchant.products.views import ProductView
from cubane.blog.models import BlogPost
from cubane.backend.models import ChangeLog
from cubane.testapp.models import (
    Settings,
    CustomPage,
    TestModel,
    TestModelFilterByCountry,
    TestTagsField,
    TestModelWithManyToMany,
    TestDirectoryContentWithBackendSections,
    Enquiry,
    TestModelImportExport,
    Category
)
from cubane.testapp.forms import CustomPageForm
from cubane.media.models import Media, MediaFolder
from cubane.lib.libjson import decode_json
from inspect import isfunction
from mock.mock import Mock, patch, PropertyMock
from undecorated import undecorated
from freezegun import freeze_time
from datetime import datetime
import os
import json
import tempfile


PAGE_PATTERN = '^(?P<slug>.*)$'


class DummyModel(object):
    @property
    def __name__(self):
        return 'DummyModel'


class DummyListing(object):
    pass


class DummyRequest(object):
    view_instance = 'view_instance'


class CustomPageView(ModelView):
    model = CustomPage


    def _get_objects(self, request):
        return self.model.objects.all()


class EnquiryView(ModelView):
    model = Enquiry


    def _get_objects(self, request):
        return self.model.objects.all()


class LibViewUrlTestCase(CubaneTestCase):
    """
    cubane.views.view_url()
    """
    def test_should_return_encapsulated_url_pattern(self):
        self.assertEqual(('regex', 'view', 'kwargs', 'name'), view_url('regex', 'view', 'kwargs', 'name'))


class LibGetColumnsTestCase(CubaneTestCase):
    """
    cubane.views.get_columns()
    """
    def test_should_return_list_of_columns(self):
        my_columns = get_columns(['arg1', 'arg2'], ['arg3', 'arg4'])
        self.assertEqual([{'fieldname': 'arg2', 'title': 'arg1'}, {'fieldname': 'arg4', 'title': 'arg3'}], my_columns)


    def test_should_retun_empty_list(self):
        my_columns = get_columns()
        self.assertEqual([], my_columns)


class LibViewTestCase(CubaneTestCase):
    """
    cubane.views.view()
    """
    def test_should_return_method_decorator(self):
        self.assertEqual('method_decorator(identity)', view(identity).__name__)


    def test_should_return_identity(self):
        self.assertEqual('identity', view().__name__)


class LibViewGetURLsTestCase(CubaneTestCase):
    """
    cubane.views.View.get_urls()
    """
    def setUp(self):
        self.view = View()
        self.view.patterns = [
            ('edit', 'edit',  {}, 'dummy.edit'),
            ('',     'index', {}, 'dummy.index'),
        ]

    def test_should_return_urls(self):
        self.assertEqual(2, len(self.view.get_urls()))


    def test_should_return_empty_list_if_patterns_empty(self):
        self.view.patterns = []
        self.assertEqual([], self.view.get_urls())


    def test_should_include_prefix(self):
        for url in self.view.get_urls('test'):
            self.assertTrue(url.regex.pattern.startswith('test/'))


    def test_should_get_all_urls(self):
        self.assertEqual(2, len(self.view.urls))


class LibViewGetURLTestCase(CubaneTestCase):
    """
    cubane.views.View.get_url()
    """
    def test_empty_patterns_should_return_empty_string(self):
        view = View()
        self.assertEqual(view.get_url(), '')


    def test_should_return_index_url(self):
        view = View()
        view.patterns = [
            ('edit', 'edit',  {}, 'dummy.edit'),
            ('', 'index', {}, 'dummy.index'),
        ]

        self.assertEqual('/dummy/index/', view.get_url())


    def test_should_return_first_available_url(self):
        view = View()
        view.patterns = [
            ('edit',    'edit',    {}, 'dummy.edit'),
            ('create',  'create',  {}, 'dummy.create'),
            ('preview', 'preview', {}, 'dummy.preview'),
        ]

        self.assertEqual('/dummy/edit/', view.get_url())


    def test_should_get_url(self):
        view = View()

        view.patterns = [
            ('edit',    'edit',    {}, 'dummy.edit'),
            ('create',  'create',  {}, 'dummy.create'),
            ('preview', 'preview', {}, 'dummy.preview'),
        ]

        self.assertEqual('/dummy/edit/', view.url)


class LibViewGetURLPatternsTestCase(CubaneTestCase):
    """
    cubane.views.View._get_urlpatterns()
    """
    def test_should_return_empty_list(self):
        view = View()
        self.assertEqual([], view._get_urlpatterns([]))


    def test_should_add_prefix(self):
        view = View()

        patterns = [
            ('edit', 'edit',  {}, 'dummy.edit'),
            ('', 'index', {}, 'dummy.index'),
        ]

        for url in view._get_urlpatterns(patterns, 'test'):
            self.assertTrue(url.regex.pattern.startswith('test/'))


    def test_should_add_prefix_with_caret(self):
        view = View()

        patterns = [
            ('^edit', 'edit',  {}, 'dummy.edit'),
            ('^create', 'index', {}, 'dummy.index'),
        ]

        for url in view._get_urlpatterns(patterns, 'test'):
            self.assertTrue(url.regex.pattern.startswith('^test/'))


    def test_should_add_namespace(self):
        view = View()
        view.namespace = 'my_namespace'

        patterns = [
            ('edit', 'edit',  {}, 'dummy.edit'),
            ('', 'index', {}, 'dummy.index'),
        ]

        for url in view._get_urlpatterns(patterns):
            self.assertTrue(url.name.startswith('my_namespace'))


class LibViewRunHanlderTestCase(CubaneTestCase):
    """
    cubane.views.View.run_handler()
    """
    def handler(self, request, *args, **kwargs):
        return 'response'


    def test_should_return_response(self):
        view = View()
        view.handler = self.handler

        request = Mock()

        self.assertEqual('response', view.run_handler(request, 'handler'))


class LibViewCreateViewHandlerTestCase(CubaneTestCase):
    """
    cubane.views.View._create_view_handler()
    """
    def handler(self, request, *args, **kwargs):
        return 'handler'


    def test_should_raise_not_implemented_exception(self):
        view = View()

        view_handler = view._create_view_handler('not_implemented')
        self.assertRaises(Http404, view_handler, DummyRequest())


    def test_should_dispatch_view(self):
        view = View()

        view.view_handler = self.handler
        view_handler = view._create_view_handler('view_handler')

        self.assertEqual('handler', view_handler(DummyRequest()))


    def test_should_return_function(self):
        view = View()

        view.view_handler = self.handler
        view_handler = view._create_view_handler('view_handler')

        self.assertTrue(isfunction(view_handler))


class LibViewDispatchTestCase(CubaneTestCase):
    """
    cubane.views.View._dispatch()
    """
    def handler(self, request, *args, **kwargs):
        return 'handler'


    def before(self, request, handler):
        return 'before'


    def after(self, request, handler, response):
        return 'after'


    def test_should_have_before_method(self):
        self.assertTrue(hasattr(View, 'before'))


    def test_should_have_after_method(self):
        self.assertTrue(hasattr(View, 'after'))


    def test_should_return_before_response(self):
        view = View()

        view.before = self.before

        self.assertEqual('before', view._dispatch(self.handler, 'request'))


    def test_should_return_after_response(self):
        view = View()

        view.after = self.after

        self.assertEqual('after', view._dispatch(self.handler, 'request'))


    def test_should_return_response(self):
        view = View()

        self.assertEqual('handler', view._dispatch(self.handler, 'request'))


class LibApiViewTestCase(CubaneTestCase):
    """
    cubane.views.ApiView.after()
    """
    def test_should_return_response(self):
        view = ApiView()
        self.assertEqual(('Content-Type', 'text/html; charset=utf-8'), view.after('request', 'handler', HttpResponse())._headers['content-type'])


    def test_should_return_json_response(self):
        view = ApiView()
        self.assertEqual(('Content-Type', 'text/javascript'), view.after('request', 'handler', {})._headers['content-type'])


class LibTemplateViewGetTemplatePathTestCase(CubaneTestCase):
    """
    cubane.views.TemplateView._get_template_path()
    """
    def test_should_return_file(self):
        view = TemplateView()

        self.assertEqual('handler.html', view._get_template_path('request', type(str('handler'), (object,), {}), {}))


    def test_should_return_path_with_file(self):
        view = TemplateView()
        view.template_path = 'path/'

        self.assertEqual('path/handler.html', view._get_template_path('request', type(str('handler'), (object,), {}), {}))


class LibTemplateViewAfterTestCase(CubaneTestCase):
    """
    cubane.views.TemplateView.after()
    """
    def test_should_return_response_if_not_template_processs(self):
        view = TemplateView()
        view.process_templates = False

        self.assertEqual('response', view.after('request', 'handler', 'response'))


    def test_should_return_response_if_response_is_httpresponse(self):
        view = TemplateView()

        response = HttpResponse()

        self.assertEqual(response, view.after('request', 'handler', response))


    def test_should_update_response_if_has_attribute_context(self):
        view = TemplateView()
        view.template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'testapp/templates/testapp/'))

        factory = RequestFactory()
        request = factory.get('/')

        view.context = {'content': 'foo'}

        self.assertEqual('foo', view.after(request, type(str('template_view_render'), (object,), {}), {}).content)


class LibModelViewModelNameTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._model_name
    """
    def test_should_return_model_name(self):
        view = ModelView()
        view.model = type(str('Model'), (object,), {})

        self.assertEqual('model', view._model_name)


class LibModelViewIsSingleInstanceTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.is_single_instance
    """
    def test_should_return_true(self):
        view = ModelView()
        view.single_instance = True

        self.assertTrue(view.is_single_instance)


    def test_should_return_false(self):
        view = ModelView()

        self.assertFalse(view.is_single_instance)

        view.single_instance = False

        self.assertFalse(view.is_single_instance)


class LibModelViewIsSingleInstanceTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.model_is_folder
    """
    def test_should_return_false_if_model_and_folder_model_are_different(self):
        view = ModelView()
        view.model = 'foo'
        view.folder_model = 'bar'

        self.assertFalse(view.model_is_folder)


    def test_should_return_true_if_model_and_folder_model_are_same(self):
        view = ModelView()

        view.model = 'foo'
        view.folder_model = 'foo'

        self.assertTrue(view.model_is_folder)


class LibModelViewListingWithImageTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.listing_with_image
    """
    def test_should_return_false(self):
        view = ModelView()

        self.assertFalse(view.listing_with_image)


class LibModelViewGetURLForModelTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_url_for_model()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel
        self.view.patterns = [
            ('^',       'index',    {}, 'dummymodel.index'),
            ('^edit',    'edit',    {}, 'dummymodel.edit'),
        ]


    def test_should_return_none_if_not_found(self):
        self.assertEqual(None, self.view.get_url_for_model('test_model_2'))


    @patch('cubane.views.reverse')
    def test_should_return_reverse_to_index(self, mock_function):
        mock_function.return_value = '/admin/test-models/'
        self.assertEqual('/admin/test-models/', self.view.get_url_for_model(self.view.model))


    @patch('cubane.views.reverse')
    def test_should_return_reverse_to_different_view(self, mock_function):
        mock_function.return_value = '/admin/test-models/edit/'
        self.assertEqual('/admin/test-models/edit/', self.view.get_url_for_model(self.view.model, 'edit'))


class LibModelViewGetUrlForModelInstanceTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_url_for_model_instance()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel
        self.view.patterns = [
            ('^',       'index',    {}, 'dummymodel.index'),
            ('^edit',    'edit',    {}, 'dummymodel.edit'),
        ]


    def test_should_return_none_if_not_found(self):
        self.assertIsNone(self.view.get_url_for_model_instance('test_model_instance'))


    def test_should_return_none_if_backend_section_does_not_match(self):
        self.view.model_attr = 'model_attr'
        self.view.model_attr_value = 'model_attr_value'
        self.assertIsNone(self.view.get_url_for_model_instance(self.view.model()))


    @patch('cubane.views.reverse')
    def test_should_return_reverse_to_index(self, mock_function):
        mock_function.return_value = '/admin/test-models/'
        self.assertEqual('/admin/test-models/', self.view.get_url_for_model_instance(self.view.model()))


    @patch('cubane.views.reverse')
    def test_should_return_reverse_to_different_view(self, mock_function):
        mock_function.return_value = '/admin/test-models/edit/'
        self.assertEqual('/admin/test-models/edit/', self.view.get_url_for_model_instance(self.view.model(), 'edit'))


class LibModelViewGetExcludeColumnsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_exclude_columns()
    """
    def test_should_return_exclude_columns_property_if_defined(self):
        view = ModelView()
        view.exclude_columns = ['foo', 'bar']
        self.assertEqual(['foo', 'bar'], view._get_exclude_columns())


    def test_should_return_empty_list_if_property_does_not_exist(self):
        view = ModelView()
        self.assertEqual([], view._get_exclude_columns())


class LibModelViewGetModelColumnsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_model_columns()
    """
    def setUp(self):
        self.view = ModelView()

    def test_should_return_list_of_default_columns_if_model_listing_columns_is_undefined(self):
        fieldnames = [f.get('fieldname') for f in self.view._get_model_columns(TestModel)]
        self.assertEqual(
            ['id', 'title', 'text', 'image'],
            fieldnames
        )


    def test_should_return_empty_list_of_columns_if_model_listing_columns_is_empty(self):
        TestModel.Listing.columns = []
        try:
            self.assertEqual([], self.view._get_model_columns(TestModel))
        finally:
            delattr(TestModel.Listing, 'columns')


    def test_should_exclude_none_editable_fields(self):
        fieldnames = [f.get('fieldname') for f in self.view._get_model_columns(TestModel)]
        self.assertNotIn('created_on', fieldnames)


    def test_should_exclude_fields_excluded_by_view(self):
        self.view.exclude_columns = ['title']
        fieldnames = [f.get('fieldname') for f in self.view._get_model_columns(TestModel)]
        self.assertEqual(['id', 'text', 'image'], fieldnames)


    def test_should_allow_override_title(self):
        columns = CustomPage.Listing.columns
        CustomPage.Listing.columns = ['title|Title']
        try:
            _columns = self.view._get_model_columns(CustomPage)
            self.assertEqual('title', _columns[0]['fieldname'])
            self.assertEqual('Title', _columns[0]['title'])
        finally:
            CustomPage.Listing.columns = columns


    def test_should_return_columns_with_url_and_boolean_true(self):
        columns = CustomPage.Listing.columns
        CustomPage.Listing.columns = ['disabled|Disabled|bool', 'url|Url|url']
        try:
            _columns = self.view._get_model_columns(CustomPage)
            self.assertTrue(_columns[0]['bool'])
            self.assertTrue(_columns[1]['url'])
        finally:
            CustomPage.Listing.columns = columns


    def test_should_ignore_fields_that_do_not_exist_in_model(self):
        TestModel.Listing.columns = ['does_not_exist']
        try:
            self.assertEqual(0, len(self.view._get_model_columns(TestModel)))
        finally:
            delattr(TestModel.Listing, 'columns')


    def test_should_use_field_verbose_name_if_title_is_not_presented(self):
        TestModel.Listing.columns = ['title']
        try:
            columns = self.view._get_model_columns(TestModel)
            self.assertEqual('Title', columns[0]['title'])
        finally:
            delattr(TestModel.Listing, 'columns')


    def test_should_return_property_if_exists_in_model(self):
        TestModel.Listing.columns = ['parent_model']
        try:
            self.assertEqual(1, len(self.view._get_model_columns(TestModel)))
        finally:
            delattr(TestModel.Listing, 'columns')


    def test_should_raise_exception_if_exceeding_max_columns(self):
        columns = CustomPage.Listing.columns
        CustomPage.Listing.columns = [
            'title',
            'meta_title',
            'meta_description',
            'meta_keywords',
            'slug',
            'url',
            'parent',
            'image'
        ]
        try:
            with self.assertRaisesRegexp(ValueError, 'exceeds the maximum number of allowed'):
                self.view._get_model_columns(CustomPage)
        finally:
            CustomPage.Listing.columns = columns


    def test_should_raise_exception_if_exceeding_max_columns_using_half_columns(self):
        columns = CustomPage.Listing.columns
        CustomPage.Listing.columns = [
            '/title',
            '/meta_title',
            '/meta_description',
            '/slug',
            '/url',
            '/parent',
            '/image',
            '/disabled',
            '/template',
            '/html_title',
            '/text_title',
            '/url_path',
            '/legacy_url'
        ]
        try:
            with self.assertRaisesRegexp(ValueError, 'exceeds the maximum number of allowed'):
                columns = self.view._get_model_columns(CustomPage)
        finally:
            CustomPage.Listing.columns = columns


    def test_should_not_include_action_if_provided_but_not_specified_as_valid_action(self):
        columns = CustomPage.Listing.columns
        CustomPage.Listing.columns =['title|Title|action:foo_action']

        try:
            _columns = self.view._get_model_columns(CustomPage)
            self.assertEqual(1, len(_columns))
            self.assertEqual('title', _columns[0].get('fieldname'))
            self.assertEqual('Title', _columns[0].get('title'))
            self.assertIsNone(_columns[0].get('action'))
        finally:
            CustomPage.Listing.columns = columns


    def test_should_include_action_if_provided_and_specified_as_valid_action(self):
        columns = CustomPage.Listing.columns
        CustomPage.Listing.columns =['title|Title|action:foo_action']

        try:
            _columns = self.view._get_model_columns(CustomPage, listing_actions=[{
                'view': 'foo_action'
            }])
            self.assertEqual(1, len(_columns))
            self.assertEqual('title', _columns[0].get('fieldname'))
            self.assertEqual('Title', _columns[0].get('title'))
            self.assertEqual({'view': 'foo_action'}, _columns[0].get('action'))
        finally:
            CustomPage.Listing.columns = columns


    def test_should_indicate_related_field(self):
        columns = CustomPage.Listing.columns
        CustomPage.Listing.columns = ['image__caption']
        try:
            _columns = self.view._get_model_columns(CustomPage)
            self.assertEqual('image__caption', _columns[0]['fieldname'])
            self.assertEqual('Caption', _columns[0]['title'])
            self.assertEqual('image', _columns[0]['related'])
            self.assertEqual(Media, _columns[0]['rel_model'])
            self.assertFalse(_columns[0]['foreign'])
            self.assertTrue(_columns[0]['related'])
        finally:
            CustomPage.Listing.columns = columns


    def test_should_indicate_foreign_field(self):
        columns = CustomPage.Listing.columns
        CustomPage.Listing.columns = ['image']
        try:
            _columns = self.view._get_model_columns(CustomPage)
            self.assertEqual('image', _columns[0]['fieldname'])
            self.assertEqual('Primary Image', _columns[0]['title'])
            self.assertIsNone(_columns[0]['related'])
            self.assertIsNone(_columns[0]['rel_model'])
            self.assertTrue(_columns[0]['foreign'])
        finally:
            CustomPage.Listing.columns = columns


class LibModelViewGetRelatedFieldsFromColumnsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_related_fields_from_columns()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_empty_array_if_columns_are_empty(self):
        self.assertEqual([], self.view._get_related_fields_from_columns([]))


    def test_should_return_list_of_related_field_names_and_foreign_keys(self):
        columns = [
            {'related': 'foo'},
            {'related': 'bar'},
            {'fieldname': 'foreign', 'foreign': True}
        ]
        self.assertEqual(
            ['foo', 'bar', 'foreign'],
            self.view._get_related_fields_from_columns(columns)
        )


    def test_should_not_yield_duplicate_field_names(self):
        columns = [
            {'related': 'foo'},
            {'related': 'foo'},
            {'fieldname': 'foo', 'foreign': True},
            {'fieldname': 'foreign', 'foreign': True},
            {'fieldname': 'foreign', 'foreign': True}
        ]
        self.assertEqual(
            ['foo', 'foreign'],
            self.view._get_related_fields_from_columns(columns)
        )


class LibModelViewCountFullColumnsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._count_full_columns()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_count_full_columns(self):
        columns = [{}, {}, {}]

        self.assertEqual(3, self.view._count_full_columns(columns))


    def test_should_count_half_columns(self):
        columns = [{'half_col': True}, {'half_col': True}, {'half_col': True}]

        self.assertEqual(1.5, self.view._count_full_columns(columns))


    def test_should_count_full_and_half_columns(self):
        columns = [{}, {}, {'half_col': True}, {'half_col': True}, {'half_col': True}]

        self.assertEqual(3.5, self.view._count_full_columns(columns))


class LibModelViewInjectColumnWidthTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._inject_column_width()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_nothing_if_no_colums_available(self):
        self.assertEqual(None, self.view._inject_column_width([]))


    def test_should_set_classes_if_all_columns_are_full_width(self):
        self.view.columns = [{'half_col': False}, {'half_col': False}, {'half_col': False}]
        self.view._inject_column_width(self.view.columns)
        self.assertEqual([{'col_class': 't-col-primary', 'half_col': False}, {'col_class': 't-col-2-4', 'half_col': False}, {'col_class': 't-col-2-4', 'half_col': False}], self.view.columns)


    def test_should_set_classes_if_all_columns_half_width_and_first_column_should_be_full_width(self):
        self.view.columns = [{'half_col': True}, {'half_col': True}, {'half_col': True}]
        self.view._inject_column_width(self.view.columns)
        self.assertEqual([{'col_class': 't-col-primary', 'half_col': False}, {'col_class': 't-col-1-2', 'half_col': True}, {'col_class': 't-col-1-2', 'half_col': True}], self.view.columns)


    def test_should_set_classes_for_mixed_full_widths_and_halfs(self):
        self.view.columns = [{'half_col': False}, {'half_col': True}, {'half_col': False}, {'half_col': True}]
        self.view._inject_column_width(self.view.columns)
        self.assertEqual([{'col_class': 't-col-primary', 'half_col': False}, {'col_class': 't-col-1-4', 'half_col': True}, {'col_class': 't-col-2-4', 'half_col': False}, {'col_class': 't-col-1-4', 'half_col': True}], self.view.columns)


class LibModelViewGetModelColumnNamesTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_model_column_names()
    """
    def test_should_return_list_of_fields_that_are_presented_by_listing_controller(self):
        view = ModelView()
        self.assertEqual(
            ['id', 'title', 'text', 'image'],
            view._get_model_column_names(TestModel)
        )


class LibModelViewGetDefaultViewTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_default_view()
    """
    def test_should_return_list_string(self):
        view = ModelView()

        self.assertEqual('list', view._get_default_view())


    def test_should_return_view(self):
        view = ModelView()
        view.model = DummyModel()
        view.model.Listing = DummyListing()
        view.model.Listing.default_view = 'default_view'

        self.assertEqual('default_view', view._get_default_view())


class LibModelViewGetFilterByTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_filter_by()
    """
    def test_should_return_filter_by(self):
        view = ModelView()

        view.model = DummyModel()
        view.model.Listing = DummyListing()
        view.model.Listing.filter_by = 'filter_by'

        self.assertEqual('filter_by', view._get_filter_by())


    def test_should_return_empty_list(self):
        view = ModelView()

        self.assertEqual([], view._get_filter_by())


class LibModelViewHasModelBackendSectionsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._has_model_backend_sections()
    """
    def test_should_return_false_when_model_attr_or_value_is_none(self):
        view = ModelView()

        self.assertEqual(False, view._has_model_backend_sections())


    def test_should_return_true_when_model_attr_and_value_provided(self):
        view = ModelView()
        view.model_attr = True
        view.model_attr_value = True

        self.assertEqual(True, view._has_model_backend_sections())


class LibModelViewConfigureModelBackendSectionTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._configure_model_backend_section()
    """
    def setUp(self):
        self.view = ModelView()
        self.model = DummyModel()


    def test_should_assign_model_attribute_if_view_has_backend_section(self):
        self.view.model_attr  = 'model_attr'
        self.view.model_attr_value = True

        self.view._configure_model_backend_section(self.model)

        self.assertTrue(hasattr(self.model, 'model_attr'))


    def test_should_should_not_assign_model_attributeif_view_has_not_backend_section(self):
        self.view._configure_model_backend_section(self.model)

        self.assertFalse(hasattr(self.model, 'model_attr'))


class LibModelViewGetModelBackendSectionTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_model_backend_section()
    """
    def test_should_return_none_if_model_has_no_backend_sections(self):
        view = ModelView()
        self.assertIsNone(view._get_model_backend_section(DummyModel()))


    def test_should_return_model_backend_section_attr(self):
        view = ModelView()
        view.model_attr = 'attr'
        view.model_attr_value = 'foo'

        model = DummyModel()
        model.attr = 'foo'

        self.assertEqual('foo', view._get_model_backend_section(model))


class LibModelViewGetFilterFormTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_filter_form()
    """
    FIELD_NAMES = [
        'title',
        'template',
        'disabled',
        'image__caption',
        'parent__title',
        'created_on'
    ]


    def setUp(self):
        self.view = ModelView()
        self.view.model = CustomPage
        self.listing = CustomPage.Listing
        self.view.model.Listing = Mock()
        self.view.model.Listing.filter_by = self.FIELD_NAMES
        self.factory = RequestFactory()
        self.request = self.factory.get('/')


    def tearDown(self):
        CustomPage.Listing = self.listing


    def test_should_return_none_if_filter_by_is_empty(self):
        self.view.model.Listing.filter_by = []

        self.assertEqual(None, self.view._get_filter_form(self.request, {}))


    def test_should_return_none_if_no_form_is_available(self):
        def _get_form():
            return None
        self.view._get_form = _get_form

        self.assertEqual(None, self.view._get_filter_form(self.request, {}))


    def test_should_ignore_filter_fields_that_do_not_exist(self):
        self.view.model.Listing.filter_by = ['does_not_exist']

        self.assertEqual(None, self.view._get_filter_form(self.request, {}))


    def test_should_configure_model_instance_with_backend_section(self):
        def _configure(form, request, instance=None, edit=False):
            self.assertEqual('foo', instance.attr)

        form = Mock
        form.fields = {}
        form.configure = _configure

        def _get_form():
            return form

        self.view.model_attr = 'attr'
        self.view.model_attr_value = 'foo'
        self.view._get_form = _get_form
        form = self.view._get_filter_form(self.request, {})


    def test_should_return_filter_form(self):
        form = self.view._get_filter_form(self.request, {})

        # pre-requirements
        self.assertTrue(hasattr(Media, 'get_filter_form'))
        self.assertFalse(hasattr(CustomPage, 'get_filter_form'))

        # form and fields
        field_names = ['_filter_%s' % fieldname for fieldname in self.FIELD_NAMES]

        self.assertIsInstance(form, CustomPageForm)
        self.assertEqual(field_names, form.fields.keys())

        # standard fields
        self.assertIsInstance(form.fields.get('_filter_title'), forms.CharField)
        self.assertIsInstance(form.fields.get('_filter_disabled'), forms.ChoiceField)

        # related fields
        self.assertIsInstance(form.fields.get('_filter_image__caption'), forms.CharField)
        self.assertIsInstance(form.fields.get('_filter_parent__title'), forms.CharField)

        # non-editable fields
        self.assertIsInstance(form.fields.get('_filter_created_on'), forms.DateTimeField)

        # all fields should be
        # - not required
        # - no initial data
        # - have no help text (unless checkbox)
        for fieldname in field_names:
            field = form.fields.get(fieldname)
            self.assertFalse(field.required, fieldname)
            if fieldname == '_filter_disabled':
                self.assertEqual('None', field.initial, fieldname)
            else:
                if fieldname == '_filter_template':
                    self.assertEqual('', field.initial, fieldname)
                else:
                    self.assertIsNone(field.initial, fieldname)
                self.assertIsNone(field.help_text, fieldname)

        # choices field should have an empty option
        self.assertEqual(('', '-------'), form.fields.get('_filter_template').choices[0])


class LibModelViewGetURLNameTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_url_name()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()


    def test_should_return_url_pattern_without_namespace(self):
        self.assertEqual('dummymodel.my_name', self.view._get_url_name('my_name'))


    def test_should_return_url_pattern_with_namespace(self):
        self.view.namespace = 'my_namespace'
        self.assertEqual('my_namespace.my_name', self.view._get_url_name('my_name', True))


    def test_should_return_name_if_namespace_and_namespace_false(self):
        self.view.namespace = 'my_namespace'
        self.assertEqual('my_name', self.view._get_url_name('my_name', False))


class LibModelViewGetUrlTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_url()
    """
    def setUp(self):
        self.request = Mock()
        self.view = ModelView()
        self.view.model = DummyModel()


    @patch('cubane.views.reverse')
    def test_should_return_url_without_args_if_get_is_empty(self, mock_function):
        mock_function.return_value = '/create'
        self.assertEqual('/create', self.view._get_url(self.request, 'my_name'))


    @patch('cubane.views.reverse')
    def test_should_return_dialog_url_if_request_contains_browse(self, mock_function):
        mock_function.return_value = '/browse'
        self.request.GET = {'browse': 'true'}
        self.assertEqual('/browse?browse=true&dialog=true', self.view._get_url(self.request, 'my_name'))


    @patch('cubane.views.reverse')
    def test_should_return_dialog_url_if_request_contains_create(self, mock_function):
        mock_function.return_value = '/create'
        self.request.GET = {'create': 'true'}
        self.assertEqual('/create?create=true&dialog=true', self.view._get_url(self.request, 'my_name'))


    @patch('cubane.views.reverse')
    def test_should_return_dialog_url_if_request_contains_edit(self, mock_function):
        mock_function.return_value = '/edit'
        self.request.GET = {'edit': 'true'}
        self.assertEqual('/edit?edit=true&dialog=true', self.view._get_url(self.request, 'my_name'))


    @patch('cubane.views.reverse')
    def test_should_return_format_url_if_format_true(self, mock_function):
        mock_function.return_value = '/format'
        self.assertEqual('/format?f=true', self.view._get_url(self.request, 'my_name', True, 'true'))


class LibModelViewGetUrlsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_urls()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()


    def test_should_return_url_patterns_for_not_single_instance(self):
        self.assertEqual(25, len(self.view.get_urls()))


    def test_should_return_url_patterns_for_single_instance(self):
        self.view.single_instance = True
        self.assertEqual(2, len(self.view.get_urls()))


    def test_should_return_url_patterns_with_view_patterns(self):
        self.view.patterns = [
            ('test/', 'test', {}, 'test')
        ]
        self.assertEqual(26, len(self.view.get_urls()))


    def test_should_return_url_patterns_with_prefix(self):
        self.view.patterns = [
            ('test/', 'test', {}, 'test')
        ]

        url = self.view.get_urls('pre').pop()
        self.assertEqual('^pre/test/$', url.regex.pattern)


    def test_should_return_url_patterns_without_prefix(self):
        self.view.patterns = [
            ('test/', 'test', {}, 'test')
        ]
        url = self.view.get_urls().pop()
        self.assertEqual('^test/$', url.regex.pattern)


class LibGetCreateUrlTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_create_url()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.request = self.get_view_handler_request(self.view, User(is_staff=True, is_superuser=True), 'dummy', 'get', '/dummy')


    @patch('cubane.views.reverse')
    def test_should_return_url_which_is_used_to_create_entity(self, mock_function):
        mock_function.return_value = '/create'
        self.assertEqual('/create', self.view._get_create_url(self.request))


    @patch('cubane.views.reverse')
    def test_should_return_url_with_preselected_folder(self, mock_function):
        mock_function.return_value = '/create'
        self.view.folder_model = Mock()
        self.assertEqual('/create?parent_id=-1', self.view._get_create_url(self.request))


class LibModelViewGetObjectTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_object()
    """
    def test_should_raise_exception(self):
        view = ModelView()
        self.assertRaises(NotImplementedError, view._get_object, 'request')


class LibModelViewGetObjectsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_objects()
    """
    def test_should_raise_exception(self):
        view = ModelView()
        self.assertRaises(NotImplementedError, view._get_objects, 'request')


class LibModelViewGetFoldersTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_folders()
    """
    def test_should_return_none(self):
        view = ModelView()
        self.assertEqual(None, view._get_folders('request', 'parent'))


class LibModelViewGetObjectOr404TestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_object_or_404()
    """
    def setUp(self):
        self.view = ModelView()

        self.view.model = DummyModel()


    def test_should_raise_exception_if_get_objects_not_implemented(self):
        self.assertRaises(NotImplementedError, self.view.get_object_or_404, Mock(), 'pk')


    def test_should_return_one_single_object(self):
        self.view._get_objects = Mock()
        self.view._get_objects.return_value.get = Mock(return_value='object')
        self.assertEqual('object', self.view.get_object_or_404(Mock(), 'pk'))


    def test_should_raise_exception_if_object_not_found(self):
        self.view._get_objects = Mock()
        self.view._get_objects.return_value.get = Mock()
        self.view._get_objects.return_value.get.side_effect = ObjectDoesNotExist()
        self.assertRaises(Http404, self.view.get_object_or_404, Mock(), 'pk')


class LibModelViewGetObjectsByIdsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_objects_by_ids()
    """
    def test_should_return_objects_by_ids(self):
        view = ModelView()
        view._get_objects = Mock()
        view._get_objects.return_value.filter = Mock(return_value=['test1', 'test2'])

        self.assertEqual(['test1', 'test2'], view._get_objects_by_ids(Mock(), [1, 2]))


class LibModelViewGetFolderByIdTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_folders_by_ids()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_raise_attribute_error_if_get_folders_return_none(self):
        self.assertRaises(AttributeError, self.view._get_folders_by_ids, Mock(), 'pk', None)


    def test_should_return_folder_by_id(self):
        self.view._get_folders = Mock()
        self.view._get_folders.return_value.in_bulk = Mock(return_value={'pk': 'folder'})
        self.assertEqual(['folder'], self.view._get_folders_by_ids(Mock(), ['pk']))


    def test_should_skip_folders_that_have_not_been_found(self):
        self.view._get_folders = Mock()
        self.view._get_folders.return_value.in_bulk = Mock(return_value={'pk': 'folder'})
        self.assertEqual([], self.view._get_folders_by_ids(Mock(), 'does-not-exist'))


class LibModelViewRedirectTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._redirect()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.instance = Mock()
        self.instance.pk = 1
        self.active_tab = '#active_tab'


    @patch('cubane.views.reverse')
    def test_should_return_redirect(self, mock_function):
        mock_function.return_value = '/admin/index/'
        self.assertEqual('/admin/index/', self.view._redirect(Mock(), 'index')['Location'])


    @patch('cubane.views.reverse')
    def test_should_return_redirect_with_pk(self, mock_function):
        mock_function.return_value = '/admin/delete/'
        self.assertEqual('/admin/delete/?pk=1', self.view._redirect(Mock(), 'delete', self.instance)['Location'])


    @patch('cubane.views.reverse')
    def test_should_return_redirect_with_active_tab(self, mock_function):
        mock_function.return_value = '/admin/index/'
        self.assertEqual('/admin/index/#active_tab', self.view._redirect(Mock(), 'index', None, self.active_tab)['Location'])


    @patch('cubane.views.reverse')
    def test_should_return_redirect_with_pk_and_active_tab(self, mock_function):
        mock_function.return_value = '/admin/update/'
        self.assertEqual('/admin/update/?pk=1#active_tab', self.view._redirect(Mock(), 'update', self.instance, self.active_tab)['Location'])


    @patch('cubane.views.reverse')
    def test_should_force_active_tab_to_contain_hash(self, mock_function):
        self.active_tab = 'active_tab'
        mock_function.return_value = '/admin/index/'
        self.assertEqual('/admin/index/#active_tab', self.view._redirect(Mock(), 'index', None, self.active_tab)['Location'])


class LibModelViewUserHasPermissionTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.user_has_permission()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.can_edit = False
        self.view.model = DummyModel
        self.user = Mock()
        self.user.is_staff = False
        self.user.is_superuser = False


    def test_should_return_false_if_user_has_not_permission(self):
        self.assertFalse(self.view.user_has_permission(self.user))


    def test_should_return_false_if_view_does_not_allow_action_to_begin_with(self):
        self.user.is_staff = True
        self.assertFalse(self.view.user_has_permission(self.user, 'edit'))


    def test_should_return_true_if_user_has_permission(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.assertTrue(self.view.user_has_permission(self.user))


class LibModelViewGetSuccessNessageTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_success_message()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = Mock()
        self.view.model._meta = Mock()
        self.view.model._meta.verbose_name = 'Name'


    def test_should_return_success_message_if_is_single_instance(self):
        self.view.single_instance = True
        self.assertEqual('<em>Name</em> task successfully.', self.view._get_success_message('label', 'task'))


    def test_should_return_success_message_if_is_not_single_instance(self):
        self.assertEqual('Name <em>label</em> task successfully.', self.view._get_success_message('label', 'task'))


class LibModelViewGetTemplatePathTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_template_path()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.handler = Mock()
        self.handler.__name__ = 'index'


    def test_should_return_path_with_template_path(self):
        self.assertEqual('dummymodel/index.html', self.view._get_template_path('request', self.handler, {}))


    def test_should_return_path_without_template_path(self):
        self.view.template_path = 'template_path'
        self.assertEqual('template_path/index.html', self.view._get_template_path('request', self.handler, {}))


class LibModelViewGetFormTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_form()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel


    def test_should_return_form_if_view_has_form(self):
        self.view.form = 'form'
        self.assertEqual('form', self.view._get_form())


    def test_should_get_form_if_model_has_form(self):
        self.view.model.get_form = Mock(return_value='get_form_call')
        self.assertEqual('get_form_call', self.view._get_form())


    def test_should_raise_exception_if_it_cannot_find_form_or_get_form_method(self):
        delattr(DummyModel, 'get_form')
        self.assertRaises(ValueError, self.view._get_form)


class LibModelViewGetRequestDataTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_request_data()
    """
    def setUp(self):
        self.view = ModelView()
        self.request = DummyRequest()


    def test_should_return_post(self):
        self.request.method = 'POST'
        self.request.POST = 'post'

        self.assertEqual('post', self.view._get_request_data(self.request))


    def test_should_return_get(self):
        self.request.method = 'GET'
        self.request.GET = 'get'

        self.assertEqual('get', self.view._get_request_data(self.request))


class LibModelViewIsJsonTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._is_json()
    """
    def setUp(self):
        self.view = ModelView()
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_return_true_if_the_request_is_an_ajax_request_or_a_sepcific_argument_has_been_provided_to_force_the_output_to_be_json(self):
        self.request.is_ajax = Mock(return_value=True)
        self.assertTrue(self.view._is_json(self.request))


    def test_should_return_false_if_the_request_is_not_an_ajax_request_or_without_specific_argument(self):
        self.assertFalse(self.view._is_json(self.request))



class LibModelViewIsAjaxHtmlTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._is_ajax_html()
    """
    def setUp(self):
        self.view = ModelView()
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_return_true_if_is_an_ajax_request_and_f_equals_html(self):
        self.request.is_ajax = Mock(return_value=True)
        self.request.GET = QueryDict('f=html')
        self.assertTrue(self.view._is_ajax_html(self.request))


    def test_should_return_false_if_is_not_an_ajax_request_or_f_is_not_html(self):
        self.assertFalse(self.view._is_ajax_html(self.request))



class LibModelViewCanImportTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._can_import()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_false(self):
        self.assertEqual(False, self.view._can_import())


    def test_should_return_true(self):
        self.view.model = DummyModel()
        self.view.model.Listing = DummyListing()
        self.view.model.Listing.data_import = True

        self.assertEqual(True, self.view._can_import())


class LibModelViewCanExportTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._can_export()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_false(self):
        self.assertEqual(self.view._can_export(), False)


    def test_should_return_true(self):
        self.view.model = DummyModel()
        self.view.model.Listing = DummyListing()
        self.view.model.Listing.data_export = True

        self.assertEqual(self.view._can_export(), True)


class LibModelCanDisableEnableTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._can_disable_enable()
    """
    def setUp(self):
        self.view =  ModelView()
        self.view.model = Mock()
        self.view.model._meta = Mock()
        self.view.model._meta.get_field = Mock()


    def test_should_raise_field_does_not_exist_exception_if_field_disabled_not_presented(self):
        self.view.model._meta.get_field.side_effect = FieldDoesNotExist()
        self.assertEqual(False, self.view._can_disable_enable())


    def test_should_return_true_if_field_disabled_presented(self):
        self.view.model._meta.get_field.return_value = Mock()
        self.assertEqual(True, self.view._can_disable_enable())


class LibModelViewSupportsGridViewTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._supports_grid_view()
    """
    def test_should_return_true_if_grid_view_is_enabled_by_view(self):
        view = self._setup_view(view_grid_view=True, model_grid_view=False)
        self.assertTrue(view._supports_grid_view())


    def test_should_return_false_if_grid_view_is_disabled_by_view(self):
        view = self._setup_view(view_grid_view=False, model_grid_view=True)
        self.assertFalse(view._supports_grid_view())


    def test_should_return_true_if_grid_view_is_allowed_by_model(self):
        view = self._setup_view(model_grid_view=True)
        self.assertTrue(view._supports_grid_view())


    def test_should_return_false_if_grid_view_is_not_allowed_by_model(self):
        view = self._setup_view(model_grid_view=False)
        self.assertFalse(view._supports_grid_view())


    def test_should_return_false_if_grid_view_is_not_defined(self):
        view = self._setup_view()
        self.assertFalse(view._supports_grid_view())


    def _setup_view(self, view_grid_view=None, model_grid_view=None):
        view = ModelView()
        view.model = DummyModel()
        view.model.Listing = DummyListing()

        if view_grid_view is not None:
            view.grid_view = view_grid_view

        if model_grid_view is not None:
            view.model.Listing.grid_view = model_grid_view

        return view


class LibModelIsSortableTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._is_sortable()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model_attr_value = True
        self.model = Mock()


    def test_should_return_false_if_model_is_sortable_returns_false(self):
        self.model.is_sortable = Mock()
        self.model.is_sortable.return_value = False

        self.assertEqual(False, self.view._is_sortable(self.model))


    def test_should_return_true_if_list_sortable_is_true(self):
        self.model.is_sortable = Mock()
        self.model.is_sortable.side_effect = AttributeError()
        self.model.Listing = Mock()
        self.model.Listing.sortable = True

        self.assertEqual(True, self.view._is_sortable(self.model))


    def test_should_return_false_if_everything_else_will_rise_exception(self):
        self.model = None

        self.assertEqual(False, self.view._is_sortable(self.model))


class LibModelViewUpdateWithHighestSeqTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._update_with_highest_seq()
    """
    def setUp(self):
        self.view = CustomPageView()
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.user = User(is_staff=True, is_superuser=True)


    def test_first_object_should_start_seq_with_1(self):
        page = CustomPage.objects.create(slug='foo')
        try:
            self.view._update_with_highest_seq(self.request, page)
            self.assertEqual(1, page.seq)
            self.assertEqual(1, CustomPage.objects.all().count())
        finally:
            page.delete()


    def test_following_object_should_continue_with_seq(self):
        first_page = CustomPage.objects.create(slug='foo', seq=1)
        second_page = CustomPage.objects.create(slug='bar')
        try:
            self.view._update_with_highest_seq(self.request, second_page)
            self.assertEqual(2, second_page.seq)
            self.assertEqual(2, CustomPage.objects.all().count())
        finally:
            first_page.delete()
            second_page.delete()


class LibModelViewGetOrderByArgTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_order_by_arg()
    """
    def setUp(self):
        self.view = CustomPageView()


    def test_should_return_none_if_order_specified_does_not_exist_in_model_description(self):
        self.assertEqual(
            (None, False),
            self.view._get_order_by_arg({'o': 'does_not_exist'}, sortable=False)
        )


    def test_should_return_default_ordering_for_model_if_order_is_not_specified(self):
        self.assertEqual(
            ('_meta_description', False),
            self.view._get_order_by_arg({}, sortable=False)
        )


    def test_should_return_first_display_column_if_order_is_not_specified_and_default_ordering_does_not_match_display_columns(self):
        view = EnquiryView()
        self.assertEqual(
            ('email', False),
            view._get_order_by_arg({}, sortable=False)
        )


    def test_should_return_default_ordering_for_model_if_order_is_not_specified_with_reverse_respected(self):
        ordering = CustomPage._meta.ordering[1]
        CustomPage._meta.ordering[1] = '-title'
        try:
            self.assertEqual(
                ('title', True),
                self.view._get_order_by_arg({}, sortable=False)
            )
        finally:
            CustomPage._meta.ordering[1] = ordering


    def test_should_return_seq_column_if_order_is_not_specified_if_sortable(self):
        view = EnquiryView()
        self.assertEqual(
            ('seq', False),
            view._get_order_by_arg({}, sortable=True)
        )


    def test_should_return_ordering_by_seq_for_model_if_order_is_not_specified(self):
        ordering = CustomPage._meta.ordering[1]
        CustomPage._meta.ordering[1] = '-title'
        try:
            self.assertEqual(
                ('seq', False),
                self.view._get_order_by_arg({}, sortable=True)
            )
        finally:
            CustomPage._meta.ordering[1] = ordering


    def test_should_return_order_by_field_as_specified_in_args(self):
        self.assertEqual(
            ('title', False),
            self.view._get_order_by_arg({'o': 'title'}, sortable=True)
        )


    def test_should_return_order_by_field_as_specified_in_args_with_reverse_respected(self):
        self.assertEqual(
            ('title', True),
            self.view._get_order_by_arg({'o': 'title', 'ro': True}, sortable=True)
        )


class LibModelViewSearchTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._search()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewSearchTestCase, cls).setUpClass()
        cls.img = Media.objects.create(caption='Test Image', filename='test.jpg')
        cls.m1 = TestModel.objects.create(id=1, title='Foo', text='foo is singing')
        cls.m2 = TestModel.objects.create(id=2, title='Bar', text='bar is dancing', image=cls.img)
        cls.view = ModelView()
        cls.model = TestModel
        cls.objects = cls.model.objects.all()


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewSearchTestCase, cls).tearDownClass()
        cls.m1.delete()
        cls.m2.delete()
        cls.img.delete()


    def test_should_ignore_if_query_is_none(self):
        items = self.view._search(self.objects, self.model, None)
        self.assertEqual(2, items.count())


    def test_should_ignore_empty_string(self):
        items = self.view._search(self.objects, self.model, '')
        self.assertEqual(2, items.count())


    def test_should_ignore_number(self):
        items = self.view._search(self.objects, self.model, 1)
        self.assertEqual(2, items.count())


    def test_should_ignore_word_too_short(self):
        items = self.view._search(self.objects, self.model, 'ab')
        self.assertEqual(2, items.count())


    def test_should_match_title(self):
        items = self.view._search(self.objects, self.model, 'Foo')
        self.assertEqual(1, items.count())
        self.assertEqual('Foo', items[0].title)


    def test_should_match_text(self):
        items = self.view._search(self.objects, self.model, 'dancing')
        self.assertEqual(1, items.count())
        self.assertEqual('Bar', items[0].title)


    def test_should_only_search_in_visible_columns(self):
        self.model.Listing.columns = ['title']
        try:
            # find by title should succeed
            items = self.view._search(self.objects, self.model, 'Foo')
            self.assertEqual(1, items.count())
            self.assertEqual('Foo', items[0].title)

            # find by text should fail
            items = self.view._search(self.objects, self.model, 'singing')
            self.assertEqual(0, items.count())
        finally:
            delattr(self.model.Listing, 'columns')


    def test_should_allow_for_additional_fields_to_be_searchable(self):
        self.model.Listing.columns = ['title']
        self.model.Listing.searchable = ['text']
        try:
            # find by title should succeed, since it is a column
            items = self.view._search(self.objects, self.model, 'Foo')
            self.assertEqual(1, items.count())
            self.assertEqual('Foo', items[0].title)

            # find by text should also success, since it is searchable
            items = self.view._search(self.objects, self.model, 'singing')
            self.assertEqual(1, items.count())
            self.assertEqual('Foo', items[0].title)
        finally:
            delattr(self.model.Listing, 'columns')
            delattr(self.model.Listing, 'searchable')


    def test_should_allow_for_searching_by_related_fields(self):
        self.model.Listing.columns = ['image__caption']
        try:
            items = self.view._search(self.objects, self.model, 'Test')
            self.assertEqual(1, items.count())
            self.assertEqual('Bar', items[0].title)
        finally:
            delattr(self.model.Listing, 'columns')


class LibModelViewGetFilterArgsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_filter_args()
    """
    def setUp(self):
        self.view = ModelView()
        self.args = Mock()


    def test_return_dict_if_items_are_empty(self):
        self.args.items = Mock(return_value=[])

        self.assertEqual({}, self.view._get_filter_args(self.args))


    def test_should_return_dict_if_items_starts_with_f(self):
        self.args.items = Mock(return_value=[('f_test_1', 1), ('f_test_2', 2)])

        self.assertEqual({'test_1': 1, 'test_2': 2}, self.view._get_filter_args(self.args))


    def test_should_return_items_starts_with_f_and_ignore_other(self):
        self.args.items = Mock(return_value=[('f_test_1', 1), ('c_test_2', 2), ('f_test_3', 3)])

        self.assertEqual({'test_1': 1, 'test_3': 3}, self.view._get_filter_args(self.args))


@freeze_time('2016-09-23')
class LibModelViewFilterTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._filter()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewFilterTestCase, cls).setUpClass()
        cls.img = Media.objects.create(caption='Test Image', filename='test.jpg')
        cls.m1 = TestModel.objects.create(id=1, title='Foo', text='foo is singing')
        cls.m2 = TestModel.objects.create(id=2, title='Bar', text='bar is dancing', image=cls.img)
        cls.view = ModelView()
        cls.view.model = TestModel
        cls.objects = TestModel.objects.all()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')
        TestModel.Listing.filter_by = ['title', 'text', 'image', 'image__caption', 'created_on']
        cls.filter_form = cls.view._get_filter_form(cls.request, {})


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewFilterTestCase, cls).tearDownClass()
        delattr(TestModel.Listing, 'filter_by')
        cls.m1.delete()
        cls.m2.delete()
        cls.img.delete()


    def test_should_ignore_without_filter_form(self):
        items = self.view._filter(self.objects, {}, None)
        self.assertEqual(2, items.count())


    def test_should_ignore_filter_values_not_defined_by_form(self):
        items = self.view._filter(self.objects, {'foo': 'Bar'}, self.filter_form)
        self.assertEqual(2, items.count())


    def test_should_filter_by_charfield(self):
        items = self.view._filter(self.objects, {'title': 'Foo'}, self.filter_form)
        self.assertEqual(1, items.count())
        self.assertEqual('Foo', items[0].title)


    def test_should_filter_by_related_field(self):
        items = self.view._filter(self.objects, {'image__caption': 'Test'}, self.filter_form)
        self.assertEqual(1, items.count())
        self.assertEqual('Bar', items[0].title)


    def test_should_filter_by_datetime(self):
        items = self.view._filter(self.objects, {'created_on': '23/09/2016'}, self.filter_form)
        self.assertEqual(2, items.count())


    def test_should_filter_by_foreign_key_choice(self):
        items = self.view._filter(self.objects, {'image': self.img.pk}, self.filter_form)
        self.assertEqual(1, items.count())
        self.assertEqual('Bar', items[0].title)


    def test_should_filter_by_tag_field(self):
        view = ModelView()
        view.model = TestTagsField
        tag1 = TestTagsField.objects.create(tags=['a', 'b'])
        tag2 = TestTagsField.objects.create(tags=['b', 'c'])
        objects = TestTagsField.objects.all()
        filter_form = view._get_filter_form(self.request, {})
        try:
            items = view._filter(objects, {'tags': ['c']}, filter_form)
            self.assertEqual(1, items.count())
            self.assertEqual(tag2.pk, items[0].pk)
        finally:
            tag2.delete()
            tag1.delete()


    def test_should_filter_by_many_to_many_field(self):
        view = ModelView()
        view.model = TestModelWithManyToMany
        page = Page.objects.create(title='Foo', slug='foo')
        obj1 = TestModelWithManyToMany.objects.create()
        obj2 = TestModelWithManyToMany.objects.create()
        obj2.pages.add(page)
        objects = TestModelWithManyToMany.objects.all()
        filter_form = view._get_filter_form(self.request, {})
        try:
            # should succeed with valid foreign key
            items = view._filter(objects, {'pages': [page.pk]}, filter_form)
            self.assertEqual(1, items.count())
            self.assertEqual(obj2.pk, items[0].pk)

            # should ignore a non-int value
            items = view._filter(objects, {'pages': ['not-a-number']}, filter_form)
            self.assertEqual(2, items.count())
        finally:
            obj2.delete()
            obj1.delete()
            page.delete()


    def test_should_filter_by_boolean(self):
        view = ModelView()
        view.model = Page
        p1 = Page.objects.create(title='Foo', disabled=True)
        p2 = Page.objects.create(title='Bar')
        objects = Page.objects.all()
        filter_form = view._get_filter_form(self.request, {})
        try:
            # shoudl match true
            items = view._filter(objects, {'disabled': True}, filter_form)
            self.assertEqual(['Foo'], [item.title for item in items])

            # should match false
            items = view._filter(objects, {'disabled': False}, filter_form)
            self.assertEqual(['Bar'], [item.title for item in items])
        finally:
            p1.delete()
            p2.delete()


    def test_should_execute_custom_filter_method_on_model(self):
        def _filter_by(model, objects, args):
            return objects.filter(title='Foo')
        TestModel.filter_by = classmethod(_filter_by)
        try:
            items = self.view._filter(self.objects, {}, self.filter_form)
            self.assertEqual(1, items.count())
            self.assertEqual('Foo', items[0].title)
        finally:
            delattr(TestModel, 'filter_by')


    def test_should_execute_custom_filter_method_on_form(self):
        def _filter_by(objects, args):
            return objects.filter(title='Foo')
        self.filter_form.filter_by = _filter_by
        try:
            items = self.view._filter(self.objects, {}, self.filter_form)
            self.assertEqual(1, items.count())
            self.assertEqual('Foo', items[0].title)
        finally:
            delattr(self.filter_form, 'filter_by')


class LibModelViewFilterNonIntegerForeignKeyTestCase(CubaneTestCase):
    """
    Tests cubane.views.ModelView._filter() when filtering by a non-integer
    foreign key.
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewFilterNonIntegerForeignKeyTestCase, cls).setUpClass()
        cls.gb = Country.objects.get(iso='GB')
        cls.de = Country.objects.get(iso='DE')
        cls.m1 = TestModelFilterByCountry.objects.create(id=1, title='Foo', country=cls.gb)
        cls.m2 = TestModelFilterByCountry.objects.create(id=2, title='Bar', country=cls.de)
        cls.view = ModelView()
        cls.view.model = TestModelFilterByCountry
        cls.objects = TestModelFilterByCountry.objects.all()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')
        cls.filter_form = cls.view._get_filter_form(cls.request, {})


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewFilterNonIntegerForeignKeyTestCase, cls).tearDownClass()
        cls.m1.delete()
        cls.m2.delete()


    def test_should_filter_by_foreign_key_choice_with_non_integer_primary_key(self):
        items = self.view._filter(self.objects, {'country': self.gb.pk}, self.filter_form)
        self.assertEqual(1, items.count())
        self.assertEqual('Foo', items[0].title)


class LibModelViewGetListingActionsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_listing_actions()
    """
    def setUp(self):
        self.view = ModelView()
        self.viewmodel = DummyModel
        self.expected_result = [{
            'confirm': 'confirm',
            'method': 'method',
            'title': 'title',
            'typ': 'typ',
            'url': '/admin/index/',
            'view': 'view',
            'dialog': False,
            'small_dialog': False,
            'external': False
        }]


    def test_should_return_empty_array_if_listing_actions_not_presented(self):
        self.assertEqual([], self.view._get_listing_actions('request'))


    @patch('cubane.views.ModelView._get_url')
    def test_should_return_list_of_additional_actions(self, mock_function):
        mock_function.return_value = '/admin/index/'
        self.view.listing_actions = [['title', 'view', 'typ', 'method', 'confirm']]

        self.assertEqual(self.expected_result, self.view._get_listing_actions('request'))


    @patch('cubane.views.ModelView._get_url')
    def test_should_return_list_of_two_additional_actions(self, mock_function):
        mock_function.return_value = '/admin/index/'
        self.view.listing_actions = [['title', 'view', 'typ', 'method', 'confirm'], ['title_2', 'view_2', 'typ_2', 'method_2', 'confirm_2']]

        self.expected_result.append({
            'confirm': 'confirm_2',
            'method': 'method_2',
            'title': 'title_2',
            'typ': 'typ_2',
            'url': '/admin/index/',
            'view': 'view_2',
            'dialog': False,
            'small_dialog': False,
            'external': False
        })

        self.assertEqual(self.expected_result, self.view._get_listing_actions('request'))


    @patch('cubane.views.ModelView._get_url')
    def test_should_retun_list_with_default_method_location_if_method_is_not_provided(self, mock_function):
        mock_function.return_value = '/admin/index/'
        self.view.listing_actions = [['title', 'view', 'typ']]

        self.expected_result = [{
            'confirm': False,
            'method': 'location',
            'title': 'title',
            'typ': 'typ',
            'url': '/admin/index/',
            'view': 'view',
            'dialog': False,
            'small_dialog': False,
            'external': False
        }]

        self.assertEqual(self.expected_result, self.view._get_listing_actions('request'))


    @patch('cubane.views.ModelView._get_url')
    def test_should_retun_list_with_default_confirm_false_if_confirm_is_not_provided(self, mock_function):
        mock_function.return_value = '/admin/index/'
        self.view.listing_actions = [['title', 'view', 'typ', 'method']]

        self.expected_result = [{
            'confirm': False,
            'method': 'method',
            'title': 'title',
            'typ': 'typ',
            'url': '/admin/index/',
            'view': 'view',
            'dialog': False,
            'small_dialog': False,
            'external': False
        }]

        self.assertEqual(self.expected_result, self.view._get_listing_actions('request'))



class LibModelViewInjectListingActionsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._inject_listing_actions()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_empty_array_if_objects_are_empty(self):
        self.assertEqual([], self.view._inject_listing_actions([], []))


    def test_should_return_empty_object_listing_actions_if_listing_actions_are_empty(self):
        objects = self.view._inject_listing_actions([Mock()], [])

        obj = objects[0]
        self.assertEqual([], obj.listing_actions)


    def test_should_return_objects_with_listing_actions(self):
        objects = self.view._inject_listing_actions([Mock()], ['view', 'edit'])

        obj = objects[0]
        self.assertEqual(['view', 'edit'], obj.listing_actions)



class LibModelViewObjectCanExecuteListingActionTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._object_can_execute_listing_action()
    """
    class ModelMockBase(object):
        pass

    class ModelMock(ModelMockBase):
        def can_execute_action(self, action):
            return action == 'edit'


    def test_should_return_true_if_model_can_execute_action(self):
        view = ModelView()
        self.assertTrue(view._object_can_execute_listing_action(self.ModelMock(), 'edit'))


    def test_should_return_false_if_model_cannot_execute_action(self):
        view = ModelView()
        self.assertFalse(view._object_can_execute_listing_action(self.ModelMock(), 'delete'))


    def test_should_return_true_if_model_does_not_define_method_for_determining_action_permissions(self):
        view = ModelView()
        self.assertTrue(view._object_can_execute_listing_action(self.ModelMockBase(), 'delete'))


class LibModelViewGetShortcutActionsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_shortcut_actions()
    """
    LISTING_ACTIONS = [
        {
            'view': 'foo',
            'typ': 'single',
        }, {
            'view': 'bar',
            'typ': 'multiple'
        }, {
            'view': 'test'
        }
    ]


    def test_should_return_empty_list_if_view_does_not_define_shortcut_actions(self):
        view = ModelView()
        self.assertEqual([], view._get_shortcut_actions(self.LISTING_ACTIONS))


    def test_should_return_empty_list_if_view_does_define_shortcut_actions_but_no_listing_actions_are_defined(self):
        view = ModelView()
        view.shortcut_actions = ['foo']
        self.assertEqual([], view._get_shortcut_actions([]))


    def test_should_return_actions_as_references_by_shortcut_actions_which_are_single_or_multiple_action_type(self):
        view = ModelView()
        view.shortcut_actions = ['foo', 'bar']
        self.assertEqual(
            [
                {'typ': 'single',   'view': 'foo'},
                {'typ': 'multiple', 'view': 'bar'},
            ],
            view._get_shortcut_actions(self.LISTING_ACTIONS)
        )


class LibModelViewGetSelectorModelTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_selector_model()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_none(self):
        self.assertEqual(None, self.view._get_selector_model())


    def test_should_return_selector_model(self):
        self.view.selector_model = 'selector_model'

        self.assertEqual('selector_model', self.view._get_selector_model())


class LibModelViewGetActiveSelectorSessionModelTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_active_selector_session_name()
    """
    def test_should_return_active_selector_session_name(self):
        view = ModelView()
        view.selector_model = DummyModel()

        self.assertEqual('foo-selector_filter_DummyModel', view._get_active_selector_session_name('foo-'))


class LibModelViewGetActiveSelectorPk(CubaneTestCase):
    """
    cubane.views.ModelView._get_active_selector_pk()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.selector_model = DummyModel()
        self.request = DummyRequest()


    def test_should_return_none_if_not_session_name(self):
        self.request.session = {}

        self.assertEqual(None, self.view._get_active_selector_pk(self.request))


    def test_should_return_pk_if_field_is_not_integerfield_or_autofield(self):
        self.view.selector_model._meta = Mock()
        self.view.selector_model._meta.pk = Mock()
        self.request.session = {'selector_filter_DummyModel': 10}

        self.assertEqual(10, self.view._get_active_selector_pk(self.request))


    def test_should_return_none_if_pk_is_not_int_and_field_is_integerfield_or_autofield(self):
        self.view.selector_model._meta = Mock()
        self.view.selector_model._meta.pk = AutoField(primary_key=True)
        self.request.session = {'selector_filter_DummyModel': 'test'}

        self.assertEqual(None, self.view._get_active_selector_pk(self.request))


    def test_should_return_pk_if_field_is_integerfield_or_autofield(self):
        self.view.selector_model._meta = Mock()
        self.view.selector_model._meta.pk = IntegerField()

        self.request = DummyRequest()
        self.request.session = {'selector_filter_DummyModel': '10'}

        self.assertEqual(10, self.view._get_active_selector_pk(self.request))


class LibModelViewSetActiveSelectorPk(CubaneTestCase):
    """
    cubane.views.ModelView._set_active_selector_pk()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.selector_model = DummyModel()
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_not_set_pk(self):
        self.view._set_active_selector_pk(self.request, None)
        self.assertEqual(None, self.request.session.get('selector_filter_DummyModel', None))


    def test_should_set_pk(self):
        self.view._set_active_selector_pk(self.request, 10)
        self.assertEqual(10, self.request.session.get('selector_filter_DummyModel', None))


class LibModelViewGetActiveFolderSessionNameTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_active_folders_session_name()
    """
    def test_should_return_session_variable_name(self):
        view = ModelView()
        view.model = DummyModel()
        self.assertEqual('foo-folders_id_DummyModel', view._get_active_folders_session_name('foo-'))


class LibModelViewGetActiveFolderId(CubaneTestCase):
    """
    cubane.views.ModelView._get_active_folder_ids()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewGetActiveFolderId, cls).setUpClass()
        cls.view = ModelView()
        cls.view.model = DummyModel()


    def setUp(self):
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_return_minus_one_if_folder_id_is_none(self):
        self.assertEqual([-1], self.view._get_active_folder_ids(self.request))


    def test_should_return_none_if_folder_id_cannot_be_converted_to_int(self):
        self.view._set_active_folder_ids(self.request, 'dummy')
        self.assertEqual([-1], self.view._get_active_folder_ids(self.request))


    def test_should_return_folder_id(self):
        self.view._set_active_folder_ids(self.request, '5')
        self.assertEqual([5], self.view._get_active_folder_ids(self.request))


class LibModelViewSetActiveFolderIdTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._set_active_folder_ids()
    """
    pass
    #@TODO


class LibModelViewGetOpenFoldersSessionNameTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_open_folders_session_name()
    """
    def test_should_return_open_folder_session_name(self):
        view = ModelView()
        view.model = DummyModel()

        self.assertEqual('folder_ids_DummyModel', view._get_open_folders_session_name())


class LibModelViewGetOpenFoldersTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_open_folders()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_return_ids_as_previously_set_to_be_open(self):
        self.view._set_open_folders(self.request, [1, 2, 3, 4, 5])
        self.assertEqual([1, 2, 3, 4, 5], self.view._get_open_folders(self.request))


    def test_should_retun_empty_array(self):
        self.assertEqual([], self.view._get_open_folders(self.request))


    def test_should_ignore_not_int_values(self):
        self.view._set_open_folders(self.request, [1, 'test', 3, 'test', 5])
        self.assertEqual([1, 3, 5], self.view._get_open_folders(self.request))


class LibModelViewSetOpenFoldersTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._set_open_folders()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')
        self.session_name = self.view._get_open_folders_session_name()


    def test_should_assume_empty_list_for_none(self):
        self.view._set_open_folders(self.request, None)
        self.assertEqual([], self.request.session.get(self.session_name, []))


    def test_should_set_folder_ids_in_session(self):
        self.view._set_open_folders(self.request, [1, 2, 3])
        self.assertEqual([1, 2, 3], self.request.session.get(self.session_name, []))


class LibModelViewGetModelSelector(CubaneTestCase):
    """
    cubane.views.ModelView._get_model_selector()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.selector_model = DummyModel()
        self.view._get_selector_objects = Mock()
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_selector_model_none_should_return_none(self):
        self.view.selector_model = None
        self.assertEqual(None, self.view._get_model_selector(DummyRequest()))


    def test_should_return_selector_objects(self):
        self.view._get_selector_objects.return_value = [1, 2, 3]
        self.assertEqual({'objects': [1, 2, 3], 'active_pk': None}, self.view._get_model_selector(self.request))


    def test_should_return_model_objects(self):
        del(self.view._get_selector_objects)
        self.view.selector_model.objects = Mock()
        self.view.selector_model.objects.all = Mock()
        self.view.selector_model.objects.all.return_value = [2, 4, 5]

        self.assertEqual({'active_pk': None, 'objects': [2, 4 ,5]}, self.view._get_model_selector(self.request))


class LibModelViewFilterBySelectorTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._filter_by_selector()
    """
    class TestModelViewWithSelectorFilter(ModelView):
        model = TestModel
        selector_model = Media

        def _select_by(self, objects, pk):
            return objects.filter(image_id=pk)


    @classmethod
    def setUpClass(cls):
        super(LibModelViewFilterBySelectorTestCase, cls).setUpClass()
        cls.img = Media.objects.create(caption='Test Image', filename='test.jpg')
        cls.m1 = TestModel.objects.create(id=1, title='Foo', text='foo is singing')
        cls.m2 = TestModel.objects.create(id=2, title='Bar', text='bar is dancing', image=cls.img)
        cls.objects = TestModel.objects.all()


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewFilterBySelectorTestCase, cls).tearDownClass()
        cls.m1.delete()
        cls.m2.delete()
        cls.img.delete()


    def test_should_not_filter_if_view_does_not_define_selector_method(self):
        view = ModelView()
        request = self.make_request('get', '/', {'s': self.img.pk})
        self.assertEqual(2, view._filter_by_selector(request, self.objects).count())


    def test_should_filter_by_given_selector_pk(self):
        view = self.TestModelViewWithSelectorFilter()
        request = self.make_request('get', '/', {'s': self.img.pk})
        items = view._filter_by_selector(request, self.objects)
        self.assertEqual(1, items.count())
        self.assertEqual('Bar', items[0].title)


    def test_should_ignore_if_selector_pk_is_not_int(self):
        view = self.TestModelViewWithSelectorFilter()
        request = self.make_request('get', '/', {'s': 'not-a-number'})
        self.assertEqual(2, view._filter_by_selector(request, self.objects).count())


    def test_should_obtain_selector_pk_from_session_if_no_selector_is_given(self):
        view = self.TestModelViewWithSelectorFilter()
        request = self.make_request('get', '/')
        view._set_active_selector_pk(request, self.img.pk)
        items = view._filter_by_selector(request, self.objects)
        self.assertEqual(1, items.count())
        self.assertEqual('Bar', items[0].title)


class LibModelViewFilterByFolderTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._filter_by_folders()
    """
    def setUp(self):
        self.view = ModelView()
        self.request = self.get_view_handler_request(self.view, User(is_staff=True, is_superuser=True), 'dummy', 'get', '/dummy')
        self.view._folder_filter = Mock(return_value=[1, 2])
        self.view._get_folders_by_ids = Mock(return_value='folders')


    def test_should_return_objects_if_folder_id_provided(self):
        self.view.folder_model = MediaFolder
        self.view.model = DummyModel
        self.request = self.get_view_handler_request(self.view, User(is_staff=True, is_superuser=True), 'dummy', 'get', '/dummy', {'folders[]': ['1']})
        self.assertEqual(([1, 2], 'folders', [1]), self.view._filter_by_folders(self.request, [1, 2, 3]))


    def test_should_return_objects_when_folder_id_value_error_exception_raises(self):
        self.view.folder_model = MediaFolder
        self.view.model = DummyModel
        self.request = self.get_view_handler_request(self.view, User(is_staff=True, is_superuser=True), 'dummy', 'get', '/dummy', {'folders[]': ['test']})
        self.assertEqual(([1, 2], 'folders', None), self.view._filter_by_folders(self.request, [1, 2, 3]))


    def test_should_return_objects_if_folder_id_is_none(self):
        self.view.folder_model = MediaFolder
        self.view.model = DummyModel
        self.assertEqual(([1, 2], 'folders', None), self.view._filter_by_folders(self.request, [1, 2, 3]))


    def test_should_return_objects_if_has_folder_return_false(self):
        self.view.has_folders = Mock(return_value=False)
        self.assertEqual(([1, 2, 3], None, None), self.view._filter_by_folders(self.request, [1, 2, 3]))


class LibModelViewFolderFilterTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._folder_filter()
    """
    def test_should_return_filtered_folders(self):
        obj = Mock()
        obj.filter = Mock(return_value=[1, 2, 3])
        view = ModelView()

        self.assertEqual([1, 2, 3], view._folder_filter(None, obj, [1]))


class LibModelViewFolderAssignTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._folder_assign()
    """
    def test_should_set_attribute_to_object(self):
        obj = Mock()
        view = ModelView()
        request = None
        view._folder_assign(request, obj, 'dst', [])

        self.assertEqual('dst', obj.parent)


class LibModelViewGetFolderAssignmentNameTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_folder_assignment_name()
    """
    def test_should_return_parent_string(self):
        view = ModelView()

        self.assertEqual('parent', view._get_folder_assignment_name())


class LibModelViewGetIndexArgsTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_index_args()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.view.model._meta = Mock()
        self.view.model._meta.app_label = 'Label'
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_return_empty_list_if_no_get_args_provided(self):
        self.assertEqual({}, self.view._get_index_args(self.request))


    def test_should_return_args(self):
        self.request.GET = QueryDict('a=1&b=2&c=3')
        self.assertEqual({'a': '1', 'b': '2', 'c': '3'}, self.view._get_index_args(self.request))


    def test_should_replace_string_to_boolean_true_and_return_args(self):
        self.request.GET = QueryDict('a=True&b=true&c=1')
        self.assertEqual({'a': True, 'b': True, 'c': '1'}, self.view._get_index_args(self.request))


    def test_should_replace_string_to_boolean_false_and_return_args(self):
        self.request.GET = QueryDict('a=False&b=false&c=2')
        self.assertEqual({'a': False, 'b': False, 'c': '2'}, self.view._get_index_args(self.request))


    def test_should_return_args_without_none_values(self):
        self.request.GET = QueryDict('a=none&b=None&c=2')
        self.assertEqual({'c': '2'}, self.view._get_index_args(self.request))


    def test_should_return_args_without_empty_values(self):
        self.request.GET = QueryDict('a=&b=2&c=')
        self.assertEqual({'b': '2'}, self.view._get_index_args(self.request))


    def test_should_return_args_including_array(self):
        self.request.GET = QueryDict('a=1&b[]=1&b[]=2&c=6')
        self.assertEqual({'a': '1', 'b': ['1', '2'], 'c': '6'}, self.view._get_index_args(self.request))


class LibModelViewGetSidePanelWidthTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_sidepanel_width()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.view.model._meta = Mock()
        self.view.model._meta.app_label = 'test'
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_return_default_width(self):
        self.assertEqual(240, self.view._get_sidepanel_width(self.request, 'folders'))


    def test_should_return_width(self):
        self.view._set_sidepanel_width(self.request, 200, 'folders')
        self.assertEqual(200, self.view._get_sidepanel_width(self.request, 'folders'))


class LibModelViewSetSidePanelWidthTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._set_sidepanel_width()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.view.model._meta = Mock()
        self.view.model._meta.app_label = 'test'
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_return_default_width_if_not_int(self):
        self.assertEqual(180, self.view._set_sidepanel_width(self.request, 'test', 'folders'))


    def test_should_return_width(self):
        self.assertEqual(200, self.view._set_sidepanel_width(self.request, 200, 'folders'))


    def test_should_set_width_as_session_variable(self):
        self.view._set_sidepanel_width(self.request, 400, 'folders')
        self.assertEqual(400, self.request.session['listing_folders_side_panel_width'])


class LibGetFormInitialTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_form_initial()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = Media
        self.factory = RequestFactory()


    def test_should_return_initials_from_model_based_on_GET(self):
        request = self.factory.get('/', {'filename': 'foo', 'caption': 'bar'})
        self.assertEqual(
            {'filename': 'foo', 'caption': 'bar'},
            self.view._get_form_initial(request)
        )


    def test_should_return_initials_from_model_based_on_GET_id_attribute_suffix(self):
        request = self.factory.get('/', {'filename_id': 'foo', 'caption_id': 'bar'})
        self.assertEqual(
            {'filename': 'foo', 'caption': 'bar'},
            self.view._get_form_initial(request)
        )


    def test_should_return_empty_initials_if_GET_empty(self):
        request = self.factory.get('/')
        self.assertEqual({}, self.view._get_form_initial(request))


class LibModelViewGetViewIdentifierTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_view_identifier()
    """
    def test_should_return_view_identifier_if_specified_in_view(self):
        view = ModelView()
        view.view_identifier = 'foo'
        self.assertEqual('foo', view._get_view_identifier())


    def test_should_return_empty_string_if_not_specified_in_view(self):
        view = ModelView()
        self.assertEqual('', view._get_view_identifier())


class LibModelViewIndexTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.index()
    """
    FOLDER_NAMES = ['a', 'b', 'c', 'd', 'e', 'f']


    @classmethod
    def setUpClass(cls):
        super(LibModelViewIndexTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()

        # pages
        cls.p1 = Page.objects.create(title='Foo', seq=1)
        cls.p2 = Page.objects.create(title='Bar', seq=2)

        # media folders
        cls.cms = get_cms()
        for i, name in enumerate(cls.FOLDER_NAMES, start=1):
            setattr(cls, 'f%d' % i, cls.cms.create_media_folder(name))


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewIndexTestCase, cls).tearDownClass()

        cls.user.delete()
        cls.p1.delete()
        cls.p2.delete()
        for i in range(1, 7):
            getattr(cls, 'f%d' % i).delete()


    def test_should_return_template_context(self):
        view = PageContentView(Page)
        request, c = self.run_view_handler_request(view, self.user, 'index', 'get', '/')
        changelog_content_type = ContentType.objects.get_for_model(view.model)

        # capabilities
        self.assertIsNone(c.get('folder'))
        self.assertFalse(c.get('import'))
        self.assertTrue(c.get('export'))
        self.assertTrue(c.get('grid_view'))
        self.assertFalse(c.get('has_folders'))
        self.assertTrue(c.get('sortable'))
        self.assertTrue(c.get('search'))

        # model and model names
        self.assertEqual(Page, c.get('model'))
        self.assertEqual('Page', c.get('model_name'))
        self.assertEqual('Pages', c.get('model_name_plural'))
        self.assertEqual('Page', c.get('verbose_name'))
        self.assertEqual('Pages', c.get('verbose_name_plural'))

        # view properties
        self.assertEqual('list', c.get('view'))
        self.assertEqual('', c.get('view_identifier'))
        self.assertEqual('cubane/backend/listing/listing_list.html', c.get('template'))

        # permissions
        self.assertEqual(
            {
                'create': True,
                'delete': True,
                'edit': True,
                'edit_or_view': True,
                'export': True,
                'import': True,
                'clean': False,
                'merge': True,
                'view': True,
                'changes': True
            }, c.get('permissions')
        )

        # urls
        self.assertEqual('cubane.cms.pages.preview', c.get('preview_url'))
        self.assertEqual({
            'create': '/admin/pages/create/',
            'delete': '/admin/pages/delete/',
            'delete_empty_folders': '/admin/pages/delete_empty_folders/',
            'disable': '/admin/pages/disable/',
            'duplicate': '/admin/pages/duplicate/',
            'edit': '/admin/pages/edit/',
            'enable': '/admin/pages/enable/',
            'export': '/admin/pages/export/',
            'get_tree': '/admin/pages/get-tree/',
            'import': '/admin/pages/import/',
            'index': '/admin/pages/?f=html',
            'save_changes': '/admin/pages/save_changes/',
            'merge': '/admin/pages/merge/',
            'changes': '/admin/changelog/?f_content_type=%d' % changelog_content_type.pk,
            'move_to_tree_node': '/admin/pages/move-to-tree-node/',
            'move_tree_node': '/admin/pages/move-tree-node/',
            'selector': '/admin/pages/selector?f=html',
            'seq': '/admin/pages/seq/',
            'tree_node_state': '/admin/pages/tree-node-state/'}, c.get('urls')
        )


    def test_should_list_parent_folder_if_folder_is_empty(self):
        view = FolderView()
        request, c = self._index(view, {
            'folders[]': [self.f1.pk]
        })
        self.assertEqual([self.f1.pk], [f.pk for f in c.get('objects')])


    def test_should_order_by_given_order_even_if_model_is_sortable(self):
        view = PageContentView(Page)
        request, c = self._index(view, {
            'o': 'title',
        })
        self.assertEqual(['Bar', 'Foo'], [p.title for p in c.get('objects')])


    def test_should_order_by_column(self):
        view = FolderView()
        request, c = self._index(view, {
            'o': 'title',
        })
        self.assertEqual(self.FOLDER_NAMES, [p.title for p in c.get('objects')])


    def test_should_order_by_column_reversed(self):
        view = FolderView()
        request, c = self._index(view, {
            'o': 'title',
            'ro': True
        })
        self.assertEqual(list(reversed(self.FOLDER_NAMES)), [p.title for p in c.get('objects')])


    def test_should_assume_page_1_if_page_argument_is_not_integer(self):
        view = FolderView()
        request, c = self._index(view, {
            'page': 'not-a-number'
        })
        self.assertEqual(1, c.get('objects_page'))


    def test_should_not_allow_page_number_below_page_one(self):
        view = FolderView()
        request, c = self._index(view, {
            'page': 0
        })
        self.assertEqual(1, c.get('objects_page'))


    @patch('cubane.views.PAGINATION_MAX_RECORDS', 4)
    def test_should_not_allow_page_number_above_max_pages_with_uneven_split_of_pages(self):
        view = FolderView()
        request, c = self._index(view, {
            'page': 3
        })
        self.assertEqual(2, c.get('objects_page'))


    @patch('cubane.views.PAGINATION_MAX_RECORDS', 3)
    def test_should_not_allow_page_number_above_max_pages_with_even_split_of_pages(self):
        view = FolderView()
        request, c = self._index(view, {
            'page': 3
        })
        self.assertEqual(2, c.get('objects_page'))


    @patch('cubane.views.PAGINATION_MAX_RECORDS', 100)
    def test_should_enfore_min_num_of_pages_to_be_one(self):
        view = PageContentView(BlogPost)
        request, c = self._index(view)
        self.assertEqual(1, c.get('objects_page'))


    @patch('cubane.views.PAGINATION_MAX_RECORDS', 1)
    @patch('cubane.views.PAGINATION_PAGES_WINDOW_SIZE', 1)
    def test_should_present_pagination_pages_links_but_always_first_and_last(self):
        self._assert_pagination_page_links(1, [1, 2, 6])
        self._assert_pagination_page_links(2, [1, 2, 3, 6])
        self._assert_pagination_page_links(3, [1, 2, 3, 4, 6])
        self._assert_pagination_page_links(4, [1, 3, 4, 5, 6])
        self._assert_pagination_page_links(5, [1, 4, 5, 6])
        self._assert_pagination_page_links(6, [1, 5, 6])


    def test_should_return_json_response_if_json_is_specified_as_format(self):
        view = FolderView()
        request, c = self._index(view, {
            'f': 'json'
        })
        self.assertEqual('text/javascript', c['Content-Type'])
        self.assertEqual(self.FOLDER_NAMES, [r.get('title') for r in decode_json(c.content)])


    def test_should_return_json_response_if_ajax_request(self):
        view = FolderView()
        request, c = self._index(view, ajax=True)
        self.assertEqual('text/javascript', c['Content-Type'])
        self.assertEqual(self.FOLDER_NAMES, [r.get('title') for r in decode_json(c.content)])


    def test_should_select_related_field_when_referencing_to_related_field_of_related_model(self):
        columns = Page.Listing.columns
        Page.Listing.columns = ['title', 'image__caption']
        try:
            view = PageContentView(Page)
            request, c = self._index(view)
            self.assertEqual(['image'], c.get('related_fields'))
        finally:
            Page.Listing.columns = columns


    def test_should_select_related_field_when_referencing_to_foreign_key(self):
        columns = Page.Listing.columns
        Page.Listing.columns = ['title', 'image']
        try:
            view = PageContentView(Page)
            request, c = self._index(view)
            self.assertEqual(['image'], c.get('related_fields'))
        finally:
            Page.Listing.columns = columns


    def test_should_return_json_html_response_if_ajax_request_specifying_html_as_output_format(self):
        view = FolderView()
        request, c = self._index(view, {
            'f': 'html'
        }, ajax=True)
        self.assertEqual('text/html; charset=utf-8', c['Content-Type'])
        self.assertIn('<div class="t t-scrollable cubane-listing-list cubane-listing-root"', c.content)


    def _index(self, view, data={}, ajax=False):
        return self.run_view_handler_request(view, self.user, 'index', 'get', '/', data, ajax)


    def _assert_pagination_page_links(self, page, expected_page_list):
        view = FolderView()
        request, c = self._index(view, {
            'page': page
        })
        page_list = c.get('objects_pages_list')
        self.assertEqual(
            expected_page_list,
            page_list,
            'List of pages for page %d is %s but was expected to be %s' % (
                page,
                page_list,
                expected_page_list
            )
        )


class LibModelViewSelectorTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.selector()
    """
    class SelectorView(ModelView):
        model = Media
        selector_model = MediaFolder

        def _get_objects(self, request):
            return self.model.objects.all()


    @classmethod
    def setUpClass(cls):
        super(LibModelViewSelectorTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()

        # folders
        cls.folder1 = MediaFolder.objects.create(title='Foo')
        cls.folder2 = MediaFolder.objects.create(title='Bar')


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewSelectorTestCase, cls).tearDownClass()

        cls.user.delete()
        cls.folder1.delete()
        cls.folder2.delete()


    def test_should_return_selector_html(self):
        view = self.SelectorView()
        request, c = self._selector(view)
        self.assertIn('<div class="cubane-selector-item"', c.content)


    def test_should_return_selector_data_for_ajax_request(self):
        view = self.SelectorView()
        request, c = self._selector(view, ajax=True)
        self.assertEqual('text/javascript', c['Content-Type'])
        self.assertEqual(['Bar', 'Foo'], [c.get('title') for c in decode_json(c.content)])


    def _selector(self, view, data={}, ajax=False):
        return self.run_view_handler_request(view, self.user, 'selector', 'get', '/', data, ajax)


class LibModelViewSeqTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.seq()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewSeqTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()

        # pages
        cls.p1 = Page.objects.create(title='Foo', seq=1)
        cls.p2 = Page.objects.create(title='Bar', seq=2)


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewSeqTestCase, cls).tearDownClass()

        cls.user.delete()
        cls.p1.delete()
        cls.p2.delete()


    def test_should_return_error_if_model_is_not_sortable(self):
        view = MediaView()
        request, c = self._seq(view)
        self.assertEqual(
            {
                'success': False,
                'message': 'Model is not sortable.'
            },
            decode_json(c.content)
        )


    def test_should_return_error_if_argument_is_not_integer_list(self):
        view = PageContentView(Page)
        request, c = self._seq(view, {'item[]': [1, 'not-a-number']})
        self.assertEqual(
            {
                'success': False,
                'message': 'Unable to parse listing id argument as an integer value.'
            },
            decode_json(c.content)
        )


    def test_should_apply_seq_in_order_given(self):
        view = PageContentView(Page)
        request, c = self._seq(view, {'item[]': [self.p2.pk, self.p1.pk]})
        self.assertEqual({'success': True, 'updated': True}, decode_json(c.content))
        self.assertEqual(['Bar', 'Foo'], [p.title for p in Page.objects.all().order_by('seq')])


    def test_should_detect_no_changes(self):
        view = PageContentView(Page)
        request, c = self._seq(view, {'item[]': [self.p1.pk, self.p2.pk]})
        self.assertEqual({'success': True, 'updated': False}, decode_json(c.content))
        self.assertEqual(['Foo', 'Bar'], [p.title for p in Page.objects.all().order_by('seq')])


    def test_should_apply_seq_from_given_order(self):
        view = PageContentView(Page)
        request, c = self._seq(view, {
            'item[]': [self.p2.pk],
            'o': 'title'
        })
        self.assertEqual({'success': True, 'updated': True}, decode_json(c.content))
        self.assertEqual(['Bar', 'Foo'], [p.title for p in Page.objects.all().order_by('seq')])


    def test_should_apply_seq_from_given_order_reversed(self):
        view = PageContentView(Page)
        try:
            self.p1.seq = 10
            self.p2.seq = 11
            self.p1.save()
            self.p2.save()

            request, c = self._seq(view, {
                'item[]': [self.p1.pk],
                'o': 'title',
                'ro': True
            })
            self.assertEqual({'success': True, 'updated': True}, decode_json(c.content))
            self.assertEqual(['Foo', 'Bar'], [p.title for p in Page.objects.all().order_by('seq')])
        finally:
            self.p1.seq = 1
            self.p2.seq = 2
            self.p1.save()
            self.p2.save()

    def _seq(self, view, data={}):
        return self.run_view_handler_request(view, self.user, 'seq', 'post', '/', data, ajax=True)


class LibModelViewFormInitialTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.form_initial()
    """
    def test_should_have_form_initial_method_base_implementation(self):
        view = ModelView()
        self.assertTrue(hasattr(view, 'form_initial'))
        view.form_initial(request=None, initial={}, instance=None, edit=False)


class LibModelView_instance_form_initial(CubaneTestCase):
    """
    cubane.views.ModelView._instance_form_initial()
    """
    def test_should_call_form_initial_method_on_model_instance(self):
        view = ModelView()
        instance = object()

        # should not crash
        view._instance_form_initial(None, {}, instance, False)


    def test_should_ignore_if_method_is_not_defined_by_model_instance(self):
        view = ModelView()
        instance = Mock()
        instance.form_initial = Mock()
        initial = {'foo': 'bar'}
        view._instance_form_initial(None, initial, instance, False)
        instance.form_initial.assert_called_with(None, initial, instance, False)


class LibModelViewBeforeSaveTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.before_save()
    """
    def test_should_have_before_save_method_abstract_implementation(self):
        view = ModelView()
        self.assertTrue(hasattr(view, 'before_save'))
        view.before_save(None, {}, None, False)


class LibModelViewAfterSaveTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.after_save()
    """
    def test_should_have_after_save_method_abstract_implementation(self):
        view = ModelView()
        self.assertTrue(hasattr(view, 'after_save'))
        view.after_save(None, {}, None, False)


class LibModelViewInstanceBeforeSaveTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._instance_before_save()
    """
    def setUp(self):
        self.view = ModelView()
        self.instance = DummyModel()


    def test_should_return_false_if_instance_has_not_got_before_save_method(self):
        self.assertEqual(False, self.view._instance_before_save('request', 'd', self.instance, 'edit'))


    def test_should_return_true_if_instance_has_got_before_save_method(self):
        self.instance.before_save = Mock(return_value=True)
        self.assertEqual(True, self.view._instance_before_save('request', 'd', self.instance, 'edit'))


class LibModelViewInstanceAfterSaveTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._instance_after_save()
    """
    def setUp(self):
        self.view = ModelView()
        self.instance = DummyModel()


    def test_should_return_false_if_instance_has_not_got_after_save_method(self):
        self.assertEqual(False, self.view._instance_after_save('request', 'd', self.instance, 'edit'))


    def test_should_return_true_if_instance_has_got_after_save_method(self):
        self.instance.after_save = Mock(return_value=True)
        self.assertEqual(True, self.view._instance_after_save('request', 'd', self.instance, 'edit'))


class LibModelViewCreateEditTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.create_edit()
    """
    def setUp(self):
        self.view = ModelView()
        self.view._edit = Mock(return_value='edit')
        self.view._view = Mock(return_value='view')
        self.view._create = Mock(return_value='create')


    def test_should_return_edit_if_edit_true_and_request_post(self):
        request = Mock()
        request.method = 'POST'
        self.assertEqual('edit', self.view.create_edit(request, 1, True))


    def test_should_return_view_if_edit_true_and_request_not_post(self):
        self.assertEqual('view', self.view.create_edit(Mock(), 1, True))


    def test_should_return_create_if_edit_false(self):
        self.assertEqual('create', self.view.create_edit(Mock(), 1))


class LibModelViewCreateEditHandlerTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._create_edit()
    """
    class FormWithoutConfigure(forms.Form):
        pass


    @classmethod
    def setUpClass(cls):
        super(LibModelViewCreateEditHandlerTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()

        # pages
        cls.p1 = Page.objects.create(title='Foo', seq=1)
        cls.p2 = Page.objects.create(title='Bar', seq=2, parent=cls.p1)


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewCreateEditHandlerTestCase, cls).tearDownClass()

        cls.user.delete()
        cls.p2.delete()
        cls.p1.delete()


    def setUp(self):
        self.view = PageContentView(Page)


    def test_should_redirect_to_index_page_if_canceled(self):
        request, c = self._create_edit(self.view, data={'cubane_form_cancel': '1'})
        self.assertIsRedirect(c, '/admin/pages/')


    def test_should_raise_error_for_missing_pk_in_edit_mode(self):
        with self.assertRaisesRegexp(Http404, 'Missing argument \'pk\''):
            self._create_edit(self.view, kwargs={'edit': True})


    def test_should_raise_error_for_missing_pk_in_duplicate_mode(self):
        with self.assertRaisesRegexp(Http404, 'Missing argument \'pk\''):
            self._create_edit(self.view, handler_name='duplicate')


    def test_should_load_single_instance_if_view_is_configured_with_single_instance(self):
        view = SettingsView()
        request, c = self._create_edit(view)
        self.assertIsInstance(c.get('object'), Settings)


    def test_should_load_object_by_given_pk_via_GET_argument(self):
        request, c = self._create_edit(self.view, path='/?pk=%d' % self.p1.pk, kwargs={'edit': True})
        self.assertEqual(self.p1, c.get('object'))


    def test_should_load_object_by_given_pk_via_URL_pattern(self):
        request, c = self._create_edit(self.view, kwargs={'edit': True, 'pk': self.p1.pk})
        self.assertEqual(self.p1, c.get('object'))


    def test_should_return_object_as_json_if_ajax_GET_request(self):
        request, c = self._create_edit(self.view, method='get', kwargs={'edit': True, 'pk': self.p1.pk}, ajax=True)
        self.assertEqual('text/javascript', c.get('Content-Type'))
        json = decode_json(c.content)
        self.assertEqual('Foo', json.get('title'))


    def test_should_raise_error_if_form_cannot_be_configured(self):
        view = PageContentView(Page)
        view.form = self.FormWithoutConfigure
        with self.assertRaisesRegexp(NotImplementedError, 'The form \w+ must implement configure'):
            self._create_edit(view)


    def test_should_create_new_object_if_not_in_edit_mode(self):
        request, c = self._create_edit(self.view)
        self.assertIsNone(c.get('object').pk)


    def test_should_configure_backend_section_if_available(self):
        from cubane.testapp.urls import backend
        self.view = backend.get_view_for_model(TestDirectoryContentWithBackendSections)
        self.view.model_attr_value = TestDirectoryContentWithBackendSections.BACKEND_SECTION_B
        try:
            request, c = self._create_edit(self.view, method='get')
            self.assertEqual(
                TestDirectoryContentWithBackendSections.BACKEND_SECTION_B,
                c.get('object').backend_section
            )
        finally:
            del self.view.model_attr_value


    def test_should_set_parent_to_the_same_parent_as_original_for_duplication(self):
        request, c = self._create_edit(self.view, handler_name='duplicate', method='get', kwargs={'pk': self.p2.pk})
        self.assertEqual(self.p1, c.get('form').initial.get('parent'))


    def test_submit_should_save_model(self):
        p = Page.objects.create(title='Test')
        try:
            request, c = self._create_edit(self.view, method='post', kwargs={'edit': True, 'pk': p.pk}, data={
                'title': 'Test 2',
                'slug': 'test-2',
                '_cubane_instance_checksum': p.get_checksum(),
                'template': 'testapp/page.html'
            })
            self.assertIsRedirect(c, '/admin/pages/')
            p = Page.objects.get(pk=p.pk)
            self.assertEqual('Test 2', p.title)
            self.assertEqual('test-2', p.slug)
        finally:
            p.delete()


    def test_should_maintain_updated_by_when_editing_instance(self):
        p = Page.objects.create(title='Test')
        try:
            request, c = self._create_edit(self.view, method='post', kwargs={'edit': True, 'pk': p.pk}, data={
                'title': 'Test 2',
                'slug': 'test-2',
                '_cubane_instance_checksum': p.get_checksum(),
                'template': 'testapp/page.html'
            })
            self.assertIsRedirect(c, '/admin/pages/')
            p = Page.objects.get(pk=p.pk)
            self.assertEqual('admin', p.updated_by.username)
            self.assertIsNone(p.created_by)
        finally:
            p.delete()


    def test_should_maintain_created_by_when_creating_instance(self):
        p = None
        try:
            request, c = self._create_edit(self.view, method='post', data={
                'title': 'Test',
                'slug': 'test',
                'template': 'testapp/page.html'
            })
            self.assertIsRedirect(c, '/admin/pages/')
            p = Page.objects.get(slug='test')
            self.assertEqual('admin', p.created_by.username)
            self.assertIsNone(p.updated_by)
        finally:
            if p:
                p.delete()


    def test_should_duplicate_instance(self):
        p = None
        try:
            # create duplication handler
            def on_duplicated(page):
                page.disabled = False
            Page.on_duplicated = on_duplicated

            # submit form (duplicate)
            request, c = self._create_edit(self.view, handler_name='duplicate', method='post', kwargs={'pk': self.p1.pk}, data={
                'title': 'Test',
                'slug': 'test',
                'template': 'testapp/page.html',
                '_cubane_instance_checksum': self.p1.get_checksum()
            })
            self.assertIsRedirect(c, '/admin/pages/')

            # new object should exist
            p = Page.objects.get(slug='test')

            # previous object should also exist
            p_old = Page.objects.get(pk=self.p1.pk)

            # they should be seperate objects
            self.assertNotEqual(p.pk, p_old.pk)

            # duplication handler should have disabled the new page
            self.assertFalse(p.disabled)
        finally:
            if hasattr(Page, 'on_duplicate'):
                delattr(Page, 'on_duplicate')
            if p:
                p.delete()


    def test_submit_should_yield_form_errors(self):
        request, c = self._create_edit(self.view, method='post', kwargs={'edit': True, 'pk': self.p1.pk}, data={
            '_cubane_instance_checksum': self.p1.get_checksum(),
            'template': 'testapp/page.html'
        })
        self.assertFormFieldError(c.get('form'), 'title', 'This field is required.')


    def test_submit_should_yield_error_if_checksum_does_not_match(self):
        p = Page.objects.create(title='Test')
        try:
            checksum = p.get_checksum()

            # in-between we have someone else changing the instance,
            # which then changes the checksum...
            p.title = 'Test Changed'
            p.save()

            # now we edit the page with the checksum of before
            request, c = self._create_edit(self.view, method='post', kwargs={'edit': True, 'pk': p.pk}, data={
                'title': 'Test 2',
                'slug': 'test-2',
                '_cubane_instance_checksum': checksum,
                'template': 'testapp/page.html'
            })

            # should not save changes, since checksums do not match
            self.assertFormFieldError(c.get('form'), '__all__', 'This entity was modified while you were editing it.')
        finally:
            p.delete()


    def test_should_yield_create_json_information_in_dialog_window_context(self):
        p = None
        try:
            request, c = self._create_edit(self.view, path='/?create=true', method='post', data={
                'title': 'Test',
                'slug': 'test',
                'template': 'testapp/page.html'
            })
            p = Page.objects.get(slug='test')
            self.assertEqual({
                'dialog_created_id': p.pk,
                'dialog_created_title': 'Test',
                'preview_url': 'cubane.cms.pages.preview'
            }, c)
        finally:
            if p: p.delete()


    def test_should_yield_edit_json_information_in_dialog_window_context(self):
        p = Page.objects.create(title='Test')
        try:
            request, c = self._create_edit(self.view, path='/?edit=true', method='post', kwargs={'edit': True, 'pk': p.pk}, data={
                'title': 'Test 2',
                'slug': 'test-2',
                'template': 'testapp/page.html',
                '_cubane_instance_checksum': p.get_checksum()
            })
            self.assertEqual({
                'dialog_edited_id': p.pk,
                'preview_url': 'cubane.cms.pages.preview'
            }, c)
        finally:
            p.delete()


    def _create_edit(self, view, path='/', method='post', kwargs={}, data={}, ajax=False, handler_name='create_edit'):
        return self.run_view_handler_request(view, self.user, handler_name, method, path, data, ajax, [], kwargs)


class LibModelViewredirect_to_index_orTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.redirect_to_index_or()
    """
    def _redirect(self, request, name, instance=None, active_tab=None):
        return name


    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel
        self.view._redirect = self._redirect
        self.request = Mock()


    def test_should_redirect_to_instance_with_active_tab_when_active_tab_is_not_equal_zero(self):
        self.request.POST = {'cubane_save_and_continue': 1}
        self.assertEqual('name', self.view.redirect_to_index_or(self.request, 'name', 'instance'))


    def test_should_redirect_to_index_when_active_tab_is_equal_to_zero(self):
        self.request.POST = {}
        self.assertEqual('index', self.view.redirect_to_index_or(self.request, 'name', 'instance'))


class LibModelViewDeleteTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.delete()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewDeleteTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewDeleteTestCase, cls).tearDownClass()
        cls.user.delete()


    def setUp(self):
        self.view = PageContentView(Page)


    def test_should_delete_instance_by_given_pk(self):
        p = Page.objects.create(title='Foo')
        try:
            request, c = self._delete(self.view, kwargs={'pk': p.pk})
            self.assertIsRedirect(c, '/admin/pages/')
            self.assertEqual(0, Page.objects.filter(pk=p.pk).count())
        finally:
            [p.delete() for p in Page.objects.filter(pk=p.pk)]


    def test_should_delete_multiple_instances_by_given_pk_list(self):
        p1 = Page.objects.create(title='Foo')
        p2 = Page.objects.create(title='Bar')
        try:
            request, c = self._delete(self.view, data={'pks[]': [p1.pk, p2.pk]})
            self.assertIsRedirect(c, '/admin/pages/')
            self.assertEqual(0, Page.objects.filter(pk__in=[p1.pk, p2.pk]).count())
        finally:
            [p.delete() for p in Page.objects.filter(pk__in=[p1.pk, p2.pk])]


    def test_should_delete_instance_by_pk_as_post_argument(self):
        p = Page.objects.create(title='Foo')
        try:
            request, c = self._delete(self.view, data={'pk': p.pk})
            self.assertIsRedirect(c, '/admin/pages/')
            self.assertEqual(0, Page.objects.filter(pk=p.pk).count())
        finally:
            [p.delete() for p in Page.objects.filter(pk=p.pk)]


    def test_should_raise_404_if_single_instance_not_found(self):
        with self.assertRaisesRegexp(Http404, 'Unknown primary key'):
            self._delete(self.view, kwargs={'pk': -1})


    def test_should_delete_sub_folders_if_instance_if_folder_model(self):
        view = FolderView()
        f1 = MediaFolder.objects.create(title='A')
        f2 = MediaFolder.objects.create(title='A.1', parent=f1)
        f3 = MediaFolder.objects.create(title='A.2', parent=f1)
        f4 = MediaFolder.objects.create(title='A.1.1', parent=f2)
        try:
            # delete root should delete all sub-folders
            self._delete(view, kwargs={'pk': f2.pk})
            self.assertEqual(2, MediaFolder.objects.count())
        finally:
            [f.delete() for f in MediaFolder.objects.all()]


    def test_should_ignore_pks_not_found_for_list_of_pks(self):
        p1 = Page.objects.create(title='Foo')
        p2 = Page.objects.create(title='Bar')
        try:
            request, c = self._delete(self.view, data={'pks[]': [p1.pk, -1]})
            self.assertIsRedirect(c, '/admin/pages/')
            self.assertEqual(1, Page.objects.filter(pk__in=[p1.pk, p2.pk]).count())
        finally:
            [p.delete() for p in Page.objects.filter(pk__in=[p1.pk, p2.pk])]


    def test_ajax_request_deleting_single_instance_should_return_json(self):
        p = Page.objects.create(title='Foo')
        try:
            request, c = self._delete(self.view, kwargs={'pk': p.pk}, ajax=True)
            content = decode_json(c.content)
            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual('Page <em>Foo</em> deleted successfully.', content.get('message'))
            self.assertTrue(content.get('success'))
            self.assertEqual(0, Page.objects.filter(pk=p.pk).count())
        finally:
            [p.delete() for p in Page.objects.filter(pk=p.pk)]


    def test_ajax_request_deleting_multiple_instances_should_return_json(self):
        p1 = Page.objects.create(title='Foo')
        p2 = Page.objects.create(title='Bar')
        try:
            request, c = self._delete(self.view, data={'pks[]': [p1.pk, p2.pk]}, ajax=True)
            content = decode_json(c.content)
            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual('2 Pages deleted successfully.', content.get('message'))
            self.assertTrue(content.get('success'))
            self.assertEqual(0, Page.objects.filter(pk__in=[p1.pk, p2.pk]).count())
        finally:
            [p.delete() for p in Page.objects.filter(pk__in=[p1.pk, p2.pk])]


    def _delete(self, view, path='/', method='post', kwargs={}, data={}, ajax=False, handler_name='delete'):
        return self.run_view_handler_request(view, self.user, handler_name, method, path, data, ajax, [], kwargs)


class LibModelViewDisableTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.disable()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewDisableTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewDisableTestCase, cls).tearDownClass()
        cls.user.delete()


    def setUp(self):
        self.view = PageContentView(Page)


    def test_should_disable_single_instance_by_pk(self):
        p = Page.objects.create(title='Foo')
        try:
            request, c = self._disable(self.view, kwargs={'pk': p.pk})
            self.assertIsRedirect(c, '/admin/pages/')

            p = Page.objects.get(pk=p.pk)
            self.assertTrue(p.disabled)
        finally:
            p.delete()


    def test_should_disable_multiple_instances_by_pk_list(self):
        p1 = Page.objects.create(title='Foo')
        p2 = Page.objects.create(title='Bar')
        try:
            request, c = self._disable(self.view, data={'pks[]': [p1.pk, p2.pk]})
            self.assertIsRedirect(c, '/admin/pages/')

            p1 = Page.objects.get(pk=p1.pk)
            p2 = Page.objects.get(pk=p2.pk)
            self.assertTrue(p1.disabled)
            self.assertTrue(p2.disabled)
        finally:
            p1.delete()
            p2.delete()


    def test_should_raise_404_if_single_instance_not_found(self):
        with self.assertRaisesRegexp(Http404, 'Unknown primary key'):
            self._disable(self.view, kwargs={'pk': -1})


    def test_should_ignore_unknown_pks_from_list(self):
        p = Page.objects.create(title='Foo')
        try:
            request, c = self._disable(self.view, data={'pks[]': [p.pk, -1]})
            self.assertIsRedirect(c, '/admin/pages/')

            p = Page.objects.get(pk=p.pk)
            self.assertTrue(p.disabled)
        finally:
            p.delete()


    def test_ajax_request_disabling_single_instance_should_return_json(self):
        p = Page.objects.create(title='Foo')
        try:
            request, c = self._disable(self.view, kwargs={'pk': p.pk}, ajax=True)
            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual({
                'message': 'Page <em>Foo</em> disabled successfully.',
                'success': True
            }, decode_json(c.content))

            p = Page.objects.get(pk=p.pk)
            self.assertTrue(p.disabled)
        finally:
            p.delete()


    def test_ajax_request_disabling_multiple_instances_should_return_json(self):
        p1 = Page.objects.create(title='Foo')
        p2 = Page.objects.create(title='Bar')
        try:
            request, c = self._disable(self.view, data={'pks[]': [p1.pk, p2.pk]}, ajax=True)
            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual({
                'message': '2 Pages disabled successfully.',
                'success': True
            }, decode_json(c.content))

            p1 = Page.objects.get(pk=p1.pk)
            p2 = Page.objects.get(pk=p2.pk)
            self.assertTrue(p1.disabled)
            self.assertTrue(p2.disabled)
        finally:
            p1.delete()
            p2.delete()


    def _disable(self, view, path='/', method='post', kwargs={}, data={}, ajax=False, handler_name='disable'):
        return self.run_view_handler_request(view, self.user, handler_name, method, path, data, ajax, [], kwargs)


class LibModelViewEnableTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.enable()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewEnableTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewEnableTestCase, cls).tearDownClass()
        cls.user.delete()


    def setUp(self):
        self.view = PageContentView(Page)


    def test_should_enable_single_instance_by_pk(self):
        p = Page.objects.create(title='Foo', disabled=True)
        try:
            request, c = self._enable(self.view, kwargs={'pk': p.pk})
            self.assertIsRedirect(c, '/admin/pages/')

            p = Page.objects.get(pk=p.pk)
            self.assertFalse(p.disabled)
        finally:
            p.delete()


    def test_should_enable_multiple_instances_by_pk_list(self):
        p1 = Page.objects.create(title='Foo', disabled=True)
        p2 = Page.objects.create(title='Bar', disabled=True)
        try:
            request, c = self._enable(self.view, data={'pks[]': [p1.pk, p2.pk]})
            self.assertIsRedirect(c, '/admin/pages/')

            p1 = Page.objects.get(pk=p1.pk)
            p2 = Page.objects.get(pk=p2.pk)
            self.assertFalse(p1.disabled)
            self.assertFalse(p2.disabled)
        finally:
            p1.delete()
            p2.delete()


    def test_should_raise_404_if_single_instance_not_found(self):
        with self.assertRaisesRegexp(Http404, 'Unknown primary key'):
            self._enable(self.view, kwargs={'pk': -1})


    def test_should_ignore_unknown_pks_from_list(self):
        p = Page.objects.create(title='Foo', disabled=True)
        try:
            request, c = self._enable(self.view, data={'pks[]': [p.pk, -1]})
            self.assertIsRedirect(c, '/admin/pages/')

            p = Page.objects.get(pk=p.pk)
            self.assertFalse(p.disabled)
        finally:
            p.delete()


    def test_ajax_request_enabling_single_instance_should_return_json(self):
        p = Page.objects.create(title='Foo', disabled=True)
        try:
            request, c = self._enable(self.view, kwargs={'pk': p.pk}, ajax=True)
            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual({
                'message': 'Page <em>Foo</em> enabled successfully.',
                'success': True
            }, decode_json(c.content))

            p = Page.objects.get(pk=p.pk)
            self.assertFalse(p.disabled)
        finally:
            p.delete()


    def test_ajax_request_enabling_multiple_instances_should_return_json(self):
        p1 = Page.objects.create(title='Foo', disabled=True)
        p2 = Page.objects.create(title='Bar', disabled=True)
        try:
            request, c = self._enable(self.view, data={'pks[]': [p1.pk, p2.pk]}, ajax=True)
            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual({
                'message': '2 Pages enabled successfully.',
                'success': True
            }, decode_json(c.content))

            p1 = Page.objects.get(pk=p1.pk)
            p2 = Page.objects.get(pk=p2.pk)
            self.assertFalse(p1.disabled)
            self.assertFalse(p2.disabled)
        finally:
            p1.delete()
            p2.delete()


    def _enable(self, view, path='/', method='post', kwargs={}, data={}, ajax=False, handler_name='enable'):
        return self.run_view_handler_request(view, self.user, handler_name, method, path, data, ajax, [], kwargs)


class LibModelViewDataImportExportBase(CubaneTestCase):
    CSV_DATA = '\r\n'.join([
        '"id","title","enabled","enabled_display","address_type","is_company"',
        '"1","Foo","True","yes","1","True"',
        '"2","Bar","False","no","2","False"'
    ]) + '\r\n'


    @classmethod
    def setUpClass(cls):
        super(LibModelViewDataImportExportBase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewDataImportExportBase, cls).tearDownClass()
        cls.user.delete()


    def setUp(self):
        self.view = ContentView(TestModelImportExport)


class LibModelViewDataImportTestCase(LibModelViewDataImportExportBase):
    """
    cubane.views.ModelView.data_import()
    """
    def test_should_present_upload_form(self):
        request, c = self._import(self.view, method='get')
        self.assertIn('type="file"', c.content)


    def test_should_import_from_csv_file(self):
        path = tempfile.gettempdir()
        filename = os.path.join(path, 'import.csv')
        f = open(filename, 'w')
        f.write('\r\n'.join([
            '"id","title","enabled","enabled_display","address_type","is_company"',
            '"1","Foo","True","yes","1","True"',
            '"2","Bar","False","no","2","False"'
        ]) + '\r\n')
        f.close()

        f = open(filename, 'r')
        try:
            request, c = self._import(self.view, data={'csvfile': f, 'encoding': 'utf_8'})

            self.assertIsRedirect(c, '/admin/test-model-import-export/')
            self.assertEqual(2, TestModelImportExport.objects.count())

            p1 = TestModelImportExport.objects.get(title='Foo')
            p2 = TestModelImportExport.objects.get(title='Bar')

            self.assertTrue(p1.enabled)
            self.assertFalse(p2.enabled)
            self.assertEqual(TestModelImportExport.ADDRESS_TYPE_BUSINESS, p1.address_type)
            self.assertEqual(TestModelImportExport.ADDRESS_TYPE_HOME, p2.address_type)
        finally:
            f.close()
            os.unlink(filename)
            [p.delete() for p in TestModelImportExport.objects.all()]


    def _import(self, view, path='/', method='post', kwargs={}, data={}, ajax=False, handler_name='data_import'):
        return self.run_view_handler_request(view, self.user, handler_name, method, path, data, ajax, [], kwargs)


class LibModelViewDataExportTestCase(LibModelViewDataImportExportBase):
    """
    cubane.views.ModelView.data_export()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewDataExportTestCase, cls).setUpClass()

        # items to export
        cls.p1 = TestModelImportExport.objects.create(title='Foo', enabled=True, address_type=TestModelImportExport.ADDRESS_TYPE_BUSINESS)
        cls.p2 = TestModelImportExport.objects.create(title='Bar', enabled=False, address_type=TestModelImportExport.ADDRESS_TYPE_HOME)


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewDataExportTestCase, cls).tearDownClass()
        cls.p1.delete()
        cls.p2.delete()


    def test_should_export_all_instances_if_no_pks_are_given(self):
        request, c = self._export(self.view)
        self.assertEqual('text/csv', c['Content-Type'])
        self.assertEqual('\ufeff' + self.CSV_DATA, c.content.decode('utf-8'))


    def test_should_export_only_referenced_instances_that_exist_if_pks_list_is_given(self):
        request, c = self._export(self.view, data={'pks[]': [self.p1.pk, -1]})
        self.assertEqual('text/csv', c['Content-Type'])
        self.assertEqual('\ufeff' + '\r\n'.join([
            '"id","title","enabled","enabled_display","address_type","is_company"',
            '"1","Foo","True","yes","1","True"',
        ]) + '\r\n', c.content.decode('utf-8'))



    def _export(self, view, path='/', method='post', kwargs={}, data={}, ajax=False, handler_name='data_export'):
        return self.run_view_handler_request(view, self.user, handler_name, method, path, data, ajax, [], kwargs)


class LibModelViewGetFolderModelTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_folder_model()
    """
    def test_should_return_none(self):
        view = ModelView()
        self.assertEqual(None, view.get_folder_model())


    def test_should_return_folder_model(self):
        view = ModelView()
        view.folder_model = 'folder_model'
        self.assertEqual('folder_model', view.get_folder_model())


class LibModelViewHasFoldersTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.has_folders()
    """
    def setUp(self):
        self.request = DummyRequest()
        self.request.user = User(is_staff=True, is_superuser=True)


    def test_should_return_true(self):
        view = ModelView()
        view.folder_model = MediaFolder
        self.assertEqual(True, view.has_folders(self.request))


    def test_should_return_false(self):
        view = ModelView()
        self.assertEqual(False, view.has_folders(self.request))


class LibModelViewGetFolderURLTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_folder_url()
    """
    def test_should_return_empty_string(self):
        view = ModelView()
        self.assertEqual('', view.get_folder_url('request', 'name'))


    def test_should_return_backend_url_form_model(self):
        view = ModelView()
        view.folder_model = 'folder_model'

        request = DummyRequest()
        request.backend = Mock(methods=['get_url_for_model'])
        request.backend.get_url_for_model.return_value = 'mocked_backend_url'

        self.assertEqual('mocked_backend_url', view.get_folder_url(request, 'name'))


class LibModelViewGetFolderModelNameSingularTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_folder_model_name_singular()
    """
    def test_should_return_empty_string(self):
        view = ModelView()
        self.assertEqual('', view.get_folder_model_name_singular())


    def test_should_return_folder_model_name_singular(self):
        view = ModelView()
        view.folder_model = Mock()
        view.folder_model._meta = Mock()
        view.folder_model._meta.verbose_name = 'verbose_name_singular'

        self.assertEqual('verbose_name_singular', view.get_folder_model_name_singular())


class LibModelViewGetFolderModelNameTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_folder_model_name()
    """
    def test_should_return_empty_string(self):
        view = ModelView()
        self.assertEqual('', view.get_folder_model_name())


    def test_should_return_folder_name_plural(self):
        view = ModelView()
        view.folder_model = Mock()
        view.folder_model._meta = Mock()
        view.folder_model._meta.verbose_name_plural = 'verbose_name_plural'

        self.assertEqual('verbose_name_plural', view.get_folder_model_name())


class LibModelViewIsLeafFolderViewTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.is_leaf_folder_view()
    """
    def setUp(self):
        self.view = MediaView()
        self.m1 = Media.objects.create()
        self.m2 = Media.objects.create()
        self.request = DummyRequest()
        self.request.user = User(is_staff=True, is_superuser=True)


    def tesarDown(self):
        self.m1.delete()
        self.m2.delete()


    def test_should_return_true_if_view_has_no_folders(self):
        self.view.folder_model = None
        self.assertTrue(self.view.is_leaf_folder_view(self.request, [1], 2))


    def test_should_return_true_if_no_folder_is_given(self):
        self.assertTrue(self.view.is_leaf_folder_view(self.request, None, 2))


    def test_should_return_true_if_empty_folder_list_is_given(self):
        self.assertTrue(self.view.is_leaf_folder_view(self.request, [], 2))


    def test_should_return_false_if_multiple_folders_are_given(self):
        self.assertFalse(self.view.is_leaf_folder_view(self.request, [1, 2], 2))


class LibModelViewGetPseudoRootTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_pseudo_root()
    """
    def test_should_return_pseudo_root(self):
        view = ModelView()
        view.folder_model = Mock()
        root = view.get_pseudo_root('children', [-1, 1, 2])

        self.assertIsInstance(root.model, Mock)
        self.assertEqual(-1, root.id)
        self.assertEqual('/', root.title)
        self.assertEqual(None, root.parent)
        self.assertEqual('children', root.children)
        self.assertEqual(True, root.is_open_folder)


class LibModelViewGetFoldersTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_folders()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewGetFoldersTestCase, cls).setUpClass()

        # folders (alphabetically)
        cls.f1 = MediaFolder.objects.create(title='A')
        cls.f2 = MediaFolder.objects.create(title='A.1', parent=cls.f1)
        cls.f3 = MediaFolder.objects.create(title='A.2', parent=cls.f1)
        cls.f4 = MediaFolder.objects.create(title='B')

        # product categories (seq)
        cls.c1 = Category.objects.create(title='A', slug='a', seq=2)
        cls.c2 = Category.objects.create(title='A.1', slug='a1', parent=cls.c1, seq=2)
        cls.c3 = Category.objects.create(title='A.2', slug='a2', parent=cls.c1, seq=1)
        cls.c4 = Category.objects.create(title='B', slug='b', seq=1)


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewGetFoldersTestCase, cls).tearDownClass()

        # folders
        cls.f1.delete()
        cls.f2.delete()
        cls.f3.delete()
        cls.f4.delete()

        # categories
        cls.c1.delete()
        cls.c2.delete()
        cls.c3.delete()
        cls.c4.delete()


    def setUp(self):
        self.request = self.make_request('get', '/', user=User(is_staff=True, is_superuser=True))


    def test_should_retun_empty_list_if_view_does_not_handle_folders(self):
        view = PageContentView(Page)
        self.assertEqual([], view.get_folders(self.request))


    def test_should_return_root_folders_and_children_sorted_alphabetically(self):
        view = MediaView()
        folders = view.get_folders(self.request)
        self.assertEqual(
            [('/', [('A', ['A.1', 'A.2']), 'B'])],
            self._tree_repr(folders)
        )


    def test_should_sort_alphabetically_taking_uppercase_and_lowercase_into_consideration(self):
        f5 = MediaFolder.objects.create(title='a')
        f6 = MediaFolder.objects.create(title='b')
        view = MediaView()
        try:
            folders = view.get_folders(self.request)
            rep = self._tree_repr(folders)

            a = [('/', [('A', ['A.1', 'A.2']), 'a', 'B', 'b'])]
            b = [('/', ['a', ('A', ['A.1', 'A.2']), 'b', 'B'])]

            self.assertTrue(
                rep == a or
                rep == b,
                'Was \'%s\' but should be \'%s\' OR \'%s\'.' % (
                    rep,
                    a,
                    b
                )
            )
        finally:
            f5.delete()
            f6.delete()


    def test_should_return_root_folders_and_children_sorted_by_seq(self):
        view = ProductView('cubane.ishop.products', with_folders=True)
        folders = view.get_folders(self.request)
        self.assertEqual(
            [('/', ['B', ('A', ['A.2', 'A.1'])])],
            self._tree_repr(folders)
        )


    def _tree_repr(self, nodes):
        def _tree_node(node):
            if node.children:
                return (node.title, self._tree_repr(node.children))
            else:
                return node.title
        return [_tree_node(node) for node in nodes]


class LibModelViewGetFolderResponseTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_folder_response()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_return_to_json_response_if_is_json(self):
        self.view._is_json = Mock(return_value=True)
        self.assertEqual(HttpResponse, type(self.view._get_folder_response(self.request)))


    def test_should_return_list_if_is_not_json(self):
        self.assertEqual(
            {'folders': [], 'folder_ids': [-1]},
            self.view._get_folder_response(self.request)
        )


class LibModelView_setTreeNodeStateTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._set_tree_node_state()
    """
    def setUp(self):
        self.view = ModelView()
        self.view.model = DummyModel()
        self.request = self.get_view_handler_request(self.view, None, 'dummy', 'get', '/dummy')


    def test_should_append_folder_to_list_of_folders_and_set_open_folders_to_session(self):
        self.view._get_open_folders = Mock(return_value=[1, 3])
        self.view._set_tree_node_state(self.request, 2, True)
        self.assertEqual([1, 3, 2], self.request.session['folder_ids_DummyModel'])


    def test_should_remove_folder_from_folders_and_set_open_folders_to_session(self):
        self.view._get_open_folders = Mock(return_value=[1, 2, 3])
        self.view._set_tree_node_state(self.request, 2, False)
        self.assertEqual([1, 3], self.request.session['folder_ids_DummyModel'])


class LibIsRootNodeTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._is_root_node()
    """
    def setUp(self):
        self.view = ModelView()
        self.node = Mock()


    def test_should_return_true_if_node_none(self):
        self.assertEqual(True, self.view._is_root_node(None))


    def test_should_return_true_if_node_minus_one(self):
        self.node.id  = -1
        self.assertEqual(True, self.view._is_root_node(self.node))


    def test_should_return_false(self):
        self.node.id = 5
        self.assertEqual(False, self.view._is_root_node(self.node))


class LibIsSameNodeTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._is_same_node()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_true_if_both_none(self):
        self.assertEqual(True, self.view._is_same_node(None, None))


    def test_should_return_if_both_presented(self):
        a = Mock()
        a.id = 2
        b = Mock()
        b.id = 2

        self.assertEqual(True, self.view._is_same_node(a, b))


    def test_should_return_false(self):
        a = Mock()
        a.id = 5
        b = Mock()
        b.id = 2

        self.assertEqual(False, self.view._is_same_node(a, b))


class LibIsChildNodeOfTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._is_child_node_of()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_true(self):
        a = Mock()
        a.id = -1
        b = Mock()
        b.id = 1
        c = Mock()
        c.id = 2

        c.parent = b
        c.parent.parent = a
        c.parent.parent.parent = None

        self.assertEqual(True, self.view._is_child_node_of(c, a))


    def test_should_return_false(self):
        a = Mock()
        a.id = -1
        b = Mock()
        b.id = 1
        c = Mock()
        c.id = 2

        b.parent = a
        b.parent.parent = None
        c.parent = 5

        self.assertEqual(False, self.view._is_child_node_of(b, c))


class LibCanMoveNodeTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._can_move_node()
    """
    def setUp(self):
        self.view = ModelView()


    def test_should_return_true(self):
        a = Mock()
        a.id = -1
        b = Mock()
        b.id = 1
        c = Mock()
        c.id = 2

        c.parent = b
        c.parent.parent = a
        c.parent.parent.parent = None

        self.assertEqual(True, self.view._can_move_node(c, a))


    def test_should_return_false(self):
        a = Mock()
        a.id = -1
        b = Mock()
        b.id = 1
        c = Mock()
        c.id = 2

        c.parent = b
        c.parent.parent = a
        c.parent.parent.parent = None

        self.assertEqual(False, self.view._can_move_node(a, b))


class LibModelViewtree_node_stateTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.tree_node_state()
    """
    def test_should_return_success_true_json_response(self):
        view = ModelView()
        view.model = DummyModel()
        request = self.get_view_handler_request(view, None, 'dummy', 'get', '/dummy')

        self.assertEqual('{"success":true}', undecorated(view.tree_node_state)(view, request).content)


class LibModelViewMoveTreeNodeTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.move_tree_node()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewMoveTreeNodeTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewMoveTreeNodeTestCase, cls).tearDownClass()
        cls.user.delete()


    def setUp(self):
        self.view = MediaView()
        self.f1 = MediaFolder.objects.create(title='A')
        self.f2 = MediaFolder.objects.create(title='A.1', parent=self.f1)
        self.f3 = MediaFolder.objects.create(title='A.2', parent=self.f1)
        self.f4 = MediaFolder.objects.create(title='B')


    def tearDown(self):
        self.f1.delete()
        self.f2.delete()
        self.f3.delete()
        self.f4.delete()


    def test_should_move_folder_and_children_into_target_folder(self):
        c, ids = self._move_tree_node({'src[]': [self.f1.pk], 'dst': self.f4.pk})
        self.assertEqual(
            [
                '/', [
                    'B', [
                        'A', [
                            'A.1',
                            'A.2'
                        ]
                    ]
                ]
            ],
            self._get_folder_titles(c.get('folders'))
        )
        self.assertEqual([self.f4.pk], ids)


    def test_should_move_folder_to_root_node(self):
        c, ids = self._move_tree_node({'src[]': [self.f3.pk], 'dst': -1})
        self.assertEqual(
            [
                '/', [
                    'A', [
                        'A.1'
                    ],
                    'A.2',
                    'B'
                ]
            ],
            self._get_folder_titles(c.get('folders'))
        )
        self.assertEqual([], ids)


    def _move_tree_node(self, data):
        request = self.get_view_handler_request(self.view, self.user, 'move_tree_node', 'post', '/', data)
        response = undecorated(self.view.move_tree_node)(self.view, request)
        open_folders = self.view._get_open_folders(request)
        return response, open_folders


    def _get_folder_titles(self, folders):
        titles = []
        for folder in folders:
            titles.append(folder.title)
            if folder.children:
                titles.append(self._get_folder_titles(folder.children))
        return titles


class LibModelViewMoveToTreeNodeTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.move_to_tree_node()
    """
    @classmethod
    def setUpClass(cls):
        super(LibModelViewMoveToTreeNodeTestCase, cls).setUpClass()

        # user
        cls.user = User.objects.create_user('admin', 'password')
        cls.user.is_staff = True
        cls.user.is_superuser = True
        cls.user.save()


    @classmethod
    def tearDownClass(cls):
        super(LibModelViewMoveToTreeNodeTestCase, cls).tearDownClass()
        cls.user.delete()


    def setUp(self):
        self.view = ImageView()
        self.folder = MediaFolder.objects.create(title='A')


    def tearDown(self):
        self.folder.delete()


    def test_should_move_media_to_folder(self):
        m1 = Media.objects.create(caption='Foo')
        m2 = Media.objects.create(caption='Bar')
        try:
            c, ids = self._move_to_tree_node(self.view, {'src[]': [m1.pk, m2.pk], 'dst': self.folder.pk})

            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual({'success': True}, decode_json(c.content))
            self.assertEqual([], ids)

            m1 = Media.objects.get(caption='Foo')
            m2 = Media.objects.get(caption='Bar')
            self.assertEqual(self.folder.pk, m1.parent_id)
            self.assertEqual(self.folder.pk, m2.parent_id)
        finally:
            m1.delete()
            m2.delete()


    def test_should_not_move_documents(self):
        d = Media.objects.create(is_image=False, caption='Foo')
        try:
            c, ids = self._move_to_tree_node(self.view, {'src[]': [d.pk], 'dst': self.folder.pk})

            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual({'success': True}, decode_json(c.content))
            self.assertEqual([], ids)

            d = Media.objects.get(caption='Foo')
            self.assertIsNone(d.parent)
        finally:
            d.delete()


    def test_should_ignore_invalid_pks(self):
        c, ids = self._move_to_tree_node(self.view, {'src[]': [-1], 'dst': self.folder.pk})
        self.assertEqual('text/javascript', c['Content-Type'])
        self.assertEqual({'success': True}, decode_json(c.content))
        self.assertEqual([], ids)


    def test_should_open_target_folder_when_moving_folders_into_it(self):
        f2 = MediaFolder.objects.create(title='B')
        try:
            folder_view = FolderView()
            c, ids = self._move_to_tree_node(folder_view, {'src[]': [f2.pk], 'dst': self.folder.pk})

            self.assertEqual('text/javascript', c['Content-Type'])
            self.assertEqual({'success': True}, decode_json(c.content))
            self.assertEqual([self.folder.pk], ids)

            f2 = MediaFolder.objects.get(title='B')
            self.assertEqual(self.folder.pk, f2.parent_id)
        finally:
            f2.delete()


    def _move_to_tree_node(self, view, data):
        request = self.get_view_handler_request(view, self.user, 'move_to_tree_node', 'post', '/', data)
        response = undecorated(view.move_to_tree_node)(view, request)
        open_folders = view._get_open_folders(request)
        return response, open_folders


class LibModelViewGetTreeTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.get_tree()
    """
    def setUp(self):
        self.user = User.objects.create_user('admin', 'password')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()


    def tearDown(self):
        self.user.delete()


    def test_should_return_current_tree(self):
        view = ModelView()
        view._get_folder_response = Mock(return_value='folder_response')
        request = self.get_view_handler_request(view, self.user, 'get_tree', 'get', '/', {})
        self.assertEqual('folder_response', undecorated(view.get_tree)(view, request))


@CubaneTestCase.complex()
class LibModelViewGetFolderChildrenTestCase(CubaneTestCase):
    """
    cubane.views.ModelView._get_folder_children()
    """
    def setUp(self):
        self.view = MediaView()
        self.folder = MediaFolder()
        self.folder.slug = 'c1'
        self.folder.save()

        c2 = MediaFolder()
        c2.slug = 'c2'
        c2.parent = self.folder
        c2.save()

        admin = User.objects.create_user('admin', 'test@test.com', 'password')
        self.request = self.get_view_handler_request(self.view, admin, 'delete_empty_folders', 'post', '/admin/products/delete_empty_folders/')


    def test_should_return_folders_if_folder_present(self):
        self.assertEqual(1, len(self.view._get_folder_children(self.request, self.folder)))


    def test_should_return_empty_array_if_folder_is_empty(self):
        self.assertEqual(0, len(self.view._get_folder_children(self.request, None)))


@CubaneTestCase.complex()
class LibModelViewDeleteEmptyNodes(CubaneTestCase):
    """
    cubane.views.ModelView.delete_empty_folders()
    """
    def setUp(self):
        self.view = MediaView()
        self.admin = User.objects.create_user('admin', 'test@test.com', 'password')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()


    def test_should_delete_one_empty_node(self):
        c1 = MediaFolder()
        c1.slug = 'c1'
        c1.save()
        c2 = MediaFolder()
        c2.slug = 'c2'
        c2.save()

        p1 = Media()
        p1.parent = c1
        p1.slug = 'p1'
        p1.save()

        request, response = self.run_view_handler_request(self.view, self.admin, 'delete_empty_folders', 'post', '/admin/products/delete_empty_folders/')
        self.assertMessage(request, '<em>1</em> Media Folders deleted.')
        self.assertEqual(1, len(MediaFolder.objects.all()))


    def test_should_delete_nested_nodes(self):
        c1 = MediaFolder()
        c1.slug = 'c1'
        c1.save()
        c2 = MediaFolder()
        c2.parent = c1
        c2.slug = 'c2'
        c2.save()

        request, response = self.run_view_handler_request(self.view, self.admin, 'delete_empty_folders', 'post', '/admin/products/delete_empty_folders/')
        self.assertMessage(request, '<em>2</em> Media Folders deleted.')
        self.assertEqual(0, len(MediaFolder.objects.all()))


    def test_should_return_already_clean(self):
        c1 = MediaFolder()
        c1.slug = 'c1'
        c1.save()

        p1 = Media()
        p1.parent = c1
        p1.slug = 'p1'
        p1.save()

        request, response = self.run_view_handler_request(self.view, self.admin, 'delete_empty_folders', 'post', '/admin/products/delete_empty_folders/')
        self.assertMessage(request, 'Media Folders are already clean.')
        self.assertEqual(1, len(MediaFolder.objects.all()))


    def test_should_not_clean_if_folder_model_is_same_as_model(self):
        self.view = FolderView()
        c1 = MediaFolder()
        c1.slug = 'c1'
        c1.save()

        request, response = self.run_view_handler_request(self.view, self.admin, 'delete_empty_folders', 'post', '/admin/media-folders/delete_empty_folders/')
        self.assertMessage(request, 'Media Folders are already clean.')
        self.assertEqual(1, len(MediaFolder.objects.all()))


class LibModelViewSidePanelResizeTestCase(CubaneTestCase):
    """
    cubane.views.ModelView.side_panel_resize()
    """
    def test_should_return_success_true_json_response(self):
        factory = RequestFactory()
        view = ModelView()
        view.model = DummyModel()
        view.model._meta = Mock()
        view.model._meta.app_label = 'dummy'

        request = self.get_view_handler_request(view, None, 'dummy', 'post', '/side-panel-resize/', {'width': 200})
        response = view.side_panel_resize(request)
        json_data = json.loads(response.content)

        self.assertEqual(True, json_data.get('success'))


class LibRobotsTxtTestCase(CubaneTestCase):
    """
    cubane.views.robots_txt()
    """
    def setUp(self):
        self.factory = RequestFactory()


    def test_should_return_default_robots_txt(self):
        request = self.factory.get('/sitemap.xml')

        self.assertEqual(
            'User-agent: *\nDisallow: /admin/\nSitemap: http://www.%s/sitemap.xml\n' % settings.DOMAIN_NAME,
            robots_txt(request).content
        )


    @patch('cubane.views.get_template')
    def test_should_return_custom_robots_txt(self, get_template):
        get_template.return_value = engines['django'].from_string('custom_robots_txt')
        request = self.factory.get('/robots.txt')

        self.assertTrue('custom_robots_txt' in robots_txt(request).content)
