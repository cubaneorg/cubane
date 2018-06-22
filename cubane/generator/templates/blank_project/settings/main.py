# coding=UTF-8
from __future__ import unicode_literals
from cubane.settings import default_env
env = default_env(
    __name__,
    '$DOMAIN_NAME$',
    '$ADMIN_EMAIL$',
    csrf=True,
    ssl=False
)


#
# Site
#
SECRET_KEY = '$SECRET_KEY$'
ROOT_URLCONF = '$TARGET_NAME$.urls'


#
# Apps
#
env.add_apps([
    'cubane',
    'cubane.backend',
    'cubane.backend.accounts',
    'cubane.cms',
    'cubane.media',
    'cubane.medialoader',
    'cubane.enquiry',
    'cubane.dbmigrate',
    'cubane.cssreset',
    'cubane.svgicons',
    'cubane.fonts',
    '$TARGET_NAME$',
])


#
# Resources
#
RESOURCES = {
    'frontend': [
        'cubane.cssreset',
        'cubane.legacy.jquery',
        'cubane.enquiry',
        'cubane.svgicons',
        '$TARGET_NAME$',
    ],
    'inline': [
        'cubane.medialoader',
    ]
}


#
# Image Shapes
#
IMAGE_SHAPES = {
    # Add you own image shapes used by your website design, for example
    # header: '1600:800'.
    # The size given here is arbitary since it only defines an aspect
    # ratio and not particular pixel sizes. For example 1600:800 could
    # also be defined as 800:400, which is the same aspect ratio.
}


#
# Navigation
#
CMS_NAVIGATION = (
    ('header', 'Header'),
    ('footer', 'Footer'),
)


#
# CMS
#
CMS = '$TARGET_NAME$.views.$TARGET_NAME_CAMEL_CASE$CMS'
CMS_TEMPLATES = (
    ('$TARGET_NAME$/page.html', 'Page'),
    ('$TARGET_NAME$/mail/enquiry_visitor.html', 'Enquiry Email'),
)
CMS_SLOTNAMES = [
    'content',
    'signature'
]
CMS_SETTINGS_MODEL = '$TARGET_NAME$.models.Settings'
CMS_PAGE_MODEL = '$TARGET_NAME$.models.CustomPage'
PAGE_HIERARCHY = False


#
# Enquiry
#
ENQUIRY_MODEL = '$TARGET_NAME$.models.Enquiry'
ENQUIRY_CLIENT_TEMPLATE = '$TARGET_NAME$/mail/enquiry_client.html'
CAPTCHA = 'new_recaptcha'
CAPTCHA_SITE_KEY = 'replace-me'
CAPTCHA_SECRET_KEY = 'replace-me'


#
# Google Maps
#
CUBANE_GOOGLE_MAP_API_KEY = 'replace-me'
