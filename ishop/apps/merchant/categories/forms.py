# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from django.forms import widgets, fields
from django.core.urlresolvers import reverse_lazy
from django.template.defaultfilters import slugify
from cubane.ishop import get_category_model
from cubane.backend.forms import BrowseField, BrowseTreeField, GalleryField
from cubane.forms import BaseModelForm
from cubane.lib.tree import is_any_child_of
from cubane.cms.forms import MetaPreviewWidget, EditableHtmlWidget
from cubane.media.forms import BrowseImagesField
from cubane.media.models import Media


class BrowseCategoryField(BrowseTreeField):
    """
    Simplified version of browse folder field for browsing shop categories.
    """
    def __init__(self, *args, **kwargs):
        model = get_category_model()
        kwargs['model'] = model
        kwargs['browse'] = reverse_lazy('cubane.ishop.%s.index' % slugify(model._meta.verbose_name_plural))
        kwargs['create'] = reverse_lazy('cubane.ishop.%s.create' % slugify(model._meta.verbose_name_plural))
        super(BrowseCategoryField, self).__init__(*args, **kwargs)


class CategoryFormBase(BaseModelForm):
    class Meta:
        model = get_category_model()
        exclude = ['seq', '_nav']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'slugify', 'autocomplete': 'off'}),
            'slug': forms.TextInput(attrs={'class': 'slug', 'autocomplete': 'off'}),
            '_excerpt': widgets.Textarea(attrs={'rows': '8'}),
            '_legacy_urls': widgets.Textarea(attrs={'rows': '4'}),
            'description': EditableHtmlWidget(no_label=True, full_height=True),
            'google_product_category': forms.Select(attrs={'class': 'select-tags'})
        }
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'title',
                    'slug',
                    'parent',
                    '_legacy_urls',
                    '_excerpt',
                    '_meta_title',
                    '_meta_description',
                    '_meta_keywords',
                    '_meta_preview'
                ]
            }, {
                'title': 'Content',
                'fields': [
                    'description'
                ]
            }, {
                'title': 'Gallery',
                'fields': [
                    'image',
                    '_gallery_images'
                ]
            }, {
                'title': 'Options',
                'fields': [
                    'nav',
                    'navigation_title',
                    'enabled',
                    'auth_required',
                    'ordering_default',
                    'google_product_category'
                ]
            }
        ]
        sections = {
            'title': 'Category Data',
            '_excerpt': 'Excerpt',
            '_meta_title': 'Meta Data',
            '_meta_preview': 'Search Result Preview',
            'nav': 'Navigation',
            'enabled': 'Options'
        }


    parent = BrowseCategoryField(
        required=False,
        help_text='The parent category of this category.'
    )

    _meta_preview = fields.Field(
        label=None,
        required=False,
        help_text='This preview is for demonstration purposes only ' +\
            'and the actual search result may differ from the preview. '
    )

    image = BrowseImagesField(
        required=False,
        help_text='Choose the main image that is used to represent this category.'
    )

    _gallery_images = GalleryField(
        label='Image Gallery',
        required=False,
        queryset=Media.objects.filter(is_image=True),
        help_text='Add an arbitarily number of images to this category.'
    )

    nav = forms.MultipleChoiceField(
        label='Navigation',
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=settings.CMS_NAVIGATION,
        help_text='Tick the navigation sections in which this page ' +
                  'should appear in.'
    )


    def configure(self, request, instance, edit):
        super(CategoryFormBase, self).configure(request, instance, edit)

        # meta preview control
        self.fields['_meta_preview'].widget = MetaPreviewWidget(attrs={
            'class': 'no-label',
            'path': request.path_info,
            'form': self
        })

        # navigation
        if edit or self.is_duplicate:
            self.fields['nav'].initial = instance.nav

        # product ordering (only present choices that have been
        # activated in settings)...
        if hasattr(request.settings, 'get_product_ordering_choices'):
            self.fields['ordering_default'].choices = \
                [('', '-------')] + request.settings.get_product_ordering_choices(has_subcategories=True)
        else:
            self.fields['ordering_default'].choices = [('', '-------')]

    def clean__legacy_urls(self):
        # remove \r from legacy_urls
        legacy_urls = self.cleaned_data.get('_legacy_urls')
        if legacy_urls:
            return legacy_urls.replace('\r', '')
        return legacy_urls


    def clean_parent(self):
        parent = self.cleaned_data.get('parent')
        if parent:
            # tree node cannot have itself as a parent
            if parent.id and self.instance.id and parent.id == self.instance.id:
                raise forms.ValidationError('Cannot have itself as parent.')

            # new parent node cannot be a child of the node we are editing
            if is_any_child_of(parent, self.instance):
                raise forms.ValidationError('New parent cannot be a child of this category.')

        return parent
