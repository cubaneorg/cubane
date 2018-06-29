# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.module import get_module_by_name, module_exists
from cubane.lib.acl import Acl
from decimal import Decimal
import os
import sys


class SettingsValidationError(ValueError):
    pass


def validate_settings(settings):
    """
    Validate the given settings.
    """
    # if staticfiles is used, make sure it is installed AFTER cubane.
    if 'django.contrib.staticfiles' in settings.INSTALLED_APPS and \
       'cubane' in settings.INSTALLED_APPS:
        # compare indicies
        index_staticfiles = settings.INSTALLED_APPS.index('django.contrib.staticfiles')
        index_cubane = settings.INSTALLED_APPS.index('cubane')
        if index_staticfiles < index_cubane:
            raise SettingsValidationError(
                'The app \'django.contrib.staticfiles\' should appear AFTER ' +
                '\'cubane\'. Use the \'add_apps()\' helper method in order ' +
                'to safely add installed apps without having to manually ' +
                'take care of the correct order.'
            )


def get_default_templates(base_path, debug):
    """
    Return the default templates settings configuration structure
    based on given base path and debug settings.
    """
    # default template loader and template paths
    _template_loaders = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )

    # load with template caching in production
    if not debug:
        _template_loaders = (
            ('django.template.loaders.cached.Loader', _template_loaders),
        )

    return [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [
                os.path.join(base_path, 'templates')
            ],
            'OPTIONS': {
                'context_processors': [
                    'django.contrib.auth.context_processors.auth',
                    'django.template.context_processors.debug',
                    'django.template.context_processors.media',
                    'django.template.context_processors.request',
                    'django.contrib.messages.context_processors.messages',
                    'cubane.context_processors.config',
                    'cubane.context_processors.backend',
                ],
                'loaders': _template_loaders
            },
        },
    ]


class SettingWrapper(object):
    """
    Returned by default_env() that provides additional helper methods for
    the project's settings file to use in order to work with settings, such as
    adding addition context processors or apps.
    """
    LOAD_APPS_AFTER_CUBANE = [
        'django.contrib.staticfiles'
    ]


    def __init__(self, m):
        """
        Create a new settings wrapper for the given settings module m.
        """
        self.m = m


    def add_template_context_processors(self, template_context_processors):
        """
        Add the given list of template processors.
        """
        if not isinstance(template_context_processors, list):
            template_context_processors = [template_context_processors]

        # create TEMPLATES if it does not exist
        if not hasattr(self.m, 'TEMPLATES'):
            setattr(self.m, 'TEMPLATES', [])

        # create generic django-based template settings if empty
        if not self.m.TEMPLATES:
            self.m.TEMPLATES = get_default_templates(self.m.BASE_PATH, self.m.DEBUG)

        # create 'OPTIONS' if not present
        if 'OPTIONS' not in self.m.TEMPLATES[0]:
            self.m.TEMPLATES[0]['OPTIONS'] = {};

        # create 'context_processors' if not present
        if 'context_processors' not in self.m.TEMPLATES[0]['OPTIONS']:
            self.m.TEMPLATES[0]['OPTIONS']['context_processors'] = [];

        # add to context processors
        self.m.TEMPLATES[0]['OPTIONS']['context_processors'].extend(template_context_processors)

        return self


    def add_apps(self, apps=None):
        """
        Add given list of apps to the system. Please note that staticfiles is
        (on purpose) kept at the end of the list, since cubane overrides
        runserver.
        """
        # convert to list
        installed_apps = self.m.INSTALLED_APPS
        if not isinstance(self.m.INSTALLED_APPS, list):
            installed_apps = list(self.m.INSTALLED_APPS)

        # convert argument to list
        if not apps:
            apps = []
        elif not isinstance(apps, list):
            apps = [apps]

        # add apps (without duplicates)
        for app in apps:
            if app not in installed_apps:
                installed_apps.append(app)

        # are we actually using cubane?
        try:
            index = installed_apps.index('cubane')
        except ValueError:
            index = -1

        if index >= 0:
            # make sure that certain apps are loaded AFTER cubane
            load_apps_after_cubane = []
            for app in self.LOAD_APPS_AFTER_CUBANE:
                # extract out of existing set of installed apps
                if app in installed_apps:
                    if app not in load_apps_after_cubane:
                        load_apps_after_cubane.append(app)
                    installed_apps.remove(app)

            # re-insert apps that need to be loaded after cubane after having
            # loaded cubane in the order they have been defined.
            if len(load_apps_after_cubane) > 0:
                installed_apps = (
                    installed_apps[:index + 1] +
                    load_apps_after_cubane +
                    installed_apps[index + 1:]
                )

        # save result in settings
        self.m.INSTALLED_APPS = installed_apps

        # adjust max. data upload fields if we are using the shop system
        if 'cubane.ishop' in installed_apps:
            self.m.DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

        return self


    @property
    def settings(self):
        """
        Return the settings module.
        """
        return self.m


def default_env(
    module_name,
    domain_name,
    admin_email,
    site_name=None,
    db_name=None,
    test=None,
    debug=None,
    debug_toolbar=False,
    high_res_images=False,
    image_credits=False,
    pull_host=None,
    pull_user=None,
    pull_sudo=None,
    pull_db_name=None,
    pull_shell=None,
    csrf=False,
    ssl=False,
    frontend_editing=False,
    email_file_log=False):
    """
    Setup default configuration, where module_name is the settings module that
    is calling this function, domain_name the name of the website or project.

    The default project configuration setup a PostgreSQL database with a name
    that is equal to the name of the project (e.g. domain_name). The base path
    is determined by the absolute path of the module that is named module_name.

    In order to pre-configure your project, add the following two lines to your
    settings.py file:

    from lib.settings import default_env
    env = default_env(__name__, 'test.co.uk')
    """
    # get settings module and normalise site name
    m = get_module_by_name(module_name)
    domain_name = domain_name.strip().lower()


    #
    # Determine if we are running under TEST
    #
    m.TEST = test if test is not None else 'test' in sys.argv


    # determine debug or production mode.
    # default is production mode unless we find the environment variable
    # DEV_MODE to be set to 1, in which case we assume DEBUG mode.
    m.DEBUG = debug if debug is not None else os.environ.get('DEV_MODE', '0') == '1' and not m.TEST
    m.MINIFY_RESOURCES = not m.DEBUG and not m.TEST


    #
    # Site
    #
    m.SITE_ID = 1
    m.DOMAIN_NAME = domain_name
    m.ALLOWED_HOSTS = ['*']
    m.TRACK_REVISION = True
    m.GENERATE_MINIFY_SRC = False
    m.DEBUG_DOMAIN_NAME = None


    #
    # Site name
    #
    m.CUBANE_SITE_NAME = site_name


    #
    # Database name
    #
    if db_name:
        m.DATABASE_NAME = db_name
    else:
        m.DATABASE_NAME = domain_name.replace('.', '_').replace('-', '_')


    #
    # Default path
    #
    m.CUBANE_PATH = os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            '../'
        )
    )
    m.BASE_PATH = os.path.realpath(
        os.path.join(
            os.path.dirname(m.__file__),
            '../'
        )
    )


    #
    # Resource compressors
    #
    if m.TEST:
        # we use yuicompressor in test, because it is much faster
        m.MINIFY_CMD_JS  = 'java -jar %s --type js' % os.path.join(m.CUBANE_PATH, 'bin', 'yui', 'yuicompressor-2.4.8.jar')
        m.MINIFY_CMD_CSS = 'java -jar %s --type css' % os.path.join(m.CUBANE_PATH, 'bin', 'yui', 'yuicompressor-2.4.8.jar')
    else:
        m.MINIFY_CMD_JS  = 'java -jar %s' % os.path.join(m.CUBANE_PATH, 'bin', 'closure-compiler', 'compiler.jar')
        m.MINIFY_CMD_CSS = 'java -jar %s --type css' % os.path.join(m.CUBANE_PATH, 'bin', 'yui', 'yuicompressor-2.4.8.jar')


    #
    # Dashboard
    #
    m.CUBANE_DASHBOARD = False


    #
    # Default Operations
    #
    m.CUBANE_LISTING_DEFAULT_CLEAN = True
    m.CUBANE_LISTING_DEFAULT_MERGE = True


    #
    # Default CMS settings
    #
    m.CMS_RENDER_SLOT_CONTAINER = False
    m.CMS_TEMPLATES = (
        ('cubane/cms/default_template.html', 'Default Template'),
    )
    m.CMS_NAVIGATION = (
        ('header', 'Header'),
        ('footer', 'Footer'),
    )
    m.CMS_NAVIGATION_INCLUDE_CHILD_PAGES = False
    m.CMS_EXCERPT_LENGTH = 60
    m.CMS_NO_AUTO_EXCERPT = False
    m.CMS_SLOTNAMES = ['content']
    m.CMS_NAVIGATION_RELATED_FIELDS = ['image']
    m.CMS_TEST_SPF = True
    m.CMS_SOFTFAIL_SPF = False
    m.CMS_ADV_EDITOR_PLUGINS = False
    m.CMS_DEFAULT_SLOTNAME = 'content'
    m.CMS_BACKEND_SITEMAP = False
    m.CMS_META_TITLE_SEPARATOR = ' | '


    #
    # Default Google Analytics key in debug mode
    #
    m.DEBUG_GOOGLE_ANALYTICS = None


    #
    # Admin and managers
    #
    m.ADMINS = m.MANAGERS = (
        ('admin', admin_email),
    )

    m.INTERNAL_IPS = (
        '127.0.0.1',
    )


    #
    # Default session serializer (Extended JSON)
    #
    m.SESSION_SERIALIZER = 'cubane.serializers.ExtendedJSONSerializer'

    #
    # Backend permissions and ACLs
    #
    m.CUBANE_BACKEND_PERMISSIONS = False
    m.CUBANE_BACKEND_ACL = {}
    m.CUBANE_BACKEND_DEFAULT_ACL = {
        'create': Acl.ALL,
        'read': Acl.ALL,
        'update': Acl.ALL,
        'delete': Acl.ALL,
        'data_import': Acl.ALL,
        'data_export': Acl.ALL,
        'merge': Acl.ALL
    }


    #
    # Cubane backend editor
    #
    m.CUBANE_BACKEND_EDITOR_PLUGINS = [
        '-advlist',
        '-autolink',
        '-charmap',
        '-print',
        '-searchreplace',
        '-visualblocks',
        '-code',
        '-fullscreen',
        '-insertdatetime',
        '-table',
        '-paste',
        '-nonbreaking',
        '-lists',
        '-cubanepreview',
        '-cubanelink'
    ]
    m.CUBANE_BACKEND_EDITOR_YOUTUBE = True


    #
    # Depreceated: Default backend presentation
    #
    m.BACKEND_THEME = {
        'product_name': 'inystem',
        'hide_innershed_logo': False,
        'color': {
            'r': 232,
            'g': 48,
            'b': 138
        }
    }


    #
    # Default backend button labels
    #
    m.CUBANE_BACKEND_DEFAULT_SAVE_BUTTON_LABEL = 'Save <small>And Close</small>'
    m.CUBANE_BACKEND_DEFAULT_SAVE_AND_CONTINUE_BUTTON_LABEL = 'Save <small>And Continue</small>'
    m.CUBANE_BACKEND_DEFAULT_BACK_BUTTON_LABEL = 'Back'


    #
    # Media options
    #
    m.CUBANE_BACKEND_MEDIA = True
    m.CUBANE_HASHED_MEDIA_URLS = False
    m.CUBANE_DEFAULT_MEDIA_PREVIEW_EXT = '.jpg'
    m.CUBANE_MEDIA_VERSIONS = True


    #
    # Video
    #
    m.CUBANE_VIDEO_TYPES = [
        'youtube'
    ]

    #
    # Timezone, Language and Formatting
    #
    m.TIME_ZONE = 'Europe/London'
    m.LANGUAGE_CODE = 'en-GB'
    m.USE_I18N = False
    m.DATE_FORMAT = 'd/m/Y'
    m.TIME_FORMAT = 'P'
    m.DATETIME_FORMAT = 'd/m/Y H:i'
    m.STR_DATE_FORMAT = '%d_%m_%Y'
    m.DATE_INPUT_FORMATS = (
        '%Y-%m-%d',   # 2006-10-25s
        '%d/%m/%Y',   # 25/10/2006
        '%d/%m/%y',   # 25/10/06
        '%d-%b-%y',   # 30-Dec-06
    )
    m.TIME_INPUT_FORMATS = (
        '%H:%M:%S',    # 14:30:55
        '%H:%M:%S.%f', # 14:30:55.123
        '%H:%M',       # 14:30
        '%I:%M %p'     # 2:30 PM
    )
    m.DATETIME_INPUT_FORMATS = (
        '%Y-%m-%dT%H:%M',        # '2010-10-10T10:15'
        '%d/%m/%Y %H:%M:%S',     # '25/10/2006 14:30:59'
        '%d/%m/%Y %H:%M:%S.%f',  # '25/10/2006 14:30:59.000200'
        '%d/%m/%Y %H:%M',        # '25/10/2006 14:30'
        '%d/%m/%Y',              # '25/10/2006'
        '%d/%m/%y %H:%M:%S',     # '25/10/06 14:30:59'
        '%d/%m/%y %H:%M:%S.%f',  # '25/10/06 14:30:59.000200'
        '%d/%m/%y %H:%M',        # '25/10/06 14:30'
        '%d/%m/%y',              # '25/10/06'
    )


    #
    # Default database setup
    #
    m.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': m.DATABASE_NAME
        }
    }


    #
    # Speed up unit testing by switching database engine to sqlite3, unless
    # the env. specifies to run a full test and not speeding up unit testing.
    #
    m.TEST_FULL = False
    if m.TEST: # pragma: no cover
        m.TEST_FULL = os.environ.get('DEV_TEST_FULL', '0') == '1'
        if not m.TEST_FULL:
            m.DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'


    #
    # Turn off django migrations if we are running under test.
    # See: http://stackoverflow.com/questions/25161425/disable-migrations-when-running-unit-tests-in-django-1-7
    #
    if m.TEST:
        m.MIGRATION_MODULES = {'myapp': None}


    #
    # Static and cache
    #
    m.CACHE_ENABLED = True
    m.CACHE_PUBLISH_ENABLED = True
    m.STATIC_URL = '/static/'
    m.PUBLIC_HTML_ROOT = os.path.abspath(os.path.join(m.BASE_PATH, '..', '..', 'public_html'))
    m.CACHE_ROOT = os.path.join(m.PUBLIC_HTML_ROOT, 'cache')
    m.STATIC_ROOT = os.path.join(m.PUBLIC_HTML_ROOT, 'static')
    m.STATICFILES_DIRS = (
        os.path.join(m.BASE_PATH, 'static'),
    )


    #
    # Media
    #
    if m.DEBUG or m.TEST:
        m.MEDIA_ROOT = os.path.abspath(os.path.join(m.BASE_PATH, 'media'))
    else:
        m.MEDIA_ROOT = os.path.abspath(os.path.join(m.BASE_PATH, '..', '..', 'public_html', 'media'))
    m.MEDIA_URL = 'media/'
    m.MEDIA_API_URL = 'media-api/'


    #
    # Media Download Url
    #
    m.MEDIA_DOWNLOAD_URL = 'download/'


    #
    # Fonts
    #
    m.CUBANE_FONT_ROOT = os.path.join(m.MEDIA_ROOT, 'fonts')
    m.CUBANE_FONT_BACKENDS = [
        'cubane.fonts.backends.GoogleFontsBackend',
    ]


    #
    # Responsive image sizes
    #
    m.DEFAULT_IMAGE_SIZE = 'x-large'
    m.CMS_EDITOR_DEFAULT_IMAGE_SIZE = 'x-large'
    m.IMAGE_SIZES = {
        'xx-small':  50,
        'x-small':  160,
        'small':    320,
        'medium':   640,
        'large':    900,
        'x-large': 1200
    }
    if high_res_images:
        m.DEFAULT_IMAGE_SIZE = 'xxx-large'
        m.CMS_EDITOR_DEFAULT_IMAGE_SIZE = 'xxx-large'
        m.IMAGE_SIZES.update({
            'xx-large':  1600,
            'xxx-large': 2400
        })

    m.DISABLE_DEVICE_RATIO = False


    #
    # Automatic image fitting
    #
    m.IMAGE_FITTING_ENABLED = False
    m.IMAGE_FITTING_SHAPES = []
    m.IMAGE_FITTING_COLOR   = 'white'


    #
    # Convert PNG files without transparency to JPG files
    #
    m.IMAGE_CONVERT_PNG_TO_JPG = True


    #
    # The default image compression for jpeg images
    #
    m.IMAGE_COMPRESSION_QUALITY = 82


    #
    # Image Optimization
    #
    m.IMAGE_OPTIMIZE = True
    m.IMAGE_JPEG_OPT_COMMAND = 'jpegtran -optimize -progressive -copy none -outfile %(dest)s %(source)s'
    m.IMAGE_PNG_OPT_COMMAND = 'optipng -o 0 -quiet -out %(dest)s %(source)s'


    #
    # Image PDF preview generation
    #
    m.IMAGE_PDF_PREVIEW_COMMAND = 'gs -sDEVICE=jpeg -o %(dest)s -dFirstPage=1 -dLastPage=1 -dJPEGQ=84 -r120 %(source)s'


    #
    # Maximal width considered to be saved as an original on the server
    #
    m.IMG_MAX_WIDTH = 2400


    #
    # Default image shape and image generator settings
    #
    m.DEFAULT_IMAGE_SHAPE = 'original'
    m.IMAGE_SHAPES = {}
    m.IMAGE_SHAPE_NAMES = {}
    m.IMAGE_ART_DIRECTION = {}


    #
    # Additional image information
    #
    m.IMAGE_CREDITS = image_credits
    m.IMAGE_EXTRA_TITLE = False
    m.IMAGE_CAPTION_LABEL = 'Caption'
    m.IMAGE_CAPTION_HELP_TEXT = 'Leave empty to fill automatically; Briefly describe the content of the image or document. This information is associated with the image or document and is analysed by search engines.'
    m.IMAGE_EXTRA_TITLE_LABEL = 'Description'
    m.IMAGE_EXTRA_TITLE_HELP_TEXT = 'If you wish to add an extra description to the image or document.'


    #
    # Devdeloper Information
    #
    m.CUBANE_PROVIDED_BY = {}


    #
    # Site Notification
    #
    m.CUBANE_SITE_NOTIFICATION = False


    #
    # Client Logo
    #
    m.CLIENT_LOGO = 'client-logo.png'


    #
    # Developer Logo
    #
    m.DEVELOPER_LOGO = 'developer-logo.png'


    #
    # Favicon Sizes used to generate the various favicons for different browsers
    #
    m.FAVICON_PATH = 'img'
    m.FAVICON_FILENAME = 'favicon.png'


    m.FAVICON_PNG_SIZES = [
        {'size': '16x16',   'filename': 'favicon-16x16.png'},
        {'size': '24x24',   'filename': 'favicon-24x24.png'},
        {'size': '32x32',   'filename': 'favicon-32x32.png'},
        {'size': '48x48',   'filename': 'favicon-48x48.png'},
        {'size': '57x57',   'filename': 'favicon-57x57.png'},
        {'size': '60x60',   'filename': 'favicon-60x60.png'},
        {'size': '64x64',   'filename': 'favicon-64x64.png'},
        {'size': '70x70',   'filename': 'favicon-70x70.png'},
        {'size': '72x72',   'filename': 'favicon-72x72.png'},
        {'size': '76x76',   'filename': 'favicon-76x76.png'},
        {'size': '96x96',   'filename': 'favicon-96x96.png'},
        {'size': '114x114', 'filename': 'favicon-114x114.png'},
        {'size': '120x120', 'filename': 'favicon-120x120.png'},
        {'size': '128x128', 'filename': 'favicon-128x128.png'},
        {'size': '144x144', 'filename': 'favicon-144x144.png'},
        {'size': '150x150', 'filename': 'favicon-150x150.png'},
        {'size': '152x152', 'filename': 'favicon-152x152.png'},
        {'size': '196x196', 'filename': 'favicon-196x196.png'},
        {'size': '310x150', 'filename': 'favicon-310x150.png'},
        {'size': '310x310', 'filename': 'favicon-310x310.png'}
    ]


    m.FAVICON_ICO_SIZES = [
        {'size': '16x16', 'filename': 'favicon-16x16.png'},
        {'size': '24x24', 'filename': 'favicon-24x24.png'},
        {'size': '32x32', 'filename': 'favicon-32x32.png'},
        {'size': '48x48', 'filename': 'favicon-48x48.png'},
        {'size': '64x64', 'filename': 'favicon-64x64.png'},
        {'size': '128x128', 'filename': 'favicon-128x128.png'}
    ]


    #
    # Default middleware
    #
    m.MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'cubane.middleware.SettingsMiddleware'
    )


    #
    # CSRF
    #
    if csrf:
        m.MIDDLEWARE_CLASSES = (
            'django.middleware.csrf.CsrfViewMiddleware',
        ) + m.MIDDLEWARE_CLASSES


    #
    # Templates
    #
    m.TEMPLATES = get_default_templates(m.BASE_PATH, m.DEBUG)


    #
    # Default apps
    #
    m.INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.sitemaps',
        'django.contrib.staticfiles'
    )


    #
    # Frontend editing
    #
    m.CUBANE_FRONTEND_EDITING = frontend_editing
    if frontend_editing:
        m.MIDDLEWARE_CLASSES += (
            'cubane.middleware.FrontendEditingMiddleware',
        )
        m.INSTALLED_APPS += (
            'cubane.frontend',
            'cubane.frontendloader',
        )


    #
    # Default locale
    #
    m.CUBANE_LOCALE = b'en_GB.UTF-8'


    #
    # Captcha
    #
    m.CAPTCHA = None
    m.RECAPTCHA_PUBLIC_KEY = ''
    m.RECAPTCHA_PRIVATE_KEY = ''
    m.CAPTCHA_PLACEHOLDER = ''


    #
    # Google Map API Key
    #
    m.CUBANE_GOOGLE_MAP_API_KEY = ''


    #
    # Google analytics
    #
    m.CUBANE_GOOGLE_ANALYTICS_ASYNC = False


    #
    # Mail
    #
    m.EMAIL_SUBJECT_PREFIX = '[%s] ' % domain_name
    if m.DEBUG:
        if email_file_log:
            m.EMAIL_BACKEND = 'cubane.backends.EmailEmlFileBackend'
            m.EMAIL_FILE_PATH = os.path.join(m.BASE_PATH, 'log')
        else:
            m.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    if m.TEST:
        m.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


    #
    # Login and Authentication
    #
    m.AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'cubane.backends.EmailAuthBackend',
    )


    #
    # Urls
    #
    m.APPEND_SLASH = True
    m.PREPEND_WWW = not m.DEBUG


    #
    # SSL - Determines whether the website should run ssl or not. This will
    # affect page redirects (which would be https:// rather than http:// but
    # will not neccessarily redirect from http:// to https:// automatically).
    #
    m.SSL = ssl
    if ssl:
        m.MIDDLEWARE_CLASSES += ('cubane.middleware.SSLResponseRedirectMiddleware',)


    #
    # Default logging setup
    #
    m.LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            }
        },
        'handlers': {
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'django.utils.log.AdminEmailHandler'
            }
        },
        'loggers': {
            'django.request': {
                'handlers': ['mail_admins'],
                'level': 'ERROR',
                'propagate': True,
            },
        }
    }


    #
    # Default file upload handlers
    #
    m.FILE_UPLOAD_HANDLERS = (
        'django.core.files.uploadhandler.TemporaryFileUploadHandler',
    )


    #
    # Default resource targets
    #
    m.RESOURCES = {}
    m.CSS_MEDIA = ['screen', 'print']

    #
    # Default Require.js entry files
    # Array of config dict: [{'filepath':s, 'baseurl':s, 'module':s},...]
    # filepath: to id the file that needs to be compiled to a single file
    # baseURL: root directory to every module search (optional)
    # module: name of the module e.g. main (from main.js) (optional)
    #
    m.REQUIRE_JS = []


    #
    # Default configuration for backend listings
    #
    m.MAX_LISTING_COLUMNS = 6


    #
    # Default location for google map (backend)
    #
    m.DEFAULT_MAP_LOCATION = [52.6370209, 1.2996577]


    #
    # Default configuration for paginator
    #
    m.DEFAULT_PAGE_SIZE     = 10
    m.DEFAULT_MIN_PAGE_SIZE = 10
    m.DEFAULT_MAX_PAGE_SIZE = 100


    #
    # Shop defaults
    #
    m.SHOP_PREAUTH = False
    m.SHOP_CUSTOM_PROPERTIES = {}
    m.SHOP_BASKET_SESSION_VAR = 'ishop_basket'
    m.SHOP_BASKET_ALLOWED_PREFIX = ['ishop_basket']
    m.SHOP_BASKET_BACKEND_PREFIX = 'ishop_backend'
    m.SHOP_DEFAULT_DELIVERY_COUNTRY_ISO = 'GB'
    m.TRACKING_PROVIDERS = []
    m.SHOP_LOCALE = b'en_GB.UTF-8'
    m.SHOP_ENABLE_KIT_BUILDER = False
    m.SHOP_VARIETY_FILTER_ENABLED = True
    m.SHOP_MULTIPLE_CATEGORIES = False
    m.SHOP_CHANGE_CUSTOMER_PASSWORD_ENABLED = True
    m.SHOP_LOAD_VARIETY_PREVIEW = True


    #
    # Payment Gateways
    #
    m.GATEWAY_TEST      = 0
    m.GATEWAY_SAGEPAY   = 1
    m.GATEWAY_PAYPAL    = 2
    m.GATEWAY_STRIPE    = 3
    m.GATEWAY_DEKO      = 4
    m.GATEWAY_OMNIPORT  = 5
    m.GATEWAY_CHOICES = (
        (m.GATEWAY_TEST, 'Test Gateway'),
        (m.GATEWAY_SAGEPAY, 'Sagepay'),
        (m.GATEWAY_PAYPAL, 'PayPal'),
        (m.GATEWAY_STRIPE, 'Stripe'),
        (m.GATEWAY_DEKO, 'Deko'),
        (m.GATEWAY_OMNIPORT, 'OmniPort')
    )


    #
    # Default Payment gateways used
    #
    m.SHOP_LOAN_ENABLED = False
    m.SHOP_DEFAULT_PAYMENT_GATEWAY = m.GATEWAY_SAGEPAY
    m.SHOP_LOAN_PAYMENT_GATEWAY = m.GATEWAY_DEKO
    m.SHOP_PAYMENT_CONFIG = {}
    m.SHOP_TEST_MODE = m.DEBUG


    #
    # Allow pages to use hierarchy
    #
    m.PAGE_HIERARCHY = False


    #
    # Postcode Lookup
    #

    m.POSTCODE_GETADDRESS = 0
    m.POSTCODE_PROVIDERS = (
        (m.POSTCODE_GETADDRESS, 'GetAddress.io')
    )
    m.DEFAULT_POSTCODE_PROVIDER = m.POSTCODE_GETADDRESS
    m.POSTCODE_PROVIDER = m.DEFAULT_POSTCODE_PROVIDER
    m.POSTCODE_DEBUG = False


    #
    # Status Code handlers
    #
    m.HANDLER_404 = 'cubane.default_views.custom404'
    m.HANDLER_500 = 'cubane.default_views.custom500'


    # Pull from production server
    m.CUBANE_PULL = {
        'DATABASE': pull_db_name if pull_db_name else m.DATABASE_NAME,
        'HOST': pull_host if pull_host else m.DOMAIN_NAME,
        'USER': pull_user if pull_user else 'root',
        'DBDUMP': 'pg_dump',
        'SUDO': pull_sudo if pull_sudo else m.DOMAIN_NAME if not pull_user else None,
        'SHELL': pull_shell if pull_shell else 'sh',
        'SUDO_DEFINED': pull_user is None
    }


    #
    # Debug Toolbar (Debug only)
    #
    m.DEBUG_TOOLBAR = debug_toolbar
    if m.DEBUG and debug_toolbar:
        m.INSTALLED_APPS = m.INSTALLED_APPS + ('debug_toolbar',)
        m.MIDDLEWARE_CLASSES = ('debug_toolbar.middleware.DebugToolbarMiddleware',) + m.MIDDLEWARE_CLASSES
        m.DEBUG_TOOLBAR_PANELS = [
            'debug_toolbar.panels.versions.VersionsPanel',
            'debug_toolbar.panels.timer.TimerPanel',
            'debug_toolbar.panels.settings.SettingsPanel',
            'debug_toolbar.panels.headers.HeadersPanel',
            'debug_toolbar.panels.request.RequestPanel',
            'debug_toolbar.panels.sql.SQLPanel',
            'debug_toolbar.panels.staticfiles.StaticFilesPanel',
            'debug_toolbar.panels.cache.CachePanel',
            'debug_toolbar.panels.signals.SignalsPanel',
            'debug_toolbar.panels.logging.LoggingPanel',
            'debug_toolbar.panels.redirects.RedirectsPanel',
            #'debug_toolbar.panels.templates.TemplatesPanel'
        ]


    return SettingWrapper(m)
