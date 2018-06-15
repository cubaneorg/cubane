# coding=UTF-8
from __future__ import unicode_literals
from django.contrib.auth.models import Group
from context import IShopClientContext


class IShop(object):
    GROUPS = [
        'admin',
        'order-manager',
        'customer-manager',
        'category-manager',
        'product-manager',
        'variety-manager',
        'presentation-manager',
        'account-manager'
    ]


    def __init__(self):
        pass


    def get_available_groups(self):
        return Group.objects.filter(name__in=self.GROUPS).order_by('name')


    def create_group(self, name):
        """
        Create new system-wide account group.
        """
        if Group.objects.filter(name=name).count() == 0:
            group = Group.objects.create(name=name)
            return group
        else:
            return None


    def get_context(self):
        """
        Return the context for the given client. The client context allows
        to query and interact with the shop system for the particular client.
        """
        # even wsgi seems to cache this. Changing options for instance requires
        # a reload of apache in order to take effect. Therefore
        # we do not cache the client context here...
        return IShopClientContext()


    def get_authenticated_context(self, user):
        """
        Verify given context and authentificated user. Return the context for
        the given client, if the user is authenticated and matches the given
        client slug. Otherwise return None.
        """
        if user.is_authenticated():
            return IShopClientContext()
        return None
