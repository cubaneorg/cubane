# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from cubane.forms import BaseModelForm
from cubane.forms import EmailInput, PhoneInput
from cubane.enquiry.models import *
from cubane.enquiry import captchas


class SimpleEnquiryForm(BaseModelForm):
    """
    Basic enquiry form: name, email and message.
    """
    class Meta:
        tabs = [
            {
                'title': 'Enquiry',
                'fields': [
                    'first_name',
                    'last_name',
                    'email',
                    'message',
                    'captcha',
                    'captcha_hash'
                ]
            },
            {
                'title': 'Extra',
                'fields': [
                    'further_action_required',
                    'action_undertaken',
                    'closed'
                ]
            }
        ]

    # init the captchas
    captcha = captchas.get_captcha_widget() if settings.CAPTCHA else None
    captcha_hash = forms.CharField(max_length=255, widget=forms.HiddenInput, required=False) if hasattr(settings, 'CAPTCHA') and not hasattr(settings, 'CAPTCHA_SECRET_KEY') else None

    def clean(self):
        d = super(SimpleEnquiryForm, self).clean()

        # clean captcha
        if not hasattr(settings, 'CAPTCHA_SECRET_KEY') and hasattr(settings, 'CAPTCHA'):
            captchas.clean_captcha_data(d, self)

        return d


class AdvancedEnquiryForm(BaseModelForm):
    """
    Advanced enquiry form: name, email, message and multiple enquiry methods.
    """
    class Meta:
        tabs = [
            {
                'title': 'Enquiry',
                'fields': [
                    'first_name',
                    'last_name',
                    'email',
                    'contact_email',
                    'contact_tel',
                    'contact_mobile',
                    'tel',
                    'mobile',
                    'message',
                    'captcha',
                    'captcha_hash'
                ]
            },
            {
                'title': 'Extra',
                'fields': [
                    'further_action_required',
                    'action_undertaken',
                    'closed'
                ]
            }
        ]

        sections = {
            'first_name': 'Name and Contact Information',
            'tel': 'How can we contact you?'
        }


    FORM_ERROR_TELEPHONE_REQUIRED = 'Telephone is required if you want to be contacted by telephone.'
    FORM_ERROR_MOBILE_REQUIRED    = 'Mobile phone number is required if you want to be contacted by mobile.'
    FORM_ERROR_NO_CONTACT_INFO    = 'We need at least one way of contacting you. Pleasse tick at least one of the corresponding options.'


    # init the captchas
    captcha = captchas.get_captcha_widget() if settings.CAPTCHA else None
    captcha_hash = forms.CharField(max_length=255, widget=forms.HiddenInput, required=False) if hasattr(settings, 'CAPTCHA') and not hasattr(settings, 'CAPTCHA_SECRET_KEY') else None

    def clean(self):
        """
        Make telephone required if telephone is checked. Same with mobile.
        """
        d = super(AdvancedEnquiryForm, self).clean()

        if d['contact_tel'] and not d['tel']:
            self.field_error('tel', self.FORM_ERROR_TELEPHONE_REQUIRED)

        if d['contact_mobile'] and not d['mobile']:
            self.field_error('mobile', self.FORM_ERROR_MOBILE_REQUIRED)

        # we do need at least one way of contact...
        if not d['contact_email'] and not d['contact_tel'] and not d['contact_mobile']:
            raise forms.ValidationError(self.FORM_ERROR_NO_CONTACT_INFO)

        if not hasattr(settings, 'CAPTCHA_SECRET_KEY') and hasattr(settings, 'CAPTCHA'):
            # clean Captcha
            captchas.clean_captcha_data(d, self)

        return d
