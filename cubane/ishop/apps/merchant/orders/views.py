# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from cubane.views import ModelView, view_url
from cubane.backend.views import BackendSection
from cubane.ishop.api import IShop
from cubane.lib.paginator import create_paginator
from cubane.lib.request import request_int_list
from cubane.ishop import get_order_model
from cubane.ishop.mail import *
from cubane.ishop.models import OrderBase
from cubane.ishop.basket import Basket
from forms import (
    ChangeOrderStatusForm,
    ApproveOrderForm,
    RejectOrderForm,
    CancelOrderForm,
    OrderForm,
)
import json


class OrderView(ModelView):
    template_path = 'cubane/ishop/merchant/orders/'
    model = get_order_model()
    namespace = 'cubane.ishop.orders'


    def __init__(self, *args, **kwargs):
        self.patterns = []
        self.listing_actions = []
        self.shortcut_actions = []

        # view order (previous order screen)
        self.patterns.append(view_url(r'view/$', 'view', name='view'))
        self.listing_actions.append( ('View', 'view', 'single') )
        self.shortcut_actions.append('view')

        # support for pre-auth payments (approval)
        if settings.SHOP_PREAUTH:
            self.patterns.extend([
                view_url(r'approve/$', 'approve', name='approve'),
                view_url(r'reject/$', 'reject', name='reject'),
                view_url(r'cancel/$', 'cancel', name='cancel')
            ])
            self.listing_actions.extend([
                ('[Approve]', 'approve', 'single'),
                ('[Reject]', 'reject', 'single'),
                ('[Cancel]', 'cancel', 'single')
            ])
            self.shortcut_actions.extend([
                'approve',
                'reject',
                'cancel',
            ])
        else:
            self.exclude_columns = ['approval_status']

        self.patterns.extend([
            view_url(r'basket-editor/',               'basket_editor',               name='basket_editor'),
            view_url(r'basket-editor-search/',        'basket_editor_search',        name='basket_editor_search'),
            view_url(r'basket-editor-add-to-basket/', 'basket_editor_add_to_basket', name='basket_editor_add_to_basket'),
        ])

        super(OrderView, self).__init__(*args, **kwargs)


    def _get_objects(self, request):
        return self.model.objects.select_related('customer', 'voucher').all()


    def _get_objects_or_404(self, request):
        return self.model.objects.select_related('customer', 'voucher').all()


    def before_save(self, request, cleaned_data, instance, edit):
        # default values
        if not edit:
            from cubane.ishop.views import get_shop
            shop = get_shop()
            instance.customer_not_present = True
            instance.payment_gateway = shop.get_default_payment_gateway()

        # save basket.
        basket = Basket(request, prefix=instance.backend_basket_prefix)
        if not basket.is_empty():
            instance.save_basket(basket)

        # change status
        if request.POST.get('next-status'):
            cleaned_data['status'] = int(request.POST.get('next-status'))


    def after_save(self, request, cleaned_data, instance, edit):
        # generate identifiers
        if not edit:
            instance.generate_identifiers(request)


    def after_save_changes(self, request, cleaned_data, instance, changes, edit):
        """
        Called after the given model instance is saved.
        """
        # determine changes
        status_changed = 'status' in changes
        tracking_changed = 'tracking_provider' in changes or 'tracking_code' in changes
        click_and_collect_changed = 'click_and_collect' in changes
        delivery_option_changed = (
            'delivery_option_id' in changes or
            'delivery_quote'     in changes
        )
        delivery_address_changed = (
            'delivery_name'       in changes or
            'delivery_company'    in changes or
            'delivery_address1'   in changes or
            'delivery_address2'   in changes or
            'delivery_address3'   in changes or
            'delivery_city'       in changes or
            'delivery_county'     in changes or
            'delivery_postcode'   in changes or
            'delivery_country_id' in changes
        )
        changed = (
            status_changed            or
            tracking_changed          or
            click_and_collect_changed or
            delivery_option_changed   or
            delivery_address_changed
        )

        # fulfillment
        if instance.status in OrderBase.FULFILLED_STATUS and not instance.fulfilled:
            (success, msg) = instance.fulfill(request)
            if success:
                messages.add_message(request, messages.SUCCESS, 'Order <em>%s</em> has been fulfilled successfully.' % instance.order_id)
            else:
                messages.add_message(request, messages.ERROR, 'Error while fulfilling order <em>%s</em>: %s' % (instance.order_id, msg))

        # send email if something of importance changed
        if changed:
            if int(instance.status) in [OrderBase.STATUS_PARTIALLY_SHIPPED, OrderBase.STATUS_SHIPPED, OrderBase.STATUS_READY_TO_COLLECT, OrderBase.STATUS_COLLECTED]:
                if mail_customer_order_status(request, instance):
                    messages.add_message(request, messages.SUCCESS, 'Email sent to customer: %s' % instance.email)

        # redirect to payment
        if request.POST.get('autosubmit'):
            return HttpResponseRedirect('%s%s' % (instance.get_absolute_url(), '?autosubmit=true'))


    def _create_edit(self, request, pk=None, edit=False, duplicate=False):
        context = super(OrderView, self)._create_edit(request, pk, edit, duplicate)
        if edit:
            context['order'] = context.get('object')
        return context


    def view(self, request):
        """
        View existing order and make some minor amendments to it (previous order screen).
        """
        pk = request.GET.get('pk')
        order = get_object_or_404(get_order_model(), pk=pk)

        if request.method == 'POST':
            form = ChangeOrderStatusForm(request.POST)
        else:
            form = ChangeOrderStatusForm(initial={
                'status': order.status,
                'tracking_provider': order.tracking_provider,
                'tracking_code': order.tracking_code,
                'delivery_type': order.delivery_type,
                'delivery_name': order.delivery_name,
                'delivery_company': order.delivery_company,
                'delivery_address1': order.delivery_address1,
                'delivery_address2': order.delivery_address2,
                'delivery_address3': order.delivery_address3,
                'delivery_city': order.delivery_city,
                'delivery_county': order.delivery_county,
                'delivery_postcode': order.delivery_postcode,
                'delivery_country': order.delivery_country,
                'special_requirements': order.special_requirements,
            })

        form.configure(request, order)

        if request.method == 'POST':
            # from cancellation
            if request.POST.get('cubane_form_cancel', '0') == '1':
                return self._redirect(request, 'index')

            # valid?
            if form.is_valid():
                d = form.cleaned_data

                # update status
                new_status = int(d.get('status'))
                status_changed = order.status != new_status
                order.status = new_status

                order.special_requirements = d.get('special_requirements')

                # update tracking code
                tracking_changed = (
                    order.tracking_provider != d.get('tracking_provider') or \
                    order.tracking_code != d.get('tracking_code')
                )
                order.tracking_provider = d.get('tracking_provider')
                order.tracking_code = d.get('tracking_code')

                # update delivery type
                new_delivery_type = int(d.get('delivery_type'))
                delivery_type_changed = order.delivery_type != new_delivery_type
                order.delivery_type = new_delivery_type

                # update delivery address, if this is a delivery order
                delivery_address_changed = False
                if not order.is_click_and_collect:
                    delivery_address_changed = (
                        order.delivery_name      != d.get('delivery_name') or \
                        order.delivery_company  != d.get('delivery_company') or \
                        order.delivery_address1 != d.get('delivery_address1') or \
                        order.delivery_address2 != d.get('delivery_address2') or \
                        order.delivery_address3 != d.get('delivery_address3') or \
                        order.delivery_city     != d.get('delivery_city') or \
                        order.delivery_county   != d.get('delivery_county') or \
                        order.delivery_postcode != d.get('delivery_postcode') or \
                        order.delivery_country  != d.get('delivery_country')
                    )
                    order.delivery_name     = d.get('delivery_name')
                    order.delivery_company  = d.get('delivery_company')
                    order.delivery_address1 = d.get('delivery_address1')
                    order.delivery_address2 = d.get('delivery_address2')
                    order.delivery_address3 = d.get('delivery_address3')
                    order.delivery_city     = d.get('delivery_city')
                    order.delivery_county   = d.get('delivery_county')
                    order.delivery_postcode = d.get('delivery_postcode')
                    order.delivery_country  = d.get('delivery_country')

                # update processing state for all line items
                order.reset_processed_state()
                indexes = request_int_list(request.POST, 'processed')
                for index in indexes:
                    order.mark_item_as_processed(index, True)

                # update shipped state for all line items
                order.reset_shipped_state()
                indexes = request_int_list(request.POST, 'shipped')
                for index in indexes:
                    order.mark_item_as_shipped(index, True)

                # save order
                order.save()

                # fulfillment
                if order.status in OrderBase.FULFILLED_STATUS and not order.fulfilled:
                    (success, msg) = order.fulfill(request)
                    if success:
                        messages.add_message(request, messages.SUCCESS, 'Order <em>%s</em> has been fulfilled successfully.' % order.order_id)
                    else:
                        messages.add_message(request, messages.ERROR, 'Error while fulfilling order <em>%s</em>: %s' % (order.order_id, msg))

                # send email if something of importance changed
                if status_changed or tracking_changed or delivery_type_changed or delivery_address_changed:
                    if int(order.status) in [OrderBase.STATUS_PARTIALLY_SHIPPED, OrderBase.STATUS_SHIPPED, OrderBase.STATUS_READY_TO_COLLECT, OrderBase.STATUS_COLLECTED]:
                        if mail_customer_order_status(request, order):
                            messages.add_message(request, messages.SUCCESS, 'Email sent to customer: %s' % order.email)
                    messages.add_message(request, messages.SUCCESS, 'Order <em>%s</em> has been updated.' % order.order_id)

                active_tab = request.POST.get('cubane_save_and_continue', '0')
                if not active_tab == '0':
                    return HttpResponseRedirect(reverse('cubane.ishop.orders.edit') + '?pk=%d' % order.pk)
                else:
                    return self._redirect(request, 'index')

        return {
            'order': order,
            'form': form,
            'edit': True
        }


    def _create_order(self, request):
        """
        Create new order.
        """
        # determine form class
        order_model = get_order_model()
        formclass = order_model.get_form()

        # create form
        if request.method == 'POST':
            form = formclass(request.POST)
        else:
            form = formclass()

        form.configure(request, None, False)

        # validate form
        if request.method == 'POST' and form.is_valid():
            d = form.cleaned_data

            # create new order
            order = order_model.create_empty_customer_not_present(request)

            # redirect to edit page
            return self._redirect(request, 'edit', order)

        return {
            'form': form,
            'edit': False
        }


    def approve(self, request):
        order_id = request.GET.get('pk')
        edit_order = request.GET.get('edit_order', 'false') == 'true'
        order = get_object_or_404(get_order_model(), pk=order_id)

        if request.method == 'POST':
            form = ApproveOrderForm(request.POST)
        else:
            form = ApproveOrderForm()

        if request.method == 'POST':
            if request.POST.get('cubane_form_cancel', '0') == '1':
                if edit_order:
                    return self._redirect(request, 'edit', order)
                else:
                    return self._redirect(request, 'index')

            if form.is_valid():
                (success, msg) = order.approve(request)

                if success and order.approval_status == OrderBase.APPROVAL_STATUS_APPROVED:
                    messages.add_message(request, messages.SUCCESS, 'Order <em>%s</em> has been approved.' % order.order_id)
                else:
                    messages.add_message(request, messages.ERROR, 'We were unable to approve the order <em>%s</em>: %s' % (order.order_id, msg))

                if edit_order:
                    return self._redirect(request, 'edit', order)
                else:
                    return self._redirect(request, 'index')

        return {
            'order': order,
            'form': form
        }


    def reject(self, request):
        order_id = request.GET.get('pk')
        edit_order = request.GET.get('edit_order', 'false') == 'true'
        order = get_object_or_404(get_order_model(), pk=order_id)

        if request.method == 'POST':
            form = RejectOrderForm(request.POST)
        else:
            form = RejectOrderForm()

        if request.method == 'POST':
            if request.POST.get('cubane_form_cancel', '0') == '1':
                if edit_order:
                    return self._redirect(request, 'edit', order)
                else:
                    return self._redirect(request, 'index')

            if form.is_valid():
                (success, msg) = order.reject(request, form.cleaned_data.get('reject_msg'))

                if success and order.approval_status == OrderBase.APPROVAL_STATUS_REJECTED:
                    messages.add_message(request, messages.SUCCESS, 'Order <em>%s</em> has been rejected.' % order.order_id)
                else:
                    messages.add_message(request, messages.ERROR, 'We were unable to reject the order <em>%s</em>: %s' % (order.order_id, msg))

                if edit_order:
                    return self._redirect(request, 'edit', order)
                else:
                    return self._redirect(request, 'index')

        return {
            'order': order,
            'form': form
        }


    def cancel(self, request):
        order_id = request.GET.get('pk')
        edit_order = request.GET.get('edit_order', 'false') == 'true'
        order = get_object_or_404(get_order_model(), pk=order_id)

        def _do_redirect():
            if edit_order:
                return self._redirect(request, 'edit', order)
            else:
                return self._redirect(request, 'index')

        # cannot cancel if we are awaiting payment approval/rejection
        if order.approval_status == OrderBase.APPROVAL_STATUS_WAITING:
            messages.add_message(request, messages.ERROR, 'Order <em>%s</em> is awaiting approval. Please accept or reject this order.' % order.order_id)
            return _do_redirect()

        # cannot cancel if the order has already been cancelled
        if order.cancelled:
            messages.add_message(request, messages.ERROR, 'Order <em>%s</em> has already been cancelled.' % order.order_id)
            return _do_redirect()

        # process cancellation form
        if request.method == 'POST':
            form = CancelOrderForm(request.POST)
        else:
            form = CancelOrderForm()

        if request.method == 'POST':
            if request.POST.get('cubane_form_cancel', '0') == '1':
                _do_redirect()

            if form.is_valid():
                (success, msg) = order.cancel(request, form.cleaned_data.get('cancel_msg'))
                if success:
                    messages.add_message(request, messages.SUCCESS, 'Order <em>%s</em> has been cancelled.' % order.order_id)
                else:
                    messages.add_message(request, messages.ERROR, 'We were unable to cancel the order <em>%s</em>: %s' % (order.order_id, msg))

                _do_redirect()

        return {
            'order': order,
            'form': form
        }


    def basket_editor(self, request):
        prefix = request.GET.get('prefix')
        basket = Basket(request, prefix=prefix)

        return {
            'basket': basket
        }


    def basket_editor_search(self, request):
        from cubane.ishop.views import get_shop

        q = request.POST.get('q')
        shop = get_shop()
        products = shop.get_products().filter(
            Q(title__icontains=q) |
            Q(barcode__startswith=q) |
            Q(part_number__startswith=q) |
            Q(sku_enabled=True, sku__startswith=q),
            draft=False
        )

        return {
            'products': products[:100]
        }


    def basket_editor_add_to_basket(self, request):
        from cubane.ishop.views import get_shop

        pk = request.POST.get('pk')
        prefix = request.POST.get('prefix')
        shop = get_shop()
        product = shop.get_products().get(pk=pk)

        return {
            'product': product,
            'prefix': prefix,
            'settings': settings
        }


class ProcessingOrderView(OrderView):
    namespace = 'cubane.ishop.processing'
    can_add = False

    def _get_objects(self, request):
        objects = super(ProcessingOrderView, self)._get_objects(request)
        objects = objects.filter(status__in=OrderBase.PROCESSING_STATUS)
        return objects


class OrderBackendSection(BackendSection):
    title = 'Orders'
    slug = 'orders'
    view = OrderView()


class ProcessingOrderBackendSection(BackendSection):
    title = 'Processing'
    slug = 'processing'
    view = ProcessingOrderView()
