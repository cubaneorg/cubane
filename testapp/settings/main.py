# coding=UTF-8
from __future__ import unicode_literals
from cubane.settings import default_env
import math
env = default_env(__name__, 'testapp.cubane.innershed.com', 'root@localhost', csrf=True)


#
# Test Runner
#
TEST_RUNNER = 'cubane.tests.runner.CubaneTestRunner'


#
# Site and Revision
#
SECRET_KEY = 'dsgdf7ymh(r9d2)_8z5s_&%rdq_77ln+k9^y(+j9c98pw(wu+6-afbldfgsdf'
ROOT_URLCONF = 'cubane.testapp.urls'


#
# Middleware
#
MIDDLEWARE_CLASSES += (
)


#
# Template Context Processors
#
env.add_template_context_processors(['cubane.ishop.context_processors.shop'])


#
# Apps
#
env.add_apps([
    'cubane',
    'cubane.legacy.jquery',
    'cubane.backend',
    'cubane.backend.accounts',
    'cubane.cms',
    'cubane.directory',
    'cubane.media',
    'cubane.medialoader',
    'cubane.enquiry',
    'cubane.default_frontend',
    'cubane.scrollable',
    'cubane.lightbox',
    'cubane.dbmigrate',
    'cubane.fonts',
    'cubane.aggregator',
    'cubane.blog',
    'cubane.svgicons',
    'cubane.ishop',
    'cubane.usstates',
    'cubane.pdfmake',
    'cubane.offcanvas_nav',
    'cubane.testapp',
    'cubane.testapp.recursive',
    'cubane.testapp.empty',
    'cubane.testapp.subapp',
    'django_coverage'
])


#
# Resources
#
RESOURCES = {
    'frontend': [
        'cubane.legacy.jquery',
        'cubane.default_frontend',
        'cubane.scrollable',
        'cubane.lightbox',
        'cubane.enquiry',
        'cubane.fonts',
        'cubane.testapp',
    ],
    'inline': [
        'cubane.medialoader',
    ],
    'testing': [
        'cubane.testapp'
    ],
    'recursive': [
        'cubane.testapp.recursive'
    ],
    'empty': [
        'cubane.testapp.empty'
    ],
    'subapp': [
        'cubane.testapp.subapp'
    ]
}


#
# Image Shapes
#
IMAGE_SHAPES = {
    'header': '1280:448',
    'grid1x1': '336:281',
    'grid1x2': '336:628',
    'grid2x2': '738:628'
}


#
# Image sizes
#
IMAGE_SIZES = {
    'xx-small':  75,
    'x-small':  149,
    'small':    254,
    'medium':   336,
    'large':    738,
    'x-large': 1280
}


#
# CMS
#
CMS = 'cubane.testapp.views.TestAppCMS'
CMS_TEMPLATES = (
    ('testapp/page.html', 'Page'),
    ('testapp/homepage.html', 'Home Page'),
    ('testapp/test.html', 'Test'),
    ('testapp/mail/enquiry_visitor.html', 'Enquiry Email'),
)
CMS_SLOTNAMES = ['content', 'introduction', 'signature']
CMS_SETTINGS_MODEL = 'cubane.testapp.models.Settings'
CMS_EXCERPT_LENGTH = 200


#
# Enquiry
#
ENQUIRY_MODEL = 'cubane.testapp.models.Enquiry'
ENQUIRY_CLIENT_TEMPLATE = 'testapp/mail/enquiry_client.html'
CAPTCHA = 'new_recaptcha'
CAPTCHA_SITE_KEY = '...'
CAPTCHA_SECRET_KEY = '...'


#
# Resource compression (require js)
#
REQUIRE_JS = [
    {
        'filename': 'testapp/js/require_js_main.js',
    }
]


#
# Navigation
#
CMS_NAVIGATION = (
    ('header', 'Header'),
    ('footer_first', 'Footer'),
)


#
# Backend theme
#
BACKEND_THEME = {
    'color': {
        'r': 243,
        'g': 146,
        'b': 0
    }
}


#
# Shop
#
SHOP = 'cubane.testapp.views.TestAppShop'
SHOP_PRODUCT_MODEL = 'cubane.testapp.models.Product'
SHOP_CATEGORY_MODEL = 'cubane.testapp.models.Category'
SHOP_ORDER_MODEL = 'cubane.testapp.models.Order'
SHOP_CUSTOMER_MODEL = 'cubane.testapp.models.Customer'
SHOP_FEATURED_ITEM_MODEL = 'cubane.testapp.models.FeaturedItem'
SHOP_CUSTOM_PROPERTIES = {
    'left-calf':  ('Left Calf', 'cm'),
    'right-calf': ('Right Calf', 'cm')
}
FEATURED_SET_CHOICES = ()
CURRENCY = '£'
CURRENCY_ISO = 'GBP'


#
# Google Maps
#
CUBANE_GOOGLE_MAP_API_KEY = 'foo'