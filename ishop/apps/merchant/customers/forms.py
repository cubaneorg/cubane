# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from cubane.backend.forms import BrowseField
from cubane.forms import BaseModelForm, BaseForm
from cubane.ishop import get_customer_model
from cubane.ishop.models import Country
from cubane.postcode.forms import PostcodeLookupField


class BrowseCustomerField(BrowseField):
    """
    Simplified version of browse folder field for browsing shop customers.
    """
    def __init__(self, *args, **kwargs):
        kwargs['model'] = User
        kwargs['name'] = 'Customers'
        kwargs['browse'] = reverse_lazy('cubane.ishop.customers.index')
        kwargs['create'] = reverse_lazy('cubane.ishop.customers.create')
        super(BrowseCustomerField, self).__init__(*args, **kwargs)


class CustomerFormBase(BaseModelForm):
    class Meta:
        model = get_customer_model()
        exclude = ['user', 'legacy_pw', '_custom']
        tabs = [{
            'title': 'Customer',
            'fields': [
                'title',
                'first_name',
                'last_name',
                'postcode_lookup',
                'company',
                'address1',
                'address2',
                'address3',
                'city',
                'county',
                'postcode',
                'country',
                'email',
                'telephone',
                'newsletter'
            ]
        }]

        sections = {
            'title': 'Name',
            'postcode_lookup': 'Billing Address',
            'email': 'Contact Information'
        }

    postcode_lookup = PostcodeLookupField(
        label='Find Address',
        address1='id_address1',
        address2='id_address2',
        address3='id_address3',
        address4=None,
        locality=None,
        city='id_city',
        county='id_county',
        postcode='id_postcode'
    )


    def configure(self, request, instance=None, edit=True):
        super(CustomerFormBase, self).configure(request, instance, edit)

        if 'cubane.postcode' not in settings.INSTALLED_APPS:
            self.remove_field('postcode_lookup')


    def clean_email(self):
        """
        Make sure that the email is not already taken, since it is used for login
        """
        email = self.cleaned_data.get('email', None)

        if email != None:
            customers = get_customer_model().objects.filter(email=email)
            if self._edit:
                customers = customers.exclude(pk=self._instance.pk)
            if customers.count() > 0:
                raise forms.ValidationError('Email address already used. Please provide a different email address.')

        return email


class CustomerChangePasswordForm(BaseForm):
    password = forms.CharField(
        label='New Password',
        max_length=255,
        required=True,
        widget=forms.PasswordInput(attrs={'size': 40, 'class': 'text'}))


    password_confirm = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.PasswordInput(attrs={'size': 40, 'class': 'text'}))


    def clean_password(self):
        password = self.cleaned_data.get('password', None)
        if password:
            if len(password) < 7:
                raise forms.ValidationError('Password needs to be at least 7 characters long.')

        return password


    def clean_password_confirm(self):
        password = self.cleaned_data.get('password', None)
        password_confirm = self.cleaned_data.get('password_confirm', None)

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError('Password Confirmation does not match Password.')

        return password_confirm
