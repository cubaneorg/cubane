# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from cubane.forms import BaseModelForm, DateInput, EmailInput, PhoneInput
from cubane.forms import FormLayout, FormSectionLayout
from cubane.cms.forms import SettingsForm, EntityForm, PageForm, ChildPageForm
from cubane.media.forms import BrowseImagesField
from cubane.enquiry import captchas
from $TARGET_NAME$.models import *


class SettingsForm(SettingsForm):
    """
    Form for editing website-wide settings.
    """
    class Meta:
        model = Settings
        fields = '__all__'


    def configure(self, request, instance=None, edit=True):
        super(SettingsForm, self).configure(request, instance, edit)

        # You may want to remove setting fields from the form depending
        # on your needs, e.g.
        # del self.fields['twitter']


class EnquiryForm(BaseModelForm):
    """
    Form for editing enquiries.
    """
    class Meta:
        model = Enquiry
        fields = '__all__'

        tabs = [
            {
                'title': 'Enquiry',
                'fields': [
                    'email',
                    'message'
                ]
            }, {
                'title': 'Additional',
                'fields': [
                    'action_undertaken',
                    'further_action_required',
                    'closed',
                ]
            }
        ]
        sections = {
            'email': 'Contact Information',
            'message': 'Enquiry',
            'action_undertaken': 'Action Taken',
        }

    captcha = captchas.get_captcha_widget('Prevent Spam', 'Please tick the box above, which helps us to prevent SPAM.') if settings.CAPTCHA else None


class FrontendEnquiryForm(EnquiryForm):
    class Meta:
        model = Enquiry
        fields = '__all__'
        layout = FormLayout.FLAT
        sections = FormSectionLayout.NONE


class CustomPageForm(PageForm):
    """
    Form for editing cms pages.
    """
    class Meta:
        model = CustomPage
        fields = '__all__'
