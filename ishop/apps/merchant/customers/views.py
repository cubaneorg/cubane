# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.encoding import force_unicode
from cubane.views import ModelView, view_url
from cubane.backend.views import BackendSection
from cubane.decorators import permission_required
from cubane.lib.url import get_absolute_url
from cubane.lib.libjson import to_json_response
from cubane.ishop.api import IShop
from cubane.lib.paginator import create_paginator
from cubane.lib.password import get_pronounceable_password
from cubane.ishop import get_customer_model
from forms import CustomerChangePasswordForm
from cubane.views import view
import hashlib
import datetime


class CustomerView(ModelView):
    template_path = 'cubane/ishop/merchant/customers/'
    namespace = 'cubane.ishop.customers'
    model = get_customer_model()


    patterns = [
        view_url(r'change-password/$', view='change_password', name='change_password'),
    ]

    listing_actions = [
        ('[Change Password]', 'change_password', 'single')
    ]

    shortcut_actions = [
        'change_password',
    ]

    def __init__(self, *args, **kwargs):
        if not settings.SHOP_CHANGE_CUSTOMER_PASSWORD_ENABLED:
            self.shortcut_actions = []
            self.listing_actions = []
        super(CustomerView, self).__init__(*args, **kwargs)


    def _get_objects(self, request):
        return self.model.objects.all()


    @view(require_POST)
    @view(permission_required('delete'))
    def delete(self, request, pk = None):
        """
        Delete existing model instance with given primary key pk or (if no
        primary key is given in the url) attempt to delete multiple entities
        that are given by ids post argument.
        """
        # determine list of pks
        pks = []
        if pk:
            pks = [pk]
        else:
            pks = request.POST.getlist('pks[]', [])
            if len(pks) == 0:
                pk = request.POST.get('pk')
                if pk:
                    pks = [pk]

        # delete instance(s)...
        if len(pks) == 1:
            instance = self.get_object_or_404(request, pks[0])
            label = instance.__unicode__()
            if not label: label = '<no label>'
            instance.delete()
            message = self._get_success_message(label, 'deleted')
        else:
            instances = self._get_objects(request).filter(pk__in=pks)
            for instance in instances:
                instance.delete()
            message = '%d %s deleted successfully.' % (
                len(instances),
                self.model._meta.verbose_name_plural
            )

        # response
        if self._is_json(request):
            return to_json_response({
                'success': True,
                'message': message
            })
        else:
            messages.add_message(request, messages.SUCCESS, message)
            return self._redirect(request, 'index')


    def change_password(self, request):
        # feature enabled?
        if not settings.SHOP_CHANGE_CUSTOMER_PASSWORD_ENABLED:
            raise Http404('Feature is not enabled.')

        customer_id = request.GET.get('pk')
        try:
            customer = self.model.objects.get(pk=customer_id)
            user = customer.user
        except self.model.DoesNotExist:
            raise Http404('Unknown customer account id %s.' % customer_id)

        if request.method == 'POST':
            form = CustomerChangePasswordForm(request.POST)
        else:
            form = CustomerChangePasswordForm()

        if request.method == 'POST' and form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.add_message(request, messages.SUCCESS, 'Password changed for <em>%s</em>.' % customer.email)
            return self._redirect(request, 'index')

        return {
            'customer': customer,
            'form': form
        }


    @view(csrf_exempt)
    def export(self, request):
        return _export(request)


class CustomerBackendSection(BackendSection):
    title = 'Customers'
    slug = 'customers'
    view = CustomerView()
