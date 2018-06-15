# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from cubane.forms import BaseForm, SectionField, EmailInput
from cubane.ishop import get_customer_model
from cubane.ishop.models import ProductBase, Country
from cubane.enquiry import captchas


class CustomerLoginForm(forms.Form):
    """
    Customer Login Form
    """
    email    = forms.EmailField(
        label='Email',
        max_length=255,
        widget=EmailInput,
    )

    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput,
    )

    checkout = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput
    )


    def __init__(self, *args, **kwargs):
        self._request = kwargs.pop('request')
        super(CustomerLoginForm, self).__init__(*args, **kwargs)


    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(email=email, password=password)

            if self.user_cache is None:
                raise forms.ValidationError('Please enter a correct username and password. Note that both fields are case-sensitive.')
            elif not self.user_cache.is_active:
                raise forms.ValidationError('This account is inactive.')
        return self.cleaned_data


    def check_for_test_cookie(self):
        if self._request and not self._request.session.test_cookie_worked():
            raise forms.ValidationError('Your Web browser doesn''t appear to have cookies enabled. Cookies are required for logging in.')


    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None


    def get_user(self):
        return self.user_cache


class PasswordForgottenForm(forms.Form):
    """
    Password forgotten form
    """
    email = forms.EmailField(label='Email', max_length=255)


class GuestLoginForm(forms.Form):
    """
    Customer signup or guest form
    """
    email = forms.EmailField(
        label='Email',
        max_length=255,
        widget=EmailInput
    )


################################################################################
# New Customer Form
################################################################################
class NewCustomerForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        max_length=255,
        widget=EmailInput
    )

    checkout = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput
    )


    def configure(self, request):
        self._request = request


    def clean_email(self):
        email = self.cleaned_data['email']
        # check customer and admin
        if get_customer_model().objects.filter(email=email).count() > 0 or get_user_model().objects.filter(email=email).count() > 0:
            raise forms.ValidationError('An account with the given email address already exists. If you forgot your password, please use the password forgotten function.')
        return email


################################################################################
# Full Signup Form
################################################################################
class SignupForm(BaseForm):
    __name = SectionField(label='Your Name')

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

    country = forms.ModelChoiceField(
        required=True,
        empty_label=None,
        initial='GB',
        queryset=Country.objects.all()
    )

    __account = SectionField(label='Account Name and Password')

    email = forms.EmailField(
        label='Email', max_length=255,
        required=True,
        help_text='This E-mail address is also your username for this website',
        widget=EmailInput
    )

    password = forms.CharField(
        label='Password',
        #min_length=6,
        max_length=255,
        required=True,
        help_text='Your password must be at least 6 characters in length.',
        widget=forms.PasswordInput(render_value=True)
    )

    password_confirm = forms.CharField(
        label='Confirm Password',
        min_length=6,
        max_length=255,
        required=True,
        help_text='Confirm your password.',
        widget=forms.PasswordInput(render_value=True)
    )

    _newsletter = SectionField(label='Newsletter (Optional)')

    newsletter = forms.BooleanField(
        label='',
        required=False,
        initial=False,
        help_text='Yes, subscribe me to the newsletter.'
    )

    # init the captchas
    captcha = captchas.get_captcha_widget() if settings.CAPTCHA else None
    captcha_hash = forms.CharField(max_length=255, widget=forms.HiddenInput, required=False) if hasattr(settings, 'CAPTCHA') and not hasattr(settings, 'CAPTCHA_SECRET_KEY') else None

    checkout = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)


    def clean(self):
        d = super(SignupForm, self).clean()

        # clean captcha
        if not hasattr(settings, 'CAPTCHA_SECRET_KEY') and hasattr(settings, 'CAPTCHA'):
            captchas.clean_captcha_data(d, self)

        return d


    def configure(self, request):
        self._request = request

        if not self._request.settings.mailchimp_enabled:
            self.remove_field('newsletter')


    def clean_email(self):
        email = self.cleaned_data['email']
        # check customer and admin
        if get_customer_model().objects.filter(email=email).count() > 0 or get_user_model().objects.filter(email=email).count() > 0:
            raise forms.ValidationError('An account with the given email address already exists. If you forgot your password, please use the password forgotten function.')
        return email


    def clean_password_confirm(self):
        """
        Password confirm must match password.
        """
        password = self.cleaned_data.get('password', None)
        password_confirm = self.cleaned_data.get('password_confirm', None)

        if password != password_confirm:
            raise forms.ValidationError('Password confirmation is required to match password.')

        return password_confirm


################################################################################
# Product order by form
################################################################################
class ProductOrderByForm(forms.Form):
    sort_by = forms.ChoiceField(
        required=False,
        choices = ProductBase.ORDER_BY_CHOICES,
        widget=forms.Select(attrs={'class': 'input-medium'})
    )


    def configure(self, request, has_subcategories=False):
        """
        Configure set of choices that are available for sorting products.
        """
        self.fields['sort_by'].choices = request.settings.get_product_ordering_choices(has_subcategories)


################################################################################
# MailChimp Form
################################################################################

class MailChimpForm(BaseForm):
    name = forms.CharField(
        label = 'Your Name',
        max_length = 255,
        required=True,
        widget=forms.TextInput(attrs={'size':'40', 'class':'text'})
    )

    email = forms.EmailField(
        label='Your Email',
        max_length=255,
        required=True,
        widget=EmailInput
    )


    def clean_name(self):
        name = self.cleaned_data.get('name').strip()
        if name == '':
            raise forms.ValidationError('This field is required.')
        return name
