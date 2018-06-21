# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.forms.formsets import BaseFormSet, formset_factory
from django.template.defaultfilters import slugify
from cubane.forms import BaseModelForm, DateInput, NumberInput, BootstrapTextInput
from cubane.ishop import get_category_model
from cubane.ishop.models import Voucher
import re


class CategoriesChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        super(CategoriesChoiceField, self).__init__(*args, **kwargs)


    def label_from_instance(self, obj):
        return obj.get_title_and_parent_title()


class VoucherForm(BaseModelForm):
    class Meta:
        model = Voucher
        fields = '__all__'
        widgets = {
            'max_usage': NumberInput(),
            'valid_from': DateInput(),
            'valid_until': DateInput(),
            'categories': forms.CheckboxSelectMultiple(),
            'delivery_countries': forms.CheckboxSelectMultiple()
        }
        sections = {
            'title': 'Name and Discount Code',
            'valid_from': 'Time Range and Discount',
            'categories': 'Categories',
            'delivery_countries': 'Delivery Countries'
        }


    categories = CategoriesChoiceField(
        queryset=None,
        label='Categories',
        required=False,
        help_text='Limit products for which this voucher may apply per category. ' +
                  'Individual products may not qualify for discounts.'
    )


    def configure(self, request, edit, instance):
        super(VoucherForm, self).configure(request, edit, instance)

        self.fields['categories'].queryset = get_category_model().objects \
            .filter(siblings=None) \
            .order_by('parent__title', 'title')


    def clean_code(self):
        """
        Make CODE uppercase and trim.
        """
        code = self.cleaned_data.get('code')

        if code:
            code = re.sub(r'\s', '', code.upper().strip())

        return code


    def clean_valid_until(self):
        """
        End date must be after start date.
        """
        data = self.cleaned_data

        if data.get('valid_from') >= data.get('valid_until'):
            raise forms.ValidationError('Valid to date must be after the Valid from date')

        return data.get('valid_until')


    def clean(self):
        d = super(VoucherForm, self).clean()

        # discount value not required? -> Default to zero.
        discount_type = d.get('discount_type')
        discount_value = d.get('discount_value')
        if discount_type is not None:
            if discount_type in Voucher.DISCOUNT_VALUE_REQUIRED:
                if not discount_value:
                    self.field_error(
                        'discount_value',
                        'This field is required for the chosen type of discount.'
                    )
            else:
                discount_value = 0

        d['discount_value'] = discount_value

        return d
