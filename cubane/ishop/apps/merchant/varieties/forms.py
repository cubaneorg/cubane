# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.forms.formsets import BaseFormSet, formset_factory
from django.core.urlresolvers import reverse_lazy
from django.template.defaultfilters import slugify
from cubane.forms import ColorInput
from cubane.forms import BaseForm, BaseModelForm, BootstrapTextInput
from cubane.media.forms import BrowseImagesField, BrowseMediaThumbnailField
from cubane.ishop.models import ShopSettings, Variety, VarietyOption
from cubane.backend.forms import BrowseTreeField


class BrowseVarietyField(BrowseTreeField):
    """
    Simplified version of browse folder field for browsing varieties.
    """
    def __init__(self, *args, **kwargs):
        model = Variety
        kwargs['model'] = model
        kwargs['browse'] = reverse_lazy('cubane.ishop.%s.index' % slugify(model._meta.verbose_name_plural))
        kwargs['create'] = reverse_lazy('cubane.ishop.%s.create' % slugify(model._meta.verbose_name_plural))
        super(BrowseVarietyField, self).__init__(*args, **kwargs)


class VarietyForm(BaseModelForm):
    class Meta:
        model = Variety
        fields = '__all__'

        widgets = {
            'display_title': forms.TextInput(attrs={'class': 'slugify', 'autocomplete': 'off'}),
            'slug': forms.TextInput(attrs={'class': 'slug', 'autocomplete': 'off'}),
        }
        sections = {
            'title': 'Variety Data',
            'sku': 'Options',
            'style': 'Presentation',
            'layer': 'SVG Image Layer'
        }


    parent = BrowseVarietyField(
        required=False,
        help_text='The parent variety of this variety.'
    )


    def configure(self, request, instance, edit):
        """
        Configure form.
        """
        super(VarietyForm, self).configure(request, instance, edit)

        # kit builder
        if not settings.SHOP_ENABLE_KIT_BUILDER:
            self.remove_field('layer')

        # unit is not used (yet)
        self.remove_field('unit')

        # update sections
        self.update_sections()


    def clean_slug(self):
        """
        Ensure that slug is unique among all varieties.
        """
        slug = self.cleaned_data.get('slug')

        if slug:
            varieties = Variety.objects.filter(slug=slug)
            if self._edit and self._instance:
                varieties = varieties.exclude(pk=self._instance.pk)
            if varieties.count() > 0:
                raise forms.ValidationError(
                    'The slug \'%s\' is already used by another variety.' % slug
                )

        return slug


class VarietyAssignmentForm(BaseForm):
    """
    Properties for a single assigned variety option in combination with a variety and a product.
    These properties essentially overwrite global properties on a per product basis.
    """
    enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'variety-enabled'})
    )

    title = forms.CharField(
        required=False,
        max_length=255,
        label='Label',
        widget=forms.TextInput(attrs={'readonly':'readonly'})
    )

    offset_type = forms.ChoiceField(
        required=False,
        label='Type',
        choices=VarietyOption.OFFSET_CHOICES,
        widget=forms.Select(attrs={'class': 'variety-offset-type input-small'})
    )

    offset_value = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        label='Offset',
        widget=BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'variety-offset-value rounded input-mini'})
    )

    text_label = forms.BooleanField(
        label='Label',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'variety-label', 'readonly': 'readonly', 'onclick': 'return false;'})
    )

    option_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )


class VarietyAttributeAssignmentForm(BaseForm):
    enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'variety-enabled'})
    )

    title = forms.CharField(
        required=False,
        max_length=255,
        label='Label',
        widget=forms.TextInput(attrs={'readonly':'readonly'})
    )

    option_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )


class VarietyOptionForm(BaseForm):
    """
    Properties for a single option as part of a variety.
    """
    enabled = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'variety-enabled'})
    )

    image = BrowseMediaThumbnailField(
        required=False
    )

    color = forms.CharField(
        label='Colour',
        max_length=16,
        required=False,
        widget=ColorInput()
    )

    title = forms.CharField(
        required=False,
        max_length=255,
        label='Label',
        widget=forms.TextInput(attrs={'class': 'input-medium'})
    )

    offset_type = forms.ChoiceField(
        required=False,
        label='Type',
        choices=VarietyOption.OFFSET_CHOICES,
        widget=forms.Select(attrs={'class': 'variety-offset-type input-small'})
    )

    offset_value = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        label='Offset',
        widget=BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'variety-offset-value rounded input-mini'})
    )

    text_label = forms.BooleanField(
        label='Label',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'variety-label'})
    )

    seq = forms.IntegerField(required=False, widget=forms.HiddenInput())
    _id = forms.IntegerField(required=False, widget=forms.HiddenInput())


class VarietyOptionBackendForm(BaseModelForm):
    class Meta:
        model = VarietyOption
        fields = '__all__'
        widgets = {
            'color': ColorInput()
        }
        sections = {
            'title': 'Title',
            'default_offset_type': 'Price Offset',
            'image': 'Presentation',
            'text_label': 'Custom Text Label'
        }


    image = BrowseImagesField(required=False)


class VarietyOptionImportForm(BaseForm):
    import_variety = forms.ModelChoiceField(
        label='Import Options',
        required=False,
        queryset=None,
        help_text='Select another variety from which options can be imported.'
    )


    def configure(self, request, exclude):
        varieties = Variety.objects.all()
        if exclude:
            varieties = varieties.exclude(pk=exclude.pk)
        self.fields['import_variety'].queryset = varieties


class VarietyOptionAttributeForm(BaseForm):
    enabled = forms.BooleanField(
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'variety-enabled'})
    )

    image = BrowseMediaThumbnailField(
        required=False
    )

    title = forms.CharField(
        required=False,
        max_length=255,
        label='Label',
        widget=forms.TextInput(attrs={'class': 'input-medium'})
    )

    seq = forms.IntegerField(required=False, widget=forms.HiddenInput())
    _id = forms.IntegerField(required=False, widget=forms.HiddenInput())


class BaseVarietyFormset(BaseFormSet):
    pass
VarietyFormset = formset_factory(VarietyOptionForm, formset=BaseVarietyFormset, can_delete=True, extra=5)
VarietyAttributeFormset = formset_factory(VarietyOptionAttributeForm, formset=BaseVarietyFormset, can_delete=True, extra=5)


class BaseVarietyAssignmentFormset(BaseFormSet):
    pass
VarietyAssignmentFormset = formset_factory(VarietyAssignmentForm, formset=BaseVarietyAssignmentFormset, can_delete=False, extra=0)
VarietyAttributeAssignmentFormset = formset_factory(VarietyAttributeAssignmentForm, formset=BaseVarietyAssignmentFormset, can_delete=False, extra=0)
