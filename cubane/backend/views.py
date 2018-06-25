# coding=UTF-8
from __future__ import unicode_literals
from django.core.exceptions import FieldDoesNotExist
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db import transaction
from django.db.models import ManyToManyField
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.core.mail import mail_admins
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils.safestring import mark_safe
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.module_loading import import_module
from django.utils.encoding import force_bytes
from django.template.defaultfilters import slugify
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.template.defaultfilters import date as filter_date
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from cubane.decorators import redirect_login, template
from cubane.views import TemplateView, ModelView, view_url, view
from cubane.forms import DataExportForm
from cubane.backend.forms import BackendLoginForm, BackendPasswordResetForm, ChangeLogForm, DashboardAddWidgetForm
from cubane.backend.models import UserProfile, ChangeLog
from cubane.backend.changelog import ChangeLogManager
from cubane.backend.dashboard import *
from cubane.tasks import TaskRunner
from cubane.decorators import is_dialog_window_request
from cubane.frontend import *
from cubane.lib.app import hash_to_model
from cubane.lib.libjson import *
from cubane.lib.mail import cubane_send_cms_enquiry_mail
from cubane.lib.url import get_absolute_url
from cubane.lib.app import get_models
from cubane.lib.auth import login_user_without_password
from cubane.lib.utf8 import DEFAULT_ENCOPDING
from cubane.lib.file import ensure_dir
from cubane.lib.acl import Acl
import cubane
import os
import copy
import requests
import json
import random
import collections
import math
import tempfile
import hashlib


class RelatedModelCollection(object):
    """
    Manages related entities, for example related products, downloads for a
    page or a media gallery.
    """
    @classmethod
    def load(cls, instance, through_model, sortable=True):
        """
        Load given list of related instances for the given instance.
        """
        # determine from/to field names automatically
        field = cls._get_field(instance, through_model)
        from_name = field.m2m_field_name()
        to_name = field.m2m_reverse_field_name()

        related = through_model.objects \
            .select_related(to_name) \
            .filter(**{from_name: instance})

        if sortable:
            related = related.order_by('seq')
        else:
            related = related.order_by(*['%s__title' % to_name])

        return [getattr(x, to_name) for x in related]


    @classmethod
    def save(cls, request, instance, items, through_model, allow_duplicates=True, sortable=True, max_items=None):
        """
        Save the given list of related items to the given instance.
        """
        if items is None:
            return

        # determine from/to field names automatically
        field = cls._get_field(instance, through_model)
        from_name = field.m2m_field_name()
        to_name = field.m2m_reverse_field_name()

        # delete all existing assignments
        assignments = through_model.objects.filter(**{
            from_name: instance
        }).all()
        index = {}
        for assignment in assignments:
            if request:
                request.changelog.delete(assignment)
            x = getattr(assignment, to_name)
            key = '%s-%s' % (instance.pk, x.pk)
            index[key] = assignment
            assignment.delete()

        # create new assignments. Ignore duplicates if we do not allow
        # duplicates and respect max_items if provicded...
        seen = {}
        n = 0
        for i, x in enumerate(items, start=1):
            # ignore duplicates?
            key = '%s-%s' % (instance.pk, x.pk)
            if not allow_duplicates and key in seen:
                continue

            # exit if we have enought items
            if max_items is not None and n >= max_items:
                break

            # create new intermediate model
            t = through_model()

            # copy values across from previous assignment (if exists)
            previous_assignment = index.get(key)
            if previous_assignment:
                for field in previous_assignment._meta.get_fields():
                    if field.name not in ['id', from_name, to_name]:
                        setattr(t, field.name, getattr(assignment, field.name))

            # set assignment
            setattr(t, from_name, instance)
            setattr(t, to_name, x)

            # set seq. order if sortable
            if sortable:
                t.seq = i

            t.save()
            seen[key] = True
            n += 1

            if request:
                request.changelog.create(t)


    @classmethod
    def _get_field(cls, instance, through_model):
        for field in instance.__class__._meta.get_fields():
            if isinstance(field, ManyToManyField) and field.rel.through == through_model:
                return field
        raise ValueError('The model class \'%s\' does not appear to have a ManyToMany field with a through model of \'%s\'.' % (
            instance.__class__,
            through_model
        ))


class EmbeddedCollection(object):
    """
    Manages an embedded collection of related entities.
    """
    @classmethod
    def load(cls, initial, field_name, queryset):
        """
        Load initial list of embedded related entities.
        """
        if hasattr(queryset.model, 'embedded_load_items'):
            instances = list(queryset)

            for i, instance in enumerate(instances, start=1):
                queryset.model.embedded_load_items(initial, field_name, instance, i)

            initial[field_name] = instances
        else:
            initial[field_name] = queryset

        return initial


    @classmethod
    def load_items(cls, initial, outer_field_name, index, field_name, queryset):
        key = 'cubane_ef_%s_%s--%s' % (outer_field_name, index, field_name)
        initial[key] = queryset
        return initial


    @classmethod
    def save_items(cls, request, items, related_field_name, instance, queryset, assignments={}):
        pks = []
        for i, item in enumerate(items, start=1):
            # previous instance
            previous_item = None
            if item.pk:
                try:
                    item_instance = queryset.get(pk=item.pk)
                    previous_item = request.changelog.get_changes(item_instance)
                except queryset.model.DoesNotExist:
                    pass

            setattr(item, related_field_name, instance)
            item.seq = i

            # additional assignments
            for attr_name, attr_value in assignments.items():
                setattr(item, attr_name, attr_value)

            # save item and keep pks
            item.save()
            pks.append(item.pk)

            # update changelog
            if previous_item:
                request.changelog.edit(item, previous_item)
            else:
                request.changelog.create(item)

            # save embedded items
            if hasattr(item, '_embedded_instances') and hasattr(item.__class__, 'embedded_save_items'):
                item.__class__.embedded_save_items(request, item._embedded_instances, item)

        # delete the ones that have been removed
        for instance in queryset.exclude(pk__in=pks).all():
            request.changelog.delete(instance)
            instance.delete()


    @classmethod
    def save(cls, request, cleaned_data, field_name, related_field_name, instance, queryset, assignments={}):
        """
        Save a list of embedded related entities.
        """
        items = cleaned_data.get(field_name)
        if items is None: items = []
        cls.save_items(request, items, related_field_name, instance, queryset, assignments)


class ProgressInfo(object):
    """
    Represents information about progress made.
    """
    def __init__(self, total, major=0, minor=0):
        self.total = total
        self.major = major
        self.minor = minor


    @classmethod
    def from_dict(cls, d):
        if d is None:
            d = {}

        return ProgressInfo(
            d.get('total', 0),
            d.get('major', 0),
            d.get('minor', 0)
        )


    def to_dict(self):
        """
        Return a JSON representation of the progress information.
        """
        return {
            'total': self.total,
            'major': self.major,
            'minor': self.minor
        }


class Progress(object):
    """
    Manages the process made while processing data on the server.
    """
    @classmethod
    def get_progress(cls, request):
        """
        Return the upload processing progress that has been made so far in
        total.
        """
        if not request: return 0

        # get progress info
        info = cls._get(request, 'progress')
        if info is None: return 0

        if info.total <= 0: info.total = 1
        step = 100.0 / float(info.total)

        percent = math.ceil(float(info.major) + (step * float(info.minor) / 100.0))
        if percent > 100: percent = 100

        return percent


    @classmethod
    def start(cls, request, total):
        """
        Set the total number of operations that are expected to happen.
        """
        if not request: return
        cls._set(request, 'progress', ProgressInfo(total))


    @classmethod
    def stop(cls, request):
        """
        Stop processing.
        """
        cls._delete(request, 'progress')


    @classmethod
    def set_progress(cls, request, counter):
        """
        Set information about the upload progress that has been made so far
        in terms of files processed.
        """
        if not request: return

        info = cls._get(request, 'progress')
        if info:
            info.major = cls._get_percent(counter, info.total)
            info.minor = 0
            cls._set(request, 'progress', info)


    @classmethod
    def set_sub_progress(cls, request, counter, total):
        """
        Set information about the upload progress that has been made so far
        for a particular file.
        """
        if not request: return

        info = cls._get(request, 'progress')
        if info:
            info.minor = cls._get_percent(counter, total)
            cls._set(request, 'progress', info)


    @classmethod
    def _get_percent(cls, counter, total):
        """
        Return the percentage of progress made based on given number of item
        that is currently being processed (counter) and the total amount of
        items to process.
        """
        return math.ceil(float(counter) / float(total) * 100.0);


    @classmethod
    def _get_name(cls, request, name):
        """
        Return the full internal name of the shared cache variable of given
        local name.
        """
        return '%s_%s_%s' % (
            request.session.session_key,
            request.GET.get('progressId'),
            name
        )


    @classmethod
    def _get_filename(cls, key):
        """
        Return the full file path to the cache file based on the given key.
        """
        path = tempfile.gettempdir()
        filename = '%s.cache' % hashlib.md5(force_bytes(key)).hexdigest()
        return os.path.join(path, filename)


    @classmethod
    def _get(cls, request, name, default=None):
        """
        Return the value of the shared cache variable with given name.
        """
        if not request: return default

        key = cls._get_name(request, name)
        try:
            return ProgressInfo.from_dict(decode_json(cls._read(key)))
        except:
            return default


    @classmethod
    def _set(cls, request, name, value):
        """
        Set shared cache variable with given name to given value.
        """
        if not request: return

        key = cls._get_name(request, name)
        try:
            cls._write(key, to_json(value.to_dict()))
        except:
            pass


    @classmethod
    def _write(cls, key, raw_value):
        """
        Write the given raw value to a cache file that depends on the given key.
        """
        filename = cls._get_filename(key)
        ensure_dir(filename)
        with open(filename, 'w') as f:
            f.write(raw_value)


    @classmethod
    def _read(cls, key):
        """
        Read cached raw value from file that depends on the given key.
        """
        filename = cls._get_filename(key)
        with open(filename, 'r') as f:
            return f.read()


    @classmethod
    def _delete(cls, request, name):
        """
        Delete cached file depending on given key.
        """
        if not request: return

        key = cls._get_name(request, name)
        filename = cls._get_filename(key)
        try:
            os.remove(filename)
        except:
            pass


class BackendSection(object):
    """
    Provides a named section within the backend system. Each section is
    organized as a separate menu within the main navigation.
    """
    divider = False
    navigatable = True
    priority = 0


    def __init__(self, *args, **kwargs):
        super(BackendSection, self).__init__()

        # generate title automatically if not set based on class name
        if not hasattr(self, 'title'):
            self.title = self.__class__.__name__

        # generate slug automatically if not set based on title
        if hasattr(self, 'title') and not hasattr(self, 'slug'):
            self.slug = slugify(self.title)


    @property
    def url(self):
        return self.get_url()


    @property
    def has_multiple_sub_sections(self):
        """
        Return True, if this section has more than one sub-section.
        """
        return hasattr(self, 'sections') and len(self.sections) > 1


    def validate_models(self):
        """
        Perform integrity checks on all managed models for this section.
        """
        # attached view?
        if hasattr(self, 'view') and self.view:
            if hasattr(self.view, 'validate_models'):
                self.view.validate_models()

        # sub-sections
        if hasattr(self, 'sections') and self.sections:
            for section in self.sections:
                section.validate_models()


    def get_first_visible_to_user(self, user):
        """
        Return the first section or sub-section that is visible to the user.
        """
        # collect view condidates, first the main section and then sub-sections
        candidates = []
        if hasattr(self, 'view'):
            candidates.append( (self, self.view) )
        if hasattr(self, 'sections'):
            for section in self.sections:
                if hasattr(section, 'view'):
                    candidates.append( ( section, section.view) )

        # we can see the section if we are allowed to see it directly or we
        # are allowed to see at least one if its sub-sections
        for section, view in candidates:
            if section.navigatable:
                if hasattr(view, 'user_has_permission'):
                    if view.user_has_permission(user, 'view'):
                        return section
                else:
                    return section

        return None


    def get_frist_visible_section_url_for(self, user):
        """
        Return the full URL to the first visible backend sub-section of this
        section.
        """
        section = self.get_first_visible_to_user(user)
        if section:
            return section.get_url()
        else:
            return ''


    def is_visible_to_user(self, user):
        """
        Return True, if the given user has permissions to view this section.
        """
        return self.get_first_visible_to_user(user) != None


    def grouped_sections(self):
        """
        Return a list of section and groups of sections.
        """
        if not hasattr(self, 'sections'):
            return []

        # group sections by group name or no group name
        groups = collections.OrderedDict()
        for s in self.sections:
            if hasattr(s, 'group'):
                group = s.group
            else:
                group = None

            if group not in groups:
                groups[group] = []

            groups[group].append(s)

        # build up list of resulting items
        items = []
        for group, sections in groups.items():
            if group:
                items.append({
                    'grouped': True,
                    'title': group,
                    'sections': sections
                })
            else:
                for s in sections:
                    items.append({
                        'grouped': False,
                        'section': s
                    })

        return items


    def get_urls(self, backend, section=None, sub_section=None, prefix=None):
        """
        Return all url patterns for this backend section based on the attached
        View handler.
        """
        urls = []

        # keep track of current section and sub-section
        if section == None:
            section = self
        elif sub_section == None:
            sub_section = self

        # collect urls from attached master view for this section
        if hasattr(self, 'view'):
            for url in self.view.get_urls(prefix=getattr(self, 'slug', None)):
                backend.dispatchable_url(url, section, sub_section)
                urls.append(url)

        # this section may have one or more sub-sections
        _prefix = section.slug if hasattr(section, 'slug') else None
        if hasattr(self, 'sections'):
            for sec in self.sections:
                sec_urls = sec.get_urls(
                    backend,
                    section,
                    sub_section,
                    prefix=_prefix
                )
                for url in sec_urls:
                    urls.append(url)

        return urls


    def get_url(self):
        """
        Return the main url for this backend section. This url is used for the
        main navigation item.
        """
        if hasattr(self, 'view'):
            return self.view.get_url()

        if hasattr(self, 'sections'):
            for section in self.sections:
                url = section.get_url()
                if url: return url

        return ''


    def get_view_for_model(self, model):
        """
        Scan through all registered sub-sections and find the view that is
        responsible for the given model.
        """
        if hasattr(self, 'view'):
            if issubclass(type(self.view), ModelView):
                if hasattr(self.view, 'model'):
                    if self.view.model == model:
                        return self.view

        if hasattr(self, 'sections'):
            for sec in self.sections:
                view = sec.get_view_for_model(model)
                if view: return view


    def get_url_for_model(self, model, view='index'):
        """
        Scan through all registered sub-sections and find the url for the
        backend section that manages the given model.
        """
        if hasattr(self, 'view'):
            if issubclass(type(self.view), ModelView):
                url = self.view.get_url_for_model(model, view)
                if url: return url

        if hasattr(self, 'sections'):
            for sec in self.sections:
                url = sec.get_url_for_model(model, view)
                if url: return url


    def get_url_for_model_instance(self, instance, view='index'):
        """
        Scan through all registered sub-sections and find the url for the
        backend section that manages the given model instance.
        """
        if hasattr(self, 'view'):
            if issubclass(type(self.view), ModelView):
                url = self.view.get_url_for_model_instance(instance, view)
                if url: return url

        if hasattr(self, 'sections'):
            for sec in self.sections:
                url = sec.get_url_for_model_instance(instance, view)
                if url: return url

        return None


    def get_section_by_class(self, cls):
        """
        Return the direct section of this section that is of given class or None.
        """
        for section in self.sections:
            if isinstance(section, cls):
                return section
        return None


    def get_model_sections(self, models):
        """
        Split given list of models into multiple backend sections according to
        the class method called 'get_backend_sections' on the model.
        """
        # construct sections
        items = []
        for model in models:
            if hasattr(model, 'get_backend_sections'):
                attr, choices = model.get_backend_sections()
                for attr_value, title in choices:
                    items.append((title, attr, attr_value, model))
            else:
                title = model._meta.verbose_name_plural
                items.append((title, None, None, model))

        # sort by title
        items.sort(key=lambda x: x[0])
        return items


class BackendView(object):
    """
    Provides a read-only version of the backend instance that is unique to
    each view handler and also holds some state that is specific to the current
    request.
    """
    def __init__(self, backend, sections, current_section, current_sub_section):
        self._backend = backend
        self._sections = sections
        self._current_section = current_section
        self._current_sub_section = current_sub_section

        # sort sections by priority
        self._sections.sort(key=lambda s: s.priority, reverse=True)


    @property
    def site(self):
        return self._backend


    @property
    def url(self):
        return self._backend.url


    @property
    def default_map_location_json(self):
        """
        Return the default map location in json format.
        """
        return to_json(settings.DEFAULT_MAP_LOCATION)


    @property
    def sections(self):
        return self._backend.sections


    @property
    def has_sub_sections(self):
        return self._backend.has_sub_sections


    @property
    def current_section(self):
        return self._current_section


    @property
    def current_sub_section(self):
        return self._current_sub_section


    @property
    def title(self):
        """
        Return the title of the current section/sub-section.
        """
        if self.current_sub_section:
            return self.current_sub_section.title
        else:
            return self.current_section.title


    def get_view_for_model(self, model):
        """
        Scan through all registered sub-sections and find the view that is
        responsible for the given model.
        """
        return self._backend.get_view_for_model(model)


    def get_url_for_model(self, model, view='index'):
        """
        Scan through all registered backend sections and find the url for the
        backend section that manages the given model. The view argument defines
        the type of view we are interested in, for example index, edit or create.
        """
        return self._backend.get_url_for_model(model, view)


    def get_url_for_model_instance(self, instance, view='index'):
        """
        Scan through all registered backend sections and find the url for the
        backend section that manages the given model instance. The view argument
        defines the type of view we are interested in, for example index,
        edit or create.
        """
        return self._backend.get_url_for_model_instance(instance, view)


class Backend(TemplateView):
    """
    Provides the innershed backend system that is the basis for managing an
    innershed website or application. Various components integrate themself into
    the backend, for example the cms subsystem. Also, application-specific
    functionality can be easily integrated alongside default functionality that
    the backend system provides, such as login, password forgotten and account
    and role management.
    """
    template_path = 'cubane/backend/'
    patterns = [
        # login/logout
        view_url(r'^login/$', 'login', name='cubane.backend.login'),
        view_url(r'^logout/$', 'logout', name='cubane.backend.logout'),
        view_url(r'^password-forgotten/$', 'password_forgotten', name='cubane.backend.password_forgotten'),
        view_url(r'^password-reset/$', 'password_reset', name='cubane.backend.password_reset'),

        # dashboard
        view_url(r'^$', 'index', name='cubane.backend.index'),
        view_url('^add-dashboard-widget/$', 'add_dashboard_widget', name='cubane.backend.add_dashboard_widget'),
        view_url('^remove-dashboard-widget/$', 'remove_dashboard_widget', name='cubane.backend.remove_dashboard_widget'),
        view_url('^dashboard_widget_options/$', 'dashboard_widget_options', name='cubane.backend.dashboard_widget_options'),
        view_url('^dashboard-seq/$', 'dashboard_seq', name='cubane.backend.dashboard_seq'),

        # internals
        view_url(r'^heartbeat/$', 'heartbeat', name='cubane.backend.heartbeat'),
        view_url(r'^progress/$', 'progress', name='cubane.backend.progress'),
        view_url(r'^messages/$', 'messages', name='cubane.backend.messages'),
        view_url(r'^undo/$', 'undo', name='cubane.backend.undo'),
        view_url(r'^download-with-encoding/$', 'download_with_encoding', name='cubane.backend.download_with_encoding'),
        view_url(r'^frontend-edit/(?P<h>[a-zA-Z\d]+)/$', 'frontend_edit', name='cubane.backend.frontend_edit'),
    ]


    PUBLIC_URL_NAMES = [
        'cubane.backend.login',
        'cubane.backend.logout',
        'cubane.backend.password_forgotten',
        'cubane.backend.heartbeat',
    ]
    PASSWORD_RESET_URL_NAME = 'cubane.backend.password_reset'


    def __init__(self):
        """
        Initialises a new Backend instance with an empty set of sections.
        Use register_section() in order to add your own sections to the backend.
        """
        self._sections = []
        self._apis = []
        self._dashboard_widgets = []
        self._collect()


    def _collect(self):
        """
        Scan through all installed apps and call install_backend module level
        if there is such a function.
        """
        for app_name in settings.INSTALLED_APPS:
            app = import_module(app_name)
            if hasattr(app, 'install_backend'):
                app.install_backend(self)


    @property
    def url(self):
        return self.get_url()


    @property
    def sections(self):
        return self._sections


    @property
    def apis(self):
        return self._apis


    def get_section_by_class(self, cls):
        """
        Return the direct section of this backend that is of given class or None.
        """
        for section in self._sections:
            if isinstance(section, cls):
                return section
        return None


    @property
    def has_sub_sections(self):
        """
        Return true, if this backend system has at least one section that has
        at least more than one sub-section in it.
        """
        for section in self._sections:
            if hasattr(section, 'sections') and len(section.sections) > 1:
                return True
        return False


    def dispatchable_url(self, url_pattern, section=None, sub_section=None):
        """
        Make the given url dispatch-able through this backend system, which
        - when dispatched - will inject state information into the backend
        objects, which then is made available to view handlers and templates
        through the request objects.
        """
        # get actual target
        handler = url_pattern.callback
        handler_name = url_pattern.name

        def view(request, *args, **kwargs):
            # we need to be at least a staff member in order to get access to
            # the backend (apart from login and password forgotten).
            if handler_name not in self.PUBLIC_URL_NAMES:
                # authneticated staff member required!
                if not(request.user.is_authenticated() and request.user.is_staff):
                    # raise permission denied if we are within a dialog window
                    if is_dialog_window_request(request):
                        raise PermissionDenied()
                    else:
                        return redirect_login(request)

                # load user profile
                try:
                    request.user_profile = UserProfile.objects.get(user=request.user)
                except UserProfile.DoesNotExist:
                    request.user_profile = UserProfile()
                    request.user_profile.user = request.user

                # create changelog manager
                request.changelog = ChangeLogManager(request)

                # password reset? redirect to password reset page if we are not
                # already on the password reset page...
                if request.user_profile.reset:
                    if handler_name not in self.PASSWORD_RESET_URL_NAME and not settings.DEBUG:
                        return HttpResponseRedirect(reverse(self.PASSWORD_RESET_URL_NAME))

            # inject current section, current sub-section and request
            request.backend = BackendView(self, self.sections, section, sub_section)

            # every response handler as part of the backend runs within a
            # transaction. Only enter a transaction if no atomic block is active
            conn = transaction.get_connection(using=None)
            if not conn.in_atomic_block and conn.autocommit:
                transaction.set_autocommit(False)
            try:
                # call response handler
                response = handler(request, *args, **kwargs)

                # if changelog has been committed, materialize the change
                if hasattr(request, 'changelog'):
                    request.changelog.materialize()

                # add no-cache headers
                if isinstance(response, HttpResponse):
                    response['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
                    response['Expires'] = 'Fri, 01 Jan 2010 00:00:00 GMT'

                return response
            except:
                transaction.rollback()
                raise
            finally:
                transaction.commit()
                transaction.set_autocommit(True)

        # cascade CSRF exemption annotation down the pipe, otherwise django
        # will not see the annotation...
        if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE_CLASSES:
            if getattr(handler, 'csrf_exempt', False):
                view.csrf_exempt = True

        # patch url pattern
        url_pattern.callback = view


    def get_urls(self):
        """
        Return all backend url patterns containing default url patterns for
        default views such as login and password forgotten as well as all
        custom backend-registered sections and API view handlers.
        The url dispatch is patched with a local dispatch handler that handles
        view handler dispatching for all related views for this backend.
        """
        # collect all url patterns that are attached to this backend
        # directly, e.g. login/logout etc...
        urls = super(Backend, self).get_urls()
        for url in urls:
            self.dispatchable_url(url)

        # add section-based url patterns
        for section in self._sections:
            urls.extend(section.get_urls(backend=self))

        # add api url patterns
        for api in self._apis:
            prefix = api.slug if hasattr(api, 'slug') else None
            for url in api.get_urls(prefix=prefix):
                self.dispatchable_url(url)
                urls.append(url)

        return urls


    def get_url(self):
        """
        Return the start page for the backend system (e.g. dashboard).
        """
        return reverse('cubane.backend.index')


    def get_view_for_model(self, model):
        """
        Scan through all registered backend sections and find the view that
        is responsible for managing the given model.
        """
        for section in self._sections:
            view = section.get_view_for_model(model)
            if view:
                return view


    def get_url_for_model(self, model, view='index'):
        """
        Scan through all registered backend sections and find the url for the
        backend section that manages the given model. The view argument defines
        the type of view we are interested in, for example index, edit or create.
        """
        for section in self._sections:
            url = section.get_url_for_model(model, view)
            if url:
                return url


    def get_url_for_model_instance(self, instance, view='index'):
        """
        Scan through all registered backend sections and find the url for the
        backend section that manages the given model instance. The view argument
        defines the type of view we are interested in, for example index,
        edit or create.
        """
        for section in self._sections:
            url = section.get_url_for_model_instance(instance, view)
            if url:
                return url
        return None


    def register_section(self, section):
        """
        Attach given backend section to this backend system, so that the section
        is visible within the main navigation. Each section may add specific
        visibility and access rules, therefore not all sections may be visible
        to all users.
        """
        section.validate_models()
        self._sections.append(section)


    def register_dashboard_widget(self, dashboard_widget):
        """
        Attach given dashboard widget to the dashboard and allow users to
        use it.
        """
        try:
            # must derive from DashboardWidget
            if not issubclass(dashboard_widget, DashboardWidget):
                raise ValueError(
                    ('Argument to register_dashboard_widget() with value ' +
                    '\'%s\' must inherit from ' +
                    '\'cubane.backend/dashboard.DashboardWidget\'.') %
                        dashboard_widget
                )
        except TypeError:
            # must be class type
            raise ValueError(
                ('Argument to register_dashboard_widget() with value \'%s\' ' +
                'appears to be an instance where it must be a class type.') %
                    dashboard_widget
            )

        self._dashboard_widgets.append(dashboard_widget)


    def get_widget_by_identifier(self, request, widget_identifier):
        """
        Return a new instance of the widget with the given identifier or
        None if no such widget is known.
        """
        for widget_class in self._dashboard_widgets:
            if widget_class.get_identifier() == widget_identifier:
                # get widget options and create new instance
                options = self.get_widget_options_by_identifier(request, widget_identifier)
                widget = widget_class(options)

                # test acl
                if not request.user.is_superuser:
                    if not widget.acl.read:
                        return None

                return widget


    def get_widget_options_by_identifier(self, request, widget_identifier):
        """
        Return widget options for the given widget identifier.
        """
        user_dashboard = request.user_profile.dashboard
        for widget_options in user_dashboard.get('widgets', []):
            if widget_options.get('id') == widget_identifier:
                return widget_options.get('options', {})


    def register_api(self, api):
        """
        Attach given api view to this backend system.
        """
        self._apis.append(api)


    def get_site_name(self):
        """
        Return the name of the site or system.
        """
        client_logo_text = None

        # site name (settings)
        if not client_logo_text:
            if settings.CUBANE_SITE_NAME:
                client_logo_text = settings.CUBANE_SITE_NAME

        # CMS settings
        if not client_logo_text:
            try:
                from cubane.cms.views import get_cms
                cms = get_cms()
                client_logo_text = cms.settings.name
            except:
                pass

        # fallback to domain name
        if not client_logo_text:
            client_logo_text = settings.DOMAIN_NAME

        return client_logo_text


    def get_welcome_message(self, user):
        """
        Return welcome message addressing the user who logged in.
        """
        username = user.first_name if user.first_name else user.username
        return mark_safe('<strong>Welcome back to %s, %s.</strong><br/>%s' % (
            self.get_site_name(),
            username,
            ('Your last login was on %s (%s).' % (
                filter_date(user.last_login),
                naturaltime(user.last_login)
            ) if user.last_login else '')
        ))


    def get_provided_by(self, request):
        """
        Return information about the developer who is providing this system
        to the end-customer.
        """
        logo_url_path = 'img/%s' % settings.DEVELOPER_LOGO
        logo_path = finders.find(logo_url_path)
        has_logo = logo_path != None
        logo = static(logo_url_path)

        provided_by = {}
        provided_by.update(settings.CUBANE_PROVIDED_BY)
        provided_by.update({
            'logo': logo
        })
        return provided_by


    def login(self, request):
        """
        View handler for the login page.
        """
        if request.method == 'POST':
            form = BackendLoginForm(request.POST)
        else:
            form = BackendLoginForm()

        form.configure(request)

        if request.method == 'POST':
            if form.is_valid():
                user = form.get_user()
                if user.is_authenticated():
                    auth_login(request, user)
                    response = HttpResponseRedirect(reverse('cubane.backend.index'))

                    # set cookie for frontend editing
                    enable_frontend_editing(request, response)

                    return response
        else:
            request.session.set_test_cookie()

        # client logo
        client_logo_url_path = 'img/%s' % settings.CLIENT_LOGO
        client_logo_path = finders.find(client_logo_url_path)
        has_client_logo = client_logo_path != None
        client_logo = static(client_logo_url_path)

        # try to get the site name from cms settings
        # (we might not use the cms at all)
        client_logo_text = self.get_site_name()

        return {
            'form': form,
            'has_client_logo': has_client_logo,
            'client_logo': client_logo,
            'client_logo_text': client_logo_text
        }


    def logout(self, request):
        """
        View handler for loging out the current user and redirecting back to the
        login page. If we have ubpublished cms content, we will ask to
        publish first and then allow the user to logout.
        """
        # logout and redirect to login page
        auth_logout(request)
        response = HttpResponseRedirect(reverse('cubane.backend.login'))
        disable_frontend_editing(response)
        return response


    def password_forgotten(self, request):
        """
        View handler for initiating the password forgotten process.
        """
        raise Http404('Not implemented.')


    def password_reset(self, request):
        """
        Enforces that the current user changes its password to a new one.
        """
        # redirect to dashboard if we do not need a reset
        if (request.user_profile and not request.user_profile.reset) or settings.DEBUG:
            return HttpResponseRedirect(reverse('cubane.backend.index'))

        # create form
        if request.method == 'POST':
            form = BackendPasswordResetForm(request.POST)
        else:
            form = BackendPasswordResetForm()

        # tell the form what the request is
        form.configure(request)

        # form validation
        if request.method == 'POST' and form.is_valid():
            d = form.cleaned_data

            # change user's password
            request.user.set_password(d.get('password'))
            request.user.save()

            # update session hash, so that we will retain the current session
            update_session_auth_hash(request, request.user)

            # remove password reset from user's profile
            request.user_profile.reset = False
            request.user_profile.save()

            # redirect to dashboard
            return HttpResponseRedirect(reverse('cubane.backend.index'))

        return {
            'form': form
        }


    def index(self, request):
        """
        View handler for the main index page (dashboard). By default, redirect
        to the first backend section that is visible to the current user.
        """
        if settings.CUBANE_DASHBOARD:
            # add widget form
            _widgets = [self.get_widget_by_identifier(request, widget_class.get_identifier()) for widget_class in self._dashboard_widgets]
            _widgets = filter(lambda x: x, _widgets)

            widget_choices = [('', '-------')] + [
                (
                    _widget.get_identifier(),
                    _widget.get_title()
                ) for _widget in _widgets
            ]
            add_widget_form = DashboardAddWidgetForm()
            add_widget_form.configure(widget_choices)

            # render list of widgets for the current user
            widgets_options = request.user_profile.dashboard.get('widgets', [])
            widgets = []
            for widget_options in widgets_options:
                widget = self.get_widget_by_identifier(request, widget_options.get('id'))
                if widget:
                    widgets.append(widget)

            # dashboard template context
            dashboard_widgets = render_dashboard_widgets(request, widgets)
            dashboard_messages = filter(lambda x: x, [widget.get('message') for widget in dashboard_widgets])
            return {
                'add_widget_form': add_widget_form,
                'dashboard_widgets': dashboard_widgets,
                'dashboard_messages': dashboard_messages,
                'welcome_message': self.get_welcome_message(request.user),
                'provided_by': self.get_provided_by(request),
                'version': cubane.VERSION_STRING
            }
        else:
            # no dashboard -> go to first section
            for section in self.sections:
                if section.navigatable:
                    s = section.get_first_visible_to_user(request.user)
                    if s:
                        return HttpResponseRedirect(s.get_url())

            return {}


    @view(require_POST)
    def add_dashboard_widget(self, request):
        """
        View handler for adding a specific widget to the user's dashboard
        (AJAX).
        """
        success = False
        widget_html = None
        widget_identifier = request.POST.get('widget')
        widget = self.get_widget_by_identifier(request, widget_identifier)
        if widget:
            # update user profile
            user_dashboard = request.user_profile.dashboard
            user_dashboard.setdefault('widgets', [])
            user_dashboard['widgets'].append({
                'id': widget_identifier,
                'options': {}
            })
            request.user_profile.dashboard = user_dashboard
            request.user_profile.save()

            # render widget
            widget_context = render_dashboard_widget(request, widget)
            success = True
            widget_html = render_dashboard_widget_to_html(widget_context)

        return to_json_response({
            'success': success,
            'widget_html': widget_html
        })


    @view(require_POST)
    def remove_dashboard_widget(self, request):
        """
        View handler for removing a specific widget from the user's
        dashboard (AJAX).
        """
        success = False
        widget_identifier = request.POST.get('widget')
        widget = self.get_widget_by_identifier(request, widget_identifier)
        if widget:
            user_dashboard = request.user_profile.dashboard
            user_dashboard.setdefault('widgets', [])
            widget_item = None
            for widget_options in user_dashboard.get('widgets'):
                if widget_options.get('id') == widget_identifier:
                    widget_item = widget_options
            if widget_item:
                user_dashboard.get('widgets').remove(widget_item)
                request.user_profile.dashboard = user_dashboard
                request.user_profile.save()
                success = True

        return to_json_response({
            'success': success
        })


    @view(require_POST)
    def dashboard_widget_options(self, request):
        """
        View handler for updating widget options for a specific widget
        from the user's dashboard (AJAX).
        """
        success = False
        widget_html = None
        widget_identifier = request.GET.get('widget')
        options = request.POST.dict()
        if isinstance(options, dict):
            widget = self.get_widget_by_identifier(request, widget_identifier)
            if widget:
                user_dashboard = request.user_profile.dashboard
                user_dashboard.setdefault('widgets', [])
                for widget_options in user_dashboard.get('widgets'):
                    if widget_options.get('id') == widget_identifier:
                        widget_options.setdefault('options', {})
                        widget_options['options'].update(options)
                        success = True
                        break

                if success:
                    # save profile
                    request.user_profile.dashboard = user_dashboard
                    request.user_profile.save()

                # render widget
                    widget_context = render_dashboard_widget(request, widget)
                    widget_html = render_dashboard_widget_to_html(widget_context)

        return to_json_response({
            'success': success,
            'widget_html': widget_html
        })


    @view(require_POST)
    def dashboard_seq(self, request):
        """
        View handler for updating the sequence order of dashboard widgets
        (AJAX).
        """
        # load widgets
        seq = request.POST.getlist('seq[]')
        user_dashboard = request.user_profile.dashboard
        user_dashboard.setdefault('widgets', [])

        # change order acccording to given seq order
        new_seq = []
        for widget_id in seq:
            for widget_config in user_dashboard['widgets']:
                if widget_config.get('id') == widget_id:
                    new_seq.append(widget_config)
                    break

        # save new order in user profile
        user_dashboard['widgets'] = new_seq
        request.user_profile.dashboard = user_dashboard
        request.user_profile.save()

        return to_json_response({
            'success': True
        })


    @view(require_POST)
    def heartbeat(self, request):
        """
        Check session state and return task runner status information.
        """
        response_data = {}

        # determine session satus
        if request.user and request.user.is_authenticated():
            response_data['result'] = 'Success'
        else:
            response_data['result'] = 'error'
            response_data['message'] = 'Reload. no session available.'

        # get task runner status
        if TaskRunner.is_available():
            response_data['taskInfo'] = TaskRunner.get_status()
        else:
            response_data['taskInfo'] = None

        return HttpResponse(json.dumps(response_data), content_type='application/json')


    @view(require_GET)
    def progress(self, request):
        """
        Return JSON information about the progress uploading and processing
        media files.
        """
        return to_json_response({
            'percent': Progress.get_progress(request)
        });


    @view(require_POST)
    def messages(self, request):
        """
        Receive latest system messages and return them as JSON.
        """
        return to_json_response_with_messages(request)


    @view(require_POST)
    def undo(self, request):
        """
        Undo given operation.
        """
        changelog = ChangeLogManager(request)
        message = None
        try:
            log, undo_create = changelog.undo(request.POST.get('change'))
        except:
            log = None
            undo_create = False
            message = 'Unable to undo this operation.'

        return to_json_response_with_messages(request, {
            'success': log is not None,
            'message': message,
            'undo_create': undo_create
        })


    @view(template('cubane/backend/listing/download_with_encoding.html'))
    def download_with_encoding(self, request):
        """
        Present form for downloading CSV data by choosing encoding.
        """
        # determine default encoding from settings
        default_encoding = self.get_default_encoding(request)

        # render download with encoding form
        return {
            'form': DataExportForm(initial={
                'encoding': default_encoding
            })
        }


    def get_default_encoding(self, request):
        """
        Return the default encoding.
        """
        encoding = DEFAULT_ENCOPDING
        if 'cubane.cms' in settings.INSTALLED_APPS:
            from cubane.cms.views import get_cms_settings
            cms_settings = get_cms_settings()
            if cms_settings.default_encoding:
                encoding = cms_settings.default_encoding

        return encoding


    def frontend_edit(self, request, h):
        """
        Present frontend editing form.
        """
        model = hash_to_model(h)
        pk = request.GET.get('pk')
        if model and pk:
            view = self.get_view_for_model(model)
            if view:
                request.view_instance = view
                context = view._edit(request, pk=pk)
                context['cubane_template_view_path'] = os.path.join(self.template_path, 'create_edit.html')
                return context

        raise PermissionDenied()


class ChangeLogView(ModelView):
    namespace = 'cubane.backend.changelog'
    template_path = 'cubane/backend/changelog/'
    model = ChangeLog
    form = ChangeLogForm
    open_in_new_window = True


    patterns = [
        view_url(r'undo', 'undo', name='undo')
    ]

    listing_actions = [
        ('Restore', 'undo', 'multiple', 'post'),
    ]


    def create_edit(self, request, pk=None, edit=False):
        # go back
        if request.method == 'POST':
            return self._redirect(request, 'index')

        # get pk of changelog entry
        if not 'pk' in request.GET:
            raise Http404("Missing argument 'pk'.")
        pk = request.GET.get('pk')

        # get chnagelog item and child elements
        changes = get_object_or_404(ChangeLog, pk=pk)
        related = ChangeLog.objects.filter(parent=pk).order_by('seq')

        # replace field names with verbose names for singular
        self._replace_field_names_by_verbose(changes)

        # replace field names with verbose names for related
        for record in related:
            self._replace_field_names_by_verbose(record)

        return {
            'changes': changes,
            'related': related
        }


    def undo(self, request):
        """
        Undo given changelog entry by identifier.
        """
        # get pks
        pks = request.POST.getlist('pks[]', [])

        # perform undo
        changelog = ChangeLogManager(request)
        try:
            changelog.undo_by_ids(pks)
            success = True
            messages.add_message(request, messages.SUCCESS, 'Operation(s) restored successfully.')
        except:
            success = False
            messages.add_message(request, messages.ERROR, 'Unable to undo set of operations.')
            raise

        return to_json_response_with_messages(request, {
            'success': success
        })


    def _replace_field_names_by_verbose(self, record):
        if record.content_type:
            model = record.content_type.model_class()
            instance = model()

            for field in record.fields:
                if isinstance(field['a'], list):
                    field['a'] = ', '.join([unicode(x) for x in field['a']])
                if isinstance(field['b'], list):
                    field['b'] = ', '.join([unicode(x) for x in field['b']])

                try:
                    field['n'] = instance._meta.get_field(field['n']).verbose_name.title()
                except FieldDoesNotExist:
                    field['n'] = field['n'].title()


    def _get_objects(self, request):
        return ChangeLog.objects.filter(parent_id=None)


class ChangeLogBackendSubSection(BackendSection):
    title = 'Changelog'
    slug = 'changelog'
    view = ChangeLogView()


class ChangeLogBackendSection(BackendSection):
    title = 'Changelog'
    slug = 'changelog'
    priority = -1
    sections = [
        ChangeLogBackendSubSection()
    ]
