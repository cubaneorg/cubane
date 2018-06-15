# coding=UTF-8
from __future__ import unicode_literals
from django.db.models import QuerySet
from cubane.tests.base import CubaneTestCase
from cubane.lib.model import get_model_field_names
from cubane.lib.model import model_has_many_to_many
from cubane.lib.model import model_to_dict
from cubane.lib.model import dict_to_model
from cubane.lib.model import save_model
from cubane.lib.model import validate_model
from cubane.lib.model import IncompatibleModelError
from cubane.lib.model import get_model_related_field
from cubane.lib.model import get_listing_option
from cubane.testapp.models import TestModel, TestModelWithManyToMany, TestModelWithJsonFields
from cubane.testapp.models import CustomPage
from cubane.cms.models import Page
from cubane.media.models import Media
from django.template.defaultfilters import slugify
import datetime


class GetModelFieldNamesTestCase(CubaneTestCase):
    """
    cubane.lib.model.get_model_field_names()
    """
    def test_get_model_field_names_should_return_list(self):
        self.assertIsInstance(get_model_field_names(TestModel), list, 'must be list')
        self.assertIsInstance(get_model_field_names(TestModel, json=True), list, 'must be list')


    def test_get_model_field_names_should_return_correct_number_of_fields(self):
        number_of_fields = len(get_model_field_names(TestModel))
        number_of_fields_json = len(get_model_field_names(TestModel, json=True))
        self.assertEqual(number_of_fields, 11)
        self.assertEqual(number_of_fields_json, 11)


    def test_get_model_field_names_should_raise_error_if_not_model(self):
        def _get_fields_for_empty_model():
            get_model_field_names('')
        def _get_fields_for_empty_model_json():
            get_model_field_names('', json=True)
        self.assertRaises(AttributeError, _get_fields_for_empty_model)
        self.assertRaises(AttributeError, _get_fields_for_empty_model_json)


    def test_get_model_field_names_should_call_get_json_fieldnames_to_determine_json_properties(self):
        self.assertEqual(
            ['id', 'title'],
            get_model_field_names(TestModelWithJsonFields(), json=True)
        )


class ModelHasManyToManyTestCase(CubaneTestCase):
    """
    cubane.lib.model.model_has_many_to_many()
    """
    def test_model_has_many_to_many_should_return_true(self):
        instance = TestModelWithManyToMany()
        self.assertEqual(model_has_many_to_many(instance), True, 'must contain many to many field')


    def test_model_has_many_to_many_should_return_false(self):
        instance = TestModel()
        self.assertEqual(model_has_many_to_many(instance), False, 'must not contain many to many field')


    def test_model_has_many_to_many_should_raise_error_if_not_instance(self):
        def _model_has_many_to_many():
            model_has_many_to_many(TestModel)
        self.assertRaises(AttributeError, _model_has_many_to_many)


class ModelToDictTestCase(CubaneTestCase):
    """
    cubane.lib.model.model_to_dict()
    """
    def setUp(self):
        self.instance = TestModel(id=1, title='Title')
        self.instance.save()


    def tearDown(self):
        TestModel.objects.all().delete()


    def test_model_to_dict_should_return_dict(self):
        self.assertIsInstance(model_to_dict(self.instance), dict)


    def test_model_to_dict_should_return_correct_fields(self):
        self.assertEqual(len(model_to_dict(self.instance)), 4)


    def test_model_to_dict_should_only_return_fields_in_the_schema(self):
        self.instance.foo = 'bar'
        self.instance.save()
        def _model_to_dict_does_not_contain_field():
            model_to_dict(self.instance)['foo']

        self.assertEqual(len(model_to_dict(self.instance)), 4)
        self.assertRaises(KeyError, _model_to_dict_does_not_contain_field)


    def test_model_to_dict_should_return_reverse_fields_if_specified(self):
        m = TestModelWithManyToMany(id=1, title='Foo')
        m.save()
        try:
            d = model_to_dict(m, fetch_related=True)
            self.assertIsInstance(d.get('pages'), QuerySet)
            self.assertEqual(1, d.get('id'))
            self.assertEqual('Foo', d.get('title'))
        finally:
            m.delete()


class DictToModelTestCase(CubaneTestCase):
    """
    cubane.lib.model.dict_to_model()
    """
    def setUp(self):
        self.page = self.create_page('Page', 0)

        self.child_page = TestModelWithManyToMany(id=1, title='Title')
        self.child_page.save()
        self.child_page.pages = [self.page.id]


    def tearDown(self):
        TestModelWithManyToMany.objects.all().delete()
        TestModel.objects.all().delete()
        Page.objects.all().delete()


    def test_dict_to_model_should_update_model_instance_field(self):
        new_title = 'New Title'
        dict_to_model({
            'title': new_title
        }, self.child_page)

        self.assertEqual(self.child_page.title, new_title, 'Title should be the same')


    def test_dict_to_model_should_exclude_many_to_many(self):
        new_page = self.create_page('New Page', 1)
        dict_to_model({
            'pages': [new_page.id]
        }, self.child_page)

        new_title = 'New Title'
        dict_to_model({
            'title': new_title,
            'pages': [self.page.id]
        }, self.child_page, exclude_many_to_many=True)

        self.assertEqual(self.child_page.title, new_title, 'Title should be the same')
        self.assertEqual(self.child_page.pages.all().count(), 1, 'Should only have one page')
        self.assertEqual(self.child_page.pages.all()[0], new_page, 'Page should be the same')


    def test_dict_to_model_should_only_change_many_to_many(self):
        new_page = self.create_page('New Page', 1)
        dict_to_model({
            'pages': [new_page.id]
        }, self.child_page)

        new_title = 'New Title'
        dict_to_model({
            'title': new_title,
            'pages': [self.page.id]
        }, self.child_page, only_many_to_many=True)

        self.assertNotEqual(self.child_page.title, new_title, 'Title should be different')
        self.assertEqual(self.child_page.title, 'Title', 'Title should be the same')
        self.assertEqual(self.child_page.pages.all().count(), 1, 'Should only have one page')
        self.assertEqual(self.child_page.pages.all()[0], self.page, 'Page should be the same')


    def create_page(self, title, seq):
        p = Page(
            title=title,
            slug=slugify(title),
            template='testapp/page.html',
            entity_type='TestModelWithManyToMany',
            _nav='header',
            seq=seq
        )
        p.save()
        return p


class SaveModelTestCase(CubaneTestCase):
    """
    cubane.lib.model.save_model()
    """
    def test_save_model_should_change_model_field_values(self):
        instance = TestModel(title='Title')
        instance.save()
        self.change_instance_title_and_confirm(instance)
        instance.delete()


    def test_save_model_should_save_instance_due_to_not_having_pk_but_having_many_to_many(self):
        instance = TestModelWithManyToMany(title='Title')
        self.change_instance_title_and_confirm(instance)
        instance.delete()


    def change_instance_title_and_confirm(self, instance):
        save_model({'title': 'New Title'}, instance)
        self.assertEqual(instance.title, 'New Title', 'Title should have changed')


class TestValidateModelTestCase(CubaneTestCase):
    """
    cubane.lib.model.validate_model()
    """
    def test_should_raise_error_if_unicode_method_is_not_implemented(self):
        class ModelMockWithoutUnicode(object):
            pass

        with self.assertRaisesRegexp(IncompatibleModelError, 'Missing __unicode__'):
            validate_model(ModelMockWithoutUnicode)


class TestGetModelRelatedFieldTestCase(CubaneTestCase):
    """
    cubane.lib.model.get_model_related_field()
    """
    def test_should_resolve_related_field_name(self):
        field, related, rel_fieldname, rel_model, title = get_model_related_field(
            CustomPage,
            'image__caption',
            'Image Caption'
        )

        self.assertEqual('image', field.name)
        self.assertEqual('image', related)
        self.assertEqual('caption', rel_fieldname)
        self.assertEqual(Media, rel_model)
        self.assertEqual('Image Caption', title)


    def test_should_generate_title_from_fieldname_if_not_specified(self):
        _, _, _, _, title = get_model_related_field(
            CustomPage,
            'image__caption'
        )

        self.assertEqual('Caption', title)


    def test_should_fail_on_many_to_many_field(self):
        field, _, _, _, _ = get_model_related_field(CustomPage, 'gallery_images__caption')
        self.assertIsNone(field)


    def test_should_fail_if_not_matching_pattern(self):
        field, _, _, _, _ = get_model_related_field(CustomPage, 'image')
        self.assertIsNone(field)


    def test_should_fail_if_field_does_not_exist(self):
        field, _, _, _, _ = get_model_related_field(CustomPage, 'foo__bar')
        self.assertIsNone(field)


    def test_should_fail_if_rel_field_does_not_exist(self):
        field, _, _, _, _ = get_model_related_field(CustomPage, 'image__foo')
        self.assertIsNone(field)


class TestGetModelOptionTestCase(CubaneTestCase):
    """
    cubane.lib.model.get_listing_option()
    Special case of cubane.lib.model.get_model_option()
    """
    class ModelWithoutListing(object):
        pass

    class ModelWithEmptyListing(object):
        class Listing:
            pass

    class ModelWithListingOption(object):
        class Listing:
            foo = 'bar'

    class BaseModelWithListingOptionModelWithoutListing(ModelWithoutListing):
        class Listing:
            foo = 'bar'

    class BaseModelWithListingOptionModelWithEmptyListing(ModelWithEmptyListing):
        class Listing:
            foo = 'bar'

    class ModelOverride(ModelWithListingOption):
        class Listing:
            foo = 'not bar anymore'

    class ModelOverrideNone(ModelWithListingOption):
        class Listing:
            foo = None


    def test_should_return_default_if_model_is_none(self):
        self.assertEqual('def', get_listing_option(None, 'foo', 'def'))


    def test_should_return_default_if_container_is_none(self):
        self.assertEqual('def', get_listing_option(self.ModelWithoutListing, 'foo', 'def'))


    def test_should_return_default_if_option_is_not_declared(self):
        self.assertEqual('def', get_listing_option(self.ModelWithEmptyListing, 'foo', 'def'))


    def test_should_return_option_if_declared(self):
        self.assertEqual('bar', get_listing_option(self.ModelWithListingOption, 'foo', 'def'))


    def test_should_return_option_from_base_class_if_container_not_declared(self):
        self.assertEqual('bar', get_listing_option(self.BaseModelWithListingOptionModelWithoutListing, 'foo', 'def'))


    def test_should_return_option_from_base_class_if_option_not_declared(self):
        self.assertEqual('bar', get_listing_option(self.BaseModelWithListingOptionModelWithEmptyListing, 'foo', 'def'))


    def test_option_should_override_base_model(self):
        self.assertEqual('not bar anymore', get_listing_option(self.ModelOverride, 'foo', 'def'))


    def test_option_should_override_base_model_even_if_none(self):
        self.assertEqual(None, get_listing_option(self.ModelOverrideNone, 'foo', 'def'))