# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.utils.module_loading import import_module
from django.contrib.staticfiles.finders import find
from cubane.lib.file import file_get_contents, file_put_contents
from cubane.lib.module import register_class_extensions
from django.template import Template
import os
import glob
import hashlib
import datetime
import string
import random
import glob
import re


RESOURCE_TAREGT_DEF = None
RESOURCE_MANAGER_CLASS = None
MAX_INCLUDE_RESOURCES_STEPS = 8


class ResourceManager(object):
    """
    Base class that can be extended by other apps to hook into the resource
    pipeline.
    """
    @classmethod
    def register_extension(cls, *args):
        """
        Register a new extension(s) for the resource manager class.
        """
        return register_class_extensions('ExtendedResourceManager', cls, args)


    def process_resource_entry(self, target, ext, css_media, prefix, resource):
        """
        Process the given (raw) resource.
        """
        return (prefix, resource)


def get_resource_manager(ignore_cache=False):
    """
    Return a new instance to the resource manager.
    """
    global RESOURCE_MANAGER_CLASS

    if not RESOURCE_MANAGER_CLASS or ignore_cache:
        RESOURCE_MANAGER_CLASS = ResourceManager
        # give each module the chance to extend the base class
        for app_name in settings.INSTALLED_APPS:
            try:
                app = import_module(app_name)
                if hasattr(app, 'install_resource_manager'):
                    RESOURCE_MANAGER_CLASS = app.install_resource_manager(RESOURCE_MANAGER_CLASS)
            except ImportError:
                raise ValueError(
                    ('Error importing app \'%s\' while loading resource ' + \
                     'manager extensions.') % app_name
                )

    # creates a new instance every time...
    return RESOURCE_MANAGER_CLASS()


def get_resource_target_definition(ignore_cache=False):
    """
    Return the app's full resource target definition from settings. Allow
    each app to declare its own resource target definitions on which
    the declaration found in settings can extend upon.
    """
    global RESOURCE_TAREGT_DEF

    if not RESOURCE_TAREGT_DEF or ignore_cache:
        RESOURCE_TAREGT_DEF = {}

        def _update_resources(resources):
            """
            extend resources by given resource target definition.
            """
            for key, items in resources.items():
                if key in RESOURCE_TAREGT_DEF:
                    for item in items:
                        if item not in RESOURCE_TAREGT_DEF[key]:
                            RESOURCE_TAREGT_DEF[key].append(item)
                else:
                    RESOURCE_TAREGT_DEF[key] = items

        # collect targets from each app
        for app_name in settings.INSTALLED_APPS:
            try:
                app = import_module(app_name)
                if hasattr(app, 'RESOURCE_TARGETS'):
                    _update_resources(app.RESOURCE_TARGETS)
            except ImportError:
                raise ValueError(
                    ('Error importing app \'%s\' while loading resource ' + \
                     'targets.') % app_name
                )

        # collect targets from settings
        _update_resources(settings.RESOURCES)

    return RESOURCE_TAREGT_DEF


def generate_resource_version_identifier():
    """
    Generate a unique hash for the resource version identifier which
    uniquely identifies a particular build of all resources.
    """
    return hashlib.sha224('%s-%s' % (
        datetime.datetime.now(),
        ''.join([random.choice(string.printable) for i in range(0, 256)])
    )).hexdigest()[:6]


def get_resource_version_filename():
    """
    Return the filename of the resource version identifier.
    """
    return os.path.join(settings.STATIC_ROOT, 'revision')


def save_resource_version_identifier(identifier):
    """
    Store resource version identifier with in website's deployment target folder.
    """
    file_put_contents(get_resource_version_filename(), identifier)


def load_resource_version_identifier():
    """
    Load resource version identifier from the website's deployment target folder.
    """
    filename = os.path.join(settings.STATIC_ROOT, 'revision')
    try:
        return file_get_contents(filename)
    except IOError:
        return None


def get_resource_files_by_identifier(identifier):
    """
    Return a list of filenames for all resource files with the given
    identifier (including svg icon files).
    """
    if identifier:
        return (
            glob.glob('%s/cubane.*.%s.min.*' % (settings.STATIC_ROOT, identifier)) +
            glob.glob('%s/cubane.svgicons.*.%s.svg' % (settings.STATIC_ROOT, identifier))
        )
    else:
        return []


def get_resource_files_not_matching_identifier(identifier):
    """
    Return a list of absolute paths to all resource files which do not match
    the given identifier.
    """
    if identifier:
        filenames = (
            glob.glob('%s/cubane.*.*.min.*' % settings.STATIC_ROOT) +
            glob.glob('%s/cubane.svgicons.*.svg' % settings.STATIC_ROOT)
        )
        return filter(lambda f: not re.match(r'^.*?cubane\..*\.%s\.min\..*$' % identifier, f) and not re.match(r'^.*?cubane\..*\.%s\.svg$' % identifier, f), filenames)
    else:
        return []


def get_resource_targets():
    """
    Return a list of resource build targets in alphabetical order.
    """
    resources = get_resource_target_definition()
    targets = []
    for keys in resources.keys():
        for key in [x.strip() for x in keys.split(',')]:
            if key not in targets and key != 'all':
                targets.append(key)
    return sorted(targets)


def collect_included_app_dependencies_for_app(app, collected_apps, ignore_apps, steps=0):
    """
    Return a list of apps the given app includes by using the
    INCLUDE_RESOURCES definition. Please note that this is evaluated recursively
    up to a fixed max. number of steps.
    """
    # max. iterations reached?
    if steps > MAX_INCLUDE_RESOURCES_STEPS:
        return

    # app has already been collected/ignored?
    if app in collected_apps or app in ignore_apps:
        return

    # app is not installed?
    if app not in settings.INSTALLED_APPS:
        return

    # make sure that the app is ignored by recursive attempts, even through
    # we have not added the app yet due to the order in which things depend
    # on each other...
    ignore_apps.append(app)

    # try to load app and load dependencies...
    try:
        m = import_module(app)
        if hasattr(m, 'INCLUDE_RESOURCES'):
            for _app in m.INCLUDE_RESOURCES:
                collect_included_app_dependencies_for_app(
                    _app,
                    collected_apps,
                    ignore_apps,
                    steps + 1
                )
    except ImportError, e:
        pass

    # add app to the list of collected apps
    collected_apps.append(app)


def get_apps_for_resource_target(target):
    """
    Return a list of apps for which the given resource target applies.
    Only return apps that are actually loaded via INSTALLED_APPS. Please note
    that an app may define further app includes on which the app itself relies
    on.
    """
    resources = get_resource_target_definition()
    target_apps = []
    for targets, apps in resources.items():
        keys = [x.strip() for x in targets.split(',')]
        if target in keys or 'all' in keys:
            for app in apps:
                # add the given app and its dependencies to the list
                collect_included_app_dependencies_for_app(
                    app,
                    target_apps,
                    []
                )

    return target_apps


def is_external_resource(url):
    """
    Return True, if the given url or path is external rather than local.
    """
    return                            \
        url.startswith('http://') or  \
        url.startswith('https://') or \
        url.startswith('//')


def get_downloadable_resource_url(url):
    """
    Return a downloadable resource url based on the given external url, which
    might use //.
    """
    if url.startswith('//'):
        url = 'https://%s' % url[2:]

    return url


def get_resources_glob(app_name, app_base_path, resources):
    """
    If we cannot find the resource itself within /static/ or /media/,
    extend the given list of resources by applying glob on each resource
    pattern.
    """
    result = []

    for resource in resources:
        # external resource from the web?
        if is_external_resource(resource):
            result.append(resource)
            continue

        url_path = resource.lstrip('/')

        # media?
        if resource.startswith('/media/'):
            result.append(resource)
        else:
            # try static
            path = find(url_path)
            if path:
                result.append(resource)
            else:
                base = os.path.join(app_base_path, 'static')
                path = os.path.join(base, resource)
                files = glob.glob(path)
                files = [filename.replace(base, '') for filename in files]
                files = sorted(files)
                result.extend(files)

    return result


def get_resources(target, ext=None, css_media=None, data_only=False, name=None):
    """
    Walk through all installed django apps in the order in which they were
    defined in settings.INSTALLED_APPS and return a list of all uniquely named
    resources that each django app defines (css and js files).
    If an extension is given, the resulting list is filtered by the given
    extension. If css_media is given, the resulting list is filtered by
    the given css media target.
    Each resource path is added to the name of the django app automatically.
    """
    if not css_media:
        css_media = 'screen'

    if ext != None:
        ext = '.%s' % ext.lower()

    # determine list of apps that apply for given target
    apps = get_apps_for_resource_target(target)

    # walk through all installed apps and extract resources
    manager = get_resource_manager()
    resources = []
    for app_name in apps:
        try:
            m = import_module(app_name)
            if hasattr(m, 'RESOURCES'):
                app_resources = []

                for r in m.RESOURCES:
                    # extract css media prefix
                    p = r.split('|', 1)
                    if len(p) == 2:
                        prefix = p[0].lower()
                        r = p[1]
                    else:
                        prefix = 'screen'

                    # hook: process raw resource entry
                    if not data_only:
                        prefix, r = manager.process_resource_entry(target, ext, css_media, prefix, r)

                    # skip blank resources
                    if r is None:
                        continue

                    # prefix must match or prefix is 'all'.
                    if css_media != prefix:
                        # let the prefix 'all' through unless we are collecting
                        # font declarations
                        if not (prefix == 'all' and css_media != 'font'):
                            continue

                    # determine full path to the file and substitude
                    # app name
                    if not data_only and not is_external_resource(r):
                        path = os.path.join(app_name.replace('.', '/'), r)
                    else:
                        path = r

                    # ext must match (if given)
                    if ext != None and os.path.splitext(path)[1].lower() != ext:
                        continue

                    # add unique resource if not collected yet
                    if path not in app_resources:
                        app_resources.append(path)

                # process glob
                if not data_only:
                    app_base_path = os.path.dirname(m.__file__)
                    app_resources = get_resources_glob(app_name, app_base_path, app_resources)

                # add app resources to combined list of resources
                resources.extend(app_resources)
        except ImportError:
            pass

    # flter by filename if provided
    if name is not None:
        resources = filter(lambda r: os.path.splitext(os.path.basename(r))[0] == name, resources)

    return resources


def get_resource_path(url_path):
    """
    Return the actual full path to the given resource.
    """
    # add leading strip so that django can find the correct asset
    # due to the base path of cubane being outside of the projects directory
    # os.path.join - If any component is an absolute path,
    # all previous components are thrown away, and joining continues.
    if url_path.startswith('/media/'):
        path = os.path.join(settings.MEDIA_ROOT, url_path[7:])
    else:
        url_path = url_path.lstrip('/')

        if not settings.MINIFY_RESOURCES:
            path = find(url_path)
        else:
            path = os.path.join(settings.STATIC_ROOT, url_path)

    return path


def get_resource(url_path):
    """
    Return the actual content of the file given by url_path, which is the
    absolute web path.
    """
    path = get_resource_path(url_path)

    # fail in DEBUG, otherwise return empty content in production
    if settings.DEBUG:
        if not os.path.isfile(path):
            raise ValueError(
                'Unable to load resource content from file \'%s\'.' % path
            )

    try:
        return file_get_contents(path)
    except IOError:
        return ''


def get_minified_filename(target, ext, css_media=None, identifier=None):
    """
    Return the filename of the minified resource file for the given revision
    of this application and the given file extension (css or js).
    """
    if ext == 'css' and not css_media:
        css_media = 'screen'

    if ext == 'js':
        css_media = None

    if identifier and settings.TRACK_REVISION:
        if css_media:
            return 'cubane.%s.%s.%s.min.%s' % (target, css_media, identifier, ext)
        else:
            return 'cubane.%s.%s.min.%s' % (target, identifier, ext)
    else:
        if css_media:
            return 'cubane.%s.%s.min.%s' % (target, css_media, ext)
        else:
            return 'cubane.%s.min.%s' % (target, ext)