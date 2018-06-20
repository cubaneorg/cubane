# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.http import StreamingHttpResponse
from django.http.request import QueryDict
from django.shortcuts import render
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy, RegexURLPattern
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.template.loader import TemplateDoesNotExist
from django.forms import ModelForm, ModelChoiceField
from django.forms.models import fields_for_model
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import slugify
from django.utils.html import mark_safe
from django.db import models
from django.db import router
from django.db import transaction
from django.db import IntegrityError
from django.db.models import Q, Max
from django.db.models import CharField, TextField, EmailField, BooleanField, DateField
from django.db.models import ManyToManyField, IntegerField, AutoField
from django.db.models import Case, When
from django.db.models.functions import Lower
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey
from django.db.models.fields.reverse_related import ManyToOneRel
from django.db.models.deletion import Collector
from django.contrib.contenttypes.models import ContentType
from cubane.decorators import template
from cubane.decorators import user_has_permission as _user_has_permission
from cubane.decorators import identity, permission_required
from cubane.forms import FormLayout
from cubane.forms import DataImportForm
from cubane.forms import DateInput
from cubane.forms import MultiSelectFormField
from cubane.forms import SectionField
from cubane.models import DateTimeReadOnlyBase, DateTimeBase
from cubane.models.fields import TagsField
from cubane.models.fields import MultiSelectField
from cubane.models.data import Exporter, Importer
from cubane.media.models import Media
from cubane.backend.forms import ModelCollectionField
from cubane.backend.models import ChangeLog
from cubane.lib.libjson import to_json_response
from cubane.lib.file import to_uniform_filename
from cubane.lib.model import *
from cubane.lib.queryset import MaterializedQuerySet
from cubane.lib.url import url_with_arg, url_with_args, parse_query_string
from cubane.lib.ident import headline_from_ident
from cubane.lib.tree import TreeBuilder
from cubane.lib.request import request_int, request_bool, request_int_list
from cubane.lib.url import make_absolute_url
from cubane.lib.text import get_words, pluralize
from cubane.lib.acl import Acl
from cubane.lib.template import get_template
from cubane.signals import before_cms_save, after_cms_save
import re
import os
import copy
import datetime


TEXT_FIELDS = (CharField, EmailField, TextField)
MAX_RECORDS = 50
PAGINATION_MAX_RECORDS = 48
PAGINATION_PAGES_WINDOW_SIZE = 6
MAX_COLUMNS = 6
MAX_HIERARCHY_LEVELS = 3


def view_url(regex, view, kwargs=None, name=None):
    """
    Encapsulates a url pattern that can be used with views. This is mainly to
    support flexible arguments, so that we do not have to provide all
    arguments all the time.
    """
    return (regex, view, kwargs, name)


def get_columns(*args):
    """
    Return a list of columns based on given arguments.
    """
    return [{
        'title': arg[0],
        'fieldname': arg[1]
    } for arg in args]


def view(decorator=None):
    """
    Since methods do have an additional argument (self), we need to transform
    a regular decorator (which works on plain view functions) to a method
    decorator.
    """
    if decorator:
        return method_decorator(decorator)
    else:
        return identity


class View(object):
    """
    A view provides a set of operations that can be performed typically on one
    type of entity, for example a CustomerView derived from this class may
    implement all features that are necessary to list, filter, search, create,
    edit and delete customers in the context of a shop system for example.
    """
    @property
    def urls(self):
        if not hasattr(self, '_urls'):
            self._urls = self.get_urls()
        return self._urls


    @property
    def url(self):
        return self.get_url()


    def _get_urlpatterns(self, patterns, prefix=None):
        """
        Return url patterns than can be added to the django's url routing
        system by extracting url patterns from the given list of patterns
        and wrapping it into instances of RegexURLPattern.
        """
        urls = []
        for regex, handler_name, kwargs, name in patterns:
            # inject url prefix into patterns
            if prefix:
                if regex.startswith('^'):
                    regex = '^%s/%s' % (prefix, regex[1:])
                else:
                    regex = '%s/%s' % (prefix, regex)

            # add namespace
            if hasattr(self, 'namespace'):
                name = self.namespace + '.' + name

            # setup url route to view method
            handler = self._create_view_handler(handler_name)
            urls.append(RegexURLPattern(regex, handler, kwargs, name))
        return urls


    def get_patterns(self):
        """
        Return a list of all url pattern that are specified by this class and
        its super classes.
        """
        _patterns = []

        # collect patterns from derived classes
        def collect_patterns(cls):
            if hasattr(cls, 'patterns'):
                _patterns.extend(cls.patterns)
            for subcls in cls.__bases__:
                collect_patterns(subcls)
        collect_patterns(self.__class__)

        # collect patterns from instance
        if hasattr(self, 'patterns') and isinstance(self.patterns, list):
            _patterns.extend(self.patterns)

        return _patterns


    def get_urls(self, prefix=None):
        """
        Return a url patterns structure for all view methods that this view
        implements. By convention, url patterns are extracted from the
        class property with the name 'patterns'.
        """
        # collect patterns from this class and all derived classes
        patterns = self.get_patterns()

        # generate url patterns
        urls = []
        if patterns:
            urls = self._get_urlpatterns(patterns, prefix)
        else:
            urls = []

        return urls


    def get_url(self):
        urls = self.get_urls()
        if len(urls) > 0:
            for p in urls:
                if p.name.endswith('.index'):
                    return reverse(p.name)
            return reverse(urls[0].name)
        return ''


    def run_handler(self, request, handler_name, *args, **kwargs):
        """
        Execute given view handler methods. This is mostly intended to be used
        by unit tests testing the functionality of the actual view
        implementation.
        """
        handler = self._create_view_handler(handler_name)

        _process_templates = getattr(self, 'process_templates', True)
        self.process_templates = False
        response = handler(request, *args, **kwargs)
        self.process_templates = _process_templates

        return response


    def _create_view_handler(self, handler_name):
        """
        Return a wrapper for handling the view which in itself calls the method
        with given name on the given view class. For each request, a new
        instance of the view class is created.
        """
        def view(request, *args, **kwargs):
            # create a new instance for each dispatch, so we do not have any
            # shared state. dispatch into method or raise 404
            instance = copy.copy(self)

            # inject view class into request, some decorators may use this
            # in order to obtain access to the view model instance that
            # is handeling the request
            request.view_instance = instance

            # get actual view handler to handler the request
            handler = getattr(instance, handler_name, None)
            if not handler:
                raise Http404(
                    'method %s is not implemented in view class %s' % (
                        handler_name,
                        instance.__class__.__name__
                    )
                )
            return instance._dispatch(handler, request, *args, **kwargs)

        # cascade CSRF excemption annotation on view handler function
        if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE_CLASSES:
            handler = getattr(self, handler_name, None)
            if handler:
                if getattr(handler, 'csrf_exempt', False):
                    view.csrf_exempt = True

        return view


    def _dispatch(self, handler, request, *args, **kwargs):
        """
        Dispatch to given view handler on this view class instance. Any dispatch
        calls before() then the actual view handler method and then after().
        - before() and after() can be overridden by a deriving view class.
        - If before() raises an exception, the actual method handler is not
          called nor is after().
        - If before() returns something, the actual method handler is not
        - called nor is after().
        - If after() returns something, it overrides the response from the
          actual view handler.
        - The response from the actual view handler is passed to after().
        """
        # before handler -> if it returns something, we are done with it...
        response = self.before(request, handler)
        if response: return response

        # dispatch into actual view handler
        response = handler(request, *args, **kwargs)

        # after handler -> may override response from actual view handler...
        after_response = self.after(request, handler, response)
        if after_response:
            return after_response
        else:
            return response


    def before(self, request, handler):
        """
        Default before handler. Override your own implementation in your
        derived class.
        """
        pass


    def after(self, request, handler, response):
        """
        Default after handler. Override your own implementation in your
        derived class.
        """
        pass


class ApiView(View):
    """
    Provides an API-related view for XHR requests. The default output format is
    JSON by default and the content type is text/javascript.
    """
    def after(self, request, handler, response):
        """
        Turn the data as returned from the actual view handler to JSON and
        return an HTTPResponse with content type text/javascript unless we
        already encounter a HttpResponse object returned by the actual view
        handler directly.
        """
        if isinstance(response, HttpResponse):
            # directly return response if it is an HttpResponse already
            return response
        else:
            return to_json_response(response)


class TemplateView(View):
    """
    Provides the ability to return a dict or HttpResponse by any view handler
    and to render a corresponding template file which name correlates with the
    name of the view handler.
    """
    template_path = None
    process_templates = True


    def _get_template_path(self, request, handler, response):
        """
        May be overridden by the derived class to customize the handler to
        template mapping. The base implementation constructs the full template
        path based on the optional base path (template_path) and the name of
        the view handler.
        """
        # allow the template path to be overwritten
        path = response.get('cubane_template_view_path')

        if not path:
            # construct path based on handler name
            path = '%s.html' % handler.__name__
            if self.template_path:
                path = os.path.join(self.template_path, path)

        return path


    def after(self, request, handler, response):
        """
        Turn template context as returned from the actual view handler into
        an HttpResponse by calling into django's render(). The template is
        based on the given template path (constructor), the name of the entity
        and the name of the handler.
        """
        # ignore template processing? (unit testing?)
        if not self.process_templates:
            return response

        if isinstance(response, (HttpResponse, StreamingHttpResponse)):
            # directly return response if it is an HttpResponse already
            return response
        else:
            # assume we have a dict-like response. Extend dict. with
            # self.context if available
            if hasattr(self, 'context'):
                response.update(self.context)

            # determine the path to the template
            path = self._get_template_path(request, handler, response)

            # pass it to the default template renderer for django
            return render(request, path, response)


class ModelView(TemplateView):
    """
    Model view provides full support for listing, creating, updating and
    deleting model entities.
    """
    def __init__(self, model=None, namespace_prefix='', related_listing=False, related_instance=None, related_instance_attr=None, *args, **kwargs):
        """
        Create a default instance for a given model.
        """
        # related listing?
        self.related_listing = related_listing
        self.related_instance = related_instance
        self.related_instance_attr = related_instance_attr

        # construct based on given model?
        if model is not None:
            self.model = model

        # no model?
        if hasattr(self, 'model') and self.model is None:
            return

        # model acl
        if hasattr(self, 'model'):
            self.acl = Acl.of(self.model)
        else:
            self.acl = Acl.default(None)

        # generate slug automatically based on model plural vebose name
        # if no slug has been defined.
        if hasattr(self, 'model') and not hasattr(self, 'slug'):
            self.slug = slugify(self.model._meta.verbose_name_plural)

        # generate namespace automatically based on model plural verbose name
        # if no namespace has been defined
        if hasattr(self, 'model') and not hasattr(self, 'namespace'):
            self.namespace = namespace_prefix + unicode(slugify(self.model._meta.verbose_name_plural))

        if not hasattr(self, 'model'):
            self.model = None

        # override: folder model
        folder_model = get_listing_view_option(self.model, 'folder_model')
        if folder_model == 'self':
            self.folder_model = self.model
        elif folder_model is not None:
            self.folder_model = folder_model

        # override: multiple folders
        multiple_folders = get_listing_view_option(self.model, 'multiple_folders')
        if multiple_folders is not None:
            self.multiple_folders = multiple_folders

        # override: list children
        list_children = get_listing_view_option(self.model, 'list_children')
        if list_children is not None:
            self.list_children = list_children


    @property
    def _model_name(self):
        return self.model.__name__.lower()


    @property
    def is_single_instance(self):
        return hasattr(self, 'single_instance') and self.single_instance


    @property
    def model_is_folder(self):
        """
        Return True, if the listing model and the folder model are the same.
        """
        return self.model == self.get_folder_model()


    @property
    def listing_with_image(self):
        """
        Return True, if the listing will preview an image alongside each item
        in standard listing mode.
        """
        return get_listing_option(self.model, 'listing_with_image', False)


    def validate_models(self):
        """
        Validate attached model that it can be used as part of the backend
        system safety.
        """
        validate_model(self.model)


    def get_url_for_model(self, model, view='index'):
        """
        Return the url for editing the given model and view or None. The view
        argument defines the type of view we are interested in, for example
        index, edit or create.
        """
        if self.model == model:
            return reverse(self._get_url_name(view, namespace=True))
        else:
            return None


    def get_url_for_model_instance(self, instance, view='index'):
        """
        Return the url for editing the given model and view or None. The view
        argument defines the type of view we are interested in, for example
        index, edit or create.
        """
        if self.model == instance.__class__:
            # there might be multiple ModelView instances managing the same
            # model, therefore we might have to consider the backend section
            # identifier as well...
            if self._has_model_backend_sections():
                if self._get_model_backend_section(instance) != self.model_attr_value:
                    return None

            return reverse(self._get_url_name(view, namespace=True))
        return None


    def _get_exclude_columns(self):
        """
        Return a list of columns that this view does not want to be presented
        within the listing nor the filter form.
        """
        if hasattr(self, 'exclude_columns'):
            return self.exclude_columns
        else:
            return []


    def _get_model_columns(
        self,
        model,
        view='list',
        listing_actions=[],
        related_instance_attr=None,
        searchable=False
    ):
        """
        Return a list of all model columns that should be presented when
        listing entities by using the default listing templates. If the
        searchable argument is True, only searchable fields are included.
        """
        # columns in edit mode
        fieldnames = None
        if view == 'edit':
            fieldnames = get_listing_option(model, 'edit_columns')
            exclude_non_editable = False

        # columns in non-edit mode, or no columns specified for edit mode
        if fieldnames is None:
            fieldnames = get_listing_option(model, 'columns')
            exclude_non_editable = False

        # fallback: Extract columns from model automatically
        if fieldnames is None:
            fieldnames = get_model_field_names(model)
            exclude_non_editable = True
            auto_columns = True
        else:
            auto_columns = False

        # process columns
        columns = []
        exclude_columns = self._get_exclude_columns()
        for fieldname in fieldnames:
            # check if field is half column
            half_col = fieldname.startswith('/')
            if half_col:
                fieldname = fieldname[1:]

            # check for explicit right-alignment
            is_right_aligned = fieldname.startswith('-')
            if is_right_aligned:
                fieldname = fieldname[1:]

            # split into fieldname and label
            # format: <column-name>[(<display-column-name)]|<title>|<format> or <action>
            # where format might be
            # - bool for yes/no
            # - url for inline link
            # - html for arbitary html content
            # - currency for currency format of number
            # - percent for percent format
            #
            # action must point to listing action, such as
            #   action:foo
            p = fieldname.split('|', 2)
            is_bool = False
            is_url = False
            is_currency = False
            is_percent = False
            is_action = False
            is_html = False
            action = None
            if len(p) == 3:
                fieldname = p[0]
                title = p[1]
                is_bool = p[2] == 'bool'
                is_url = p[2] == 'url'
                is_currency = p[2] == 'currency'
                is_percent = p[2] == 'percent'
                is_html = p[2] == 'html'

                if p[2].startswith('action:'):
                    action_view = p[2].replace('action:', '')
                    for _action in listing_actions:
                        if _action.get('view') == action_view:
                            action = _action
                            break
            elif len(p) == 2:
                fieldname = p[0]
                title = p[1]
            else:
                title = None

            # fieldname may express a different field or property for
            # display purposes...
            m = re.match(r'^(?P<fieldname>.*?)\((?P<display_fieldname>.*?)\)$', fieldname)
            if m:
                fieldname = m.group('fieldname')
                display_fieldname = m.group('display_fieldname')
            else:
                display_fieldname = fieldname

            # do not present a column that we filter by for an embedded listing
            # view, this would be repeated and the same for every instance
            # anyhow...
            if fieldname == related_instance_attr:
                continue

            # do not include a column that the view does not want
            # to be presented...
            if fieldname in exclude_columns:
                continue

            # get field
            try:
                field = model._meta.get_field(fieldname)
            except FieldDoesNotExist:
                # foreign field?
                field, related, rel_fieldname, rel_model, title = get_model_related_field(model, fieldname, title)

                # generate automatic title
                if not title:
                    title = headline_from_ident(fieldname)

                # foreign field, property or callable
                if related != None or (not searchable and hasattr(model, fieldname)):
                    columns.append({
                        'fieldname': fieldname,
                        'display_fieldname': display_fieldname,
                        'title': title,
                        'sortable': related != None,
                        'bool': is_bool,
                        'html': is_html,
                        'currency': is_currency,
                        'percent': is_percent,
                        'choices': False,
                        'url': fieldname.endswith('_url') or is_url,
                        'action': action,
                        'half_col': half_col,
                        'foreign': False,
                        'related': related,
                        'rel_model': rel_model,
                        'right_aligned': is_right_aligned
                    })
                    continue

            # no field?
            if not field:
                continue

            # do not include fields that are not editable?
            if exclude_non_editable and not field.editable:
                continue

            # determine verbose name
            if isinstance(field, ManyToOneRel):
                verbose_name = field.field.verbose_name
            else:
                verbose_name = field.verbose_name

            # determine field title
            if not title:
                title = ' '.join(x.capitalize() for x in verbose_name.split())

            # many to many?
            many2many = isinstance(field, (ManyToManyField, ManyToOneRel))

            # choices?
            has_choices = hasattr(field, 'choices') and field.choices and len(field.choices) > 0

            # add to result
            columns.append({
                'fieldname': fieldname,
                'display_fieldname': display_fieldname,
                'title': title,
                'sortable': True,
                'bool': isinstance(field, BooleanField) or is_bool,
                'html': is_html,
                'currency': is_currency,
                'percent': is_percent,
                'choices': has_choices,
                'many2many': many2many,
                'choice_display': 'get_%s_display' % fieldname,
                'url': fieldname.endswith('_url') or is_url,
                'action': action,
                'half_col': half_col,
                'related': None,
                'foreign': isinstance(field, ForeignKey),
                'rel_model': None,
                'right_aligned': is_right_aligned
            })

        # we should not have more than a fixed number of (full) columns
        # (including half columns).
        if self._count_full_columns(columns) > MAX_COLUMNS:
            if auto_columns:
                columns = columns[:MAX_COLUMNS]
            else:
                raise ValueError(
                    'This view exceeds the maximum number of allowed (full) ' +
                    ' columns of %d.' % MAX_COLUMNS
                )

        # determine column widths based on full/half columns
        self._inject_column_width(columns)

        return columns


    def _get_related_fields_from_columns(self, columns):
        """
        Return list of related model fields (foreign keys) based on the given
        list of model columns. The result can be used for select_related() on
        the corresponding model queryset in order to fetch related models that
        are used. The default listing view may present an image, which is why
        the 'image' column is always included (if the model defines it)
        """
        result = []
        for column in columns:
            related = column.get('related')
            foreign = column.get('foreign')
            fieldname = column.get('fieldname')

            if related != None and related not in result:
                result.append(related)
            elif foreign and not fieldname in result:
                result.append(fieldname)

        # image field
        if 'image' not in result and hasattr(self, 'model') and self.model is not None:
            try:
                image_field = self.model._meta.get_field('image')
                if isinstance(image_field, ForeignKey) and issubclass(image_field.related_model, Media):
                    result.append('image')
            except FieldDoesNotExist:
                pass

        return result


    def _count_full_columns(self, columns):
        """
        Return the number of full columns, where one half columns count as
        0.5 full columns, therefore this function may yield a multiply of 0.5.
        """
        i = 0.0
        for c in columns:
            if c.get('half_col'):
                i += 0.5
            else:
                i += 1
        return i


    def _inject_column_width(self, columns):
        """
        Determine column width on the basis of full columns and half columns.
        """
        try:
            # force first column to be full width
            columns[0]['half_col'] = False
        except:
            # no columns available.
            return

        k = len(filter(lambda col: col.get('half_col', False), columns))
        n = len(columns) - 1 - k

        denominator = k + 2 * n

        for i, col in enumerate(columns):
            if i == 0:
                col['col_class'] = 't-col-primary'
            else:
                col['col_class'] = 't-col-%s-%s' % (1 if col.get('half_col', False) else 2, denominator)


    def _get_model_column_names(self, model, view='list', searchable=False):
        """
        Return a list of field names for the model that are presented by the
        listing controller.
        """
        fields = self._get_model_columns(model, view, listing_actions=[], searchable=searchable)
        return [f['fieldname'] for f in fields]


    def _get_default_view(self):
        """
        Return the default listing view for the model. If no default view
        is defined via the 'default_view' attribute, the default listing
        view is 'list'.
        """
        return get_listing_option(self.model, 'default_view', 'list')


    def _get_filter_by(self):
        """
        Return a list of columns that the model can be filtered by or the empty
        list.
        """
        return get_listing_option(self.model, 'filter_by', [])


    def _has_model_backend_sections(self):
        """
        Return True, if this view supports multiple model types for multiple
        backend sections.
        """
        try:
            return self.model_attr and self.model_attr_value
        except:
            return False


    def _configure_model_backend_section(self, instance):
        """
        Make sure that the model has the correct backend section assigned to it.
        """
        if self._has_model_backend_sections():
            setattr(instance, self.model_attr, self.model_attr_value)


    def _get_model_backend_section(self, instance):
        """
        Return the backend section of the given model instance.
        """
        if self._has_model_backend_sections():
            return getattr(instance, self.model_attr, None)
        else:
            return None


    def _get_filter_form(self, request, args):
        """
        Return the filter form that is used to filter records for this model
        view. Please note that the form is based on the model form or any
        form that is returned by get_filter_form().
        """
        filter_by = self._get_filter_by()

        # if we do not filter by any fields, we do not need a filter form
        if len(filter_by) == 0:
            return None

        # get form class
        try:
            formclass = self.model.get_filter_form()
        except:
            formclass = self._get_form()

        # instantiate new form instance
        if formclass:
            form = formclass(initial=args)
        else:
            form = None

        if form:
            # construct an empty instance to configure the form with
            instance = self.model()

            # pre-configure instance model type if available
            self._configure_model_backend_section(instance)

            # configure form
            form.is_duplicate = False
            form.is_embedded = False
            form.parent_form = None
            form.parent_instance = None
            form.view = self
            form.configure(request, instance=instance, edit=False)

            # remove fields that we are not filtering by or are excluded
            # by the view...filter out columns that the view may not want...
            exclude_columns = self._get_exclude_columns()
            for fieldname, field in form.fields.items():
                if fieldname not in filter_by or fieldname in exclude_columns:
                    del form.fields[fieldname]

            # foreign field?
            for fieldname in filter_by:
                field, related, rel_fieldname, rel_model, title = get_model_related_field(self.model, fieldname)
                if rel_model:
                    # try to get form for related entity
                    try:
                        rel_formclass = rel_model.get_filter_form()
                    except:
                        try:
                            rel_formclass = rel_model.get_form()
                        except:
                            rel_formclass = None

                    # if this fails, try the form we already know about...
                    if not rel_formclass:
                        rel_formclass = formclass

                    if rel_formclass:
                        rel_form = rel_formclass()
                        field = rel_form.fields.get(rel_fieldname)
                        if field:
                            form.fields[fieldname] = field

            # create fields that are not included in the form because they are
            # not editable...Only include those fields if we directly refer
            # to such field via Meta.filter_by
            for fieldname in filter_by:
                if fieldname not in form.fields:
                    if fieldname.startswith(':'):
                        # section field
                        label = fieldname[1:]
                        fname = '__%s' % slugify(label)
                        field = SectionField(label=label)
                        form.fields[fname] = field
                    else:
                        # regular field
                        try:
                            model_field = self.model._meta.get_field(fieldname)
                        except FieldDoesNotExist:
                            continue

                        # only include if the field is non-editable
                        if model_field.editable:
                            continue

                        # determine widgets based on type
                        kwargs = {}
                        if isinstance(model_field, models.DateTimeField):
                            kwargs['widget'] = DateInput()

                        field = model_field.formfield(**kwargs)
                        form.fields[fieldname] = field

            # we do not need to present an empty filter form...
            if len(form.fields) == 0:
                return None

            # make sure that all fields are:
            # - not required and
            # - do not have help text (unless it is a checkbox/radio)
            for fieldname, field in form.fields.items():
                # required
                field.required = False

                # remove initial so that the form does not start filtering.
                if hasattr(field, 'initial'):
                    field.initial = None

                # no help text unless checkbox or radio
                if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                    field.help_text = None

                # multiple-choices fields must have an empty value, unless
                # they are tags
                if hasattr(field, 'choices') and not hasattr(field, 'queryset') and 'select-tags' not in field.widget.attrs.get('class', ''):
                    # choices may already contain a choice for empty value
                    if not any(map(lambda v: v == '', [value for value, _ in field.choices])):
                        field.choices = [('', '-------')] + field.choices
                    field.initial = ''

                # make sure that choice fields with queryset have
                # an empty choice
                if isinstance(field, ModelChoiceField):
                    field.empty_label = '-------'

                # boolean fields are replaced with 3-value choice fields,
                # e.g. OFF, YES and NO.
                if isinstance(field, forms.BooleanField):
                    field = form.fields[fieldname] = forms.ChoiceField(
                        label=field.label,
                        required=False,
                        widget=forms.RadioSelect,
                        initial=unicode(args.get(fieldname)),
                        choices=(
                            ('None', 'Off'),
                            ('True', 'Yes'),
                            ('False', 'No')
                        )
                    )

                # field with class containing editable-html should be removed.
                # We do not want to have editable html fields in filter panel
                if 'editable-html' in field.widget.attrs.get('class', ''):
                    field.widget.attrs['class'] = field.widget.attrs['class'].replace('editable-html', '')

            # respect the order in which filter columns have been declared
            for fieldname in filter_by:
                if fieldname.startswith(':'):
                    fieldname = '__%s' % slugify(fieldname[1:])

                if fieldname in form.fields:
                    field = form.fields.get(fieldname)
                    del form.fields[fieldname]
                    form.fields[fieldname] = field

            # if we only have one field per section, then we do not need a
            # label for it...
            _fields = []
            _sections = []
            _second_seen = False
            for fieldname in filter_by:
                if fieldname.startswith(':'):
                    if _fields:
                        _sections.append(_fields)
                    _fields = []
                    _second_seen = True
                elif _second_seen:
                    _field = form.fields.get(fieldname)
                    if _field:
                        _fields.append(_field)
            if _fields:
                _sections.append(_fields)
            for _fields_per_section in _sections:
                if len(_fields_per_section) == 1:
                    for _field in _fields_per_section:
                        _field.no_label = True

            # prefix names
            fields = {}
            for fieldname, field in form.fields.items():
                form.fields['_filter_%s' % fieldname] = field
                del form.fields[fieldname]

                if fieldname in form.initial:
                    form.initial['_filter_%s' % fieldname] = form.initial.get(fieldname)
                    del form.initial[fieldname]

        return form


    def _get_url_name(self, name, namespace=False):
        """
        Return the full url pattern name based on the url namespace and the
        given name of the operation. if no namespace is used, the name of the
        model is used as a prefix.
        """
        if hasattr(self, 'namespace'):
            if namespace:
                return '%s.%s' % (self.namespace, name)
            else:
                return name
        else:
            return '%s.%s' % (self._model_name, name)


    def _get_url(self, request, name, namespace=True, format=None, args=None, pk=None):
        """
        Return the full url based on the given name. if no namespace is used,
        the name of the model is used as a prefix. If we present in a dialog
        window, all urls will contain the browse argument.
        """
        # get full url name to lookup
        if name.startswith('/'):
            name = name[1:]
        else:
            name = self._get_url_name(name, namespace)

        # split query arguments
        if '?' in name:
            name, query_string = name.split('?', 2)
        else:
            query_string = None

        # resolve url and append browse/create arguments
        url = reverse(name, args=args)

        # append query string
        if query_string:
            args = parse_query_string(query_string)
            url = url_with_args(url, args)

        # are we in dialog mode for browse, create or edit?
        index  = request.GET.get('index-dialog', 'false') == 'true'
        browse = request.GET.get('browse', 'false') == 'true'
        create = request.GET.get('create', 'false') == 'true'
        edit = request.GET.get('edit', 'false') == 'true'
        frontend_editing = request.GET.get('frontend-editing', 'false') == 'true'

        # append dialog mode
        if index or browse or create or edit:
            url = url_with_arg(url, 'dialog', 'true')

        if index:
            url = url_with_arg(url, 'index-dialog', 'true')

        if browse:
            url = url_with_arg(url, 'browse', 'true')

        if create:
            url = url_with_arg(url, 'create', 'true')

        if edit:
            url = url_with_arg(url, 'edit', 'true')

        if frontend_editing:
            url = url_with_arg(url, 'frontend-editing', 'true')

        if format:
            url = url_with_arg(url, 'f', format)

        if pk is not None:
            url = url_with_arg(url, 'pk', pk)

        return url


    def get_urls(self, prefix=None):
        """
        Return a url patterns structure for all CRUD operations that this model
        view supports based on the given model and url namespace.
        """
        # crud urls
        if not self.is_single_instance:
            _patterns = [
                ('',                         'index',                {},             'index'),
                ('selector',                 'selector',             {},             'selector'),
                ('seq/',                     'seq',                  {},             'seq'),
                ('create/',                  'create_edit',          {},             'create'),
                ('delete/(?P<pk>[^/]+)/',    'delete',               {},             'delete'),
                ('delete/',                  'delete',               {},             'delete'),
                ('edit/',                    'create_edit',          {'edit': True}, 'edit'),
                ('edit/(?P<pk>[^/]+)/',      'create_edit',          {'edit': True}, 'edit'),
                ('duplicate/(?P<pk>[^/]+)/', 'duplicate',            {},             'duplicate'),
                ('duplicate/',               'duplicate',            {},             'duplicate'),
                ('disable/(?P<pk>[^/]+)/',   'disable',              {},             'disable'),
                ('disable/',                 'disable',              {},             'disable'),
                ('enable/(?P<pk>[^/]+)/',    'enable',               {},             'enable'),
                ('enable/',                  'enable',               {},             'enable'),
                ('import/',                  'data_import',          {},             'data_import'),
                ('export/',                  'data_export',          {},             'data_export'),
                ('save_changes/',            'save_changes',         {},             'save_changes'),
                ('merge/',                   'merge',                {},             'merge'),
                ('tree-node-state/',         'tree_node_state',      {},             'tree_node_state'),
                ('move-tree-node/',          'move_tree_node',       {},             'move_tree_node'),
                ('move-to-tree-node/',       'move_to_tree_node',    {},             'move_to_tree_node'),
                ('get-tree/',                'get_tree',             {},             'get_tree'),
                ('delete_empty_folders/',    'delete_empty_folders', {},             'delete_empty_folders'),
                ('side-panel-resize/',       'side_panel_resize',    {},             'side_panel_resize'),
            ]
        else:
            _patterns = [
                ('', 'create_edit', {}, 'index'),
            ]

        # summary info
        _patterns += [
            ('summary-info/', 'summary_info', {}, 'summary_info'),
        ]

        # attach addition url patterns as defined with patterns (if present)
        _patterns += self.get_patterns()

        # generate crud url patterns
        urls = self._get_urlpatterns([
            view_url(
                '^' + ('%s/' % prefix if prefix else '') + regex + '$',
                method_name,
                kwargs,
                self._get_url_name(name)
            ) for regex, method_name, kwargs, name in _patterns
        ])

        return urls


    def _get_create_url(self, request, session_prefix=''):
        """
        Return the url that is used for creating a new entity. The create url
        may encode the current folder id if folders are presented by this view,
        so that the currently selected folder is pre-selected when creating a
        new entity.
        """
        url = self._get_url(request, 'create', namespace=True)

        if self.has_folders(request):
            url = url_with_arg(url, '%s_id' % self._get_folder_assignment_name(), self._get_active_folder_id(request, session_prefix))

        if self.related_instance and self.related_instance_attr:
            url = url_with_arg(url, '%s_id' % self.related_instance_attr, self.related_instance.pk)

        return url


    def _get_object(self, request):
        """
        Overridden by derived class in the case that the ModelView is used for
        single instances: Returns one model instance that is controlled by this
        model view.
        """
        raise NotImplementedError(
            ('The derived class of ModelView \'%s\' must implement _get_object() ' + \
             'if single_instance is True.') % self.__class__.__name__
        )


    def _get_objects(self, request):
        """
        Overridden by derived class: Returns a queryset containing all possible
        model entities that can be controlled by this model view. This may
        be all entities, e.g. ModelClass.objects.all() or a subset that is
        restricted perhaps by the current user, for example
        ModelClass.objects.filter(owner=request.user).
        """
        if hasattr(self, 'model') and hasattr(self.model, 'objects'):
            return self.model.objects.all()
        else:
            raise NotImplementedError(
                ('A derived class of ModelView \'%s\' must implement ' + \
                 '_get_objects(). Model is not defined and a default ' + \
                 'implementation cannot be provided.') % self.__class__.__name__
            )


    def _get_objects_or_404(self, request):
        """
        Overridden by derived class: Return a queryset containing all possible
        model entities that can be controlled by this model view whenever a
        particular model instance is requested - for example for the purpose
        of editing or deleting the instance.
        By default, the default get_objects() implementation is called.
        """
        return self._get_objects(request)


    def filter_acl(self, request, objects):
        """
        Return a queryset that confirms to ACL rules of this model view.
        """
        return self.acl.filter(request, objects)


    def _get_objects_base(self, request, related_instance_attr=None, related_instance_pk=None, get_object_or_404=False):
        """
        Return a queryset that yields all available objects (base query).
        """
        # get user's base query
        if get_object_or_404:
            objects = self._get_objects_or_404(request)
        else:
            objects = self._get_objects(request)

        # staff members can only see items that belong to them
        objects = self.filter_acl(request, objects)

        # related listing (filter by instance we are editing)
        if related_instance_attr:
            if related_instance_pk:
                objects = objects.filter(**{related_instance_attr: related_instance_pk})
            else:
                objects = objects.none()

        return objects


    def _get_objects_for_seq(self, request):
        """
        Overridden by derived class: Returns a queryset containing all
        possible model entities that are controlled by this model view for
        the purpose of updating the seq.
        """
        return self._get_objects_base(request)


    def _get_folders(self, request, parent):
        """
        Overridden by derived class: Returns a queryset containing all folders
        for this view.
        """
        folders = self.folder_model.objects.all()

        if parent:
            folders = folders.filter(parent=parent)

        return folders


    def configure(self, request, instance=None, edit=False):
        """
        Configure this view in the context of a form that is being processed
        (embedded related listing).
        """
        if self.related_listing:
            self.related_instance = instance

            # find related instance field name automatically if we are a related
            # listing
            if self.related_instance_attr is None:
                for fieldname in get_model_field_names(self.model):
                    try:
                        field = self.model._meta.get_field(fieldname)
                        if isinstance(field, ForeignKey):
                            if field.rel.to == self.related_instance.__class__:
                                self.related_instance_attr = fieldname
                                break
                    except FieldDoesNotExist:
                        pass


    def get_object_or_404(self, request, pk):
        """
        Return one single objects with the given primary key pk. Please note
        that the given primary key must be in the subset of the queryset that
        is returned by self._get_objects().
        If no such object exists, 404 is raised.
        """
        try:
            return self._get_objects_base(request, get_object_or_404=True).get(pk=pk)
        except (ObjectDoesNotExist, ValueError):
            raise Http404(
                'Unknown primary key %s for %s.' % (pk, self._model_name)
            )


    def _get_objects_by_ids(self, request, ids):
        """
        Return a list of all objects matching the given list of ids.
        """
        return self._get_objects_base(request).filter(pk__in=ids)


    def _get_folder_by_id(self, request, pk, parent=None):
        """
        Return the folder with the given primary keys in the or None.
        """
        if not pk:
            return None

        try:
            return self._get_folders(request, parent).get(pk=pk)
        except self.folder_model.DoesNotExist:
            return None


    def _get_folders_by_ids(self, request, pks, parent=None):
        """
        Return a list of folder instances with the given primary keys in the
        order in which the keys are given or None.
        """
        if not pks:
            return []

        items = self._get_folders(request, parent).in_bulk(pks)
        folders = []
        if pks:
            for pk in pks:
                item = items.get(pk, None)
                if item:
                    folders.append(item)
        return folders


    def _redirect(self, request, name, instance=None, active_tab=None, args=None):
        """
        Create a redirect response to the url with the given name that is part
        of this model view. The name must be 'index', 'create', 'update' or
        'delete'.
        """
        if active_tab:
            if not active_tab.startswith('#'):
                active_tab = '#%s' % active_tab

        url = self._get_url(request, name, namespace=True, args=args)

        if instance:
            url = url_with_arg(url, 'pk', instance.pk)

        return HttpResponseRedirect(
            url +
            (('%s' % active_tab) if active_tab else '')
        )


    def user_has_permission(self, user, view=None, default=True):
        """
        Return True, if the given user has sufficient permissions to perform
        the given action on the current model; otherwise False.
        Please note that permissions are only checked if
        settings.CUBANE_BACKEND_PERMISSIONS is True; otherwise we only enforce
        staff membership.
        """
        # return false if the view itself does not allow it to begin with
        if view:
            if hasattr(self, 'can_%s' % view):
                _can = getattr(self, 'can_%s' % view)
                if callable(_can):
                    _can = _can(user)

                if _can == False:
                    return False

        # check model acl
        if not user.is_superuser:
            if not self.acl.can(view):
                return False

        # check the user/model permission system
        return _user_has_permission(user, self.model, view, default)


    def _get_success_message(self, label, completed_task):
        """
        Return a plain success message confirming that the given task
        was completed on the given instance successfully.
        """
        if self.is_single_instance:
            return '<em>%s</em> %s successfully.' % (
                self.model._meta.verbose_name,
                completed_task
            )
        else:
            return '%s <em>%s</em> %s successfully.' % (
                self.model._meta.verbose_name,
                label,
                completed_task
            )


    def _get_template_path(self, request, handler, response):
        """
        Return the full template path based on the base template path
        (optional) and the name of the handler. If no template path is given,
        the name of the model is used as a template path.
        """
        # allow the template path to be overwritten on a per request basis
        path = response.get('cubane_template_view_path')

        # determine path
        if not path:
            name = '%s.html' % handler.__name__
            if self.template_path:
                path = os.path.join(self.template_path, name)
            else:
                path = os.path.join(self._model_name, name)

        return path


    def _get_form(self):
        """
        Return the form that we are supposed to use for managing the model.
        This is usually defined as a class method on the model (get_form) or
        as the form property on the derived ModelView class.
        """
        if hasattr(self, 'form'):
            return self.form
        elif hasattr(self.model, 'get_form'):
            return self.model.get_form()
        else:
            raise ValueError(
                ("We do not know which form to use for processing model " +
                 "'%(name)s'. Please implement the class method 'get_form()' " +
                 "in model class '%(name)s' and return the form class " +
                 "to use for editing.") % {
                    'name': self.model.__name__
                }
            )


    def _get_request_data(self, request):
        """
        Returns request.POST if the request is a post, otherwise request.GET.
        """
        return request.POST if request.method == 'POST' else request.GET


    def _is_json(self, request):
        """
        Return True, if the request is an ajax request or a sepcific argument
        has been provided to force the output to be json.
        """
        d = self._get_request_data(request)
        f = d.get('f', None)
        if request.is_ajax() and not f:
            f = 'json'
        return f == 'json'


    def _is_ajax_html(self, request):
        """
        Return True, if the request is an ajax request that specifically
        defines html as the output format.
        """
        d = self._get_request_data(request)
        f = d.get('f', None)
        return request.is_ajax() and f == 'html'


    def _can_import(self):
        """
        Return True, if the model can be imported.
        """
        return get_listing_option(self.model, 'data_import', False)


    def _can_export(self):
        """
        Return True, if the model can be exported.
        """
        return get_listing_option(self.model, 'data_export', False)


    def _can_disable_enable(self):
        """
        Return True, if the model can be disabled.
        """
        try:
            field = self.model._meta.get_field('disabled')
            return True
        except FieldDoesNotExist:
            return False


    def _can_folder_model_create(self):
        """
        Return True, if new folder model instances can be created from within
        the folder tree view. By default: True, unless folder_model_create is
        set.
        """
        try:
            return self.folder_model_create
        except:
            return True


    def _supports_grid_view(self):
        """
        Return True, if the model supports to be presented in an image-rich,
        grid view that requires the media app. This view may override the model.
        """
        if hasattr(self, 'grid_view'):
            return self.grid_view
        else:
            return get_listing_option(self.model, 'grid_view', False)


    def _supports_edit_view(self):
        """
        Return True, if the model supports bulk editing mode.
        """
        if hasattr(self, 'edit_view'):
            return self.edit_view
        else:
            return get_listing_option(self.model, 'edit_view', False)


    def _is_sortable(self, model):
        """
        Returns True, if the given model is sortable (drag and drop).
        """
        # try view first, which may override model
        try:
            return self.sortable
        except AttributeError:
            pass

        # try method first
        try:
            return model.is_sortable(self.model_attr_value)
        except AttributeError:
            pass

        # otherwise try the default sortable property within the
        # Listing meta class
        return get_listing_option(model, 'sortable', False)


    def _update_with_highest_seq(self, request, instance):
        """
        Update given instance with the highest seq. number that is available
        (starting with 1).
        """
        r = self._get_objects_base(request).aggregate(Max('seq'))
        seq = r.get('seq__max')
        instance.seq = seq + 1
        instance.save()


    def _get_order_by_arg(self, args, sortable):
        """
        Extract the ordering argument from the request and verify that the
        argument is correct. If no argument is given, return the default
        order as defined by the Meta class of the model. If the model is
        sortable, the default ordering is by 'seq'.
        """
        # possible candidates for ordering. Only visible columns can be
        # used for sorting.
        candidates = self._get_model_column_names(self.model, 'list', searchable=True)

        if sortable and 'seq' not in candidates:
            candidates.append('seq')

        # extarct order from request arguments or fall back to defaults
        order_by = args.get('o', None)
        reverse = args.get('ro', False) in [True, 'true', 'True', '1']
        if not order_by:
            # find column which matches the list of candidates we can search by
            found = False
            for _order_by in self.model._meta.ordering:
                order_by = _order_by.strip()
                reverse = order_by.startswith('-')
                order_by = order_by.replace('-', '')
                if order_by in candidates:
                    found = True
                    break

            # if we cannnot find anything, order by first visible column
            if not found:
                if sortable:
                    order_by = 'seq'
                elif candidates:
                    order_by = candidates[0]
                else:
                    order_by = None

        # verify that the order we have is a valid one
        if order_by in candidates:
            return (order_by, reverse)
        else:
            return (None, False)


    def _order_queryset(self, request, objects, order_by, reverse_order):
        """
        Order the given object queryset by given column (optionally reversed)
        and return a new queryset that expresses the applied order of items.
        """
        if order_by:
            attr = self._get_folder_assignment_name()
            prefix = '-' if reverse_order else ''
            order = []

            if self.has_folders(request) and order_by == 'seq':
                # determine if folders have hierarchie
                if hasattr(self.folder_model, 'parent'):
                    max_hierarchie = MAX_HIERARCHY_LEVELS + 1
                else:
                    max_hierarchie = 0

                if self.has_multiple_folders():
                    # determine order name
                    field = self.model._meta.get_field(attr)
                    through_model = field.rel.through
                    object_field_name = field.m2m_field_name()
                    target_field_name = field.m2m_reverse_field_name()
                    object_field = through_model._meta.get_field(object_field_name)
                    related_name = object_field.rel.related_name

                    for i in range(0, max_hierarchie):
                        order.append('%s%s__%s%s__%s' % (
                            prefix,
                            related_name,
                            target_field_name,
                            '__parent' * (max_hierarchie - i),
                            order_by
                        ))
                    order.append('%s%s__%s' % (prefix, related_name, order_by))

                    pks = [x.get('id') for x in objects.order_by(*order).values('id')]
                    if pks:
                        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pks)])
                        objects = objects.order_by(preserved_order)
                else:
                    # single folder
                    for i in range(0, max_hierarchie):
                        order.append('%s%s%s__%s' % (
                            prefix,
                            attr,
                            '__parent' * (max_hierarchie - i),
                            order_by
                        ))
                    order.append('%s%s' % (prefix, order_by))
                    objects = objects.order_by(*order)
            else:
                # arbitary field or no folders
                objects = objects.order_by('%s%s' % (prefix, order_by))

        return objects


    def _search_filter_by_words(self, fieldname, words):
        """
        Return a query expression for filtering objects by the given fieldname
        and query value q.
        """
        q = Q()
        name = '%s__icontains' % fieldname

        for w in words:
            q &= Q(**{name: w})

        return q


    def _search(self, objects, model, q):
        """
        Filter given queryset objects by given search query q, where all
        model properties are searched (only the ones defined by the model).
        """
        if q:
            fieldnames = self._get_model_column_names(model, 'list', searchable=True)

            # we may add additional field names to this list
            # based on Listing.searchable
            for fieldname in get_listing_option(model, 'searchable', []):
                if fieldname not in fieldnames:
                    fieldnames.append(fieldname)

            if len(fieldnames) > 0:
                # split input query into seperate words
                words = get_words(unicode(q), min_word_length=3, max_words=5, allow_digits=True)

                # build search query across all searchable fields
                f = Q()
                filtered = False
                searchable_fields = (CharField, TextField, EmailField)
                for fieldname in fieldnames:
                    related = False
                    try:
                        field = model._meta.get_field(fieldname)
                    except FieldDoesNotExist:
                        # foreign key?
                        field, related, rel_fieldname, rel_model, title = get_model_related_field(model, fieldname)
                        if field and rel_model:
                            try:
                                field = rel_model._meta.get_field(rel_fieldname)
                            except FieldDoesNotExist:
                                continue

                    if field:
                        # searchable field?
                        if isinstance(field, searchable_fields):
                            q = self._search_filter_by_words(fieldname, words)
                            if q:
                                filtered = True
                                f |= q
                if filtered:
                    objects = objects.filter(f)
        return objects


    def _get_filter_args(self, args):
        """
        Return only arguments that are relevant to the filter form, which
        names begin with the prefix 'f_'.
        """
        d = dict()
        for k, v in args.items():
            if k.startswith('f_'):
                d[k[2:]] = v
        return d


    def _filter(self, objects, args, filter_form):
        """
        Perform filter operation on given objects queryset based on given
        GET arguments and filter form. First, filters are added that are
        matching the model. Then the filter method on the model's manager
        is performed (if available) to perform additional custom filtering.
        """
        if filter_form:
            # filter by model fields
            filter_distinct = False
            for fieldname, field in filter_form.fields.items():
                # rewrite fieldname without prefix
                fieldname = fieldname.replace('_filter_', '')

                if fieldname in args:
                    related = False
                    value = args.get(fieldname)

                    try:
                        field = self.model._meta.get_field(fieldname)
                    except FieldDoesNotExist:
                        # related field?
                        field, related, rel_fieldname, rel_model, _ = get_model_related_field(self.model, fieldname)
                        if field and related:
                            field = field.rel.to._meta.get_field(rel_fieldname)

                    if field:
                        # get filter for specific field type
                        if related:
                            filter_distinct = True

                        objects = self._filter_by_field(objects, fieldname, field, value)

            # custom filter (model)
            if hasattr(self.model, 'filter_by'):
                objects = self.model.filter_by(objects, args)

            # custom filter (form)
            if hasattr(filter_form, 'filter_by'):
                objects = filter_form.filter_by(objects, args)

            # we always want distinct records in the result
            # many to many may - based filters may inject duplicates
            if filter_distinct:
                objects = objects.distinct()

        return objects


    def _filter_by_field(self, objects, fieldname, field, value):
        """
        Apply query filter for filtering the given field with the given value.
        """
        if isinstance(field, (TagsField, MultiSelectField)) and isinstance(value, list):
            esc = '#' if isinstance(field, TagsField) else ''
            q = Q()
            for tag in value:
                _tag = esc + tag + esc
                q &= Q(**{'%s__icontains' % fieldname: _tag})
            if len(q) > 0:
                objects = objects.filter(q)
        elif isinstance(field, TEXT_FIELDS):
            filtername = '%s__icontains' % fieldname
            objects = objects.filter(**{filtername: value})
        elif isinstance(field, ForeignKey):
            filtername = '%s__pk' % fieldname
            objects = objects.filter(**{filtername: value})
        elif isinstance(field, DateField):
            value = datetime.datetime.strptime(value, '%d/%m/%Y')
            objects = objects.filter(**{
                '%s__year' % fieldname: value.year,
                '%s__month' % fieldname: value.month,
                '%s__day' % fieldname: value.day
            })
        elif isinstance(field, ManyToManyField):
            if not isinstance(value, list):
                value = [value]

            filtername = '%s__in' % fieldname
            value_arr = []
            for v in value:
                try:
                    value_arr.append(int(v))
                except ValueError:
                    pass
            value = value_arr
            if len(value) > 0:
                objects = objects.filter(**{filtername: value})
        else:
            objects = objects.filter(**{fieldname: value})

        return objects


    def _get_listing_actions(self, request):
        """
        Return a list of additional actions that can be performed on single or
        multiple entities from the listing control. Additional buttons are
        presented to perform those actions.
        """
        try:
            listing_actions = self.listing_actions
        except:
            listing_actions = []

        actions = []
        for action in listing_actions:
            # title, dialog?
            dialog = False
            small_dialog = False
            title = action[0].strip()
            if title.startswith('[') and title.endswith(']'):
                title = title[1:-1]
                dialog = True
                if title.startswith('/'):
                    small_dialog = True
                    title = title[1:]

            # view, external?
            view = action[1]
            if view.startswith('/'):
                external = True
            else:
                external = False

            # url name
            url_name = view
            if '?' in view:
                view, _ = view.split('?', 2)

            actions.append({
                'title': title,
                'view': view,
                'url': self._get_url(request, url_name, namespace=True),
                'typ': action[2],
                'method': action[3] if len(action) >= 4 else 'location',
                'confirm': action[4] if len(action) >= 5 else False,
                'dialog': dialog,
                'small_dialog': small_dialog,
                'external': external
            })

        return actions


    def _inject_listing_actions(self, objects, listing_actions):
        """
        Set listing action for each object. Some objects may not have an
        action depending on its internal state.
        """
        for obj in objects:
            obj.listing_actions = []
            for action in listing_actions:
                if self._object_can_execute_listing_action(obj, action):
                    obj.listing_actions.append(action)
        return objects


    def _object_can_execute_listing_action(self, obj, action):
        """
        Return True, if the given object instance can execute the given action.
        Otherwise return True.
        """
        try:
            return obj.can_execute_action(action)
        except:
            return True


    def _get_shortcut_actions(self, listing_actions):
        """
        Return a list of listing actions that are available for individual
        records based on the list of listing actions. Each shortcut action
        is presented for each item within the listing.
        """
        try:
            shortcut_actions = self.shortcut_actions
        except:
            shortcut_actions = []

        actions = []
        for action in listing_actions:
            if action.get('view') in shortcut_actions and action.get('typ') in ['single', 'multiple', 'any']:
                actions.append(action)

        return actions


    def _get_selector_model(self):
        """
        Return the model of the entity that is used as a selector for cross
        filtering against the main listing.
        """
        if hasattr(self, 'selector_model'):
            return self.selector_model
        else:
            return None


    def _get_active_selector_session_name(self, session_prefix):
        """
        Return the name of the session variable that is used for storing
        the pk of the currently selected selector item. Selector items are
        stored by selector model.
        """
        selector_model = self._get_selector_model()
        return '%sselector_filter_%s' % (
            session_prefix,
            selector_model.__name__
        )


    def _get_active_selector_pk(self, request, session_prefix=''):
        """
        Return the pk of the currently selected selector item or None.
        """
        session_name = self._get_active_selector_session_name(session_prefix)
        pk = request.session.get(session_name, None)

        if pk:
            # make sure that the selector is an int if the primary key of
            # the selector model is an int.
            field = self.selector_model._meta.pk
            if isinstance(field, IntegerField) or isinstance(field, AutoField):
                try:
                    pk = int(pk)
                except ValueError:
                    pk = None

        return pk


    def _set_active_selector_pk(self, request, pk, session_prefix=''):
        """
        Store the given pk of the currently selected selector item in session.
        """
        if pk != None:
            session_name = self._get_active_selector_session_name(session_prefix)
            request.session[session_name] = pk


    def _get_active_folders_session_name(self, session_prefix):
        """
        Return the name of the session variable that is used for storing
        the folder id of the currently selected folder item. Active folders are
        stored by model.
        """
        return '%sfolders_id_%s' % (
            session_prefix,
            self.model.__name__
        )


    def _get_active_folder_ids(self, request, session_prefix=''):
        """
        Return the folder_ids of the currently selected folders or None.
        """
        session_name = self._get_active_folders_session_name(session_prefix)
        folder_ids = request.session.get(session_name, None)

        if folder_ids == None:
            folder_ids = [-1]

        if not isinstance(folder_ids, list):
            folder_ids = [folder_ids]

        ids = []
        for _id in folder_ids:
            try:
                ids.append(int(_id))
            except ValueError:
                pass

        if len(ids) == 0:
            ids = [-1]

        return ids


    def _get_active_folder_id(self, request, session_prefix):
        """
        Return the first folder id of the currently selected list of folders or
        None.
        """
        folder_ids = self._get_active_folder_ids(request, session_prefix)
        if folder_ids:
            return folder_ids[0]
        else:
            return None


    def _set_active_folder_ids(self, request, folder_ids, session_prefix=''):
        """
        Store the given folder ids of the currently selected folder nodes
        in session.
        """
        if folder_ids != None:
            session_name = self._get_active_folders_session_name(session_prefix)
            request.session[session_name] = folder_ids


    def _get_open_folders_session_name(self):
        """
        Return the name of the session variable that is used for storing
        a list of all opoen folder tree nodes.
        """
        return 'folder_ids_%s' % self.model.__name__


    def _get_open_folders(self, request):
        """
        Return a list of ids of open folder tree nodes.
        """
        session_name = self._get_open_folders_session_name()
        folder_ids = request.session.get(session_name, [])
        _ids = []
        if folder_ids:
            for _id in folder_ids:
                try:
                    _ids.append(int(_id))
                except ValueError:
                    pass
        return _ids


    def _set_open_folders(self, request, folder_ids):
        """
        Store the given list of folder tree node ids in the session.
        """
        if folder_ids == None:
            folder_ids = []

        session_name = self._get_open_folders_session_name()
        request.session[session_name] = folder_ids


    def _get_model_selector(self, request, session_prefix=''):
        """
        Return template information on the selector area for the listing view,
        which allows users to cross-filter against the main listing.
        """
        selector_model = self._get_selector_model()
        if selector_model:
            if hasattr(self, '_get_selector_objects'):
                objects = self._get_selector_objects(request)
            else:
                objects = self.selector_model.objects.all()

            # search
            q = request.GET.get('sq', None)
            objects = self._search(objects, selector_model, q)

            return {
                'objects': objects,
                'active_pk': self._get_active_selector_pk(request, session_prefix)
            }

        return None


    def _filter_by_selector(self, request, objects, session_prefix='', update_session=True):
        """
        Filter given main list of objects by selector argument. The selector
        argument is persistent between requests, so that we can select the
        selector filter once and it remains as such.
        """
        if hasattr(self, '_select_by'):
            selector_model = self._get_selector_model()
            filter_name = 'selector_filter_%s' % selector_model.__name__
            pk = request.GET.get('s', None)

            if pk:
                # make sure that the pk of the selector item is an int
                # if the primary key is an integer
                field = self.selector_model._meta.pk
                if isinstance(field, IntegerField) or isinstance(field, AutoField):
                    try:
                        pk = int(pk)
                    except ValueError:
                        pk = None
            else:
                # try to obtain pk from session
                if update_session:
                    pk = self._get_active_selector_pk(request, session_prefix)
                else:
                    pk = None

            # store new pk in session
            if update_session:
                self._set_active_selector_pk(request, pk, session_prefix)

            # filter by selector
            if pk and pk != 0 and pk != '0':
                # apply filter
                objects = self._select_by(objects, pk)

        return objects


    def _filter_by_folders(self, request, objects, session_prefix='', update_session=True):
        """
        Filter given list of objects by given list of parent folders, if
        provided; otherwise return all objects that are not assigned to a
        folder yet.
        """
        folder_ids = None
        folders = None
        pks = None
        if self.has_folders(request):
            folder_ids = request_int_list(request.GET, 'folders[]')
            if not folder_ids:
                # try to obtain folder id from session
                if update_session:
                    folder_ids = self._get_active_folder_ids(request, session_prefix)
                else:
                    folder_ids = None

            # store new pk in session
            if update_session:
                self._set_active_folder_ids(request, folder_ids, session_prefix)

            # filter
            pks = folder_ids
            if pks == -1: pks = None
            if pks and pks[0] == -1: pks = None

            objects = self._folder_filter(request, objects, pks)
            folders = self._get_folders_by_ids(request, pks)

        return (objects, folders, pks)


    def _folder_filter(self, request, objects, folder_pks):
        """
        Virtual: Filter given object queryset by the given folder primary key(s).
        """
        return self._folder_filter_base(request, objects, folder_pks)


    def _folder_filter_base(self, request, objects, folder_pks):
        """
        Filter given object queryset by the given folder primary key(s).
        """
        attr_name = self._get_folder_assignment_name()

        if self.is_listing_children():
            if folder_pks:
                q = Q()
                has_parent_field = self.folder_has_parent_field(request)
                for pk in folder_pks:
                    q |= Q(**{('%s__id' % attr_name): pk})

                    if has_parent_field:
                         q |= Q(**{('%s__parent_id' % attr_name): pk}) | \
                              Q(**{('%s__parent__parent_id' % attr_name): pk}) | \
                              Q(**{('%s__parent__parent__parent_id' % attr_name): pk}) | \
                              Q(**{('%s__parent__parent__parent__parent_id' % attr_name): pk}) | \
                              Q(**{('%s__parent__parent__parent__parent__parent_id' % attr_name): pk})
                objects = objects.filter(q)
        else:
            if folder_pks:
                q = Q()
                for folder_pk in folder_pks:
                    q |= Q(**{attr_name: folder_pk})
                objects = objects.filter(q)
            else:
                objects = objects.filter(**{attr_name: None})

        return objects


    def folder_has_parent_field(self, request):
        """
        Return True, if the folder model has a 'parent' field that can
        (potentially) point to parents.
        """
        if self.has_folders(request):
            attr_name = self._get_folder_assignment_name()
            try:
                self.folder_model._meta.get_field(attr_name)
                return True
            except FieldDoesNotExist:
                pass
        return False


    def _folder_assign(self, request, obj, dst, cur):
        """
        Assign the given destination folder to the given object.
        """
        if self.has_multiple_folders():
            # get through model
            field = self.model._meta.get_field(self._get_folder_assignment_name())
            through_model = field.rel.through
            object_field_name = field.m2m_field_name()
            target_field_name = field.m2m_reverse_field_name()

            # change existing assignment to given folder
            try:
                assignment = through_model.objects.filter(**{
                    object_field_name: obj,
                    ('%s__in' % target_field_name): cur
                })[0]
                if dst is not None:
                    # already exists?
                    try:
                        new_assignment = through_model.objects.filter(**{
                            object_field_name: obj,
                            ('%s__in' % target_field_name): [dst]
                        })[0]

                        # already exists -> delete current once, since we are
                        # moving assignment over...
                        assignment.delete()
                    except IndexError:
                        # does not exist, save to change
                        setattr(assignment, target_field_name, dst)
                        assignment.save()
                else:
                    assignment.delete()
            except IndexError:
                try:
                    # no existing category -> add to the end of all existing items
                    seq = self._folder_filter(request, self._get_objects_base(request), [dst.pk]).count() + 1
                    with transaction.atomic():
                        item = through_model()
                        setattr(item, object_field_name, obj)
                        setattr(item, target_field_name, dst)
                        setattr(item, 'seq', seq)
                        item.save()
                except IntegrityError:
                    # object already in this category, rare case when two people will move the same object to same category at same time
                    pass
        else:
            # assign to new folder, keeping seq from old folder
            setattr(obj, self._get_folder_assignment_name(), dst)


    def _get_folder_assignment_name(self):
        """
        Return the name of the field that is used to assign a folder to.
        """
        folder_assignment_name = get_listing_view_option(self.model, 'folder_assignment_name')
        if folder_assignment_name is not None:
            return folder_assignment_name
        else:
            try:
                return self.folder_assignment_name
            except:
                return 'parent'


    def _get_folder_title_name(self):
        """
        Return the name that is used to sort folders by.
        """
        folder_title_name = get_listing_view_option(self.model, 'folder_title_name')
        if folder_title_name is not None:
            return folder_title_name
        else:
            try:
                return self.folder_title_name
            except:
                return 'title'


    def _get_index_session_name(self, session_prefix):
        """
        Return the name of the session variable that is used to store
        view-specific state.
        """
        return ('%slisting_%s_%s' % (
            session_prefix,
            slugify(self.model._meta.app_label),
            slugify(unicode(self.model.__name__))
        )).replace('-', '_')


    def _get_index_args(self, request, session_prefix='', update_session=True):
        """
        Return view arguments for the index view related to search, sorting and
        filtering. Arguments are loaded from session, combined with new
        arguments via request.GET and finally saved back to session.
        """
        session_name = self._get_index_session_name(session_prefix)

        if update_session:
            args = request.session.get(session_name, {})
        else:
            args = {}

        # update arguments from GET (overwriting data from session)
        for k, v in request.GET.items():
            if k.endswith('[]'):
                args[k[:-2]] = request.GET.getlist(k)
            else:
                args[k] = v

        # remove empty arguments and rewrite boolean values
        d = dict()
        for k, v in args.items():
            if v in ['true', 'True']:
                v = True
            elif v in ['false', 'False']:
                v = False
            elif v in ['none', 'None']:
                v = None

            if v != '' and v != None:
                d[k] = v
        args = d

        # save new arguments in session for next time
        if update_session:
            request.session[session_name] = args

        return args


    def _set_session_index_args(self, request, session_prefix, attr, value):
        """
        Overwrite a particular attribute value for the index arguments that
        may be stored within the session for the current view.
        """
        session_name = self._get_index_session_name(session_prefix)
        args = request.session.get(session_name, {})
        args[attr] = value
        request.session[session_name] = args
        return args


    def _get_objects_page(self, args, objects_total):
        """
        Return various aspects of pagination data based on the given
        page argument within given set of arguments.
        """
        objects_page = args.get('page', '1')
        if objects_page != 'all':
            try:
                objects_page = int(objects_page)
            except ValueError:
                objects_page = 1

        # determine count of total pages with overflow checks
        objects_pages = objects_total / PAGINATION_MAX_RECORDS
        if objects_total % PAGINATION_MAX_RECORDS > 0:
            objects_pages += 1
        if objects_pages < 1:
            objects_pages = 1

        # overflow current page index
        if objects_page != 'all':
            if objects_page < 1:
                objects_page = 1
            if objects_page > objects_pages:
                objects_page = objects_pages

        # current page index (numeric)
        if objects_page != 'all':
            page_index = (objects_page - 1) * PAGINATION_MAX_RECORDS
        else:
            page_index = 0

        return objects_page, objects_pages, page_index


    def _get_sidepanel_width(self, request, resize_panel_id):
        """
        Return the side panel width.
        """
        session_name = ('listing_%s_side_panel_width' % (
            resize_panel_id
        )).replace('-', '_')

        return request.session.get(session_name, 240)


    def _set_sidepanel_width(self, request, width, resize_panel_id):
        """
        Set the side panel width.
        """
        session_name = ('listing_%s_side_panel_width' % (
            resize_panel_id
        )).replace('-', '_')

        try:
            width = int(width)
        except:
            width = 180

        request.session[session_name] = width
        return width


    def _get_form_initial(self, request):
        """
        Return the form initials based on given request.
        """
        initial = {}

        fieldnames = get_model_field_names(self.model)
        for fieldname in fieldnames:
            v = request.GET.get(fieldname)
            if not v:
                v = request.GET.get('%s_id' % fieldname)
            if v:
                initial[fieldname] = v

        return initial


    def _get_view_identifier(self):
        """
        Return a unique view identifier.
        """
        try:
            return self.view_identifier
        except:
            return ''


    def _create_object_edit_form(self, request, formclass, instance, column_names, queryset_cache):
        """
        Create and return a new instance of an edit form for editing the
        given object.
        """
        # create form as assign instance and initial data
        form = formclass()
        form.instance = instance
        form.initial = model_to_dict(instance, fetch_related=False, fields=column_names)

        # initial data
        self.bulk_form_initial(request, form.initial, instance, edit=True)

        # re-use cached querysets for ModelChoiceFields
        for fieldname, queryset in queryset_cache.items():
            form.fields[fieldname].queryset = queryset

        # configure form for edit
        form.configure(request, instance=instance, edit=True)

        # remove fields that we are not presenting
        for fieldname, _ in form.fields.items():
            if fieldname not in column_names:
                del form.fields[fieldname]

        return form


    def _inject_edit_form(self, request, objects, columns):
        """
        Generate edit forms for each given object.
        """
        # get form class
        try:
            formclass = self.model.get_form()
        except:
            formclass = self._get_form()

        # construct cache of querysets within ModelChoice fields
        form = formclass()
        column_names = [c.get('fieldname') for c in columns]
        queryset_cache = {}
        for fieldname, field in form.fields.items():
            if fieldname in column_names:
                if isinstance(field, ModelChoiceField):
                    queryset_cache[fieldname] = MaterializedQuerySet(queryset=field.queryset)

        # create form for each object
        for instance in objects:
            instance.cubane_view_edit_form = self._create_object_edit_form(
                request,
                formclass,
                instance,
                column_names,
                queryset_cache
            )


    def _is_dialog(self, request):
        """
        Return True, if this request is made from within a dialog window.
        """
        is_browse_dialog = request.GET.get('browse', 'false') == 'true'
        is_index_dialog = request.GET.get('index-dialog', 'false') == 'true'
        is_external_dialog = request.GET.get('external-dialog', 'false') == 'true'
        is_frontend_editing = request.GET.get('frontend-editing', 'false') == 'true'
        is_dialog = request.GET.get('dialog', 'false') == 'true'
        return is_dialog or is_browse_dialog or is_index_dialog or is_external_dialog or is_frontend_editing


    def _get_session_prefix(self, request):
        """
        Return the session prefix based on the current request. Usually, we
        will use a different session prefix within dialog windows.
        """
        return 'dialog-' if self._is_dialog(request) else ''


    def _has_actions(self, context):
        """
        Determine if there are actions available for this view.
        """
        permissions = context.get('permissions')
        has_folders = context.get('has_folders')
        model_is_folder = context.get('model_is_folder')
        duplicate = permissions.get('view') and permissions.get('edit') and permissions.get('create')
        _import = context.get('import') and permissions.get('import')
        _export = context.get('export') and permissions.get('export')
        clean = permissions.get('clean')
        merge = permissions.get('merge')
        changes = permissions.get('changes')

        return duplicate or _import or _export or clean or merge or changes


    def _open_in_new_window(self):
        """
        Return True, if view/edit actions are suppose to open a new window.
        """
        try:
            return self.open_in_new_window
        except:
            return False


    @view(permission_required('view'))
    def index(self, request):
        """
        List all model instances.
        """
        # get content type
        content_type = ContentType.objects.get_for_model(self.model)

        # we use a different session prefix within dialog windows
        session_prefix = self._get_session_prefix(request)

        # get index listing arguments (session and/or GET)
        args = self._get_index_args(request, session_prefix)
        related_listing = request.GET.get('r_listing', '1' if self.related_listing else '0') == '1'
        related_instance_pk = request.GET.get('r_pk', self.related_instance.pk if self.related_instance else None)
        related_instance_attr = request.GET.get('r_attr', self.related_instance_attr)
        if related_instance_pk == 'None': related_instance_pk = None

        # in the context of a dialog window, close the dialog window once
        # we go back to an index page...
        if not related_listing and request.GET.get('index-dialog', 'false') == 'true':
            return {
                'close_index_dialog': True
            }

        # get base list of records
        base_objects = self._get_objects_base(request, related_instance_attr, related_instance_pk)

        # filter by folder
        if not related_instance_pk:
            objects, current_folders, folder_ids = self._filter_by_folders(request, base_objects, session_prefix)
        else:
            objects = base_objects
            current_folders = None
            folder_ids = None
        objects_count = objects.count()

        # if we have an empty result and the folder model is the same as
        # the entity model, then we present the one folder instead rather
        # than an empty result, which makes working with folders much easier.
        if not related_instance_pk and folder_ids and objects_count == 0 and hasattr(self, 'model') and hasattr(self, 'folder_model') and self.model == self.folder_model:
            objects = base_objects.filter(pk__in=folder_ids)
            objects_count = 1

        # filter by selector
        if not related_instance_pk:
            objects = self._filter_by_selector(request, objects, session_prefix)

        # search
        q = args.get('q', None)
        objects = self._search(objects, self.model, q)

        # filter
        filter_args = self._get_filter_args(args)
        filter_form = self._get_filter_form(request, filter_args)
        objects = self._filter(objects, filter_args, filter_form)

        # determine order
        sortable = \
            self._is_sortable(self.model) and \
            self.user_has_permission(request.user, 'edit')
        reverse_order = False
        order_by, reverse_order = self._get_order_by_arg(args, sortable)
        objects = self._order_queryset(request, objects, order_by, reverse_order)

        # pagination and object count
        objects_total = objects.count()
        objects_page, objects_pages, page_index = self._get_objects_page(args, objects_total)

        # list of pages
        if objects_page != 'all':
            objects_pages_list = [x for x in range(objects_page - PAGINATION_PAGES_WINDOW_SIZE, objects_page + PAGINATION_PAGES_WINDOW_SIZE + 1) if x >= 1 and x <= objects_pages]
        else:
            objects_pages_list = [x for x in range(1 - PAGINATION_PAGES_WINDOW_SIZE, 1 + PAGINATION_PAGES_WINDOW_SIZE + 1) if x >= 1 and x <= objects_pages]

        if objects_pages_list[0] != 1:
            objects_pages_list = [1] + objects_pages_list
        if objects_pages_list[-1] != objects_pages:
            objects_pages_list = objects_pages_list + [objects_pages]

        # paged result
        if objects_page != 'all':
            objects = objects[page_index:page_index + PAGINATION_MAX_RECORDS]

        # determine view template (list or grid)
        default_view = self._get_default_view()
        view = args.get('v', default_view)
        if view not in ['list', 'list-compact', 'edit', 'grid']: view = 'list'
        if not self._supports_grid_view() and view == 'grid': view = 'list'
        if (not self._supports_edit_view() or related_instance_attr) and view == 'edit': view = 'list'
        template = 'cubane/backend/listing/listing_%s.html' % view

        # generate response
        if self._is_json(request):
            return to_json_response(
                objects,
                fields=get_model_field_names(self.model, json=True)
            )
        else:
            listing_actions = self._get_listing_actions(request)
            shortcut_actions = self._get_shortcut_actions(listing_actions)
            model_name = self.model._meta.verbose_name.title()
            selector = self._get_model_selector(request, session_prefix)

            # get columns
            columns = self._get_model_columns(self.model, view, listing_actions, related_instance_attr)

            # update select_related, if we have some foreign columns
            related_fields = self._get_related_fields_from_columns(columns)
            if len(related_fields) > 0:
                objects = objects.select_related(*related_fields)

            # materialise objects
            objects = list(objects)
            objects = self._inject_listing_actions(objects, shortcut_actions)

            # create edit forms for each object in edit mode
            if view == 'edit':
                self._inject_edit_form(request, objects, columns)

            # get folders
            folders = self.get_folders(request)
            has_folders = self.has_folders(request) and not related_listing

            context = {
                'related_listing': related_listing,
                'related_instance_pk': related_instance_pk,
                'related_instance_attr': related_instance_attr,
                'controls_visible': not related_instance_attr or (related_instance_attr and related_instance_pk),
                'q': q,
                'order_by': order_by,
                'reverse_order': reverse_order,
                'view': view,
                'grid_view': self._supports_grid_view(),
                'edit_view': self._supports_edit_view() and not related_listing,
                'template': template,
                'model': self.model,
                'model_name': model_name,
                'model_name_plural': self.model._meta.verbose_name_plural.title(),
                'model_is_folder': self.model_is_folder,
                'related_fields': related_fields,
                'view_identifier': self._get_view_identifier(),
                'has_folders': has_folders,
                'create_folder_url': self.get_folder_url(request, 'create'),
                'edit_folder_url': self.get_folder_url(request, 'edit'),
                'folder_model_name_singular': self.get_folder_model_name_singular(),
                'folder_model_name': self.get_folder_model_name(),
                'single_model_with_folders': self.model_is_folder,
                'folder_model_create': self._can_folder_model_create(),
                'folders': folders,
                'current_folders': current_folders,
                'current_folder': current_folders[0] if current_folders else None,
                'is_leaf_folder_view': self.is_leaf_folder_view(request, current_folders, objects_count),
                'folder_ids': folder_ids,
                'folder_id': folder_ids[0] if folder_ids else -1,
                'folder_assignment_name': '%s_id' % self._get_folder_assignment_name(),
                'objects': objects,
                'objects_count': objects_count,
                'objects_total': objects_total,
                'objects_filtered': objects_count - objects_total,
                'objects_pages': objects_pages,
                'objects_page': objects_page,
                'objects_pages_list': objects_pages_list,
                'import': self._can_import(),
                'export': self._can_export(),
                'disable_enable': self._can_disable_enable(),
                'verbose_name': self.model._meta.verbose_name,
                'verbose_name_plural': self.model._meta.verbose_name_plural,
                'filter_form': filter_form,
                'listing_actions': listing_actions,
                'sidepanel_folder_width': self._get_sidepanel_width(request, 'folders'),
                'sidepanel_filter_width': self._get_sidepanel_width(request, 'filter'),
                'permissions': {
                    'create': self.user_has_permission(request.user, 'add'),
                    'view': self.user_has_permission(request.user, 'view'),
                    'edit': self.user_has_permission(request.user, 'edit'),
                    'edit_or_view':
                        self.user_has_permission(request.user, 'edit') or
                        self.user_has_permission(request.user, 'view'),
                    'delete': self.user_has_permission(request.user, 'delete'),
                    'import': self.user_has_permission(request.user, 'import'),
                    'export': self.user_has_permission(request.user, 'export'),
                    'clean': (
                        self.user_has_permission(request.user, 'clean', settings.CUBANE_LISTING_DEFAULT_CLEAN) and
                        self.user_has_permission(request.user, 'delete') and
                        has_folders and
                        not self.model_is_folder
                    ),
                    'merge': self.user_has_permission(request.user, 'merge', settings.CUBANE_LISTING_DEFAULT_MERGE),
                    'changes': not isinstance(self.model, ChangeLog)
                },
                'columns': columns,
                'urls': {
                    'index': self._get_url(request, 'index', namespace=True, format='html'),
                    'create': self._get_create_url(request, session_prefix),
                    'edit': self._get_url(request, 'edit', namespace=True),
                    'duplicate': self._get_url(request, 'duplicate', namespace=True),
                    'delete': self._get_url(request, 'delete', namespace=True),
                    'disable': self._get_url(request, 'disable', namespace=True),
                    'enable': self._get_url(request, 'enable', namespace=True),
                    'import': self._get_url(request, 'data_import', namespace=True),
                    'export': self._get_url(request, 'data_export', namespace=True),
                    'merge': self._get_url(request, 'merge', namespace=True),
                    'selector': self._get_url(request, 'selector', namespace=True, format='html'),
                    'seq': self._get_url(request, 'seq', namespace=True),
                    'tree_node_state': self._get_url(request, 'tree_node_state', namespace=True),
                    'move_tree_node': self._get_url(request, 'move_tree_node', namespace=True),
                    'move_to_tree_node': self._get_url(request, 'move_to_tree_node', namespace=True),
                    'get_tree': self._get_url(request, 'get_tree', namespace=True),
                    'delete_empty_folders': self._get_url(request, 'delete_empty_folders', namespace=True),
                    'save_changes': self._get_url(request, 'save_changes', namespace=True),
                    'changes': reverse('cubane.backend.changelog.index') + ('?f_content_type=%d' % content_type.pk)
                },
                'sortable': sortable,
                'selector': selector,
                'filter_enabled': args.get('ff', False),
                'search': True,
                'listing_with_image': self.listing_with_image,
                'open_in_new_window': self._open_in_new_window()
            }

            # determine if there are actions available
            context['has_actions'] = self._has_actions(context)

            if self._is_ajax_html(request):
                return render(
                    request,
                    template,
                    context
                )
            else:
                return context


    @view(require_GET)
    @view(permission_required('view'))
    @view(template('cubane/backend/listing/selector.html'))
    def selector(self, request):
        """
        List all model instances for the selector listing.
        """
        session_prefix = self._get_session_prefix(request)
        sel_model = self._get_selector_model()
        selector = self._get_model_selector(request, session_prefix)
        if self._is_json(request):
            return to_json_response(
                selector.get('objects', []),
                fields=get_model_field_names(sel_model)
            )
        else:
            return {
                'selector': selector
            }


    @view(require_POST)
    @view(permission_required('edit'))
    def seq(self, request):
        """
        Update element sequence (sortable).
        """
        # cannot update seq if model is not sortable
        if not self._is_sortable(self.model):
            return to_json_response({
                'success': False,
                'message': 'Model is not sortable.'
            })

        # get list of ids in the order in which they should be
        try:
            ids = [int(x) for x in request.POST.getlist('item[]')]
        except ValueError:
            return to_json_response({
                'success': False,
                'message': 'Unable to parse listing id argument as an integer value.'
            })

        # get current sorting order. We do not support reversed order
        # for 'seq' order
        order_by, reverse_order = self._get_order_by_arg(request.POST, sortable=True)
        if order_by == 'seq':
            reverse_order = False

        # get folder
        folder_ids = request_int_list(request.POST, 'folders')

        # base query
        objects = self._get_objects_base(request)
        objects = self._order_queryset(request, objects, order_by, reverse_order)

        # filter by folder
        folder_pks = folder_ids
        if folder_pks == -1: folder_pks = None
        if folder_pks and folder_pks[0] == -1: folder_pks = None
        if folder_pks:
            objects = self._folder_filter(request, objects, folder_pks)

        # pagination and object count
        objects = objects.distinct()
        objects_total = objects.count()
        objects_page, objects_pages, page_index = self._get_objects_page(request.POST, objects_total)

        # if the current order is not by 'seq', then we first apply the
        # general seq. by the current sorting order...
        if order_by != 'seq':
            # get list of all ids in the target seq
            all_ids = list(objects.values_list('id', flat=True))

            # merge existing ids we were given into the result, so that we have
            # a complete list of all identifiers in the required seq. order
            n = min(PAGINATION_MAX_RECORDS, len(ids))
            for j, i in enumerate(range(page_index, page_index + n)):
                all_ids[i] = ids[j]
            ids = all_ids
            start_index = 0
        else:
            # switch view order column back to 'seq'
            session_prefix = self._get_session_prefix(request)
            self._set_session_index_args(request, session_prefix, 'o', 'seq')
            start_index = page_index

        # get all items (seq and last-mod timestamp)
        if self.has_multiple_folders():
            attr = self._get_folder_assignment_name()
            field = self.model._meta.get_field(attr)
            through_model = field.rel.through
            target_field_name = field.m2m_reverse_field_name()
            items = {}
            for obj in objects:
                folders = getattr(obj, attr, None)
                if folders:
                    for assignment in folders.all():
                        folder = getattr(assignment, target_field_name, None)
                        if folder.pk in folder_pks:
                            items[obj.pk] = assignment
        else:
            items = objects.select_related().only('seq', 'updated_on').in_bulk(ids)

        # apply new seq.
        updated_on = datetime.datetime.now()
        updated = False
        for i, _id in enumerate(ids, start=start_index + 1):
            # only update if seq changed...
            item = items.get(_id)
            if item and item.seq != i:
                updated = True
                if self.has_multiple_folders():
                    item.seq = i
                    item.save()
                    self._get_objects_for_seq(request).filter(pk=_id).update(
                        updated_on=updated_on
                    )
                else:
                    self._get_objects_for_seq(request).filter(pk=_id).update(
                        seq=i,
                        updated_on=updated_on
                    )

        # clear cache if we had to update at least one item
        if updated and 'cubane.cms' in settings.INSTALLED_APPS:
            from cubane.cms.views import get_cms
            cms = get_cms()
            cms.invalidate(verbose=False)

        # json response
        return to_json_response({
            'success': True,
            'updated': updated
        })


    def form_initial(self, request, initial, instance, edit):
        """
        Called before a form is created with initial data.
        """
        pass


    def bulk_form_initial(self, request, initial, instance, edit):
        """
        Called before a form is created with initial data in bulk editing mode.
        """
        pass


    def form_configure(self, request, form, edit, instance):
        """
        Called after the form has been configured to perform further form
        configuration if required.
        """
        pass


    def _instance_form_initial(self, request, initial, instance, edit):
        """
        Call instance.form_initial if method is defined.
        """
        if hasattr(instance, 'form_initial'):
            return instance.form_initial(request, initial, instance, edit)
        return False


    def before_save(self, request, cleaned_data, instance, edit):
        """
        Called before the given model instance is saved.
        """
        pass


    def before_save_changes(self, request, cleaned_data, instance, changes, edit):
        """
        Called before the given model instance is saved.
        """
        pass


    def before_bulk_save(self, request, cleaned_data, instance, edit):
        """
        Called before the given model instance is saved as part of bulk editing.
        """
        pass


    def after_save(self, request, cleaned_data, instance, edit):
        """
        Called after the given model instance is saved.
        """
        pass


    def after_save_changes(self, request, cleaned_data, instance, changes, edit):
        """
        Called after the given model instance is saved.
        """
        pass


    def after_bulk_save(self, request, cleaned_data, instance, edit):
        """
        Called after the given model instance is saved as part of bulk editing.
        """
        pass


    def before_delete(self, request, instance):
        """
        Called before the given model instance is deleted.
        """
        pass


    def after_delete(self, request, instance):
        """
        Called after the given model instance has been deleted.
        """
        pass


    def _instance_before_save(self, request, d, instance, edit):
        """
        Call instance.before_save if method is defined.
        """
        if hasattr(instance, 'before_save'):
            return instance.before_save(request, d, instance, edit)
        return False


    def _instance_before_save_changes(self, request, d, instance, changes, edit):
        """
        Call instance.before_save_changes if method is defined.
        """
        if hasattr(instance, 'before_save_changes'):
            return instance.before_save_changes(request, d, instance, changes, edit)
        return False


    def _instance_before_bulk_save(self, request, d, instance, edit):
        """
        Call instance.before_bulk_save if method is defined.
        """
        if hasattr(instance, 'before_bulk_save'):
            return instance.before_bulk_save(request, d, instance, edit)
        return False


    def _instance_after_save(self, request, d, instance, edit):
        """
        Call instance.after_save if method is defined.
        """
        if hasattr(instance, 'after_save'):
            return instance.after_save(request, d, instance, edit)
        return False


    def _instance_after_save_changes(self, request, d, instance, changes, edit):
        """
        Call instance.after_save_changes if method is defined.
        """
        if hasattr(instance, 'after_save_changes'):
            return instance.after_save_changes(request, d, instance, changes, edit)
        return False


    def _instance_after_bulk_save(self, request, d, instance, edit):
        """
        Call instance.after_bulk_save if method is defined.
        """
        if hasattr(instance, 'after_bulk_save'):
            return instance.after_bulk_save(request, d, instance, edit)
        return False


    def _apply_frontend_editing_to_from(self, request, form):
        """
        Configure the given form for frontend editing, if frontend editing
        is configured and requested.
        """
        is_frontend_editing = request.GET.get('frontend-editing', 'false') == 'true'
        property_names = request.GET.get('property-names')
        if settings.CUBANE_FRONTEND_EDITING and is_frontend_editing and property_names:
            property_names = property_names.split(':')
            property_names = [p.strip() for p in property_names]
            property_names = filter(lambda x: x, property_names)

            if not (len(property_names) == 1 and property_names[0] == '*'):
                # remove all fields that are not relevant
                for fieldname in form.fields.keys():
                    if fieldname not in property_names:
                        form.remove_field(fieldname)

                # update layout and sections
                form.layout = FormLayout.FLAT
                form.remove_tabs();
                form.update_sections()


    def _apply_acl_to_form(self, request, form):
        """
        Ensure that ACL rules for model querysets are applied for the given
        form instance.
        """
        for fieldname, field in form.fields.items():
            if hasattr(field, 'queryset'):
                acl = Acl.of(field.queryset.model)
                if acl:
                    field.queryset = acl.filter(request, field.queryset)


    def _get_changes(self, changes):
        """
        Return a dictionary containing all changes made based on the change
        data provided by the change log system.
        """
        d = {}
        for entry in changes:
            name = entry.get('n')
            old = entry.get('a')
            new = entry.get('b')
            d[name] = (old, new)
        return d


    def create_edit(self, request, pk=None, edit=False):
        """
        Create a new instance or edit an existing model instance with given
        primary key pk.
        """
        if edit:
            if request.method == 'POST':
                return self._edit(request, pk)
            else:
                return self._view(request, pk)
        else:
            return self._create(request)


    def summary_info(self, request):
        """
        Return summary information for the given instance.
        """
        pk = request.GET.get('pk')
        instance = self.get_object_or_404(request, pk)
        return {
            'object': instance,
            'urls': {
                'summary_info': self._get_url(request, 'summary_info', namespace=True)
            },
            'object_summary_items': self.get_object_summary_items(instance),
            'cubane_template_view_path': 'cubane/backend/summary_info.html'
        }


    def duplicate(self, request, pk=None):
        """
        Duplicate an existing instance and edit the copy.
        """
        return self._duplicate(request, pk)


    @view(permission_required('add'))
    def _create(self, request):
        return self._create_edit(request)


    @view(permission_required('view'))
    def _view(self, request, pk):
        return self._create_edit(request, pk, True)


    @view(permission_required('edit'))
    def _edit(self, request, pk):
        return self._create_edit(request, pk, True)


    @view(permission_required('add'))
    @view(permission_required('view'))
    def _duplicate(self, request, pk):
        return self._create_edit(request, pk, False, duplicate=True)


    def _create_edit(self, request, pk=None, edit=False, duplicate=False):
        """
        Create a new instance or edit an existing model instance with given
        primary key pk. This is the actual implementation of the view handler.
        """
        # cancel?
        if request.POST.get('cubane_form_cancel', '0') == '1':
            return self._redirect(request, 'index')

        # id argument?
        if (edit or duplicate) and not pk:
            if not 'pk' in request.GET:
                raise Http404("Missing argument 'pk'.")
            pk = request.GET.get('pk')

        # single instance?
        instance = None
        if self.is_single_instance:
            instance = self._get_object(request)
            pk = instance.pk if instance else None
            edit = instance != None

        # get existing or create new object
        if edit or duplicate:
            if not instance:
                instance = self.get_object_or_404(request, pk)

            # ajax GET?
            if request.method == 'GET' and self._is_json(request):
                return to_json_response(
                    instance,
                    fields=get_model_field_names(self.model, json=True)
                )

            fetch_related = get_listing_option(self.model, 'fetch_related', False)
            initial = model_to_dict(instance, fetch_related)
        else:
            instance = self.model()
            initial = self._get_form_initial(request)

        # pre-configure instance model type if available
        self._configure_model_backend_section(instance)

        # if duplicate set parent
        if duplicate and hasattr(instance, 'parent'):
            initial['parent'] = instance.parent

        # if we have a model form, pass in the current instance
        formclass = self._get_form()
        if edit and issubclass(formclass, ModelForm):
            kwargs = {'instance': instance}
        else:
            kwargs = {}

        # create form
        if request.method == 'POST':
            form = formclass(request.POST, request.FILES, **kwargs)
        else:
            self.form_initial(request, initial, instance, edit)
            self._instance_form_initial(request, initial, instance, edit)
            form = formclass(initial=initial, **kwargs)

        # remove pk and dates if duplication
        if duplicate:
            instance.pk = None

            if hasattr(instance, 'created_on'):
                instance.created_on = None
            if hasattr(instance, 'updated_on'):
                instance.updated_on = None

        # configure form
        if not hasattr(form, 'configure'):
            raise NotImplementedError(
                ('The form %s must implement ' +
                 'configure(request, edit, instance) in order to comply with ' +
                 'the model view %s.') % (
                    self._get_form().__name__,
                    self.__class__.__name__
                )
            )

        form.is_duplicate = duplicate
        form.is_embedded = False
        form.parent_form = None
        form.parent_instance = None
        form.view = self
        form.configure(request, edit=edit, instance=instance)
        self.form_configure(request, form, edit, instance)

        # scope form for frontend editing
        self._apply_frontend_editing_to_from(request, form)

        # make sure that ACL rules are enforced on any querysets that are part
        # of the form
        self._apply_acl_to_form(request, form)

        # keep copy of original instance before we are changing it for the
        # purpose of detecting changes made
        previous_instance = request.changelog.get_changes(instance)

        # validate form
        if request.method == 'POST' and form.is_valid():
            # update properties in model instance
            d = form.cleaned_data

            # set creator/updater
            if not request.user.is_anonymous():
                if edit and isinstance(instance, DateTimeBase):
                    instance.updated_by = request.user
                if not edit and isinstance(instance, (
                    DateTimeReadOnlyBase,
                    DateTimeBase
                )):
                    instance.created_by = request.user

            # duplication? -> Remove pk to create a copy and tell model instance
            # we also remove created_on and updated_on
            if duplicate:
                if hasattr(instance, 'on_duplicated'):
                    instance.on_duplicated()

            # save model instance
            before_cms_save.send_robust(
                sender=self.model,
                request=request,
                cleaned_form_data=d,
                model_instance=instance,
                was_edited=edit
            )

            # before save handlers
            changes = self._get_changes(request.changelog.get_changes(instance, previous_instance))
            self.before_save(request, d, instance, edit)
            self.before_save_changes(request, d, instance, changes, edit)
            self._instance_before_save(request, d, instance, edit)
            self._instance_before_save_changes(request, d, instance, changes, edit)

            # make changes
            save_model(d, instance)

            # create only: update seq if model is sortable
            if not edit and self._is_sortable(self.model):
                self._update_with_highest_seq(request, instance)

            # post save handler
            changes = self._get_changes(request.changelog.get_changes(instance, previous_instance))
            custom_response = None

            # after_safe()
            _custom_response = self.after_save(request, d, instance, edit)
            if _custom_response: custom_response = _custom_response

            # after_save_changes()
            _custom_response = self.after_save_changes(request, d, instance, changes, edit)
            if _custom_response: custom_response = _custom_response

            # instance after_safe()
            _custom_response = self._instance_after_save(request, d, instance, edit)
            if _custom_response: custom_response = _custom_response

            # instance after_safe_changes()
            _custom_response = self._instance_after_save_changes(request, d, instance, changes, edit)
            if _custom_response: custom_response = _custom_response

            # send signal
            after_cms_save.send_robust(
                sender=self.model,
                request=request,
                cleaned_form_data=d,
                model_instance=instance,
                was_edited=edit
            )

            # create success message
            message = self._get_success_message(
                unicode(instance),
                'duplicated' if duplicate else 'updated' if edit else 'created'
            )

            # commit changelog
            if edit and not duplicate:
                request.changelog.edit(instance, previous_instance)
            else:
                request.changelog.create(instance)
            change = request.changelog.commit(message, instance)

            # ajax operation, simply return success and message information
            if request.is_ajax():
                return to_json_response({
                    'success': True,
                    'message': message,
                    'change': change,
                    'next': self.get_index_url_or(request, 'edit', instance),
                    'instance_id': instance.pk,
                    'instance_title': unicode(instance)
                })

            # save frontend editing form
            if request.GET.get('frontend-editing', 'false') == 'true':
                return {
                    'frontend_editing_id': instance.pk
                }

            # if this is a create operation within a dialog window
            # which was initiated by clicking the '+' button,
            # we pass on information on the entity that was just created
            # which will then generate javascript code in the template that
            # will close to modal dialog window
            if request.GET.get('create', 'false') == 'true':
                return {
                    'dialog_created_id': instance.pk,
                    'dialog_created_title': unicode(instance)
                }

            # if this is an edit operation within a dialog window
            # which was initiates by clicking an annnotated edit button,
            # we pass on information on the entity that was edited
            # which will then generate javascript code in the template that
            # will close the model dialog window.
            if request.GET.get('edit', 'false') == 'true':
                return {
                    'dialog_edited_id': instance.pk
                }

            # return to listing or stay on edit page or return custom response
            # if available
            if custom_response and isinstance(custom_response, HttpResponse):
                return custom_response
            else:
                return self.redirect_to_index_or(request, 'edit', instance)
        elif request.is_ajax():
            return to_json_response({
                'success': False,
                'errors': form.errors
            })

        # summary items
        object_summary_items = self.get_object_summary_items(instance)

        return {
            'edit': edit,
            'create_edit_page': True,
            'object': instance,
            'form': form,
            'verbose_name': self.model._meta.verbose_name,
            'permissions': {
                'create': self.user_has_permission(request.user, 'add'),
                'view': self.user_has_permission(request.user, 'view'),
                'edit': self.user_has_permission(request.user, 'edit')
            },
            'urls': {
                'summary_info': self._get_url(request, 'summary_info', namespace=True)
            },
            'object_summary_items': object_summary_items
        }


    def get_object_summary_items(self, instance):
        """
        Return summary items for the given instance.
        """
        try:
            object_summary_items = instance.summary_items
        except AttributeError, e:
            if 'summary_items' in unicode(e):
                object_summary_items = {}
            else:
                raise

        return object_summary_items


    def get_index_url_or(self, request, name, instance):
        """
        Return the next url which is usually the index url or the url
        based on the given name in case of continuation.
        """
        active_tab = request.POST.get('cubane_save_and_continue', '0')
        if not active_tab == '0':
            # single view may not have edit
            if name == 'edit' and getattr(self, 'single_instance', False):
                name = 'index'
        else:
            name = 'index'
            instance = None
            active_tag = None

        url = self._get_url(request, name, namespace=True)
        if instance:
            url = url_with_arg(url, 'pk', instance.pk)

        return url


    def redirect_to_index_or(self, request, name, instance):
        """
        Redirect to index after we saved or stay on the current page if
        we clicked on "Save and Continue".
        """
        active_tab = request.POST.get('cubane_save_and_continue', '0')
        if not active_tab == '0':
            # single view may not have edit
            if name == 'edit' and getattr(self, 'single_instance', False):
                name = 'index'

            return self._redirect(request, name, instance, active_tab)
        else:
            return self._redirect(request, 'index')


    @view(require_POST)
    @view(permission_required('delete'))
    def delete(self, request, pk=None):
        """
        Delete existing model instance with given primary key pk or (if no
        primary key is given in the url) attempt to delete multiple entities
        that are given by ids post argument.
        """
        # determine list of pks
        pks = []
        if pk:
            pks = [pk]
        else:
            pks = request.POST.getlist('pks[]', [])
            if len(pks) == 0:
                pk = request.POST.get('pk')
                if pk:
                    pks = [pk]

        # delete actual instance
        folder_model = self.get_folder_model()
        def _delete_instance(instance):
            # deleting a folder should delete all children first
            if self.model == folder_model and isinstance(instance, folder_model):
                for child in self._get_objects_base(request).filter(parent=instance):
                    _delete_instance(child)

            # delete instance itself
            self.before_delete(request, instance)
            request.changelog.delete(instance)
            instance.delete()
            self.after_delete(request, instance)

        # delete instance(s)...
        if len(pks) == 1:
            instance = self.get_object_or_404(request, pks[0])
            label = instance.__unicode__()
            if not label: label = '<no label>'
            _delete_instance(instance)
            message = self._get_success_message(label, 'deleted')
        else:
            instances = self._get_objects_base(request).filter(pk__in=pks)
            for instance in instances:
                _delete_instance(instance)
            message = '%d %s deleted successfully.' % (
                len(instances),
                self.model._meta.verbose_name_plural
            )

        # commit changelog
        change = request.changelog.commit(message, flash=False)

        # response
        if self._is_json(request):
            return to_json_response({
                'success': True,
                'message': message,
                'change': change
            })
        else:
            request.changelog.add_message(messages.SUCCESS, message, change)
            return self._redirect(request, 'index')


    @view(require_POST)
    @view(permission_required('edit'))
    def disable(self, request, pk=None):
        """
        Disable existing model instance with given primary key pk or (if no
        primary key is given in the url) attempt to disable multiple entities
        that are given by ids post argument.
        """
        # determine list of pks
        if pk:
            pks = [pk]
        else:
            pks = request.POST.getlist('pks[]', [])

        # disable instance(s)...
        if len(pks) == 1:
            instance = self.get_object_or_404(request, pks[0])
            label = instance.__unicode__()
            if not label: label = '<no label>'
            instance.disabled = True
            instance.save()
            message = self._get_success_message(label, 'disabled')
        else:
            instances = self._get_objects_base(request).filter(pk__in=pks)
            for instance in instances:
                instance.disabled = True
                instance.save()
            message = '%d %s disabled successfully.' % (
                len(instances),
                self.model._meta.verbose_name_plural
            )

        # response
        if self._is_json(request):
            return to_json_response({
                'success': True,
                'message': message
            })
        else:
            messages.add_message(request, messages.SUCCESS, message)
            return self._redirect(request, 'index')


    @view(require_POST)
    @view(permission_required('edit'))
    def enable(self, request, pk=None):
        """
        Enable existing model instance with given primary key pk or (if no
        primary key is given in the url) attemt to enable multiple entities
        that are given by ids post argument.
        """
        # determine list of pks
        if pk:
            pks = [pk]
        else:
            pks = request.POST.getlist('pks[]', [])

        # disable instance(s)...
        if len(pks) == 1:
            instance = self.get_object_or_404(request, pks[0])
            label = instance.__unicode__()
            if not label: label = '<no label>'
            instance.disabled = False
            instance.save()
            message = self._get_success_message(label, 'enabled')
        else:
            instances = self._get_objects_base(request).filter(pk__in=pks)
            for instance in instances:
                instance.disabled = False
                instance.save()
            message = '%d %s enabled successfully.' % (
                len(instances),
                self.model._meta.verbose_name_plural
            )

        # response
        if self._is_json(request):
            return to_json_response({
                'success': True,
                'message': message
            })
        else:
            messages.add_message(request, messages.SUCCESS, message)
            return self._redirect(request, 'index')


    @view(csrf_exempt)
    @view(template('cubane/backend/listing/upload_with_encoding.html'))
    @view(permission_required('import'))
    def data_import(self, request):
        """
        Provides the ability to import data.
        """
        if request.method == 'POST':
            form = DataImportForm(request.POST, request.FILES)
        else:
            form = DataImportForm()

        form.configure(request)

        if request.method == 'POST' and form.is_valid():
            d = form.cleaned_data
            i = 0

            # import
            importer = Importer(
                self.model,
                self._get_form(),
                self._get_objects_base(request),
                request.user,
                encoding=d.get('encoding', 'utf-8')
            )
            i_success, i_error = importer.import_from_stream(
                request,
                request.FILES['csvfile']
            )

            # present general information what happend during import
            typ = messages.SUCCESS if i_error == 0 else messages.ERROR
            message = '<em>%d</em> records imported, <em>%d</em> errors occurred.' % (
                i_success,
                i_error
            )
            messages.add_message(request, typ, message)
            return self._redirect(request, 'index')

        return {
            'form': form
        }


    @view(csrf_exempt)
    @view(permission_required('export'))
    def data_export(self, request):
        """
        Export data and provide file download.
        """
        # get data
        objects = self._get_objects_base(request)
        pks = request.POST.getlist('pks[]', []);
        objects = self._get_objects_base(request)
        if len(pks) > 0:
            objects = objects.filter(pk__in=pks)

        # export
        exporter = Exporter(self.model, encoding=request.GET.get('encoding', 'utf-8'))
        filename = to_uniform_filename(
            self.model._meta.verbose_name_plural,
            with_timestamp=True,
            ext='.csv'
        )
        return exporter.export_to_response(objects, filename)


    @view(require_POST)
    @view(permission_required('edit'))
    def save_changes(self, request):
        """
        Save all changes made in edit mode at once and return some information
        about form errors if there are any. If there is any error for any record
        then no information is saved at all.
        """
        ids = request.POST.getlist('ids[]');
        listing_actions = self._get_listing_actions(request)
        columns = self._get_model_columns(self.model, 'edit', listing_actions)
        column_names = [c.get('fieldname') for c in columns]
        errors = {}
        records = []
        for pk in ids:
            form_data = request.POST.get('pk-%s' % pk, None)
            if form_data:
                # get instance
                instance = self.model.objects.get(pk=pk)

                # keep original state of instance
                previous_instance = request.changelog.get_changes(instance)

                # determine form class
                formclass = self._get_form()
                if issubclass(formclass, forms.ModelForm):
                    kwargs = {'instance': instance}
                else:
                    kwargs = {}

                # parse initial for given record
                initial = parse_query_string(form_data)

                # enforce arrays for certain form fields
                for k, v in initial.items():
                    if not isinstance(v, list):
                        field = formclass.base_fields.get(k)
                        if field and isinstance(field, (ModelCollectionField, MultiSelectFormField)):
                            initial[k] = [v]

                # create form
                form = formclass(initial, **kwargs)

                # configure form
                if hasattr(form, 'configure'):
                    form.is_duplicate = False
                    form.is_embedded = False
                    form.parent_form = None
                    form.parent_instance = None
                    form.view = self
                    form.configure(request, edit=True, instance=instance)

                # remove fields that were not presented
                for fieldname, field in form.fields.items():
                    if fieldname not in column_names:
                        del form.fields[fieldname]

                # validate form
                if form.is_valid():
                    d = form.cleaned_data
                    records.append( (d, instance, previous_instance) )
                else:
                    errors['pk-%s' % pk] = form.errors

        # save data if we have no errors and support undo
        if not errors:
            n = 0
            for d, instance, previous_instance in records:
                # before save
                self.before_bulk_save(request, d, instance, edit=True)
                self._instance_before_bulk_save(request, d, instance, edit=True)

                # save
                save_model(d, instance)

                # after save
                self.after_bulk_save(request, d, instance, edit=True)
                self._instance_after_bulk_save(request, d, instance, edit=True)

                # generate changelog
                request.changelog.edit(instance, previous_instance)
                n += 1

            # commit changes
            message = pluralize(n, [self.model._meta.verbose_name, self.model._meta.verbose_name_plural], 'saved successfully.', tag='em')
            change = request.changelog.commit(message, model=self.model, flash=False)

            return to_json_response({
                'success': True,
                'message': message,
                'change': change
            })

        return to_json_response({
            'success': not errors,
            'errors': errors
        })


    @view(permission_required('merge'))
    def merge(self, request):
        """
        Merge multiple instances together into one instance.
        """
        def get_m2m_field(obj, field):
            """
            Return the other foreign key field as part of a many to many
            relationship that is not the given field.
            """
            for rel_field in obj._meta.get_fields():
                if rel_field != field and isinstance(rel_field, ForeignKey):
                    return rel_field
            return None

        def get_existing_relation(obj, field, rel_field, target):
            """
            Try to return an existing many to many relationship between
            the existing entity and the new target.
            """
            try:
                rel_value = getattr(obj, rel_field.name)
                if rel_value is not None:
                    return obj.__class__.objects.get(**{
                        rel_field.name: rel_value,
                        field.name: target
                    })
            except obj.__class__.DoesNotExist:
                pass

            return None

        def same_m2m_properties(obj, rel_obj):
            """
            Return True, if both m2m relationships are equal excluding foreign
            keys. Also return True, if there are no more properties other than
            foreign keys.
            """
            for field in obj._meta.get_fields():
                if not isinstance(field, ForeignKey) and not field.primary_key:
                    a = getattr(obj, field.attname)
                    b = getattr(rel_obj, field.attname)
                    if a != b:
                        # convert raw values to display values if the field is
                        # a choice field...
                        if field.choices:
                            getter = 'get_%s_display' % field.name
                            a = getattr(obj, getter)()
                            b = getattr(rel_obj, getter)()

                        # generate info message
                        return False, '<em>%s</em> is not the same, should be <em>%s</em> but was <em>%s</em>' % (
                            field.verbose_name, a, b
                        )
            return True, None

        def can_merge(obj, field, target):
            info = field.get_reverse_path_info()
            if info and info[0].m2m:
                # get the other many to many foreign key
                rel_field = get_m2m_field(obj, field)
                if rel_field:
                    # get existing m2m relationship
                    existing_rel = get_existing_relation(obj, field, rel_field, target)
                    if existing_rel:
                        # test if fields are the same, if not we should not
                        # merge...
                        return same_m2m_properties(obj, existing_rel)
            return True, None

        def link_to_target(obj, target):
            """
            try to re-link first, this may fail for ManyToMany due
            to unique-together constraints...
            """
            attr_found = False
            for field in obj._meta.get_fields():
                if isinstance(field, ForeignKey) and issubclass(field.related_model, self.model):
                    setattr(obj, field.name, target)
                    attr_found = True
            return attr_found

        def get_objects(source, using):
            """
            Return list of related objects from given collector.
            """
            collector = Collector(using)
            collector.collect(sources, keep_parents=True)
            collector.sort()

            result = []
            for model, obj in collector.instances_with_model():
                # ignore the original source
                if model == self.model and obj.pk == source.pk:
                    continue
                result.append( (model, obj) )
            return result

        # abort?
        if request.POST.get('cubane_form_cancel', '0') == '1':
            return self._redirect(request, 'index')

        # get objects to merge
        pks = request_int_list(request.GET, 'pks[]')
        objects = self.model.objects.in_bulk(pks)
        sources = []
        for pk in pks:
            obj = objects.get(pk)
            if obj is not None:
                sources.append(obj)

        # need at least two objects to work with, first object is always the
        # target...
        if len(sources) >= 2:
            target = sources[0]
            sources = sources[1:]
        else:
            target = None
            sources = []

        # we have to have a target
        if target is None:
            messages.add_message(request, messages.ERROR, 'Unable to merge less than two objects.')
            return self._redirect(request, 'index')

        # ask the target model instance if it can merge with the given list
        # of sources
        if hasattr(target, 'can_merge_with'):
            _can_merge = target.can_merge_with(sources)
            if isinstance(_can_merge, tuple):
                _can_merge, _message = _can_merge
            else:
                _message = 'Unable to merge.'
            if not _can_merge:
                messages.add_message(request, messages.ERROR, _message)
                return self._redirect(request, 'index')

        # find all objects that are referencing one of the sources...
        using = router.db_for_write(self.model, instance=target)
        errors = False
        for source in sources:
            # get related objects pointing to source
            objects = get_objects(source, using)

            # determine any errors that may prevent the user from
            # going ahead...
            if request.method != 'POST':
                for model, obj in objects:
                    for field in obj._meta.get_fields():
                        if isinstance(field, ForeignKey) and issubclass(field.related_model, self.model):
                             _can_merge, info_msg = can_merge(obj, field, target)
                             if not _can_merge:
                                 message = mark_safe(info_msg)
                                 source.merge_error_message = message
                                 errors = True
                                 break

            # execute merge on POST, ignore any errors
            if request.method == 'POST':
                # keep original state of target
                previous_target_instance = request.changelog.get_changes(target)

                for model, obj in objects:
                    # keep original state of instance
                    previous_instance = request.changelog.get_changes(obj)
                    previous_instance_label = unicode(obj)

                    # try to link...
                    if link_to_target(obj, target):
                        try:
                            # try to save re-linked relationship
                            with transaction.atomic():
                                obj.save()
                                request.changelog.edit(obj, previous_instance, instance_label=previous_instance_label)
                        except IntegrityError:
                            pass

                # post merge handler
                self.post_merge(request, sources, target)
                request.changelog.edit(target, previous_target_instance)

                # all dependencies have been eliminated for the given source,
                # so we can physically remove the source, which may fail because
                # we may have already removed dependencies...
                for source in sources:
                    request.changelog.delete(source)
                    source.delete()

                # success message
                message = pluralize(len(sources), [self.model._meta.verbose_name, self.model._meta.verbose_name_plural], 'merged into <em>%s</em> successfully.' % target, tag='em')

                # commit changes
                request.changelog.commit(message, target)

                # redirect back to index
                return self._redirect(request, 'index')

        return {
            'cubane_template_view_path': 'cubane/backend/merge.html',
            'verbose_name_plural': self.model._meta.verbose_name_plural,
            'target': target,
            'sources': sources,
            'errors': errors
        }


    def post_merge(self, request, sources, target):
        """
        Virtual: Called as part of a merge operation after the given list of
        source objects have been merged into the given target.
        """
        pass


    def get_folder_model(self):
        """
        Return the model that represents folders used for the folders view
        or None if no folders are supported for the corresponding model.
        """
        try:
            return self.folder_model
        except:
            return None


    def has_folders(self, request):
        """
        Return True, if this view supports folders and the current user has
        read permissions to the folder model.
        """
        if self.related_listing:
            return False

        folder_model = self.get_folder_model()
        if folder_model is None:
            return False

        if not request.user.is_superuser:
            if not Acl.of(folder_model).read:
                return False

        return True


    def has_multiple_folders(self):
        """
        Return True, if this view supports not only folders but also
        allows entities to be assigned to multiple folders at once.
        """
        try:
            return self.multiple_folders
        except:
            return False


    def is_listing_children(self):
        """
        Return True, if this view will list children and grand-children
        of a set of folders or not.
        """
        try:
            return self.list_children
        except:
            return False


    def get_folder_url(self, request, name):
        """
        Return the backend url for creating a new folder.
        """
        model = self.get_folder_model()
        if model:
            return request.backend.get_url_for_model(model, name)
        else:
            return ''


    def get_folder_model_name_singular(self):
        """
        Return the verbose name (singular) of the folder model for this view.
        """
        model = self.get_folder_model()
        if model:
            return model._meta.verbose_name
        else:
            return ''


    def get_folder_model_name(self):
        """
        Return the name of the folder model for this view.
        """
        model = self.get_folder_model()
        if model:
            return model._meta.verbose_name_plural
        else:
            return ''


    def is_leaf_folder_view(self, request, current_folders, objects_count):
        """
        Return True, if the given set of folders represents folders of the same
        level - and therefore the view can support sorting.
        """
        # no folders? -> no mixed hierarchie
        if not self.has_folders(request):
            return True

        # multiple folders? -> mixed hierarchie
        if current_folders and len(current_folders) > 1:
            return False

        # folder pks
        if current_folders:
            folder_pks = [folder.pk for folder in current_folders]
        else:
            folder_pks = None

        # count objects we should have within the current (single) folder,
        # which might be the root folder
        objects = self._get_objects_base(request)
        objects = self._folder_filter_base(request, objects, folder_pks)
        count = objects.count()
        return count == objects_count


    def get_pseudo_root(self, children, open_folder_ids):
        """
        Return the pseudo root folder node.
        """
        model = self.get_folder_model()
        root = model()
        root.id = -1
        root.title = '/'
        root.parent = None
        root.children = children
        root.is_open_folder = root.id in open_folder_ids
        return root


    def get_folders(self, request, parent=None):
        """
        Return all folders for this model view.
        """
        if self.has_folders(request):
            # get base queryset
            folders = self._get_folders(request, parent)

            # determine if folders are sortable
            folder_sortable = get_listing_option(self.folder_model, 'sortable', False)

            # determine folder order seq.
            if folder_sortable:
                # sortable folders
                folders = folders.order_by('seq')
            else:
                # sort by folder title, case-insensetively
                folder_title_name = self._get_folder_title_name()
                folders = folders.order_by(Lower(folder_title_name), folder_title_name)

            # materialise database query
            folders = list(folders)

            # open/close states
            folder_ids = self._get_open_folders(request)
            for folder in folders:
                folder.is_open_folder = folder.id in folder_ids

            # make tree
            folders = TreeBuilder().make_tree(folders)
            folders = [self.get_pseudo_root(folders, folder_ids)]

            return folders
        else:
            return []


    def _get_folder_response(self, request, session_prefix=''):
        """
        Return template or json for all folders.
        """
        folders = self.get_folders(request)

        if self._is_json(request):
            return to_json_response(folders)
        else:
            return {
                'folders': folders,
                'folder_ids': self._get_active_folder_ids(request, session_prefix)
            }


    def _set_tree_node_state(self, request, folder_id, folder_open):
        """
        Set the open state for the given tree node.
        """
        folder_ids = self._get_open_folders(request)

        if folder_open:
            if folder_id not in folder_ids:
                folder_ids.append(folder_id)
        else:
            if folder_id in folder_ids:
                folder_ids.remove(folder_id)

        self._set_open_folders(request, folder_ids)


    def _is_root_node(self, node):
        """
        Return True, if the given node is the root node.
        """
        return node == None or node.id == -1


    def _is_same_node(self, a, b):
        """
        Return True, if a and b are the same nodes.
        """
        a_id = a.id if a else -1
        b_id = b.id if b else -1
        return a_id == b_id


    def _is_child_node_of(self, child, parent):
        """
        Return True, if child is a child (or indirect child) of parent.
        """
        node = child
        while node:
            try:
                node = node.parent
            except AttributeError:
                return False

            if self._is_same_node(node, parent):
                return True
        return False


    def _can_move_node(self, src, dst):
        """
        Return True, if the given src node can be moved to dst while the
        integrity of the tree stays intact.
        """
        return \
            not self._is_root_node(src) and \
            not self._is_same_node(src, dst) and \
            not self._is_child_node_of(dst, src)


    @view(require_POST)
    @view(permission_required('view'))
    def tree_node_state(self, request):
        """
        Store visual state (open|closed) for the given tree node in the session.
        """
        folder_id = request_int(request.POST, 'id')
        folder_open = request_bool(request.POST, 'open')

        self._set_tree_node_state(request, folder_id, folder_open)

        return to_json_response({
            'success': True
        })


    @view(require_POST)
    @view(template('cubane/backend/listing/folders.html'))
    @view(permission_required('edit'))
    def move_tree_node(self, request):
        """
        Move the given source tree node into the given destination tree node
        and return the markup for the entire new tree as a result of the
        operation. The dest. tree node is opened automatically.
        """
        src_ids = request_int_list(request.POST, 'src[]')
        src = self._get_folders_by_ids(request, src_ids)
        dst = self._get_folder_by_id(request, request.POST.get('dst'))

        # determine if we can move each node
        can_move = True
        for node in src:
            if not self._can_move_node(node, dst):
                can_move = False
                break

        # if we can move, move each node into target node
        if can_move:
            for node in src:
                node.parent = dst
                node.save()

        # open target automatically, unless root node
        if dst:
            self._set_tree_node_state(request, dst.id, True)

        session_prefix = self._get_session_prefix(request)
        return self._get_folder_response(request, session_prefix)


    @view(require_POST)
    @view(permission_required('edit'))
    def move_to_tree_node(self, request):
        """
        Move a list of model instances to the given destination tree node
        folder. Since the seq. attribute is not changed initially, the moved
        items will place themselves into the order that already exists, unless
        the folder is empty. In any case, we will re-generate the seq. in order
        to guarantee that the sequence begins with 1 and is consistent without
        duplicates or gaps.
        """
        src = self._get_objects_by_ids(request, request_int_list(request.POST, 'src[]'))
        dst = self._get_folder_by_id(request, request.POST.get('dst'))
        cur = self._get_folders_by_ids(request, request_int_list(request.POST, 'cur[]'))

        # move
        updated = False
        for obj in src:
            if not self.model_is_folder or self._can_move_node(obj, dst):
                updated = True
                self._folder_assign(request, obj, dst, cur)
                obj.save()

        # re-apply seq. for all items within the target folder
        if updated and self._is_sortable(self.model):
            updated_on = datetime.datetime.now()
            objects = self._get_objects_base(request).order_by('seq')
            if dst:
                objects = self._folder_filter(request, objects, [dst.pk])
            for i, item in enumerate(objects, start=1):
                # only update if seq changed...
                if item.seq != i:
                    self._get_objects_base(request).filter(pk=item.pk).update(
                        seq=i,
                        updated_on=updated_on
                    )

        # open target node if we are moving tree nodes
        if dst and self.model_is_folder:
            self._set_tree_node_state(request, dst.id, True)

        # clear cache if we had to update at least one item
        if updated and 'cubane.cms' in settings.INSTALLED_APPS:
            from cubane.cms.views import get_cms
            cms = get_cms()
            cms.invalidate(verbose=False)

        return to_json_response({
            'success': True
        })


    @view(require_GET)
    @view(template('cubane/backend/listing/folders.html'))
    @view(permission_required('view'))
    def get_tree(self, request):
        """
        Return the current tree.
        """
        session_prefix = self._get_session_prefix(request)
        return self._get_folder_response(request, session_prefix)


    def _folder_is_empty(self, request, folder):
        """
        Return true if folder is empty.
        """
        if self._get_folders(request, folder).count() == 0 and self.model.objects.filter(**{self._get_folder_assignment_name(): folder}).count() == 0:
            return True
        return False


    def _get_folder_children(self, request, folder):
        """
        Return folder children otherwise empty.
        """
        if folder:
            return self._get_folders(request, folder)
        else:
            return []


    def _delete_folder_if_empty(self, request, folder):
        """
        Delete the given folder if the folder is empty.
        """
        for child in self._get_folder_children(request, folder):
            self._delete_folder_if_empty(request, child)

        if self._folder_is_empty(request, folder):
            request.changelog.delete(folder)
            folder.delete()
            self._deleted += 1


    @view(require_POST)
    @view(permission_required('delete'))
    def delete_empty_folders(self, request):
        """
        Delete ALL empty folders from tree.
        """
        self._deleted = 0
        if self.has_folders(request) and not self.model_is_folder:
            for folder in self._get_folders(request, None).filter(parent=None):
                self._delete_folder_if_empty(request, folder)

        if self._deleted == 0:
            msg = '%s are already clean.' % self.get_folder_model_name()
            messages.add_message(request, messages.SUCCESS, msg)
        else:
            request.changelog.commit(
                '<em>%s</em> %s deleted.' % (self._deleted, self.get_folder_model_name()),
                model=self.folder_model
            )

        return to_json_response({
            'success': True
        })


    @view(require_POST)
    def side_panel_resize(self, request):
        """
        Change side panel width for this view.
        """
        self._set_sidepanel_width(request, request.POST.get('width'), request.POST.get('resize_panel_id'))

        return to_json_response({
            'success': True
        })


def robots_txt(request):
    """
    Render robots.txt
    """
    try:
        t = get_template('robots.txt')
    except TemplateDoesNotExist:
        t = get_template('cubane/robots.txt')

    return HttpResponse(
        t.render({
            'domainname': make_absolute_url('/sitemap.xml')
        }, request),
        content_type='text'
    )
