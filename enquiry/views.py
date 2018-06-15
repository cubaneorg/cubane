# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponseRedirect
from django.conf import settings
from django.contrib import messages
from django.db.models.query import QuerySet
from cubane.views import ModelView
from cubane.backend.views import BackendSection
from cubane.lib.module import get_class_from_string
from cubane.lib.model import save_model
from cubane.lib.url import no_cache_url
from cubane.lib.libjson import to_json_response, to_json


BACKEND_FORM_FIELD_NAMES = [
    'action_undertaken',
    'further_action_required',
    'closed'
]


def get_enquiry_model():
    """
    Return the enquiry model as configured by settings.ENQUIRY_MODEL.
    """
    try:
        if hasattr(settings, 'ENQUIRY_MODEL'):
            return get_class_from_string(settings.ENQUIRY_MODEL)
        else:
            raise ImportError()
    except ImportError:
        raise ValueError(
            "cubane.enquiry requires the settings variable 'ENQUIRY_MODEL' " +
            "to be set to the full path of the model class that represents " +
            "enquiry messages, for example myproject.models.Enquiry. The " +
            "settings variable is either not configured or the model or class " +
            "cannot be imported."
        )


def create_blank_enquiry_form(modelclass, formclass=None):
    """
    Create and return the default enquiry form without any initial data applied.
    """
    if not formclass:
        formclass = modelclass.get_form()

    form = formclass()
    remove_backend_fields(form)

    return form


def remove_backend_fields(form):
    """
    Remove backend-related form fields from the given form that should not
    be presented to the visitor of the website. This will also remove related
    section fields.
    """
    for property_name in BACKEND_FORM_FIELD_NAMES:
        if property_name in form.fields:
            del form.fields[property_name]
    form.remove_tabs()
    form.update_sections()


def validate_captcha(request):
    """
    Validate captcha (Google Recaptcha)
    """
    # always validates in DEBUG mode
    if settings.DEBUG:
        return True

    # validate captcha by communicating with captcha backend
    captcha = True
    if hasattr(settings, 'CAPTCHA_SECRET_KEY'):
        import urllib2
        import json

        response = urllib2.urlopen('https://www.google.com/recaptcha/api/siteverify?secret=' + settings.CAPTCHA_SECRET_KEY + '&response=' + unicode(request.POST.get('g-recaptcha-response')))
        data = json.load(response)
        if data['success'] == False:
            captcha = False
    return captcha


def default_enquiry_form(request, context, template_context, modelclass, formclass=None):
    """
    Default View handler for processing the given enquiry form. If no form is
    given, the default form is determined by the get_form class method of
    the given enquiry model.
    """
    if 'cubane.cms' not in settings.INSTALLED_APPS:
        raise ValueError(
            'cubane.cms required for sending cms page emails.'
        )

    if not hasattr(settings, 'ENQUIRY_CLIENT_TEMPLATE'):
        raise ValueError(
            "'ENQUIRY_CLIENT_TEMPLATE' is required in settings for sending " + \
            "emails to clients."
        )

    if not formclass:
        formclass = modelclass.get_form()

    if formclass:
        from cubane.cms.views import get_cms
        cms = get_cms()

        if request.method == 'POST':
            form = formclass(request.POST)
        else:
            initial = {}
            for k, v in request.GET.items():
                initial[k] = v
            form = formclass(initial=initial)

        remove_backend_fields(form)

        if getattr(form, 'configure'):
            cms.enquiry_configure_form(request, form, instance=None, edit=False)

        if request.method == 'POST':
            captcha = validate_captcha(request)
            if not captcha:
                messages.add_message(request, messages.ERROR,
                    'Please tick the checkbox at the bottom of the form to prevent SPAM.'
                )

            if form.is_valid() and captcha:
                # don't save the request on the backend if no enquiry_email is present
                # just present an error message, that the functionality isn't working atm
                if not cms.settings.enquiry_email:
                    msg = 'Our enquiry form isn\'t working at the moment ' +\
                          'because we don\'t have an email address yet. ' +\
                          'Please use other means of contacting us.'
                    if request.is_ajax():
                        return to_json_response({'errors': {'__all__': [msg]}, 'success': False})
                    else:
                        messages.add_message(request, messages.ERROR, msg)
                        return HttpResponseRedirect(no_cache_url(request.get_full_path()))

                d = form.cleaned_data

                instance = modelclass()
                save_model(d, instance)

                # success message (unless this is an ajax call)
                if not request.is_ajax():
                    messages.add_message(request, messages.SUCCESS,
                        'Thank you for your enquiry. We will contact you shortly.'
                    )

                # send email to website visitor
                cms.enquiry_send_mail_to_customer(request, instance, d)

                # remove captcha information from the email to the client
                if 'captcha' in d: del d['captcha']
                if 'captcha_hash' in d: del d['captcha_hash']

                # send email to client
                cms.enquiry_send_mail_to_client(request, instance, d)

                # successfull enquiry made
                cms.on_enquiry_send(request, instance, d)

                # send response
                if request.is_ajax():
                    return to_json_response({'success': True})
                else:
                    return HttpResponseRedirect(no_cache_url(request.get_full_path()))
            else:
                # if form is not valid or captcha failed
                if request.is_ajax():
                    errors = form._errors

                    if not captcha:
                        if '__all__' not in errors:
                            errors['__all__'] = []
                        errors['__all__'].append('Please tick the checkbox at the bottom of the form to prevent SPAM.')

                    return to_json_response({'success': False, 'errors': errors})

        template_context.update({
            'enquiry_form': form
        })

    return template_context


class EnquiryView(ModelView):
    """
    View enquiry messages.
    """
    namespace = 'cubane.enquiry'
    template_path = 'cubane/enquiry/'


    def _get_objects(self, request):
        return self.model.objects.order_by('-created_on')


    def __init__(self, *args, **kwargs):
        self.model = get_enquiry_model()
        super(EnquiryView, self).__init__(*args, **kwargs)


class EnquiryBackendSection(BackendSection):
    """
    Backend section for managing enquiries.
    """
    title = 'Enquiry'
    slug = 'enquiry'
    view = EnquiryView()
