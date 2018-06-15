# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from django.forms.utils import ErrorList
from cubane.forms import BaseForm, BaseModelForm, BootstrapTextInput
from cubane.ishop.models import DeliveryOption


class DeliveryOptionForm(BaseModelForm):
    class Meta:
        model = DeliveryOption
        exclude = ['seq']
        widgets = {
            'free_delivery_threshold': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
            'uk_def': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
            'eu_def': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
            'world_def': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
            'description': forms.Textarea(attrs={'class': 'editable-html preview no-label full-height'}),
        }
        tabs = [
            {
                'title': 'Delivery',
                'fields': [
                    'title',
                    'enabled',
                    'free_delivery',
                    'free_delivery_threshold',
                    'deliver_uk',
                    'quote_uk',
                    'uk_def',
                    'deliver_eu',
                    'quote_eu',
                    'eu_def',
                    'deliver_world',
                    'quote_world',
                    'world_def',
                ]
            }, {
                'title': 'Description',
                'fields': [
                    'description'
                ]
            }
        ]
        sections = {
            'title': 'Title',
            'free_delivery': 'Free Delivery',
            'deliver_uk': 'UK Delivery',
            'deliver_eu': 'EU Delivery',
            'deliver_world': 'Worldwide Delivery'
        }


    def _clean_delivery_to(self):
        uk = self.cleaned_data.get('deliver_uk')
        eu = self.cleaned_data.get('deliver_eu')
        world = self.cleaned_data.get('deliver_world')

        if not any([uk, eu, world]):
            msg = 'At least one delivery destination must be selected.'
            self._errors.setdefault('deliver_uk', ErrorList()).append(msg)
            raise forms.ValidationError(msg)


    def _clean_required(self, prefix):
        d = self.cleaned_data.get('deliver_%s' % prefix, None)
        v = self.cleaned_data.get('%s_def' % prefix, None)

        if d:
            if v == None:
                self._errors.setdefault('%s_def' % prefix, ErrorList()).append('This field is required.')


    def _clean_free_delivery_threshold(self):
        free_delivery = self.cleaned_data.get('free_delivery')
        t = self.cleaned_data.get('free_delivery_threshold')

        # threshold is required if free delivery is activated
        if free_delivery and not t:
            self._errors.setdefault('free_delivery_threshold', ErrorList()).append('This field is required if free delivery is activated.')


    def clean_title(self):
        title = self.cleaned_data['title']
        q = DeliveryOption.objects.filter(title=title)
        if self.instance != None and hasattr(self.instance, 'id'):
            q = q.exclude(pk=self.instance.id)
        if q.count() > 0:
            raise forms.ValidationError("The given title '%s' has already been used for another delivery option." % title)
        return title


    def clean(self):
        self._clean_delivery_to()

        self._clean_required('uk')
        self._clean_required('eu')
        self._clean_required('world')

        self._clean_free_delivery_threshold()

        return self.cleaned_data
