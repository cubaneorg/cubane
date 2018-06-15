# coding=UTF-8
from __future__ import unicode_literals
from django.contrib.auth.models import User, Group, Permission


class ProxyUser(User):
    """
    Proxy for default user model, so that we can define additional
    listing options.
    """
    class Meta:
        proxy               = True
        app_label           = 'auth'
        verbose_name        = 'User'
        verbose_name_plural = 'Users'


    class Listing:
        columns = [
            'username',
            'email',
            'first_name',
            'last_name',
            '/is_active',
        ]
        filter_by = [
            ':Name',
            'first_name',
            'last_name',
            'email',

            ':Status',
            'is_active',
            'is_staff',
            'is_superuser',
        ]
        edit_view = True
        data_export = True
        data_columns = [
            'username',
            'first_name',
            'last_name',
            'email',
            'is_active',
        ]


class ProxyGroup(Group):
    """
    Proxy for default user group, so that we can define additional
    listing options.
    """
    class Meta:
        proxy               = True
        app_label           = 'auth'
        verbose_name        = 'Group'
        verbose_name_plural = 'Groups'


    class Listing:
        columns = ['name']


class ProxyPermission(Permission):
    """
    Proxy for default permission, so that we can define additional
    listing options.
    """
    class Meta:
        proxy               = True
        app_label           = 'auth'
        verbose_name        = 'Permission'
        verbose_name_plural = 'Permissions'


    class Listing:
        columns = ['name', 'content_type']
        filter_by = [
            'name',
            'content_type',
        ]

