# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.core.urlresolvers import reverse_lazy
from cubane.forms import BaseForm, BaseModelForm
from cubane.forms import DateInput
from cubane.backend.forms import BrowseField, GalleryField, ModelCollectionField
from cubane.cms.forms import EntityForm, ChildPageForm, PageForm
from cubane.cms.forms import BrowsePagesField
from cubane.ishop.forms import ShopSettingsForm
from cubane.enquiry.forms import AdvancedEnquiryForm, BaseModelForm
from cubane.media.forms import BrowseImagesField, BrowseDocumentsField
from cubane.directory.forms import DirectoryContentBaseForm
from cubane.directory.forms import DirectoryContentAggregatorPageForm
from cubane.directory.forms import DirectoryContentAggregatorChildPageForm
from cubane.directory.forms import DirectoryContentAndAggregatorBaseForm
from cubane.directory.forms import DirectoryContentEntityForm
from cubane.directory.forms import DirectoryCategoryForm
from cubane.testapp.models import *


class SettingsForm(ShopSettingsForm):
    """
    Form for editing cms settings.
    """
    class Meta:
        model = Settings
        fields = '__all__'


class EnquiryForm(AdvancedEnquiryForm):
    """
    Form for editing enquiries.
    """
    class Meta:
        model = Enquiry
        fields = '__all__'


class CustomEnquiryForm(BaseModelForm):
    """
    Custom enquiry form.
    """
    class Meta:
        model = Enquiry
        fields = '__all__'


    enquiry_title = forms.CharField(max_length=255)


class CustomPageForm(PageForm):
    """
    Form for editing custom pages.
    """
    class Meta:
        model = CustomPage
        fields = '__all__'


class CustomChildPageForm(ChildPageForm):
    """
    Form for editing custom child pages.
    """
    class Meta:
        model = CustomChildPage
        fields = '__all__'


class CustomDirectoryPageForm(DirectoryContentAggregatorPageForm):
    """
    Form for editing cms pages (directory).
    """
    class Meta:
        model = CustomDirectoryPage
        fields = '__all__'


class TestModelForm(EntityForm):
    """
    Form for editing a TestModel.
    """
    class Meta:
        model = TestModel
        fields = '__all__'


class TestModelFilterByCountryForm(EntityForm):
    """
    Form for editing a TestModelFilterByCountry.
    """
    class Meta:
        model = TestModelFilterByCountry
        fields = '__all__'


class TestModelWithManyToManyForm(EntityForm):
    """
    Form for editing a TestModelWithManyToMany.
    """
    class Meta:
        model = TestModelWithManyToMany
        fields = '__all__'


class TestModelImportExportForm(EntityForm):
    """
    Form that is involved in testing data import.
    """
    class Meta:
        model = TestModelImportExport
        fields = '__all__'


class TestModelImportNumericZeroForm(EntityForm):
    """
    Form that is involved in testing data import.
    """
    class Meta:
        model = TestModelImportNumericZero
        fields = '__all__'


class TestMultiSelectFieldForm(BaseModelForm):
    """
    Form for testing MultiSelectField.
    """
    class Meta:
        model = TestMultiSelectField
        fields = '__all__'


class TestMultiSelectOptGroupFieldForm(BaseModelForm):
    """
    Form for testing MultiSelectField (OptGroup).
    """
    class Meta:
        model = TestMultiSelectOptGroupChoicesField
        fields = '__all__'


class TestTagsFieldForm(BaseModelForm):
    """
    Form for testing TagsField.
    """
    class Meta:
        model = TestTagsField
        fields = '__all__'


class TestTagsOptGroupFieldForm(BaseModelForm):
    """
    Form for testing TagsField (OptGroup).
    """
    class Meta:
        model = TestTagsOptGroupField
        fields = '__all__'


class TestGalleryFieldForm(BaseForm):
    images = GalleryField(queryset=Media.objects.all())


class TestModelCollectionFieldForm(BaseForm):
    pages = ModelCollectionField(queryset=Page.objects.all())


class TestDirectoryContentForm(DirectoryContentBaseForm):
    class Meta:
        model = TestDirectoryContent
        fields = '__all__'


class TestDirectoryPageAggregatorForm(DirectoryContentAggregatorPageForm):
    class Meta:
        model = TestDirectoryPageAggregator
        fields = '__all__'


class TestDirectoryContentAggregatorChildPageForm(DirectoryContentAggregatorChildPageForm):
    class Meta:
        model = TestDirectoryChildPageAggregator
        fields = '__all__'


class TestDirectoryContentAndAggregatorForm(DirectoryContentAndAggregatorBaseForm):
    class Meta:
        model = TestContentAggregator
        fields = '__all__'


class TestDirectoryContentEntityForm(DirectoryContentEntityForm):
    class Meta:
        model = TestDirectoryContentEntity
        fields = '__all__'
        tabs = [
            {
                'title': 'Title',
                'fields': ['title']
            }
        ]


class TestDirectoryCategoryForm(DirectoryCategoryForm):
    class Meta:
        model = TestDirectoryCategory
        fields = '__all__'