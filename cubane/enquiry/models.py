# coding=UTF-8
from __future__ import unicode_literals
from django.db import models
from cubane.models import DateTimeReadOnlyBase


class EnquiryBase(DateTimeReadOnlyBase):
    """
    Base Enquiry.
    """
    class Meta:
        abstract = True


    # website owner comments
    action_undertaken = models.TextField(
        verbose_name='Action undertaken',
        blank=True,
        default=''
    )

    further_action_required = models.TextField(
        verbose_name='Further action required',
        blank=True,
        default=''
    )

    # flag to mark enquiries that have been dealt with
    closed = models.BooleanField(
        verbose_name='Closed',
        default=False,
        db_index=True,
        help_text='Enquiry was \'dealt with\'.'
    )


    def __unicode__(self):
        return self.email


class SimpleEnquiry(EnquiryBase):
    """
    Simplae enquiry: name, email and message.
    """
    class Meta:
        abstract = True


    class Listing:
        columns = [
            'first_name',
            'last_name',
            'email',
            'closed',
            'created_on'
        ]
        edit_columns = [
            'first_name',
            'last_name',
            'email',
            'closed'
        ]
        filter_by = [
            'first_name',
            'last_name',
            'email',
        ]
        edit_view = True


    first_name = models.CharField(
        verbose_name='First name',
        max_length=255,
        db_index=True
    )

    last_name = models.CharField(
        verbose_name='Surname',
        max_length=255,
        db_index=True
    )

    email = models.EmailField(
        verbose_name='Your email address',
        db_index=True,
        help_text='We will use your email address in order to reply to your enquiry shortly.'
    )

    message = models.TextField(
        verbose_name='Enquiry message',
        max_length = 1000,
        help_text='Please enter your enquiry...(max. 1000 characters).'
    )


class AdvancedEnquiry(EnquiryBase):
    """
    Advances enquiry based on multiple contact options.
    """
    class Meta:
        abstract = True


    class Listing:
        columns = [
            'email',
            '/first_name',
            '/last_name',
            '/closed',
            '/created_on',
        ]
        edit_columns = [
            '/first_name',
            '/last_name',
            'email',
            '/closed',
            'contact_email|Email',
            'contact_tel|Tel',
            'contact_mobile|Mobile'
        ]
        filter_by = [
            'first_name',
            'last_name',
            'email',
            'contact_email',
            'contact_tel',
            'contact_mobile',
            'tel',
            'mobile',
        ]
        edit_view = True


    first_name = models.CharField(
        verbose_name='First name',
        max_length=255,
        db_index=True
    )

    last_name = models.CharField(
        verbose_name='Surname',
        max_length=255,
        db_index=True
    )

    email = models.EmailField(
        verbose_name='Your email address',
        db_index=True,
        help_text='We may use your email address for further enquiries only if you\'ve ticked the corresponding option.'
    )

    contact_email = models.BooleanField(
        verbose_name='Please contact me by...',
        default=True,
        db_index=True,
        help_text='Email'
    )

    contact_tel = models.BooleanField(
        verbose_name='',
        db_index=True,
        help_text='Telephone'
    )

    contact_mobile = models.BooleanField(
        verbose_name='',
        db_index=True,
        help_text='Mobile'
    )

    tel = models.CharField(
        verbose_name='Telephone',
        null=True,
        blank=True,
        max_length=255,
        db_index=True,
        help_text='Optional, unless you specify that you would like to be contacted via this telephone number.'
    )

    mobile = models.CharField(
        verbose_name='Mobile',
        null=True,
        blank=True,
        max_length=255,
        db_index=True,
        help_text='Optional, unless you specify that you would like to be contact via this mobile phone number.'
    )

    message = models.TextField(
        verbose_name='Enquiry message',
        max_length = 1000,
        help_text='Please enter your enquiry...(max. 1000 characters).'
    )
