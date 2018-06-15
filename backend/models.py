# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from cubane.lib.mail import cubane_send_mail_template
from cubane.lib.url import make_absolute_url
from cubane.lib.libjson import to_json, decode_json
from cubane.lib.text import text_from_html
from cubane.models.fields import MultiSelectField
import datetime
import random
import hashlib
import string


class UserProfile(models.Model):
    """
    Provides additional information about user for the backend system, such as
    password reset and dashboard information
    """
    user = models.OneToOneField(User)
    reset = models.BooleanField(db_index=True, default=False)
    dashboard_json = models.TextField(null=True)


    def save(self, *args, **kwargs):
        """
        Save user profile and invalidate local caches.
        """
        super(UserProfile, self).save(*args, **kwargs)
        self.invalidate_dashboard_cache()

    def get_dashboard(self):
        """
        Return information about the user's dashboard.
        """
        if not hasattr(self, '_dashbaord_cache'):
            if self.dashboard_json:
                self._dashbaord_cache = decode_json(self.dashboard_json)
            else:
                self._dashbaord_cache = {}
        return self._dashbaord_cache


    def set_dashboard(self, v):
        """
        Set dashboard information for the current user.
        """
        if v:
            self.dashboard_json = to_json(v)
        else:
            self.dashboard_json = None

        self.invalidate_dashboard_cache()

    dashboard = property(get_dashboard, set_dashboard)


    def invalidate_dashboard_cache(self):
        """
        Invalidate dashboard cache.
        """
        if hasattr(self, '_dashbaord_cache'):
            del self._dashbaord_cache


class UserToken(models.Model):
    """
    One-time usage security token related to user tasks, such as
    password forgotten.
    """
    EXPIRES_HOURS = 1


    user = models.ForeignKey(User)
    hashcode = models.CharField(max_length=128, db_index=True, unique=True)
    usage = models.CharField(max_length=32, db_index=True)
    created_on = models.DateTimeField(db_index=True)


    @classmethod
    def create(cls, user, usage):
        if not user:
            raise ValueError('User cannot be none.')

        if not usage:
            raise ValueError('Usage cannot be none or empty.')

        token = UserToken()
        token.user = user
        token.usage = usage
        token.created_on = datetime.datetime.now()
        token.hashcode = UserToken.generate_hashcode()
        token.save()
        return token


    @classmethod
    def generate_hashcode(cls):
        r = random.SystemRandom()
        return hashlib.sha224(''.join([r.choice(string.printable) for i in range(0, 1024)])).hexdigest()


    @classmethod
    def get_expired(cls):
        """
        Return the timestamp when any given token would have been expired based
        on the current date and time calling this method.
        """
        return datetime.datetime.now() - datetime.timedelta(hours=UserToken.EXPIRES_HOURS)


    @classmethod
    def get_or_404(cls, hashcode, usage):
        """
        Return a valid user token based on the given hashcode and usage or raise 404.
        """
        try:
            return UserToken.objects.get(
                user__isnull=False,
                user__is_active=True,
                hashcode=hashcode,
                usage=usage,
                created_on__gte=UserToken.get_expired()
            )
        except UserToken.DoesNotExist:
            raise Http404('User token with hashcode \'%s\' for usage \'%s\' does not exist, has become invalid or has expired.' % (hashcode, usage))


    @classmethod
    def cleanup(cls):
        """
        Destroy all invalid/expired user tokens.
        """
        tokens = UserToken.objects.filter(
            Q(user__isnull=True) |
            Q(user__is_active=False) |
            Q(created_on__lt=UserToken.get_expired())
        )

        for token in tokens:
            token.delete()


    def send_email(self, request, template, url, subject, message, reason=None):
        """
        Send an email to the customer with the given subject line and message. The email will also contain
        a unique link to prompt the user to perform the desired action, for example to change the password.
        """
        if 'cubane.cms' in settings.INSTALLED_APPS:
            from cubane.cms.views import get_cms
            cms = get_cms()

            if cms.settings.name:
                subject = '%s | %s' % (subject, cms.settings.name)
        else:
            cms = None

        cubane_send_mail_template(
            request,
            self.user.email,
            subject,
            template,
            {
                'message': message,
                'url': make_absolute_url(url),
                'reason': reason,
                'settings': cms.settings if cms else None
            }
        )


class ChangeLog(models.Model):
    """
    Logs changes made through the backend.
    """
    class Meta:
        ordering = ['-created_on']
        verbose_name = 'Changelog'
        verbose_name_plural = 'Changelogs'


    class Listing:
        columns = [
            'title|Title|html',
            'user',
            'action',
            'content_type',
            'restored',
            'created_on'
        ]

        filter_by = [
            ':Title',
            'title',

            ':User and Action',
            'user',
            'action',

            ':Entity Type and Target ID',
            'content_type',
            'target_id',

            ':Date',
            'created_on',

            ':Restored',
            'restored'
        ]


    can_edit = False
    can_create = False
    can_merge = False
    can_add = False
    can_delete = False


    ACTION_CREATE = 'create'
    ACTION_EDIT   = 'edit'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = (
        (ACTION_CREATE, 'Create'),
        (ACTION_EDIT,   'Edit'),
        (ACTION_DELETE, 'Delete')
    )


    title = models.CharField(
        max_length=255,
        db_index=True
    )

    user = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
    )

    action = models.CharField(
        max_length=16,
        null=True,
        choices=ACTION_CHOICES,
        db_index=True
    )

    content_type = models.ForeignKey(
        ContentType,
        null=True
    )

    target_id = models.PositiveIntegerField(
        null=True
    )

    target = GenericForeignKey(
        'content_type',
        'target_id'
    )

    parent = models.ForeignKey(
        'self',
        null=True,
    )

    changes = models.TextField(
        null=True
    )

    hashcode = models.CharField(
        max_length=128,
        db_index=True,
        unique=True
    )

    seq = models.IntegerField(
        db_index=True,
        default=1,
        editable=False
    )

    created_on = models.DateTimeField(
        db_index=True
    )

    restored = models.BooleanField(
        db_index=True,
        default=False
    )


    @property
    def plain_title(self):
        """
        Return the title of this changelog entry without markup.
        """
        return text_from_html(self.title)


    @property
    def listing_annotation(self):
        """
        Return status indication (color annotation)
        """
        return 'success' if self.restored else ''


    @property
    def fields(self):
        """
        Return list of fields that represents the changes that occurred on a
        model instance as part of this changelog entry.
        """
        if not hasattr(self, '_fields'):
            if self.changes is None:
                self._fields = []
            else:
                self._fields = decode_json(self.changes)
                if self._fields is None:
                    self._fields = []
        return self._fields


    @property
    def field_dict(self):
        """
        Return a dictionary that represents the data captured of the model
        instance as part of this changelog entry.
        """
        if not hasattr(self, '_field_dict'):
            self._field_dict = {}
            for field in self.fields:
                key = field.get('n')
                value = field.get('a')
                self._field_dict[key] = value
        return self._field_dict


    @property
    def previous_field_dict(self):
        """
        Return a dictionary that represents the previous data captured of the
        model instance as part of this changelog entry before the instance has
        been changed.
        """
        if not hasattr(self, '_previous_field_dict'):
            self._previous_field_dict = {}
            for field in self.fields:
                key = field.get('n')
                value = field.get('b')
                self._previous_field_dict[key] = value
        return self._previous_field_dict


    def __unicode__(self):
        return self.title