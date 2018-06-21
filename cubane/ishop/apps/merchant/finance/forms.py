# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from cubane.forms import BaseForm, BaseModelForm, BootstrapTextInput
from cubane.ishop import get_product_model
from cubane.ishop.models import FinanceOption


class FinanceOptionForm(BaseModelForm):
    """
    Form for editing finance options.
    """
    class Meta:
        model = FinanceOption
        fields = '__all__'
        widgets = {
            'min_basket_value': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'})
        }
        sections = {
            'title': 'Title',
            'min_basket_value': 'Options'
        }


    def configure(self, request, instance, edit):
        super(FinanceOptionForm, self).configure(request, instance, edit)
