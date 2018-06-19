# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.template import Context
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from cubane.lib.url import make_absolute_url, get_absolute_url
from cubane.lib.mail import cubane_send_shop_mail
from cubane.lib.template import get_template
import os.path


def mail_error(msg):
    mail_admins('[ISHOP] Error', msg)


def send_client_mail(request, email, subject, context, attachments=None):
    from cubane.cms.views import get_cms
    cms = get_cms()
    cubane_send_shop_mail(request, email, subject, context, attachments=attachments)


def get_mail_order_context(request, order, customer=True, extras=None):
    context = {
        'request': request,
        'settings': request.settings,
        'CURRENCY': settings.CURRENCY,
        'is_customer': customer,
        'order': order,
        'order_url': make_absolute_url(order.get_absolute_url(), https=True),
        'order_products': order.basket.items,
        'order_totals': order.basket.totals,
        'DOMAIN_NAME': 'http://%s' % settings.DOMAIN_NAME,
        'backend_order_url': get_absolute_url('cubane.ishop.orders.edit', args=[order.id], https=True)
    }
    if extras:
        context.update(extras)
    return context


def mail_customer_order_cancelled(request, order):
    try:
        send_client_mail(request, order.email, 'Order cancelled: %s' % order.order_id, get_mail_order_context(request, order, extras={'order_cancelled': True}))
        return True
    except:
        if settings.DEBUG:
            raise
        else:
            mail_error('Unable to send order cancelled email to customer: %s' % order.email)
            return False


def mail_customer_order_settled(request, order):
    try:
        send_client_mail(request, order.email, 'Order settled: %s' % order.order_id, get_mail_order_context(request, order, extras={'order_settled': True}))
        return True
    except:
        if settings.DEBUG:
            raise
        else:
            mail_error('Unable to send order cancelled email to customer: %s' % order.email)
            return False


def mail_customer_order_status(request, order):
    try:
        send_client_mail(request, order.email, 'Order Status: %s' % order.order_id, get_mail_order_context(request, order, extras={'order_status': True}))
        return True
    except:
        if settings.DEBUG:
            raise
        else:
            mail_error('Unable to send order status email to customer: %s' % order.email)
            return False


def mail_customer_order_approved(request, order):
    try:
        send_client_mail(request, order.email, 'Order approved: %s' % order.order_id, get_mail_order_context(request, order, extras={'order_approved': True}))
        return True
    except:
        if settings.DEBUG:
            raise
        else:
            mail_error('Unable to send order approved email to customer: %s' % order.email)
            return False


def mail_customer_order_rejected(request, order):
    try:
        send_client_mail(request, order.email, 'Order rejected: %s' % order.order_id, get_mail_order_context(request, order, extras={'order_rejected': True}))
        return True
    except:
        if settings.DEBUG:
            raise
        else:
            mail_error('Unable to send order rejected email to customer: %s' % order.email)


def mail_customer_order_cancelled(request, order):
    try:
        send_client_mail(request, order.email, 'Order cancelled: %s' % order.order_id, get_mail_order_context(request, order, extras={'order_cancelled': True}))
        return True
    except:
        if settings.DEBUG:
            raise
        else:
            mail_error('Unable to send order cancellation email to customer: %s' % order.email)


def mail_client_new_order(request, order, attachments=None):
    try:
        send_client_mail(request, request.settings.enquiry_email, 'Order: %s' % order.order_id, get_mail_order_context(request, order, customer=False, extras={'order_client': True}), attachments=attachments)
        return True
    except:
        if settings.DEBUG:
            raise
        else:
            mail_error('Unable to send confirmation email to client: %s' % request.settings.enquiry_email)
            return False


def mail_customer_new_order(request, order):
    try:
        send_client_mail(request, order.email, 'Order: %s' % order.order_id, get_mail_order_context(request, order, extras={'order_customer': True}))
        return True
    except:
        if settings.DEBUG:
            raise
        else:
            mail_error('Unable to send confirmation email to customer: %s' % order.email)
            return False
