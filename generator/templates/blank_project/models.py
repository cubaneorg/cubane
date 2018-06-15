# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db import models
from django.utils.html import mark_safe
from cubane.models import DateTimeBase
from cubane.cms.models import Entity, SettingsBase, PageAbstract, ChildPage
from cubane.media.models import Media
from cubane.enquiry.models import EnquiryBase


class Settings(SettingsBase):
    """
    Site Settings
    """
    @classmethod
    def get_form(cls):
        from $TARGET_NAME$.forms import SettingsForm
        return SettingsForm


class Enquiry(EnquiryBase):
    """
    Enquiry.
    """
    class Listing:
        columns = ['email', 'created_on']
        filter_by = ['email', 'message']
        data_export = True
        data_import = True


    email = models.EmailField(
        verbose_name='Email',
        db_index=True
    )

    message = models.TextField(
        verbose_name='Message',
        max_length=1000
    )


    @classmethod
    def get_form(cls):
        from $TARGET_NAME$.forms import EnquiryForm
        return EnquiryForm


    def __unicode__(self):
        return self.email


class CustomPage(PageAbstract):
    """
    CMS Page.
    """
    @classmethod
    def get_form(cls):
        from $TARGET_NAME$.forms import CustomPageForm
        return CustomPageForm