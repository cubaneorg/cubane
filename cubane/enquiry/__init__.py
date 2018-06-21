from cubane.lib.app import require_app
from django.conf import settings


RESOURCES = [
    '/cubane/js/cubane.js',
    'css/cubane.enquiry.gmap.css',
    'js/cubane.enquiry.gmap.js'
]

if settings.CAPTCHA == 'innershed_captcha':
    RESOURCES += ['js/innershedCaptcha.js',
        'css/innershedCaptcha.css']


def install_backend(backend):
    from cubane.enquiry.views import EnquiryBackendSection
    backend.register_section(EnquiryBackendSection())