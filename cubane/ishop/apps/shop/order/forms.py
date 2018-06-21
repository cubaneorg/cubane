# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from django.utils.safestring import mark_safe
from cubane.forms import BaseForm, SectionField, EmailInput, PhoneInput, RangeInput
from cubane.ishop import get_customer_model
from cubane.ishop.forms import clean_address
from cubane.ishop.models import Country
from cubane.ishop.basket import Basket
from cubane.postcode.forms import PostcodeLookupField


class DeliveryAddressFrom(BaseForm):
    ADDRESS_FIELD_NAMES = [
        'company',
        'address1',
        'address2',
        'address3',
        'city',
        'country',
        'county',
        'postcode'
    ]


    _customer_information = SectionField(label='Customer Information')

    title = forms.ChoiceField(
        required=True,
        choices=get_customer_model().TITLE_CHOICES
    )

    first_name = forms.CharField(
        label='First Name',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    last_name = forms.CharField(
        label='Last Name',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    email = forms.EmailField(
        max_length=255,
        required=True,
        widget=EmailInput
    )

    telephone = forms.CharField(
        max_length=40,
        required=True,
        widget=PhoneInput
    )

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

    _billing_address = SectionField(label='Billing Address')

    company = forms.CharField(
        label='Company',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    address1 = forms.CharField(
        label='Address 1',
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    address2 = forms.CharField(
        label='Address 2',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    address3 = forms.CharField(
        label='Address 3',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    city = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    country = forms.ModelChoiceField(
        required=True,
        empty_label=None,
        initial='GB',
        queryset=Country.objects.all()
    )

    county = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    postcode = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'size':'10', 'class': 'text'})
    )

    update_profile = forms.BooleanField(
        required=False,
        initial=True,
        help_text='Make this billing address my permanent address to be used for the next checkout.'
    )

    delivery_postcode_lookup = PostcodeLookupField(
        label='Find Address',
        address1='id_delivery_address1',
        address2='id_delivery_address2',
        address3='id_delivery_address3',
        address4=None,
        locality=None,
        city='id_delivery_city',
        county='id_delivery_county',
        postcode='id_delivery_postcode',
        custom_css='text'
    )

    _delivery_address = SectionField(label='Delivery Address')

    FREE_DELIVERY_TO = 'free_delivery_to'
    DELIVERY_BILLING_ADDRESS = 'billing_address'
    DELIVERY_NEW_ADDRESS = 'new_address'
    DELIVERY_COLLECTION = 'click_and_collect'

    DELIVERY_CHOICES = (
        (DELIVERY_COLLECTION, 'Click and Collect'),
        (DELIVERY_BILLING_ADDRESS, 'Deliver to my billing address'),
        (DELIVERY_NEW_ADDRESS, 'Enter new delivery address')
    )
    DELIVERY_CHOICES_RESTRICTED = (
        (DELIVERY_COLLECTION, 'Click and Collect'),
        (DELIVERY_BILLING_ADDRESS, 'Deliver to my billing address'),
    )

    deliver_to = forms.ChoiceField(
        required=True,
        choices=DELIVERY_CHOICES,
        widget=forms.RadioSelect()
    )


    delivery_free_name = forms.CharField(
        label='Name',
        max_length='255',
        required=False
    )

    delivery_name = forms.CharField(
        label='Name',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    delivery_company = forms.CharField(
        label='Company',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    delivery_address1 = forms.CharField(
        label='Address 1',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    delivery_address2 = forms.CharField(
        label='Address 2',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    delivery_address3 = forms.CharField(
        label='Address 3',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    delivery_city = forms.CharField(
        label='City',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    delivery_country = forms.ModelChoiceField(
        label='Country',
        required=False,
        empty_label=None,
        initial='GB',
        queryset=Country.objects.all()
    )

    delivery_county = forms.CharField(
        label='County',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'size':'40', 'class': 'text'})
    )

    delivery_postcode = forms.CharField(
        label='Postcode',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'size':'10', 'class': 'text'})
    )

    _discount = SectionField(label='Discount')

    signup = forms.BooleanField(
        required=False,
        initial=False,
        help_text='Save this information to make checkout quicker next time.'
    )

    password = forms.CharField(
        label='Password',
        min_length=6,
        max_length=255,
        required=False,
        help_text='Your password must be at least 6 characters in length.',
        widget=forms.PasswordInput(render_value=True)
    )

    password_confirm = forms.CharField(
        label='Password (Confirm)',
        min_length=6,
        max_length=255,
        required=False,
        help_text='Confirm your new password.',
        widget=forms.PasswordInput(render_value=True)
    )

    newsletter = forms.BooleanField(
        label='Newsletter',
        required=False,
        initial=False,
        help_text='Yes, subscribe me to the newsletter.'
    )

    delivery_code = forms.CharField(
        label='Delivery Code',
        required=False,
        max_length=32
    )

    special_req = forms.CharField(
        label='Special Requirements',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={'cols': '40', 'rows': '4'}),
        help_text='For example: Special Delivery Requirements.'
    )

    survey = forms.ChoiceField(
        required=False,
        choices=[],
        help_text='Where did you hear about us?'
    )

    finance_option = forms.ModelChoiceField(
        label='Finance Option',
        queryset=None,
        required=False,
        help_text='Choose the finance option that best suits your requirements.'
    )

    loan_deposit = forms.IntegerField(
        label='Deposit',
        required=False,
        widget=RangeInput(attrs={'step': '1', 'min': '10', 'max': '50'})
    )

    terms = forms.BooleanField(
        label='Accept Terms',
        required=True,
        initial=False
    )


    def configure(self, request, basket):
        self._request = request
        self._basket = basket

        fields_list = ['email', 'signup', 'password', 'password_confirm', 'survey']

        if request.settings.has_survey:
           self.fields['survey'].choices = [('', '-------')] + [(o, o) for o in request.settings.get_survey_options()]
        else:
            del self.fields['survey']

        if not request.settings.mailchimp_enabled:
            del self.fields['newsletter']

        # finance option
        self.fields['finance_option'].queryset = basket.get_finance_options_queryset()

        # terms and condition
        if not request.settings.has_terms:
            del self.fields['terms']
        else:
            self.fields['terms'].help_text = mark_safe('I have read and agree to the <a href="' + request.settings.get_terms() +'" target="_blank">terms and conditions</a>.')

        # collect additional delivery address options from customer's profile
        # (only available if we are allowed to edit the delivery address)
        if basket.can_edit_delivery_address and not request.user.is_anonymous():
            addresses = [(x.id, unicode(x)) for x in request.user.delivery_addresses.all()]
            self.fields['deliver_to'].choices += addresses

        if not request.user.is_anonymous():
            # authenticated user with a valid profile do not need to fill out
            # all the information but we pre fill out the majority of the
            # fields...
            self.fields['first_name'].initial = request.user.first_name
            self.fields['last_name'].initial = request.user.last_name

            try:
                p = get_customer_model().objects.get(user=request.user)

                self.fields['title'].initial = p.title
                self.fields['address1'].initial = p.address1
                self.fields['address2'].initial = p.address2
                self.fields['address3'].initial = p.address3
                self.fields['city'].initial = p.city
                self.fields['county'].initial = p.county
                self.fields['postcode'].initial = p.postcode
                self.fields['country'].initial = p.country
                self.fields['telephone'].initial = p.telephone

                if p.newsletter:
                    if 'newsletter' in self.fields:
                        del self.fields['newsletter']
                    if '_newsletter' in self.fields:
                        del self.fields['_newsletter']

                for field in fields_list:
                    if field in self.fields:
                        del self.fields[field]
            except get_customer_model().DoesNotExist:
                pass
        else:
            # guests need to fill out the entire form, copy only the email
            self.fields['email'].initial = request.session.get(settings.GUEST_USER_SESSION_VAR, '')
            del self.fields['update_profile']

        # billing address changable?
        if not basket.can_edit_billing_address:
            for field in self.ADDRESS_FIELD_NAMES:
                del self.fields[field]

        # delivery address changeable?
        if not basket.can_edit_delivery_address:
            self.fields['deliver_to'].choices = self.DELIVERY_CHOICES_RESTRICTED
            for field in self.ADDRESS_FIELD_NAMES:
                del self.fields['delivery_%s' % field]

        # free delivery to
        if basket.can_have_free_delivery_to():
            self.fields['deliver_to'].choices = [(DeliveryAddressFrom.FREE_DELIVERY_TO, 'Free delivery to %s' % basket.get_free_delivery_to())] + self.fields['deliver_to'].choices
        else:
            del self.fields['delivery_code']

        # special requirements
        if not request.settings.special_requirements:
            del self.fields['special_req']


    def clean_email(self):
        """
        Make sure that the email is not taken if the user checked signup.
        """
        signup = self.cleaned_data.get('signup', False)
        email = self.cleaned_data.get('email', None)

        if signup == True:
            if get_customer_model().objects.filter(email=email).count() > 0:
                raise forms.ValidationError('Email address already used. Please provide a different email address for signing up for a new account.')

        return email


    def clean_password(self):
        """
        Password is required if signup is checked
        """
        signup = self.cleaned_data.get('signup', False)
        password = self.cleaned_data.get('password', None)

        if signup == True:
            if not password:
                raise forms.ValidationError('Password is required in order to signup for a new account.')

        return password


    def clean_password_confirm(self):
        """
        Password confirm is required and must match password if signup is checked.
        """
        signup = self.cleaned_data.get('signup', False)
        password = self.cleaned_data.get('password', None)
        password_confirm = self.cleaned_data.get('password_confirm', None)

        if signup == True:
            if not password_confirm:
                raise forms.ValidationError('Password confirmation is required in order to signup for a new account.')
            if password != password_confirm:
                raise forms.ValidationError('Password confirmation is required to match password.')

        return password_confirm


    def clean_deliver_to(self):
        deliver_to = self.cleaned_data.get('deliver_to')

        if deliver_to:
            if self._basket.is_collection_only() and deliver_to != DeliveryAddressFrom.DELIVERY_COLLECTION:
                raise forms.ValidationError('At least one product cannot be delivered and must be collected from store. Please select Click and Collect.')

        return deliver_to


    def clean(self):
        d = super(DeliveryAddressFrom, self).clean()

        # deliver to
        deliver_to = d.get('deliver_to')
        if deliver_to:
            if deliver_to == DeliveryAddressFrom.DELIVERY_NEW_ADDRESS:
                fields = ['delivery_name', 'delivery_address1', 'delivery_city', 'delivery_county', 'delivery_country', 'delivery_postcode']
                for field in fields:
                    if not d.get(field):
                        self._errors[field] = self.error_class(['This field is required for the delivery address.'])

        # finance option is required if we ticked finance option
        loan = d.get('loan')
        finance_option = d.get('finance_option')

        if self._basket.can_have_free_delivery_to():
            delivery_code = d.get('delivery_code')

            if deliver_to == DeliveryAddressFrom.FREE_DELIVERY_TO:
                if delivery_code != self._basket.get_free_delivery_to().delivery_code:
                    self._errors['delivery_code'] =  self.error_class(['Unfortunately we are unable to recognise your free delivery code. Please try again.'])

                if not d.get('delivery_free_name'):
                    self._errors['delivery_free_name'] =  self.error_class(['This field is required for the free delivery.'])


        if loan and not finance_option:
            self.form_error('finance_option', 'This field is required.')
        if loan and not loan_deposit:
            self.form_error('loan_deposit', 'This field is required.')

        # clean address
        return clean_address(self, d)


    def get_address(self):
        """
        Return the address information as provided from this form.
        """
        d = self.cleaned_data
        return {
            'title': d.get('title'),
            'first_name': d.get('first_name'),
            'last_name': d.get('last_name'),
            'name': d.get('delivery_name') if d.get('delivery_name') else d.get('delivery_free_name'),
            'address1': d.get('address1'),
            'address2': d.get('address2'),
            'address3': d.get('address3'),
            'city': d.get('city'),
            'county': d.get('county'),
            'state': d.get('county') if d.get('country').iso == 'US' else '',
            'postcode': d.get('postcode'),
            'country': d.get('country'),
            'country-iso': d.get('country').iso
        }


class DeliveryOptionsFrom(BaseForm):
    delivery_option = forms.ChoiceField(
        label='Delivery Method',
        required=True,
        choices=()
    )

    def configure(self, request, choices, option):
        self._request = request
        self.fields['delivery_option'].choices = choices

        if option:
            self.fields['delivery_option'].initial = option.id
