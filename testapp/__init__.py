# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings


RESOURCES = [
    # fonts
    'font|Open Sans',

    # css and print style
    'css/style.templating.css',
    'print|css/print.css',

    # testing glob
    'css/glob/*.css',

    # svg icons
    'svgicons/email.svg',
    'svgicons/location.svg',
    'with-style|svgicons/phone.svg'
]


def get_deploy_context():
    return {
        'background_color': '#123456',
    }