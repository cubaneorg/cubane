# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.db.models import CharField, TextField
from cubane.tests.base import CubaneTestCase
from cubane.models.fields import MultiSelectField, IntegerRangeField
from cubane.testapp.models import TestMultiSelectField
from cubane.testapp.models import TestNullableMultiSelectField
from cubane.testapp.models import TestTagsField
from cubane.testapp.models import TestNullableTagsField
from cubane.testapp.forms import TestMultiSelectFieldForm
from cubane.testapp.forms import TestMultiSelectOptGroupFieldForm
from cubane.testapp.forms import TestTagsFieldForm
from cubane.testapp.forms import TestTagsOptGroupFieldForm


class CubaneModelsMultiSelectFieldTestCase(CubaneTestCase):
    def tearDown(self):
        [m.delete() for m in TestMultiSelectField.objects.all()]
        [m.delete() for m in TestNullableMultiSelectField.objects.all()]


    def test_assign_multiple_values_should_return_same_list_of_values(self):
        m = TestMultiSelectField.objects.create(department=['it', 'development', 'design'])
        m = TestMultiSelectField.objects.get(pk=m.pk)
        self.assertEqual(['it', 'development', 'design'], m.department)


    def test_string_value_should_return_list_with_trimmed_items(self):
        m = TestMultiSelectField.objects.create(department='it, development, design')
        m = TestMultiSelectField.objects.get(pk=m.pk)
        self.assertEqual(['it', 'development', 'design'], m.department)


    def test_none_value_should_return_empty_list(self):
        m = TestNullableMultiSelectField.objects.create(department=None)
        m = TestNullableMultiSelectField.objects.get(pk=m.pk)
        self.assertEqual([], m.department)


    def test_empty_list_value_should_return_empty_list(self):
        m = TestMultiSelectField.objects.create(department=[])
        m = TestMultiSelectField.objects.get(pk=m.pk)
        self.assertEqual([], m.department)


    def test_assign_multiple_values_should_encode_comma_seperated(self):
        field = TestMultiSelectField._meta.get_field('department')
        m = TestMultiSelectField(department=['it', 'qa'])
        self.assertEqual('it,qa', field.value_to_string(m))


    def test_get_field_display_should_return_display_values(self):
        m = TestMultiSelectField(department=['it', 'development', 'design'])
        self.assertEqual('IT, Development, Design', m.get_department_display())


    def test_field_width_default_should_set_initial(self):
        field = TestMultiSelectField._meta.get_field('department')
        self.assertEqual('it,sales', field.default)

        form = TestMultiSelectFieldForm()
        self.assertEqual('it,sales', form.fields.get('department').initial)


    def test_form_validation_required(self):
        form = TestMultiSelectFieldForm()
        self.assertFalse(form.is_valid())


    def test_form_validation_invalid_value(self):
        form = TestMultiSelectFieldForm({'department': ['it', 'does-not-exist']})
        self.assertFalse(form.is_valid())


    def test_form_validation_none_value(self):
        form = TestMultiSelectFieldForm({'department': None})
        self.assertFalse(form.is_valid())


    def test_form_validation_valid_value(self):
        form = TestMultiSelectFieldForm({'department': ['it', 'qa']})
        self.assertTrue(form.is_valid())
        self.assertEqual(['it', 'qa'], form.cleaned_data.get('department'))


    def test_form_validation_should_validate_against_opt_group_choices(self):
        form = TestMultiSelectOptGroupFieldForm({'department': ['it', 'qa']})
        self.assertTrue(form.is_valid())
        self.assertEqual(['it', 'qa'], form.cleaned_data.get('department'))


class CubaneModelsTagsFieldTestCase(CubaneTestCase):
    def tearDown(self):
        [tag.delete() for tag in TestTagsField.objects.all()]
        [tag.delete() for tag in TestNullableTagsField.objects.all()]


    def test_assign_multiple_values_should_return_same_list_of_values(self):
        m = TestTagsField.objects.create(tags=['a', 'b', 'c'])
        m = TestTagsField.objects.get(pk=m.pk)
        self.assertEqual(['a', 'b', 'c'], m.tags)


    def test_assign_string_value_should_return_list_of_tags(self):
        m = TestTagsField.objects.create(tags='#a#b#c#')
        m = TestTagsField.objects.get(pk=m.pk)
        self.assertEqual(['a', 'b', 'c'], m.tags)


    def test_none_value_should_return_empty_list(self):
        m = TestNullableTagsField.objects.create(tags=None)
        m = TestNullableTagsField.objects.get(pk=m.pk)
        self.assertEqual([], m.tags)


    def test_empty_list_value_should_return_empty_list(self):
        m = TestTagsField.objects.create(tags=[])
        m = TestTagsField.objects.get(pk=m.pk)
        self.assertEqual([], m.tags)


    def test_assign_multiple_values_should_encode_comma_seperated(self):
        field = TestTagsField._meta.get_field('tags')
        m = TestTagsField.objects.create(tags=['a', 'b', 'c'])
        m = TestTagsField.objects.get(pk=m.pk)
        self.assertEqual('#a#b#c#', field.value_to_string(m))


    def test_get_field_display_should_return_display_values(self):
        m = TestTagsField.objects.create(tags=['a', 'b', 'c'])
        m = TestTagsField.objects.get(pk=m.pk)
        self.assertEqual('a, b, c', m.get_tags_display())


    def test_field_width_default_should_set_initial(self):
        field = TestTagsField._meta.get_field('tags')
        self.assertEqual('#a#b#', field.default)

        form = TestTagsFieldForm()
        self.assertEqual('#a#b#', form.fields.get('tags').initial)


    def test_form_validation_required(self):
        form = TestTagsFieldForm()
        self.assertFalse(form.is_valid())


    def test_form_validation_none_value(self):
        form = TestTagsFieldForm({'tags': None})
        self.assertFalse(form.is_valid())


    def test_form_validation_valid_value(self):
        form = TestTagsFieldForm({'tags': ['a', 'b', 'c']})
        self.assertTrue(form.is_valid())
        self.assertEqual(['a', 'b', 'c'], form.cleaned_data.get('tags'))


    def test_form_validation_invalid_value(self):
        form = TestTagsFieldForm({'tags': ['a', 'does-not-exist']})
        self.assertFalse(form.is_valid())


    def test_form_validation_should_validate_against_opt_group_choices(self):
        form = TestTagsOptGroupFieldForm({'tags': ['a', 'b', 'c']})
        self.assertTrue(form.is_valid())
        self.assertEqual(['a', 'b', 'c'], form.cleaned_data.get('tags'))


class CubaneModelsIntegerRangeFieldTestCase(CubaneTestCase):
    def test_min_max_arguments(self):
        f = IntegerRangeField(min_value=2, max_value=5)
        self.assertEqual(2, f.min_value)
        self.assertEqual(5, f.max_value)


    def test_formfield_should_provide_min_max_defaults_for_from_field(self):
        f = IntegerRangeField(min_value=2, max_value=5)
        field = f.formfield()
        self.assertEqual(2, field.min_value)
        self.assertEqual(5, field.max_value)