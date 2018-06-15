# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from django.contrib.auth import get_user_model
from cubane.forms import BaseForm, SectionField, EmailInput
from cubane.ishop import get_customer_model
from cubane.ishop.models import Country
from cubane.ishop.forms import clean_address
from cubane.postcode.forms import PostcodeLookupField


class ChangeDetailsForm(BaseForm):
    _name = SectionField(label='Personal Details', help_text='These details are also used on your delivery address')

    title = forms.ChoiceField(
        required=True,
        choices=get_customer_model().TITLE_CHOICES)

    first_name = forms.CharField(
        label='First Name',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    last_name = forms.CharField(
        label='Last Name',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    phone = forms.CharField(
        label='Phone',
        max_length=40,
        required=True,
        help_text='We may give you a call regarding your order if required.'
    )

    email_address = forms.EmailField(
        label='Email',
        help_text='This E-mail address is also your username for this website',
        widget=EmailInput
    )

    newsletter = forms.BooleanField(
        label='',
        required=False,
        initial=False,
        help_text='Yes, subscribe me to the newsletter.'
    )


    def configure(self, request):
        self._request = request
        u = self._request.user
        p = get_customer_model().objects.get(user=u)

        self.fields['first_name'].initial = u.first_name
        self.fields['last_name'].initial = u.last_name
        self.fields['email_address'].initial = u.email

        self.fields['title'].initial = p.title
        self.fields['phone'].initial = p.telephone
        self.fields['newsletter'].initial = p.newsletter

        if not request.settings.mailchimp_enabled:
            self.remove_field('newsletter')


    def clean(self):
        d = super(ChangeDetailsForm, self).clean()
        return clean_address(self, d)


    def clean_email_address(self):
        email = self.cleaned_data['email_address']

        if 'email_address' in self.changed_data:
            if get_customer_model().objects.filter(email=email).count() > 0 or get_user_model().objects.filter(email=email).count() > 0:
                raise forms.ValidationError('An account with the given email address already exists.')
        return email


class BillingAddressForm(BaseForm):
    postcode_lookup = PostcodeLookupField(
        label='Find Address',
        address1='id_address1',
        address2='id_address2',
        address3='id_address3',
        address4=None,
        locality=None,
        city='id_city',
        county='id_county',
        postcode='id_postcode',
        custom_css='text'
    )

    __name = SectionField(label='Name')

    title = forms.ChoiceField(
        required=True,
        choices=get_customer_model().TITLE_CHOICES)

    first_name = forms.CharField(
        label='First Name',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    last_name = forms.CharField(
        label='Last Name',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))


    __address = SectionField(label='Address')


    company = forms.CharField(
        label='Company',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))


    address1 = forms.CharField(
        label='Address 1',
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    address2 = forms.CharField(
        label='Address 2',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    address3 = forms.CharField(
        label='Address 3',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    city = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    country = forms.ModelChoiceField(
        required=True,
        empty_label=None,
        initial='GB',
        queryset=Country.objects.all())

    county = forms.CharField(
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    postcode = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'size':'10', 'class': 'text'}))


    def configure(self, request):
        self._request = request
        u = self._request.user
        p = get_customer_model().objects.get(user=u)

        self.fields['first_name'].initial = u.first_name
        self.fields['last_name'].initial = u.last_name
        self.fields['title'].initial = p.title
        self.fields['company'].initial = p.company

        self.fields['address1'].initial = p.address1
        self.fields['address2'].initial = p.address2
        self.fields['address3'].initial = p.address3
        self.fields['city'].initial = p.city
        self.fields['county'].initial = p.county
        self.fields['postcode'].initial = p.postcode
        self.fields['country'].initial = p.country

        if 'cubane.postcode' not in settings.INSTALLED_APPS:
            self.remove_field('postcode_lookup')


    def clean(self):
        d = super(BillingAddressForm, self).clean()
        return clean_address(self, d)


class DeliveryAddressForm(BaseForm):
    delivery_postcode_lookup = PostcodeLookupField(
        label='Find Address',
        address1='id_address1',
        address2='id_address2',
        address3='id_address3',
        address4=None,
        locality=None,
        city='id_city',
        county='id_county',
        postcode='id_postcode',
        custom_css='text'
    )


    name = forms.CharField(
        label='Name',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))


    company = forms.CharField(
        label='Company',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))


    address1 = forms.CharField(
        label='Address 1',
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    address2 = forms.CharField(
        label='Address 2',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    address3 = forms.CharField(
        label='Address 3',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    city = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    country = forms.ModelChoiceField(
        required=True,
        empty_label=None,
        initial='GB',
        queryset=Country.objects.all())

    county = forms.CharField(
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'}))

    postcode = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'size':'10', 'class': 'text'}))


    def configure(self, request):
        self._request = request

        if 'cubane.postcode' not in settings.INSTALLED_APPS:
            self.remove_field('delivery_postcode_lookup')


    def clean(self):
        d = super(DeliveryAddressForm, self).clean()
        return clean_address(self, d)


class ChangePasswordForm(BaseForm):
    current = forms.CharField(
        label='Current Password',
        min_length=6,
        max_length=255,
        required=True,
        widget=forms.PasswordInput(render_value=True)
    )

    password = forms.CharField(
        label='New Password',
        min_length=6,
        max_length=255,
        required=True,
        help_text='Your new password must be at least 6 characters in length.',
        widget=forms.PasswordInput(render_value=True)
    )

    password_confirm = forms.CharField(
        label='New Password',
        min_length=6,
        max_length=255,
        required=True,
        help_text='Confirm your new password.',
        widget=forms.PasswordInput(render_value=True)
    )

    def configure(self, request):
        self._request = request


    def clean_current(self):
        data = self.data
        if not self._request.user.check_password(data.get('current')):
            raise forms.ValidationError('Your Current Password is incorrect.')


    def clean_password(self):
        data = self.data

        if data.get('password') != data.get('password_confirm'):
            raise forms.ValidationError('Your New Password\'s do not match.')

        return data.get('password')
