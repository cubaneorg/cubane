# coding=UTF-8
from __future__ import unicode_literals
from cubane.forms import BaseModelForm
from django import forms
from cubane.forms import NumberInput
from cubane.cms.forms import PageFormBase, PageForm, ChildPageForm, EntityForm
from cubane.cms.views import get_cms
from cubane.directory.models import DirectoryTag
import re


def configure_tags(fields, names):
    choices = get_cms().get_directory_tag_choices()
    for name in names:
        if name in fields:
            fields[name].choices = choices


class DirectoryTagForm(BaseModelForm):
    class Meta:
        model = DirectoryTag
        fields = '__all__'


    def clean_title(self):
        title = self.cleaned_data.get('title')

        if title:
            title = title.lower()

            if len(re.findall(r'[^-\w\d]', title)) > 0:
                raise forms.ValidationError(
                    'The tag name contains invalid characters; only A-Z, 0-9 ' +
                    'are allowed without spaces or punctation characters.'
                )

        return title


class DirectoryContentBaseForm(PageFormBase):
    """
    Form for editing directory content.
    """
    class Meta:
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    '_nav_title:after(title)'
                ]
            }, {
                'title': 'Directory',
                'fields': [
                    'tags',
                    'ptags',
                    'top_priority'
                ]
            }
        ]
        sections = {
            'navigation': 'Navigation',
            'tags': 'Classification (Where it is presented)'
        }


    custom_date = forms.DateField(
        label='Custom Date',
        required=False
    )


    def configure(self, request, instance, edit):
        super(DirectoryContentBaseForm, self).configure(request, instance, edit)
        configure_tags(self.fields, ['tags', 'ptags'])


    def is_colliding(self, slug):
        """
        Return True, if there is already another directory content page of the
        same type with the given slug.
        """
        model = self._instance.__class__
        pages = model.objects.filter(slug=slug)
        if self._edit:
            pages = pages.exclude(pk=self._instance.id)
        return pages.count() > 0


    def clean_slug(self):
        slug = self.cleaned_data.get('slug')

        if slug:
            # is there another directory content (of same type) with
            # the same slug?
            if self.is_colliding(slug):
                raise forms.ValidationError(
                    'There is already a slug with this name. Please ' +
                    'choose another name.'
                )

        return slug


class DirectoryContentAggregatorPageForm(PageForm):
    """
    Form for editing pages that are directory content aggregators.
    """
    class Meta:
        widgets = {
            'max_items': NumberInput()
        }
        tabs = [
            {
                'title': 'Navigation',
                'fields': [
                    'nav_include_tags',
                    'nav_exclude_tags',
                    'nav_order_mode',
                ]
            }, {
                'title': 'Directory',
                'fields': [
                    'include_tags_1',
                    'include_tags_2',
                    'include_tags_3',
                    'include_tags_4',
                    'include_tags_5',
                    'include_tags_6',
                    'exclude_tags',
                    'order_mode',
                    'max_items'
                ]
            }
        ]
        sections = {
            'nav_include_tags': 'Navigation Aggregation (What it presents within the navigation)',
            'include_tags_1': 'Aggregation (What it presents)'
        }


    def configure(self, request, instance, edit):
        super(DirectoryContentAggregatorPageForm, self).configure(request, instance, edit)
        configure_tags(self.fields, [
            'include_tags_1',
            'include_tags_2',
            'include_tags_3',
            'include_tags_4',
            'include_tags_5',
            'include_tags_6',
            'exclude_tags',
            'nav_include_tags',
            'nav_exclude_tags']
        )


class DirectoryContentAggregatorChildPageForm(ChildPageForm):
    """
    Form for editing child pages that are directory content aggregators.
    """
    class Meta:
        widgets = {
            'max_items': NumberInput()
        }
        tabs = [
            {
                'title': 'Directory',
                'fields': [
                    'include_tags_1',
                    'include_tags_2',
                    'include_tags_3',
                    'include_tags_4',
                    'include_tags_5',
                    'include_tags_6',
                    'exclude_tags',
                    'order_mode',
                    'max_items'
                ]
            }
        ]

    def configure(self, request, instance, edit):
        super(DirectoryContentAggregatorChildPageForm, self).configure(request, instance, edit)
        configure_tags(self.fields, [
            'include_tags_1',
            'include_tags_2',
            'include_tags_3',
            'include_tags_4',
            'include_tags_5',
            'include_tags_6',
            'exclude_tags'
        ])


class DirectoryContentAndAggregatorBaseForm(DirectoryContentBaseForm):
    """
    Form for editing pages that are directory content pages and aggregator
    pages at the same time.
    """
    class Meta:
        widgets = {
            'max_items': NumberInput()
        }
        tabs = [
            {
                'title': 'Directory',
                'fields': [
                    'include_tags_1',
                    'include_tags_2',
                    'include_tags_3',
                    'include_tags_4',
                    'include_tags_5',
                    'include_tags_6',
                    'exclude_tags',
                    'order_mode',
                    'max_items',
                    'cascade_tags',
                ]
            }
        ]
        sections = {
            'tags': 'Classification (Where it is presented)',
            'include_tags_1': 'Aggregation (What it presents)'
        }


    def configure(self, request, instance, edit):
        super(DirectoryContentAndAggregatorBaseForm, self).configure(request, instance, edit)
        configure_tags(self.fields, [
            'include_tags_1',
            'include_tags_2',
            'include_tags_3',
            'include_tags_4',
            'include_tags_5',
            'include_tags_6',
            'exclude_tags'
        ])


class DirectoryContentEntityForm(EntityForm):
    class Meta:
        tabs = [
            {
                'title': 'General',
                'fields': []
            },
            {
                'title': 'Visibility',
                'fields': ['disabled']
            },
            {
                'title': 'Directory',
                'fields': [
                    'tags',
                    'ptags',
                    'top_priority'
                ]
            }
        ]
        sections = {
            'tags': 'Classification (Where it is presented)',
        }


    def configure(self, request, instance, edit):
        super(DirectoryContentEntityForm, self).configure(request, instance, edit)
        configure_tags(self.fields, ['tags', 'ptags'])


class DirectoryEntityForm(BaseModelForm):
    """
    Base class for editing cms entities. Derive from this form in order to
    create new cms entity forms for your specific business objects.
    """
    pass


class DirectoryCategoryForm(BaseModelForm):
    class Meta:
        widgets = {
            'max_items': NumberInput()
        }
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'title',
                    'disabled'
                ]
            }, {
                'title': 'Directory',
                'fields': [
                    'include_tags_1',
                    'include_tags_2',
                    'include_tags_3',
                    'include_tags_4',
                    'include_tags_5',
                    'include_tags_6',
                    'exclude_tags',
                    'order_mode',
                    'max_items'
                ]
            }
        ]
        sections = {
            'title': 'Title',
            'include_tags_1': 'Aggregation (What it presents)'
        }


    def configure(self, request, instance, edit):
        super(DirectoryCategoryForm, self).configure(request, instance, edit)
        configure_tags(self.fields, [
            'include_tags_1',
            'include_tags_2',
            'include_tags_3',
            'include_tags_4',
            'include_tags_5',
            'include_tags_6',
            'exclude_tags'
        ])
