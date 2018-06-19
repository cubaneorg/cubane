# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.http import QueryDict
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.backends.cache import SessionStore
from cubane.tests.base import CubaneTestCase
from cubane.forms import *
from cubane.testapp.models import TestModel


class TestFormWithoutMeta(BaseForm):
    pass


class TestFormBase(BaseForm):
    class Meta:
        exclude = ['excluded']
        widgets = {
            'title': forms.Textarea()
        }
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'title',
                    'slug'
                ]
            }, {
                'title': 'Options',
                'fields': [
                    'enabled',
                    'excluded'
                ]
            }
        ]


    title = forms.CharField(
        max_length=8,
        required=True
    )

    slug = forms.SlugField(
        required=True
    )

    enabled = forms.BooleanField(
        required=False
    )

    excluded = forms.BooleanField(
        required=True
    )


class TestForm(TestFormBase):
    pass


class TestRenamingTabWithoutFieldsForm(TestForm):
    class Meta:
        tabs = [
            {
                'title': 'Title:as(Renamed Title)',
                'fields': []
            }
        ]


class TestRenamingTabWithAdditionalFieldForm(TestForm):
    class Meta:
        tabs = [
            {
                'title': 'Title:as(Renamed Title)',
                'fields': ['name']
            }
        ]


    name = forms.CharField(max_length=16)


class TestFormNewTabWithExistingField(TestFormBase):
    class Meta:
        tabs = [
            {
                'title': 'New Tab',
                'fields': ['slug']
            }
        ]


class TestFormInsertFieldBase(TestFormBase):
    class Meta:
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'url:before(title)',
                    'name:after(title)'
                ]
            }
        ]


    url = forms.CharField(max_length=16)
    name = forms.CharField(max_length=16)


class TestFormInsertField(TestFormInsertFieldBase):
    pass


class TestFormInsertFieldReferenceDoesNotExist(TestFormBase):
    class Meta:
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'url:before(does_not_exist)'
                ]
            }
        ]


    url = forms.CharField(max_length=16)


class TestFormFieldDoesNotExist(TestFormBase):
    class Meta:
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'does_not_exist'
                ]
            }
        ]


class TestFormIncorrectFieldReference(TestFormBase):
    class Meta:
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    '()'
                ]
            }
        ]


class TestFormWithStepsInBase(TestFormBase):
    class Meta:
        pass


class TestStripFieldsForm(BaseForm):
    title = forms.CharField(
        max_length=8,
        required=True
    )

    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput()
    )


class TestTwoFieldsBaseForm(BaseForm):
    title = forms.CharField(max_length=16, required=True)
    slug = forms.CharField(max_length=16, required=True)


class TestAllFieldsRequiredForm(TestTwoFieldsBaseForm):
    pass


class TestRenderForm(BaseForm):
    title = forms.CharField(max_length=16, required=True)


class TestNonTabbedForm(TestTwoFieldsBaseForm):
    pass


class TestSectionsForm(TestTwoFieldsBaseForm):
    class Meta:
        sections = {
            'title': 'Title',
            'slug': 'Slug'
        }


class TestNoSectionsForm(TestTwoFieldsBaseForm):
    pass


class TestNoStepsForm(TestTwoFieldsBaseForm):
    pass


class TestFormWithSectionsBase(BaseForm):
    class Meta:
        steps = True
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'title',
                    'slug'
                ]
            }, {
                'title': 'Options',
                'fields': [
                    'enabled',
                ]
            }
        ]
        sections = {
            'title': 'Title and Slug',
            'enabled': 'Enabled'
        }


    title = forms.CharField(
        max_length=8,
        required=True
    )

    slug = forms.SlugField(
        required=True
    )

    enabled = forms.BooleanField(
        required=False
    )


class TestFormWithSectionsRenamingExistingSection(TestFormWithSectionsBase):
    class Meta:
        sections = {
            'enabled': 'Options'
        }


class TestFormWithSectionsReferencingUnknownField(TestFormWithSectionsBase):
    class Meta:
        sections = {
            'does_not_exist': 'Foo'
        }


class TestFormWithSectionsTurnedOffByDerivedClass(TestFormWithSectionsBase):
    class Meta:
        sections = FormSectionLayout.NONE


class TestFormCollectExclude(TestFormBase):
    class Meta:
        exclude = ['enabled']


class TestFormCollectExcludeOnlyOnce(TestFormBase):
    class Meta:
        exclude = ['excluded']


class TestFormCollectWidgets(TestFormBase):
    class Meta:
        widgets = {
            'slug': forms.Textarea()
        }

class TestFormEmailField(TestFormBase):
    email = forms.EmailField(
        required=False
    )


class TestFormCollectWidgetsOverrideBase(TestFormBase):
    class Meta:
        widgets = {
            'title': forms.Select()
        }


class TestFormNoLayoutNoSections(BaseForm):
    pass


class TestFormNoLayoutButSections(BaseForm):
    class Meta:
        sections = {
            'title': 'Title'
        }


    title = forms.CharField(max_length=8, required=False)


class TestFormWithLayout(BaseForm):
    class Meta:
        layout = FormLayout.COLUMNS


class TestFormRequiredFieldNotReferenced(BaseForm):
    class Meta:
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'title'
                ]
            }
        ]

    title = forms.CharField(max_length=8, required=False)
    slug = forms.CharField(max_length=8, required=True)


class TestFormPrefixSuffix(BaseForm):
    title = forms.CharField(max_length=8, required=False)


class TestLoginForm(BaseLoginForm):
    username = forms.CharField(max_length=32, required=False)
    password = forms.CharField(max_length=32, required=False)


class TestPasswordForgottenForm(BasePasswordForgottenForm):
    pass


class TestChangePasswordForm(BaseChangePasswordForm):
    pass


class FormsHTML5InputsTestCase(CubaneTestCase):
    def test_number_input(self):
        self.assertEqual('number', NumberInput.input_type)


    def test_date_input(self):
        date = DateInput()

        self.assertEqual('text', DateInput.input_type)
        self.assertTrue('date-field' in date.render('my_name', None))


    def test_time_input(self):
        time = TimeInput()

        self.assertEqual('text', TimeInput.input_type)
        self.assertTrue('time-field' in time.render('my_name', None))


    def test_datetime_input(self):
        self.assertEqual('datetime-local', DateTimeInput.input_type)


    def test_datetimezone_input(self):
        self.assertEqual('datetime', DateTimeZoneInput.input_type)


    def test_email_input(self):
        self.assertEqual('email', EmailInput.input_type)


    def test_phone_input(self):
        self.assertEqual('tel', PhoneInput.input_type)


class FormsColorInputTestCase(CubaneTestCase):
    def test_color_input_type(self):
        self.assertEqual('text', ColorInput.input_type)


    def test_should_render_value_if_not_empty(self):
        widget = ColorInput()
        html = widget.render('foo', '#123456')
        self.assertEqual('<input name="foo" type="text" value="#123456" class="color-text" />', html)


    def test_should_render_no_value_if_none(self):
        widget = ColorInput()
        html = widget.render('foo', None)
        self.assertEqual('<input name="foo" type="text" class="color-text" />', html)


    def test_should_render_no_value_if_empty(self):
        widget = ColorInput()
        html = widget.render('foo', '')
        self.assertEqual('<input name="foo" type="text" class="color-text" />', html)


class FormsBootstrapTextInputTestCase(CubaneTestCase):
    def test_no_prepend_nor_append(self):
        widget = BootstrapTextInput()
        html = widget.render('foo', 'bar')
        self.assertMarkup(html, 'input', {
            'name': 'foo',
            'type': 'text',
            'value': 'bar'
        })


    def test_prepend_and_append(self):
        widget = BootstrapTextInput(prepend='£', append='###.##')
        html = widget.render('foo', 'bar')
        self.assertMarkup(html, 'div', {'class': 'input-prepend input-append'})
        self.assertMarkup(html, 'span', {'class': 'add-on'}, '\xa3')
        self.assertMarkup(html, 'input', {
            'name': 'foo',
            'type': 'text',
            'value': 'bar'
        })
        self.assertMarkup(html, 'span', {'class': 'add-on'}, '###.##')


    def test_prepend(self):
        widget = BootstrapTextInput(prepend='£')
        html = widget.render('foo', 'bar')
        self.assertMarkup(html, 'div', {'class': 'input-prepend'})
        self.assertMarkup(html, 'span', {'class': 'add-on'}, '\xa3')
        self.assertMarkup(html, 'input', {
            'name': 'foo',
            'type': 'text',
            'value': 'bar'
        })


    def test_append(self):
        widget = BootstrapTextInput(append='###.##')
        html = widget.render('foo', 'bar')
        self.assertMarkup(html, 'div', {'class': 'input-append'})
        self.assertMarkup(html, 'input', {
            'name': 'foo',
            'type': 'text',
            'value': 'bar'
        })
        self.assertMarkup(html, 'span', {'class': 'add-on'}, '###.##')


class FormsUrlInputTestCase(CubaneTestCase):
    def test_input_type(self):
        self.assertEqual('url', UrlInput.input_type)


    def test_prepend_url(self):
        widget = UrlInput()
        html = widget.render('foo', 'http://innershed.com/')
        self.assertMarkup(html, 'div', {'class': 'input-prepend'})
        self.assertMarkup(html, 'span', {'class': 'add-on'}, 'URL:')
        self.assertMarkup(html, 'input', {
            'name': 'foo',
            'type': 'url',
            'value': 'http://innershed.com/'
        })


class FormsSectionWidgetAndFieldTestCase(CubaneTestCase):
    def test_render_widget(self):
        widget = SectionWidget(attrs={'label': 'Label'})
        html = widget.render('foo', None)
        self.assertEqual(html, '<h2 class="form-section">Label</h2>')


    def test_render_widget_with_help_text(self):
        widget = SectionWidget(attrs={'label': 'Label', 'help_text': 'HelpText'})
        html = widget.render('foo', None)
        self.assertEqual('<h2 class="form-section with-help-text">Label</h2><div class="form-section-help">HelpText</div>', html)


    def test_field_should_be_not_required_by_default(self):
        field = SectionField()
        self.assertFalse(field.required)


    def test_field_should_propagate_label_and_help_text_to_widget(self):
        field = SectionField(label='Label', help_text='Help Text')
        attrs = field.widget_attrs(SectionWidget())
        self.assertEqual('Label', attrs.get('label'))
        self.assertEqual('Help Text', attrs.get('help_text'))


class FormsLocationMapWidgetTestCase(CubaneTestCase):
    def test_render_with_defaults(self):
        widget = LocationMapWidget()
        html = widget.render('foo', None)
        self.assertEqual('<div class="map-canvas" data-key="foo" data-lat="id_lat" data-lng="id_lng" data-zoom="id_zoom"></div>', html)


    def test_render_with_attrs(self):
        widget = LocationMapWidget()
        html = widget.render('foo', None, attrs={
            'class': 'bar',
            'data-lat': 'lat-field',
            'data-lng': 'lng-field',
            'data-zoom': 'zoom-field'
        })
        self.assertEqual('<div class="bar map-canvas" data-key="foo" data-lat="lat-field" data-lng="lng-field" data-zoom="zoom-field"></div>', html)


class FormsLocationMapFieldTestCase(CubaneTestCase):
    def test_should_not_be_required(self):
        field = LocationMapField()
        self.assertFalse(field.required)


class FormsExtFileFieldTestCase(CubaneTestCase):
    class UploadedFileMock(object):
        def __init__(self, name):
            self.name = name
            self.size = 1024


    def test_defualt_list_of_extensions_is_empty(self):
        self.assertEqual(ExtFileField().ext, [])


    def test_valid_extension_required_jpg(self):
        self._create_field().clean(self.UploadedFileMock('test.jpg'))


    def test_valid_extension_required_png(self):
        self._create_field().clean(self.UploadedFileMock('test.png'))


    def test_valid_extension_required_txt_png(self):
        self._create_field().clean(self.UploadedFileMock('test.txt.png'))


    def test_invalid_extension_should_raise_validation_error_txt(self):
        with self.assertRaisesRegexp(forms.ValidationError, '\'\.txt\' is not allowed'):
            self._create_field().clean(self.UploadedFileMock('test.txt'))


    def test_invalid_extension_should_raise_validation_error_jpg_txt(self):
        with self.assertRaisesRegexp(forms.ValidationError, '\'\.txt\' is not allowed'):
            self._create_field().clean(self.UploadedFileMock('test.jpg.txt'))


    def _create_field(self):
        return ExtFileField(ext=['.jpg', '.png'])


class FormsMultiSelectFormFieldTestCase(CubaneTestCase):
    def test_should_default_max_choices_0(self):
        self.assertEqual(MultiSelectFormField().max_choices, 0)


    def test_should_not_raise_if_value_is_present(self):
        field = MultiSelectFormField(required=True)
        field.clean(5)


    def test_should_require_value_if_required(self):
        with self.assertRaisesRegexp(forms.ValidationError, 'This field is required'):
            field = MultiSelectFormField(required=True)
            field.clean(None)


class FormsFormTabTestCase(CubaneTestCase):
    def test_should_assign_attributes(self):
        tab = FormTab('Test Title', ['a', 'b', 'c'])
        self.assertEqual('Test Title', tab.title)
        self.assertEqual('test-title', tab.slug)
        self.assertEqual(['a', 'b', 'c'], tab.fields)


class FormFullCleanTestCase(CubaneTestCase):
    def test_should_strip_all_char_fields(self):
        form = TestStripFieldsForm(QueryDict('title=%20Title%20&password=%20password%20'))
        self.assertTrue(form.is_valid())

        d = form.cleaned_data
        self.assertEqual('Title', d.get('title'))
        self.assertEqual('password', d.get('password'))


class FormCleanTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(FormCleanTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.post('/')


    def test_checksum_should_be_required(self):
        instance = TestModel(title='Foo', text='Bar')
        form = self._create_form()
        form.configure(self.request, instance, edit=True)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, '_cubane_instance_checksum', 'This field is required.')


    def test_should_raise_error_if_checksum_does_not_match(self):
        instance = TestModel(title='Foo', text='Bar', updated_by=User(first_name='Jan'))
        form = self._create_form({'_cubane_instance_checksum': 'does-not-match'})
        form.configure(self.request, instance, edit=True)
        self.assertFalse(form.is_valid())
        self.assertFormError(form, 'This entity was modified while you were editing it.')


    def test_should_raise_error_for_unknown_user_if_checksum_does_not_match(self):
        instance = TestModel(title='Foo', text='Bar')
        form = self._create_form({'_cubane_instance_checksum': 'does-not-match'})
        form.configure(self.request, instance, edit=True)
        self.assertFalse(form.is_valid())
        self.assertFormError(form, 'This entity was modified while you were editing it.')


    def test_should_validate_if_checksum_matches(self):
        instance = TestModel(title='Foo', text='Bar')
        form = self._create_form({'_cubane_instance_checksum': instance.get_checksum()})
        form.configure(self.request, instance, edit=True)
        self.assertTrue(form.is_valid())


    def _form_data(self, data):
        d = {
            'title': 'Foo2',
            'text': 'Bar2'
        }
        d.update(data)
        return d


    def _create_form(self, data={}):
        return TestModel.get_form()(self._form_data(data))


class FormExcludeFieldsTestCase(CubaneTestCase):
    def test_should_remove_excluded_fields_from_form_data(self):
        form = TestForm({
            'title': 'Foo',
            'slug': 'bar',
            'excluded': True
        })
        self.assertTrue(form.is_valid())
        self.assertEqual({'enabled': False, 'slug': 'bar', 'title': 'Foo'}, form.cleaned_data)


class FormRequiredFieldsTestCase(CubaneTestCase):
    def test_should_return_list_of_required_bound_fields(self):
        form = TestForm()
        self.assertEqual(
            [
                 self._bound_field('title'),
                 self._bound_field('slug'),
                 self._bound_field('excluded')
            ],
            [(f.__class__, f.name) for f in form.required_fields()]
        )


    def _bound_field(self, title):
        return (forms.forms.BoundField, title)


class FormAreAllFieldsRequriedCase(CubaneTestCase):
    def test_should_return_true_if_all_fields_are_required(self):
        form = TestAllFieldsRequiredForm()
        self.assertTrue(form.are_all_fields_requried())


    def test_should_return_false_if_not_all_fields_are_required(self):
        form = TestAllFieldsRequiredForm()
        form.fields['title'].required = False
        self.assertFalse(form.are_all_fields_requried())


class FormHasRequiredFieldsTestCase(CubaneTestCase):
    def test_should_return_true_if_at_least_one_field_is_required(self):
        form = TestAllFieldsRequiredForm()
        form.fields['title'].required = False
        self.assertTrue(form.has_required_fields())


    def test_should_return_false_if_there_is_no_field_that_is_required(self):
        form = TestAllFieldsRequiredForm()
        form.fields['title'].required = False
        form.fields['slug'].required = False
        self.assertFalse(form.has_required_fields())


class FormConfigureTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(FormConfigureTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.post('/')


    def test_should_not_inject_checksum_on_create(self):
        form = TestForm()
        instance = TestModel()
        form.configure(self.request, instance, edit=False)
        self.assertIsNone(form.fields.get('_cubane_instance_checksum'))


    def test_should_not_inject_checksum_if_instance_is_none(self):
        form = TestForm()
        instance = TestModel()
        form.configure(self.request, None, edit=True)
        self.assertIsNone(form.fields.get('_cubane_instance_checksum'))


    def test_should_inject_entity_checksum_as_hidden_field(self):
        form = TestForm()
        instance = TestModel()
        form.configure(self.request, instance, edit=True)

        field = form.fields.get('_cubane_instance_checksum')
        self.assertIsNotNone(field)
        self.assertIsInstance(field, forms.CharField)
        self.assertIsInstance(field.widget, forms.HiddenInput)
        self.assertEqual(field.initial, instance.get_checksum())


class FormUnicodeTestCase(CubaneTestCase):
    def test_should_render_form_using_default_form_render_templates(self):
        markup = unicode(TestRenderForm())
        self.assertIn('<form class="form-horizontal', markup)
        self.assertIn('<span class="required_indicator">*</span>', markup)
        self.assertMarkup(markup, 'input', {
            'id': 'id_title',
            'maxlength': '16',
            'name': 'title',
            'type': 'text',
            'required': True
        })


class FormToDictTestCase(CubaneTestCase):
    def test_should_return_from_as_dictionary(self):
        d = TestForm().to_dict()
        self.assertEqual(4, len(d))
        self.assertEqual('title', d[0].get('name'))
        self.assertEqual('textarea', d[0].get('type'))


class FormIsTabbedTestCase(CubaneTestCase):
    def test_should_return_true_if_form_is_tabbed(self):
        self.assertTrue(TestForm().is_tabbed)


    def test_should_return_false_if_form_is_not_tabbed(self):
        self.assertFalse(TestNonTabbedForm().is_tabbed)


class FormHasSectionsTestCase(CubaneTestCase):
    def test_should_return_true_if_form_has_at_least_one_section(self):
        self.assertTrue(TestSectionsForm().has_sections)


    def test_should_return_false_if_form_has_no_sections(self):
        self.assertFalse(TestNoSectionsForm().has_sections)


class FormGetAllTabsTestCase(CubaneTestCase):
    def test_should_return_all_tabs_with_fields(self):
        tabs = TestFormInsertField().tabs
        self.assertEqual(2, len(tabs))

        self.assertEqual(('Title', 'title'), (tabs[0].title, tabs[0].slug))
        self.assertEqual(['url', 'title', 'name', 'slug'], [f.name for f in tabs[0].fields])

        self.assertEqual(('Options', 'options'), (tabs[1].title, tabs[1].slug))
        self.assertEqual(['enabled', 'excluded'], [f.name for f in tabs[1].fields])


class FormGetTabByTitleTestCase(CubaneTestCase):
    def test_should_return_tab_by_title(self):
        self.assertEqual(
            {'fields': ['title', 'slug'], 'title': 'Title'},
            TestForm().get_tab_by_title('Title')
        )


    def test_should_return_none_if_tab_with_given_title_does_not_exist(self):
        self.assertIsNone(TestForm().get_tab_by_title('Does Not Exist'))


class FormMergeTabsTestCase(CubaneTestCase):
    def test_should_rename_existing_title_without_additional_fields(self):
        form = TestRenamingTabWithoutFieldsForm()
        self.assertEqual(
            {'fields': ['title', 'slug'], 'title': 'Renamed Title'},
            form.get_tab_by_title('Renamed Title')
        )
        self.assertIsNone(form.get_tab_by_title('Title'))


    def test_should_rename_existing_title_with_additional_field(self):
        form = TestRenamingTabWithAdditionalFieldForm()
        self.assertEqual(
            {'fields': ['title', 'slug', 'name'], 'title': 'Renamed Title'},
            form.get_tab_by_title('Renamed Title')
        )
        self.assertIsNone(form.get_tab_by_title('Title'))


    def test_should_create_new_tab_with_existing_field_keeping_existing_field_reference(self):
        form = TestFormNewTabWithExistingField()
        self.assertEqual(
            {'fields': ['title', 'slug'], 'title': 'Title'},
            form.get_tab_by_title('Title')
        )
        self.assertEqual(
            {'fields': ['slug'], 'title': 'New Tab'},
            form.get_tab_by_title('New Tab')
        )


    def test_should_append_field_after_or_before_referenced_field(self):
        form = TestFormInsertField()
        self.assertEqual(
            {'fields': ['url', 'title', 'name', 'slug'], 'title': 'Title'},
            form.get_tab_by_title('Title')
        )


    def test_should_raise_exception_if_referenced_field_does_not_exist(self):
        with self.assertRaisesRegexp(ValueError, 'does not exist'):
            TestFormInsertFieldReferenceDoesNotExist()


    def test_should_ignore_unknown_fields(self):
        form = TestFormFieldDoesNotExist()
        self.assertEqual(
            {'fields': ['title', 'slug', 'does_not_exist'], 'title': 'Title'},
            form.get_tab_by_title('Title')
        )


    def test_should_raise_exception_for_invalid_field_reference_format(self):
        with self.assertRaisesRegexp(ValueError, 'Incorrect field reference'):
            TestFormIncorrectFieldReference()


class FormUpdateSectionsTestCase(CubaneTestCase):
    def test_should_collect_sections_from_class_and_bases(self):
        form = TestFormWithSectionsBase()
        self.assertEqual(
            {'fields': ['_title', 'title', 'slug'], 'title': 'Title'},
            form.get_tab_by_title('Title')
        )
        self.assertIsInstance(form.fields['_title'], SectionField)
        self.assertEqual('Title and Slug', form.fields['_title'].label)

        self.assertEqual(
            {'fields': ['_enabled', 'enabled'], 'title': 'Options'},
            form.get_tab_by_title('Options')
        )
        self.assertIsInstance(form.fields['_enabled'], SectionField)
        self.assertEqual('Enabled', form.fields['_enabled'].label)


    def test_should_rename_existing_section(self):
        form = TestFormWithSectionsRenamingExistingSection()
        self.assertEqual(
            {'fields': ['_enabled', 'enabled'], 'title': 'Options'},
            form.get_tab_by_title('Options')
        )
        self.assertEqual('Options', form.fields['_enabled'].label)


    def test_should_ignore_section_referencing_field_that_does_not_exist(self):
        form = TestFormWithSectionsReferencingUnknownField()
        self.assertEqual(
            {'fields': ['_title', 'title', 'slug'], 'title': 'Title'},
            form.get_tab_by_title('Title')
        )
        self.assertEqual(
            {'fields': ['_enabled', 'enabled'], 'title': 'Options'},
            form.get_tab_by_title('Options')
        )


    def test_should_ignore_sections_if_turned_off_in_derived_class(self):
        form = TestFormWithSectionsTurnedOffByDerivedClass()
        self.assertEqual(
            {'fields': ['title', 'slug'], 'title': 'Title'},
            form.get_tab_by_title('Title')
        )
        self.assertIsNone(form.fields.get('_title'))

        self.assertEqual(
            {'fields': ['enabled'], 'title': 'Options'},
            form.get_tab_by_title('Options')
        )
        self.assertIsNone(form.fields.get('_enabled'))


class FormSetupTestCase(CubaneTestCase):
    def test_should_enforce_meta(self):
        form = TestFormWithoutMeta()
        self.assertTrue(hasattr(form, 'Meta'))


class FormSetupCollectExclusionsTestCase(CubaneTestCase):
    def test_should_collection_field_exclusions_from_base_classes(self):
        self.assertEqual(['enabled', 'excluded'], TestFormCollectExclude().excluded_fields)


    def test_should_collect_excluded_fields_only_once(self):
        self.assertEqual(['excluded'], TestFormCollectExcludeOnlyOnce().excluded_fields)


class FormSetupCollectWidgetsTestCase(CubaneTestCase):
    def test_should_collect_widgets_from_base_classes(self):
        form = TestFormCollectWidgets()
        self.assertIsInstance(form.fields['title'].widget, forms.Textarea)
        self.assertIsInstance(form.fields['slug'].widget, forms.Textarea)


    def test_should_allow_override_widget_from_base_class(self):
        form = TestFormCollectWidgetsOverrideBase()
        self.assertIsInstance(form.fields['title'].widget, forms.Select)


class FormSetupEmailFieldTestCase(CubaneTestCase):
    def test_should_replace_default_email_validator(self):
        form = TestFormEmailField()
        self.assertEqual(1, len(form.fields['email'].validators))
        self.assertNotIsInstance(form.fields['email'].validators[0], EmailValidator)



class FormSetupDeterminesLayoutTestCase(CubaneTestCase):
    def test_form_without_layout_and_sections_should_use_flat_layout(self):
        self.assertEqual(FormLayout.FLAT, TestFormNoLayoutNoSections().layout)


    def test_form_without_layout_but_with_sections_should_use_columns_layout(self):
        self.assertEqual(FormLayout.COLUMNS, TestFormNoLayoutButSections().layout)


    def test_form_with_layout_should_apply_layout_specified(self):
        self.assertEqual(FormLayout.COLUMNS, TestFormWithLayout().layout)


class FormSetupRequiredFieldNotReferencedTestCase(CubaneTestCase):
    def test_should_raise_exception_if_required_field_is_not_referenced_by_tabbed_form(self):
        with self.assertRaisesRegexp(ValueError, 'does not refer to required field'):
            TestFormRequiredFieldNotReferenced()


class FormRemoveSectionFieldsTestCase(CubaneTestCase):
    def test_should_remove_all_section_fields_from_form(self):
        form = TestFormWithSectionsBase()
        form_remove_section_fields(form)
        self.assertIsNone(form.fields.get('_title'))
        self.assertIsNone(form.fields.get('_enabled'))


class FormFieldPrefixTestCase(CubaneTestCase):
    def test_field_with_prefix_should_return_field_value_with_given_prefix(self):
        form = TestFormPrefixSuffix({'title': 'Foo'})
        self.assertTrue(form.is_valid())
        self.assertEqual('_Foo', form.field_with_prefix('title', '_'))


    def test_field_with_prefix_should_return_empty_string_if_field_is_empty(self):
        form = TestFormPrefixSuffix({})
        self.assertTrue(form.is_valid())
        self.assertEqual('', form.field_with_prefix('title', '_'))


    def test_field_with_prefix_should_raise_exception_if_form_is_not_validated(self):
        form = TestFormPrefixSuffix({})
        with self.assertRaisesRegexp(AttributeError, 'object has no attribute \'cleaned_data\''):
            form.field_with_prefix('title', '_')


class FormFieldSuffixTestCase(CubaneTestCase):
    def test_field_with_suffix_should_return_field_value_with_given_suffix(self):
        form = TestFormPrefixSuffix({'title': 'Foo'})
        self.assertTrue(form.is_valid())
        self.assertEqual('Foo_', form.field_with_suffix('title', '_'))


    def test_field_with_suffix_should_return_empty_string_if_field_is_empty(self):
        form = TestFormPrefixSuffix({})
        self.assertTrue(form.is_valid())
        self.assertEqual('', form.field_with_suffix('title', '_'))


    def test_field_with_suffix_should_raise_exception_if_form_is_not_validated(self):
        form = TestFormPrefixSuffix({})
        with self.assertRaisesRegexp(AttributeError, 'object has no attribute \'cleaned_data\''):
            form.field_with_suffix('title', '_')


class FormRemoveTabTestCase(CubaneTestCase):
    def test_should_remove_tab(self):
        form = TestFormWithSectionsBase()
        form.remove_tab('Title')
        form.update_sections()

        self.assertIsNotNone(form.fields.get('title'))
        self.assertIsNotNone(form.fields.get('slug'))


    def test_should_remove_tab_and_referenced_fields(self):
        form = TestFormWithSectionsBase()
        form.remove_tab('Title', remove_fields=True)
        form.update_sections()

        self.assertIsNone(form.fields.get('title'))
        self.assertIsNone(form.fields.get('slug'))
        self.assertIsNone(form.fields.get('_title'))


    def test_should_raise_exception_if_tab_does_not_exist(self):
        form = TestFormWithSectionsBase()
        with self.assertRaisesRegexp(ValueError, 'does not exist'):
            form.remove_tab('Does Not Exist')


class FormRemoveTabsTestCase(CubaneTestCase):
    def test_should_remove_all_tabs_but_leave_fields(self):
        form = TestFormWithSectionsBase()
        form.remove_tabs()

        # tabs are gone
        self.assertEqual([], form.tabs)
        self.assertFalse(form.is_tabbed)

        # fields are still there
        self.assertIsNotNone(form.fields.get('_title'))
        self.assertIsNotNone(form.fields.get('title'))
        self.assertIsNotNone(form.fields.get('slug'))
        self.assertIsNotNone(form.fields.get('_enabled'))
        self.assertIsNotNone(form.fields.get('enabled'))


class FormHasTabTestCase(CubaneTestCase):
    def test_should_return_true_if_tab_exists(self):
        self.assertTrue(TestForm().has_tab('Title'))


    def test_should_return_false_if_tab_does_not_exist(self):
        self.assertFalse(TestForm().has_tab('Does Not Exist'))


class FormRemoveFieldTestCase(CubaneTestCase):
    def test_should_remove_form_field_and_section(self):
        form = TestFormWithSectionsBase()
        form.remove_field('title')
        form.update_sections()

        self.assertIsNone(form.fields.get('_title'))
        self.assertIsNone(form.fields.get('title'))


    def test_should_raise_exception_if_field_does_not_exist(self):
        form = TestFormWithSectionsBase()
        with self.assertRaisesRegexp(ValueError, 'does not exist'):
            form.remove_field('does_not_exist')


class FormRemoveMultipleFieldsTestCase(CubaneTestCase):
    def test_should_remove_multiple_fields_and_sections(self):
        form = TestFormWithSectionsBase()
        form.remove_fields(['title', 'enabled'])
        form.update_sections()

        self.assertIsNone(form.fields.get('_title'))
        self.assertIsNone(form.fields.get('title'))
        self.assertIsNone(form.fields.get('_enabled'))
        self.assertIsNone(form.fields.get('enabled'))


    def test_should_raise_exception_if_field_does_not_exist(self):
        form = TestFormWithSectionsBase()
        with self.assertRaisesRegexp(ValueError, 'does not exist'):
            form.remove_fields(['title', 'does_not_exist'])


class FormFieldErrorTestCase(CubaneTestCase):
    def test_should_add_error_to_errorlist_for_given_field(self):
        form = TestFormWithSectionsBase({'title': 'Foo', 'slug': 'Bar'})
        self.assertTrue(form.is_valid())
        form.field_error('title', 'Error')
        self.assertEqual({'title': ['Error']}, form.errors)


    def test_should_raise_exception_if_field_does_not_exist(self):
        form = TestFormWithSectionsBase({'title': 'Foo', 'slug': 'Bar'})
        self.assertTrue(form.is_valid())

        with self.assertRaisesRegexp(ValueError, 'does not exist'):
            form.field_error('does_not_exist', 'Error')


class FormIsDuplicatePropertyTestCase(CubaneTestCase):
    def test_should_set_and_get_property(self):
        form = TestForm()
        self.assertFalse(form.is_duplicate)

        form.is_duplicate = True
        self.assertTrue(form.is_duplicate)


class FormTestCaseBase(CubaneTestCase):
    @classmethod
    def create_user(cls, username, email, password, active=True):
        user = User.objects.create_user(username, email, password)

        if not active:
            user.is_active = active
            user.save()

        return user


    def _create_form_with(self, formclass, data):
        form = formclass(data)
        form.configure(self.request)
        return form


class FormBaseLoginFormTestCase(FormTestCaseBase):
    @classmethod
    def setUpClass(cls):
        super(FormBaseLoginFormTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.post('/')
        cls.request.session = SessionStore()
        cls.email_user = cls.create_user('foo', 'info@innershed.com', 'password')
        cls.inactive_user = cls.create_user('inactive', 'inactive@innershed.com', 'password', active=False)


    @classmethod
    def tearDownClass(cls):
        cls.email_user.delete()
        cls.inactive_user.delete()
        super(FormBaseLoginFormTestCase, cls).tearDownClass()


    def test_should_authenticate_via_username(self):
        form = self._create_form('foo')
        self.assertTrue(form.is_valid())
        self.assertEqual(self.email_user.pk, form.get_user_id())
        self.assertEqual(self.email_user.pk, form.get_user().pk)


    def test_should_authenticate_via_email(self):
        form = self._create_form('info@innershed.com')
        self.assertTrue(form.is_valid())
        self.assertEqual(self.email_user.pk, form.get_user_id())


    def test_should_authenticate_via_email_lowercase(self):
        form = self._create_form('INFO@InnerShed.Com')
        self.assertTrue(form.is_valid())
        self.assertEqual(self.email_user.pk, form.get_user_id())


    def test_should_fail_with_missing_username(self):
        form = self._create_form_with(TestLoginForm, {'password': 'password'})
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_should_fail_with_missing_password(self):
        form = self._create_form_with(TestLoginForm, {'username': 'foo'})
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_should_fail_with_missing_username_and_password(self):
        form = self._create_form_with(TestLoginForm, {})
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_should_fail_with_incorrect_username(self):
        form = self._create_form('user_does_not_exist')
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_should_fail_with_incorrect_email(self):
        form = self._create_form('doesnotexists@innershed.com')
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_should_fail_with_incorrect_password_for_correct_username(self):
        form = self._create_form('foo', 'incorrect-password')
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_should_fail_with_incorrect_password_for_correct_email(self):
        form = self._create_form('info@innershed.com', 'incorrect-password')
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_should_fail_with_inactive_user(self):
        form = self._create_form('inactive')
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INACTIVE_ACCOUNT)


    def test_should_return_none_for_user_if_not_validated(self):
        form = self._create_form('foo')
        self.assertIsNone(form.get_user_id())
        self.assertIsNone(form.get_user())


    def _create_form(self, username, password='password'):
        return self._create_form_with(TestLoginForm, {'username': username, 'password': password})


class FormBasePasswordForgottenFormTestCase(FormTestCaseBase):
    @classmethod
    def setUpClass(cls):
        super(FormBasePasswordForgottenFormTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.post('/')
        cls.request.session = SessionStore()
        cls.user = cls.create_user('foo', 'foo@bar.com', 'password')
        cls.inactive_user = cls.create_user('inactive', 'inactive@bar.com', 'password', active=False)


    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.inactive_user.delete()
        super(FormBasePasswordForgottenFormTestCase, cls).tearDownClass()


    def test_should_return_correct_user_for_existing_email(self):
        form = self._create_form('foo@bar.com')
        self.assertTrue(form.is_valid())
        self.assertEqual(self.user.pk, form.get_user().pk)


    def test_should_return_correct_user_for_existing_email_lowercase(self):
        form = self._create_form('FOO@Bar.Com')
        self.assertTrue(form.is_valid())
        self.assertEqual(self.user.pk, form.get_user().pk)


    def test_should_fail_for_non_existing_user(self):
        form = self._create_form('doesnotexist@bar.com')
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'email', BasePasswordForgottenForm.ERROR_UNKNOWN_EMAIL)


    def test_should_fail_for_inactive_user(self):
        form = self._create_form('inactive@bar.com')
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'email', BasePasswordForgottenForm.ERROR_INACTIVE_ACCOUNT)


    def _create_form(self, email):
        return self._create_form_with(TestPasswordForgottenForm, {'email': email})


class FormBaseChangePasswordFormTestCase(FormTestCaseBase):
    @classmethod
    def setUpClass(cls):
        super(FormBaseChangePasswordFormTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.post('/')
        cls.request.session = SessionStore()


    def test_should_validate_if_password_matches_confirmation(self):
        form = self._create_form('password', 'password')
        self.assertTrue(form.is_valid())


    def test_should_fail_if_password_differs_confirmation(self):
        form = self._create_form('password', '12345678')
        self.assertFalse(form.is_valid())


    def test_should_fail_if_password_differs_confirmation_case(self):
        form = self._create_form('password', 'PASSWORD')
        self.assertFalse(form.is_valid())


    def test_should_fail_with_missing_password(self):
        form = self._create_form(None, 'password')
        self.assertFalse(form.is_valid())


    def test_should_fail_with_missing_password_confirmation(self):
        form = self._create_form('password', None)
        self.assertFalse(form.is_valid())


    def test_should_fail_with_missing_password_and_confirmation(self):
        form = self._create_form(None, None)
        self.assertFalse(form.is_valid())


    def _create_form(self, password, confirm):
      return self._create_form_with(TestChangePasswordForm, {'password': password, 'password_confirm': confirm})
