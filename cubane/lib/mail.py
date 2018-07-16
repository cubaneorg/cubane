# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.views.debug import ExceptionReporter
from django.template import Context
from django.db.models.query import QuerySet
from django.test import RequestFactory
from cubane.lib.text import text_from_html
from cubane.lib.template import get_template
import email
import os
import sys
import traceback


def trigger_exception_email(request, subject, data=None):
    """
    Raise an exception with given subject message and send an exception email.
    """
    try:
        raise ValueError(subject)
    except:
        send_exception_email(request)


def send_exception_email(request=None):
    """
    Send exception report email for the given exception e.
    """
    if request is None:
        factory = RequestFactory()
        request = factory.get('/')

    exc_info = sys.exc_info()
    reporter = ExceptionReporter(request, is_email=True, *exc_info)
    subject = unicode(exc_info[1].message).replace('\n', '\\n').replace('\r', '\\r')[:989]

    mail_admins(
        subject,
        reporter.get_traceback_text(),
        fail_silently=True,
        html_message=reporter.get_traceback_html()
    )


def cubane_send_mail_no_html(to, subject, text, attachments=None):
    """
    Send an email to the given recepient with given subject line and text
    content.
    """
    if 'cubane.cms' not in settings.INSTALLED_APPS:
        raise ValueError('cubane.cms required for sending cms page emails.')
    from cubane.cms.views import get_cms
    cms = get_cms()

    # construct email
    msg = EmailMultiAlternatives(
        subject,
        text,
        cms.settings.enquiry_reply,
        [to],
        headers={
            'Reply-To': cms.settings.enquiry_reply,
            'From': cms.settings.enquiry_from
        }
    )

    # attachement(s)
    if attachments:
        if not isinstance(attachments, list):
            attachments = [attachments]
        for attachment in attachments:
            msg.attach_file(attachment)

    # send it off
    msg.send()


def cubane_send_mail(to, subject, html, attachments=None, cc=None, bcc=None):
    """
    Send an email to the given recepient with given subject line and html
    content.
    """
    if 'cubane.cms' not in settings.INSTALLED_APPS:
        raise ValueError('cubane.cms required for sending cms page emails.')

    from cubane.cms.views import get_cms
    cms = get_cms()

    text = 'There is a html version of this email available. To see this ' + \
           'version, please configure your email application.'

    # construct email
    msg = EmailMultiAlternatives(
        subject,
        text,
        cms.settings.enquiry_reply,
        [to],
        headers={
            'Reply-To': cms.settings.enquiry_reply,
            'From': cms.settings.enquiry_from
        },
        cc=cc,
        bcc=bcc
    )
    msg.attach_alternative(html, 'text/html')

    # attachement(s)
    if attachments:
        if not isinstance(attachments, list):
            attachments = [attachments]
        for attachment in attachments:
            if isinstance(attachment, tuple):
                msg.attach(*attachment)
            else:
                msg.attach_file(attachment)

    # send it off
    msg.send()


def cubane_send_mail_template(request, to, subject, template, template_context, attachments=None):
    """
    Send an email to the given recepient with given subject line.
    The email is constructed from the given template.
    """
    t = get_template(template)
    html = t.render(template_context)

    # send email
    cubane_send_mail(to, subject, html, attachments)


def cubane_send_cms_mail(request, to, subject, page, context=None, cc=None, bcc=None, attachments=None):
    """
    Send an email to the given recepient with given subject line.
    The email is send from the sender that is configured in the
    cms settings. The email content is derived from rendering the
    given cms page.
    """
    if 'cubane.cms' not in settings.INSTALLED_APPS:
        raise ValueError('cubane.cms required for sending cms page emails.')

    # construct email message (derived from cms content)
    from cubane.cms.views import get_cms
    cms = get_cms()
    html = cms.render_page(page, request=None, additional_context=context).content

    # send email
    cubane_send_mail(to, subject, html, cc=cc, bcc=bcc, attachments=attachments)


def cubane_send_cms_enquiry_mail(request, to, subject, context=None):
    """
    Send an email to the given recepient with the given subject line.
    The email is sent from the sender that is configured in the cms settings.
    The email content is derived from the cms page that is configured as the
    enquiry email template page.
    """
    if 'cubane.cms' not in settings.INSTALLED_APPS:
        raise ValueError('cubane.cms required for sending cms page emails.')

    from cubane.cms.views import get_cms
    cms = get_cms()
    page = cms.settings.enquiry_template

    return cubane_send_cms_mail(request, to, subject, page, context)


def cubane_send_shop_mail(request, to, subject, context=None, attachments=None):
    """
    Send an email to the given recepient with the given subject line.
    The email is sent from the sender that is configured in the cms settings.
    The email content is derived from the cms page that is configured as the
    shop mail template page.
    """
    if 'cubane.ishop' not in settings.INSTALLED_APPS:
        raise ValueError('cubane.ishop required for sending shop page emails.')

    from cubane.cms.views import get_cms
    cms = get_cms()
    page = cms.settings.shop_email_template
    html = cms.render_page(page, request=None, additional_context=context).content

    # send email
    return cubane_send_mail(to, subject, html, attachments)


def get_ordered_list_of_fields(fields, fields_items):
    """
    Helper method for email forms
    """
    return [{
        'name': k,
        'title': k.replace('_', ' ').title(),
        'value': fields.get(k, ''),
        'list': isinstance(_, list) or isinstance(fields.get(k, ''), QuerySet)
    } for (k, _) in filter(lambda x: not x[0].startswith('_'), fields_items)]


def get_decoded_email_part(part):
    text = part.get_payload(decode=True)
    charset = part.get_content_charset()

    if charset != None:
        text = unicode(text, str(charset), 'ignore').encode('utf8', 'replace')

    return text.strip()


def get_decoded_email_body(message_body):
    """
    Decode email body.
    Based on: https://gist.github.com/miohtama/5389146

    Detect character set if the header is not set.
    We try to get text/html, but if there is not one then fallback to text/plain.

    :param message_body: Raw 7-bit message body input e.g. from imaplib.
    Double encoded in quoted-printable and latin-1

    :return: Message body as unicode string
    """
    text = ''

    msg = email.message_from_string(message_body)
    if msg.is_multipart():
        for part in msg.get_payload():
            text = get_decoded_email_part(part)
    else:
        text = get_decoded_email_part(msg)

    return text.strip()
