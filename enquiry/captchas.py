# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
from cubane.forms import form_field_error
import requests


class RecaptchaWidget(forms.TextInput):
    """
    Using Googles Recaptcha Widget. It needs a private and a public key, of
    which both are stored in the settings.
    """
    def __init__(self, *args, **kwargs):
        super(RecaptchaWidget, self).__init__(*args, **kwargs)


    def render(self, *args, **kwargs):
        return mark_safe('<script type="text/javascript" ' +\
            'src="http://www.google.com/recaptcha/api/challenge?k=%s">' % (settings.RECAPTCHA_PUBLIC_KEY) +\
            '</script>' +\
            '<noscript>' +\
            '<iframe src="http://www.google.com/recaptcha/api/noscript?k=%s"' % (settings.RECAPTCHA_PUBLIC_KEY) +\
            ' height="300" width="500" frameborder="0">' +\
            '</iframe><br>' +\
            '<textarea name="recaptcha_challenge_field" rows="3" cols="40">' +\
            '</textarea>' +\
            '<input type="hidden" name="recaptcha_response_field" ' +\
            'value="manual_challenge">' +\
            '</noscript>')


class NewRecaptchaWidget(forms.TextInput):
    """
    Using Googles new Recaptcha Widget. It needs a secret key,
    which is stored in the settings.
    """
    def __init__(self, *args, **kwargs):
        super(NewRecaptchaWidget, self).__init__(*args, **kwargs)


    def render(self, *args, **kwargs):
        return mark_safe('<div class="g-recaptcha" data-sitekey="%s" ></div>' % (settings.CAPTCHA_SITE_KEY))


class HashWidget(forms.HiddenInput):
    """
    Using a widget that displays nothing and display the captcha_hash entry in
    the Captcha widget, as both rely on the requested hash display nothing,
    instead display the input together with (under) the image.
    """
    def __init__(self, *args, **kwargs):
        super(HashWidget, self).__init__(*args, **kwargs)


    def render(self, *args, **kwargs):
        return ''


class InnershedCaptchaWidget(forms.TextInput):
    """
    Using the Innershed Captcha we request a hash first and then load an iframe which displays the image
    """
    def __init__(self, *args, **kwargs):
        super(InnershedCaptchaWidget, self).__init__(*args, **kwargs)


    def render(self, *args, **kwargs):
        html = '<input id="id_captcha" maxlength="255" name="captcha" '
        if settings.CAPTCHA_PLACEHOLDER:
            html += 'placeholder="' + settings.CAPTCHA_PLACEHOLDER + '" '
        html += 'type="text">'
        return mark_safe(html)


CAPTCHA_WIDGETS = [
    RecaptchaWidget,
    InnershedCaptchaWidget,
    NewRecaptchaWidget
]


def get_captcha_widget(label='Captcha', help_text=None):
    """
    Selection logic, selects the widget based on the settings.
    """
    if settings.CAPTCHA and settings.CAPTCHA == 'recaptcha':
        return forms.CharField(label=label, help_text=help_text, max_length=255, widget=RecaptchaWidget)
    elif settings.CAPTCHA and settings.CAPTCHA == 'innershed_captcha':
        # empty render widget for the captcha_hash and the image
        # widget renders both
        return forms.CharField(label=label, help_text=help_text, max_length=255, widget=InnershedCaptchaWidget)
    elif settings.CAPTCHA and settings.CAPTCHA == 'new_recaptcha':
        return forms.CharField(label=label, help_text=help_text, max_length=255, required=False, widget=NewRecaptchaWidget)
    else:
        return ''


def clean_captcha_data(data, form):
    """
    Clean up logic, only works for the innershed captcha at the moment.
    """
    if settings.CAPTCHA:
        if 'captcha' in data.keys():
            # verify the captcha
            if not 'captcha_hash' in data.keys():
                form_field_error(form, 'captcha', 'Captcha hash argument is missing.')
            else:
                valid = requests.get('http://captcha.innershed.com/captcha_api.php?action=validate&hash=%s&password=%s' % (data['captcha_hash'], data['captcha']))
                if valid.text != 'valid':
                    form_field_error(form, 'captcha', 'Please enter the correct captcha.')
        else:
            # captcha enabled but user didn't type it in
            form_field_error(form, 'captcha', 'Please enter the captcha.')
            return data
    return data


def is_captcha_widget(widget):
    """
    Return True, if the given widget is a capcha widget.
    """
    for _class in CAPTCHA_WIDGETS:
        if isinstance(widget, _class):
            return True
    return False