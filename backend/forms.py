# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.db import models
from django.forms import widgets, fields, ValidationError, ModelForm
from django.forms.utils import flatatt
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.contrib.auth import authenticate
from cubane.forms import *
from cubane.lib.tree import TreeBuilder, TreeModelChoiceIterator
from cubane.lib.parse import parse_int
from cubane.lib.queryset import MaterializedQuerySet
from cubane.lib.model import get_listing_option, dict_to_model, get_fields
from cubane.lib.widget import build_attrs
from cubane.media.templatetags.media_tags import render_image
from cubane.media.templatetags.media_tags import render_background_image_attr
from cubane.media.models import Media
from cubane.backend.models import ChangeLog
from itertools import chain
import copy


class ChangeLogForm(BaseModelForm):
    """
    ChangeLog Filter Form.
    """
    class Meta:
        model = ChangeLog
        fields = '__all__'
        widgets = {
            'created_on': DateInput()
        }


class BackendLoginForm(BaseLoginForm):
    """
    Login form that is used by the backend system to authentificate users.
    """
    username = forms.CharField(
        label='Username or Email',
        max_length=75,
        widget=forms.TextInput(attrs={'placeholder': 'Username or Email Address'})
    )

    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )


    def authenticate(self, username, password):
        """
        We require at least a staff member for the backend.
        """
        user = super(BackendLoginForm, self).authenticate(username, password)

        if user and not user.is_staff:
            user = None

        return user


class BackendPasswordResetForm(BaseChangePasswordForm):
    """
    Form for enforcing the user to change the password as part of the password
    reset process after login.
    """
    ERROR_PASSWORD_IN_USE = (
        'Please use a different password, since this password is ' +
        'currently in use.'
    )


    def configure(self, request):
        """
        Configure the form with the request object.
        """
        self._request = request


    def clean(self):
        """
        Make sure that the password chosen differs from the current password
        """
        d = super(BackendPasswordResetForm, self).clean()

        password = d.get('password')

        if password:
            # try to authenticate with the password. If this works then require
            # the new password to be different from the current one...
            user = authenticate(username=self._request.user.username, password=password)
            if user is not None:
                self.field_error('password', self.ERROR_PASSWORD_IN_USE)

        return d


class DashboardAddWidgetForm(BaseForm):
    """
    Form for adding a new widget to the dashboard.
    """
    widgets = forms.ChoiceField(
        label='Add',
        required=False,
        choices=[]
    )


    def configure(self, widget_choices):
        self.fields['widgets'].choices = widget_choices


class BrowseSelect(widgets.Select):
    """
    Provides a default select box for selecting backend entities,
    but also provides a "Browse" button to browse for entities.
    """
    def __init__(self, *args, **kwargs):
        # defaults
        self.name = kwargs.pop('name', None)
        self.browse = kwargs.pop('browse', None)
        self.create = kwargs.pop('create', None)

        # initiate by model (if given)
        model = kwargs.pop('model', None)
        prefix = kwargs.pop('prefix', 'cubane.cms')
        if model is not None:
            if prefix: prefix += '.'

            if self.name is None:
                self.name = unicode(model._meta.verbose_name_plural).title()
            if self.browse is None:
                self.browse = reverse_lazy('%s%s.index' % (prefix, slugify(model._meta.verbose_name_plural)))
            if self.create is None:
                self.create = reverse_lazy('%s%s.create' % (prefix, slugify(model._meta.verbose_name_plural)))

        if self.name is None: self.name = ''
        if self.browse is None: self.browse = ''
        if self.create is None: self.create = ''

        super(BrowseSelect, self).__init__(*args, **kwargs)


    def render(self, *args, **kwargs):
        name = self.attrs.pop('name', self.name)
        browse = self.attrs.pop('browse', self.browse)
        create = self.attrs.pop('create', self.create)
        output = super(BrowseSelect, self).render(*args, **kwargs)

        return mark_safe(
            '<div class="cubane-backend-browse clearfix">' + \
                '<div class="cubane-backend-browse-select">' + \
                    output + \
                '</div>' + \
                (('<div class="cubane-backend-browse-button">' + \
                    '<span class="btn" ' + \
                        'data-browse-url="' + unicode(browse) + '" ' + \
                        'data-model-name="' + unicode(name) + '">' + \
                        'Browse...</span></div>') if browse else '') + \
                (('<div class="cubane-backend-browse-add-button">' + \
                    '<span class="btn" ' + \
                        'data-create-url="' + unicode(create) + '" ' + \
                        'data-model-name="' + unicode(name) + '">' + \
                        '+</span></div>') if create else '') + \

            '</div>'
        )


class BrowseSelectThumbnail(widgets.Select):
    """
    Provides a thumbnail image that can be changed by clicking on the image,
    which then opens the media gallery to choose a different image.
    """
    def __init__(self, *args, **kwargs):
        # defaults
        self.data_name = kwargs.pop('data_name', None)
        self.browse = kwargs.pop('browse', None)
        self.create = kwargs.pop('create', None)
        self.edit = kwargs.pop('edit', None)

        # initiate by model (if given)
        model = kwargs.pop('model', None)
        prefix = kwargs.pop('prefix', 'cubane.cms')
        if model is not None:
            if prefix: prefix += '.'

            if self.data_name is None:
                self.data_name = unicode(model._meta.verbose_name_plural).title()
            if self.browse is None:
                self.browse = reverse_lazy('%s%s.index' % (prefix, slugify(model._meta.verbose_name_plural)))
            if self.create is None:
                self.create = reverse_lazy('%s%s.create' % (prefix, slugify(model._meta.verbose_name_plural)))
            if self.edit is None:
                self.create = reverse_lazy('%s%s.edit' % (prefix, slugify(model._meta.verbose_name_plural)))

        if self.data_name is None: self.data_name = ''
        if self.browse is None: self.browse = ''
        if self.create is None: self.create = ''
        if self.edit is None: self.edit = ''

        super(BrowseSelectThumbnail, self).__init__(*args, **kwargs)


    def render(self, name, value, attrs={}, choices=(), renderer=None):
        data_name = self.attrs.get('data_name', self.data_name)
        browse = self.attrs.get('browse', self.browse)
        create = self.attrs.get('create', self.create)
        edit = self.attrs.get('edit', self.edit)

        if value == None:
            value = ''

        # load image
        image = None
        image_pk = None
        image_html = ''
        image_url = ''

        if value:
            try:
                image = Media.objects.get(pk=value)
                image_html = render_image(image)
                image_url = image.url
                image_pk = image.pk
            except Media.DoesNotExist:
                pass

        return mark_safe(
            '<div class="cubane-backend-browse-thumbnail' + (' with-image' if image else '') + '" ' + \
                'data-pk="' + unicode(image_pk) + '" ' + \
                'data-browse-url="' + unicode(browse) + '" ' + \
                'data-create-url="' + unicode(create) + '" ' + \
                'data-edit-url="' + unicode(edit) + '" ' + \
                'data-model-name="' + unicode(data_name) + '">' + \
                '<div role="button" class="cubane-backend-browse-thumbnail-remove" title="Remove Image"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg></div>' + \
                '<a href="' + image_url + '" class="cubane-backend-browse-thumbnail-enlarge cubane-lightbox" title="Enlarge Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-enlarge"/></svg></a>' + \
                '<div role="button" class="cubane-backend-browse-thumbnail-edit" title="Edit Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-edit"/></svg></div>' + \
                '<div role="button" class="cubane-backend-browse-thumbnail-upload" title="Upload New Image"><svg viewBox="0 0 64 64"><use xlink:href="#icon-upload"/></svg></div>' + \
                '<input type="hidden" name="' + name + '" id="' + attrs.get('id', '') + '" value="' + unicode(value) + '"/>' + \
                '<div role="button" class="cubane-backend-browse-thumbnail-image" title="Choose Image">' + \
                    image_html + \
                '</div>' + \
            '</div>'
        )


class BrowseField(forms.ModelChoiceField):
    """
    Replaces ModelChoiceField by using the BrowseSelect widget by default
    in order to present a "Browse" button alongside the ordinary select
    field. Optionally a "+" button can be added to automatically create
    (and assign) a new entity.
    """
    widget = BrowseSelect


    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop('name', None)
        self.browse = kwargs.pop('browse', None)
        self.create = kwargs.pop('create', None)
        self.slug = kwargs.pop('slug', None)

        # initiate by model (if given)
        model = kwargs.pop('model', None)
        prefix = kwargs.pop('prefix', '')
        if model is not None:
            if prefix: prefix += '.'

            if 'queryset' not in kwargs:
                kwargs['queryset'] = model.objects.all()
            if self.name is None:
                self.name = unicode(model._meta.verbose_name_plural).title()
            if self.slug is None:
                self.slug = slugify(model._meta.verbose_name_plural)
            if self.browse is None:
                self.browse = reverse_lazy('%s%s.index' % (prefix, self.slug))
            if self.create is None:
                self.create = reverse_lazy('%s%s.create' % (prefix, self.slug))

        super(BrowseField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        attrs = super(BrowseField, self).widget_attrs(widget)
        if isinstance(widget, BrowseSelect):
            if self.name is not None:
                attrs['name'] = self.name
            if self.browse is not None:
                attrs['browse'] = self.browse
            if self.create is not None:
                attrs['create'] = self.create
        return attrs


class BrowseThumbnailField(forms.ModelChoiceField):
    """
    Replaces ModelChoiceField by presenting a thumbnail image
    and allowing the user to change the image by clicking on it, which
    then opens the media gallery (dialog window).
    """
    widget = BrowseSelectThumbnail


    def __init__(self, *args, **kwargs):
        self.data_name = kwargs.pop('data_name', None)
        self.browse = kwargs.pop('browse', '')
        self.create = kwargs.pop('create', '')
        self.edit = kwargs.pop('edit', '')
        super(BrowseThumbnailField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        attrs = super(BrowseThumbnailField, self).widget_attrs(widget)
        if isinstance(widget, BrowseSelectThumbnail):
            if self.data_name is not None:
                attrs['data_name'] = self.data_name
            if self.browse is not None:
                attrs['browse'] = self.browse
            if self.create is not None:
                attrs['create'] = self.create
            if self.edit is not None:
                attrs['edit'] = self.edit
        return attrs


class BrowseChoiceField(forms.ChoiceField):
    """
    Replaces ChoiceField by using the BrowseSelect widget by default
    in order to present a "Browse" button alongside the ordinary select
    field. Optionally a "+" button can be added to automatically create
    (and assign) a new entity.
    """
    widget = BrowseSelect


    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop('name', None)
        self.browse = kwargs.pop('browse', '')
        self.create = kwargs.pop('create', '')
        super(BrowseChoiceField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        attrs = super(BrowseChoiceField, self).widget_attrs(widget)
        if isinstance(widget, BrowseSelect):
            if self.name is not None:
                attrs['name'] = self.name
            if self.browse is not None:
                attrs['browse'] = self.browse
            if self.create is not None:
                attrs['create'] = self.create
        return attrs


class BrowseTreeField(BrowseField):
    """
    browse select field for browsing tree content.
    """
    def __init__(self, *args, **kwargs):
        self._model = kwargs.pop('model')
        if 'queryset' not in kwargs:
            kwargs['queryset'] = self._model.objects.all()

            # if model is sortable, sort by seq
            try:
                if self._model and get_listing_option(self._model, 'sortable'):
                    kwargs['queryset'] = kwargs['queryset'].order_by('seq')
            except:
                pass

        kwargs['name'] = self._model._meta.verbose_name_plural
        super(BrowseTreeField, self).__init__(*args, **kwargs)


    def label_from_instance(self, obj):
        return mark_safe(('&nbsp;' * 2 * obj.level) + obj.title)


    def _get_choices(self):
        # make sure that the queryset is not cached
        if not isinstance(self._queryset, MaterializedQuerySet):
            self._queryset = copy.deepcopy(self._queryset)

        return TreeModelChoiceIterator(self, self._queryset)


    choices = property(_get_choices, forms.ChoiceField._set_choices)


class ModelSelectMultiple(widgets.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=(), renderer=None):
        queryset         = self.attrs.get('queryset', None)
        url              = self.attrs.get('url', '')
        alt_url          = self.attrs.get('alt_url', '')
        add_label        = self.attrs.get('add_label', 'Add')
        alt_label        = self.attrs.get('alt_label', 'Add')
        title            = self.attrs.get('title', 'Collection')
        model_title      = self.attrs.get('model_title', '')
        alt_model_title  = self.attrs.get('alt_model_title', '')
        sortable         = self.attrs.get('sortable', True)
        viewmode         = self.attrs.get('viewmode', ModelCollectionField.VIEWMODE_GRID)
        allow_duplicates = self.attrs.get('allow_duplicates', True)
        max_items        = self.attrs.get('max_items', None)
        no_label         = self.attrs.get('no_label', False)

        if value is None: value = []
        value = filter(lambda v: v is not None, [parse_int(v, None) for v in value])

        final_attrs = build_attrs(self.attrs, attrs, name=name)
        str_values = set([force_text(v) for v in value])

        output = [
            '<div class="cubane-collection-items" data-name="%s" data-url="%s" data-alt-url="%s" data-title="%s" data-model-title="%s" data-alt-model-title="%s" data-sortable="%s" data-allow-duplicates="%s" data-max-items="%s">' % (name, url, alt_url, title, model_title, alt_model_title, sortable, allow_duplicates, max_items),
                '<div class="cubane-collection-items-header">',
                    '<a class="add-collection-items btn btn-primary" href="#add-collection-items"><i class="icon icon-plus"></i> ' + add_label + '...</a>',
                    ('<a class="add-collection-items alternative-collection-items btn btn-primary" href="#add-collection-items"><i class="icon icon-plus"></i> ' + alt_label + '...</a>') if alt_url else '',
                '</div>',
                '<div class="cubane-collection-items-container%s%s">' % (
                    (' cubane-listing-grid-items' if viewmode == ModelCollectionField.VIEWMODE_GRID else ' cubane-listing-list'),
                    (' ui-sortable' if sortable else '')
                )
        ]

        media = []
        if queryset:
            media = list(queryset.filter(pk__in=value))
        for i, v in enumerate(value):
            try:
                obj = filter(lambda m: m.pk == v, media)[0]
            except IndexError:
                continue

            option_value = unicode(obj.pk)
            option_label = unicode(obj)
            if getattr(obj, 'small_url', None):
                image = obj
            elif getattr(obj, 'image', None):
                image = obj.image
            else:
                image = None

            if option_value not in str_values:
                continue

            output.extend(self._render_item(viewmode, name, option_value, option_label, image, sortable))

        output.append('</div></div>')
        return mark_safe('\n'.join(output))


    def _render_item(self, viewmode, name, option_value, option_label, image, sortable):
        result = [
            '<div class="cubane-listing-item collection-item%s" title="%s" data-id="%s">' % (
                ' cubane-listing-grid-item' if viewmode == ModelCollectionField.VIEWMODE_GRID else ' cubane-listing-list',
                option_label,
                option_value
            )
        ]

        if viewmode == ModelCollectionField.VIEWMODE_GRID:
            result.extend(self._render_grid_item(name, option_value, option_label, image, sortable))
        elif viewmode == ModelCollectionField.VIEWMODE_LIST:
            result.extend(self._render_list_item(name, option_value, option_label, sortable))

        result.extend([
                '<input type="hidden" name="%s" value="%s"/>' % (name, option_value),
            '</div>'
        ])
        return result


    def _render_grid_item(self, name, option_value, option_label, image, sortable):
        classes = ['thumbnail-image']
        image_attr = ''

        if image is not None:
            classes.append('lazy-load')
            if image.is_svg:
                classes.append('thumbnail-image-icon')
            elif image.backend_orientation_mismatch:
                classes.append('thumbnail-image-contain')
            image_attr = render_background_image_attr(image)

        return [
            '<div class="thumbnail">',
                '<div class="ui-remove"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg><span class="ui-remove-label">Remove</span></div>',
                '<div class="thumbnail-image-frame">',
                    '<div class="%s" %s></div>' % (' '.join(classes), image_attr),
                '</div>',
                '<div class="thumbnail-filename primary"><span>%s</span></div>' % option_label,
            '</div>',
        ]


    def _render_list_item(self, name, option_value, option_label, sortable):
        return [
            '<div class="cubane-collection-item-container%s">' % (' ui-sortable' if sortable else ''),
                '<div class="cubane-collection-item-title primary ui-edit">', option_label, '</div>',
                '<div class="ui-remove"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg><span class="ui-remove-label">Remove</span></div>',
                '<div class="ui-sortable-handle"></div>',
            '</div>'
        ]


class ModelCollectionField(forms.ModelMultipleChoiceField):
    """
    Replaces ModelMultipleChoiceField by allowing a generic intermediate
    generic model which supports sequencing of items.
    """
    widget = ModelSelectMultiple


    VIEWMODE_LIST = 'list'
    VIEWMODE_GRID = 'grid'


    def __init__(self, *args, **kwargs):
        self.queryset         = kwargs.get('queryset', None)
        self.title            = kwargs.pop('title', None)
        self.url              = kwargs.pop('url', None)
        self.alt_url          = kwargs.pop('alt_url', None)
        self.add_label        = kwargs.pop('add_label', 'Add')
        self.alt_label        = kwargs.pop('alt_label', 'Add')
        self.model_title      = kwargs.pop('model_title', None)
        self.alt_model_title  = kwargs.pop('alt_model_title', None)
        self.sortable         = kwargs.pop('sortable', True)
        self.viewmode         = kwargs.pop('viewmode', self.VIEWMODE_GRID)
        self.allow_duplicates = kwargs.pop('allow_duplicates', True)
        self.max_items        = kwargs.pop('max_items', None)
        self.no_label         = kwargs.pop('no_label', False)
        super(ModelCollectionField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        attrs = super(ModelCollectionField, self).widget_attrs(widget)
        attrs['queryset']         = self.queryset
        attrs['title']            = self.title
        attrs['url']              = self.url
        attrs['alt_url']          = self.alt_url
        attrs['add_label']        = self.add_label
        attrs['alt_label']        = self.alt_label
        attrs['model_title']      = self.model_title
        attrs['alt_model_title']  = self.alt_model_title
        attrs['sortable']         = self.sortable
        attrs['viewmode']         = self.viewmode
        attrs['allow_duplicates'] = self.allow_duplicates
        attrs['max_items']        = self.max_items
        attrs['no_label']         = self.no_label
        return attrs


    def clean(self, value):
        """
        Same as the original implementation, but we guarantee that the
        resulting list of assets is in the correct order.
        """
        if self.required and not value:
            raise ValidationError(self.error_messages['required'], code='required')
        elif not self.required and not value:
            return self.queryset.none()
        if not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages['list'], code='list')
        key = self.to_field_name or 'pk'
        qs = []

        # filter out empty values
        value = filter(lambda x: x, value)

        for pk in value:
            try:
                qs.append(self.queryset.get(**{key: pk}))
            except ValueError:
                raise ValidationError(self.error_messages['invalid_pk_value'] % {'pk': pk})
            except ObjectDoesNotExist:
                pass
        pks = set(force_text(getattr(o, key)) for o in qs)
        for val in value:
            if force_text(val) not in pks:
                raise ValidationError(self.error_messages['invalid_choice'] % {'value': val})

        # Since this overrides the inherited ModelChoiceField.clean
        # we run custom validators here
        self.run_validators(value)
        return qs


class GalleryField(ModelCollectionField):
    """
    Replaces ModelMultipleChoiceField by allowing a gneric intermediate
    generic model which supports sequencing of items.
    """
    def __init__(self, *args, **kwargs):
        self.queryset = kwargs.get('queryset', None)
        super(GalleryField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        attrs = super(GalleryField, self).widget_attrs(widget)
        attrs['queryset']    = self.queryset
        attrs['title']       = 'Gallery'
        attrs['url']         = '/admin/images/'
        attrs['model_title'] = 'Images'
        return attrs


class RelatedListingWidget(widgets.Widget):
    """
    Widget to present a listing of related model instances.
    """
    def render(self, name, value, attrs=None, renderer=None):
        view = self.attrs.get('view')
        context = view.index(self._request)
        context['full_height'] = self.attrs.get('full_height')
        return render_to_string('cubane/backend/listing/listing.html', context)


    def configure(self, request, form, instance=None, edit=False):
        """
        Configure this form field based on the configuration of the form.
        """
        self._request = request
        self._form = form
        self._instance = instance
        self._edit = edit

        view = self.attrs.get('view')
        if hasattr(view, 'configure'):
            view.configure(request, instance, edit)


class RelatedListingField(fields.Field):
    """
    Form field to present a listing of related model instances.
    """
    widget = RelatedListingWidget


    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        self.view = kwargs.pop('view', None)
        self.no_label = kwargs.pop('no_label', True)
        self.full_height = kwargs.pop('full_height', True)
        self.namespace_prefix = kwargs.pop('namespace_prefix', '')
        self._instance = None
        kwargs['required'] = False

        if self.model is None and self.view is None:
            raise ValueError('RelatedListingField must be provided with either a model or view argument.')

        if self.view is None:
            # construct default view based on given model
            from cubane.views import ModelView
            self.view = ModelView(self.model, self.namespace_prefix, related_listing=True)
        else:
            # configure view to be a related view
            self.view.related_listing = True

        super(RelatedListingField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        attrs = super(RelatedListingField, self).widget_attrs(widget)
        attrs['view'] = self.view
        attrs['full_height'] = self.full_height

        if self.no_label:
            attrs['class'] = 'no-label'

        return attrs


    def to_python(self, value):
        return None


    def configure(self, request, form, instance=None, edit=False):
        """
        Configure this form field based on the configuration of the form.
        """
        self._request = request
        self._form = form
        self._instance = instance
        self._edit = edit
        self.widget.configure(request, form, instance, edit)


class RelatedEditWidget(widgets.Widget):
    """
    Widget to present a list of editable related model instances.
    """
    def render(self, name, value, attrs=None, renderer=None):
        # try to obtain value from initials with prefix in case we are
        # a nested form with a prefix...
        if value is None:
            value = self._form.initial.get(name)

        # create list of embedded forms
        if value is not None:
            forms = []
            for i, instance in enumerate(value, start=1):
                # when duplicating content, make sure that we are removing
                # any pks
                if self._form.is_duplicate:
                    instance.pk = None
                    if hasattr(instance, 'created_on'):
                        instance.created_on = None
                    if hasattr(instance, 'updated_on'):
                        instance.updated_on = None

                forms.append(self._field.get_embedded_form(i, instance))
        else:
            forms, _ = self._field.get_embedded_forms()

        # model and verbose name
        model = self._field.model
        if model and hasattr(model, '_meta'):
            verbose_name = model._meta.verbose_name
        else:
            verbose_name = ''

        # form template
        form_template = self._field.get_embedded_form(0)

        # render form instances
        return render_to_string(self._field.template_path + 'form_embedded.html', {
            'forms': forms,
            'prefix_pattern': self._field.get_prefix_pattern(),
            'form_template': form_template,
            'sortable': self.attrs.get('sortable', False),
            'form_summary': self._field.get_summary(forms),
            'field_template': self._field.template_path + '/form_embedded_fields.html',
            'verbose_name': verbose_name
        })


    def configure(self, request, form, field, instance=None, edit=False):
        """
        Configure this form field based on the configuration of the form.
        """
        self._request = request
        self._form = form
        self._field = field
        self._instance = instance
        self._edit = edit
        self._is_valid = True


class RelatedEditField(fields.Field):
    """
    Form field to present and edit related model instances in-place.
    """
    widget = RelatedEditWidget


    def __init__(self, *args, **kwargs):
        kwargs['required'] = False
        self.model = kwargs.pop('model', None)
        self.no_label = kwargs.pop('no_label', False)
        self.sortable = kwargs.pop('sortable', False)
        self.calc = kwargs.pop('calc', None)
        self.template_path = kwargs.pop('template_path', 'cubane/backend/form/')
        self.initial_rows = kwargs.pop('initial_rows', 0)

        if self.model is None:
            raise ValueError('RelatedEditField must be provided with a model.')

        super(RelatedEditField, self).__init__(*args, **kwargs)


    def to_python(self, value):
        """
        Convert post-data to actual values
        """
        # ignore passed value and obtain values from raw form data
        forms, _ = self.get_embedded_forms()
        instances = []
        for form in forms:
            if isinstance(form, ModelForm):
                instance = form.instance
            else:
                instance = self.model()
                dict_to_model(
                    form.cleaned_data,
                    instance,
                    exclude_many_to_many=True
                )

            instances.append(instance)

        if isinstance(self._form, ModelForm):
            self._form.instance._embedded_instances = instances

        return instances


    def clean(self, value):
        forms, is_valid = self.get_embedded_forms()
        if not is_valid:
            raise ValidationError('One or more embedded elements have one or more errors.')

        return super(RelatedEditField, self).clean(value)


    def get_name(self):
        """
        Return the form field's name of this form field.
        """
        if not hasattr(self, '_name_cache'):
            for fieldname, field in self._form.fields.items():
                if field == self:
                    self._name_cache = fieldname
                    break
        return self._name_cache


    def get_prefix(self, seq):
        """
        Return the form prefix for an embedded form with given seq. order.
        """
        return '%s_%s-' % (self.get_prefix_pattern(), seq)


    def get_prefix_pattern(self):
        """
        Return the prefix pattern on which basis the prefix for a form
        is generated by adding a numeric seq. number to it.
        """
        if self._form.prefix:
            return '%s-%s' % (self._form.prefix, slugify(self.get_name()))
        else:
            return 'cubane_ef_%s' % slugify(self.get_name())


    def get_embedded_forms(self):
        """
        Return a list of embedded forms.
        """
        if not hasattr(self, '_embedded_forms'):
            # collect pk-field names
            i = 1
            pk_fields = []
            while True:
                # we should have at least a seq field for each row
                prefix = self.get_prefix(i)
                seq_field = '%s-seq' % prefix
                if seq_field not in self._form.data and i > self.initial_rows:
                    break

                pk_fields.append('%s-pk' % prefix)
                i += 1

            # collect all pks
            pks = []
            for pk_field in pk_fields:
                if pk_field in self._form.data:
                    pks.append(self._form.data[pk_field])

            # load all model references (one query), if this is a model
            if issubclass(self.model, models.Model):
                instances = self.model.objects.in_bulk(pks)
            else:
                instances = {}

            # construct list of forms and validate
            forms = []
            is_valid = True
            for i, pk_field in enumerate(pk_fields, start=1):
                if pk_field in self._form.data:
                    pk = self._form.data[pk_field]
                    try:
                        pk = int(pk)
                    except ValueError:
                        pass

                    instance = instances.get(pk)
                else:
                    instance = self.model()

                # create form
                # validate on post
                form = self.get_embedded_form(i, instance)
                if self._request.method == 'POST':
                    if not form.is_valid():
                        is_valid = False

                forms.append(form)

            # only cache if valid
            self._embedded_forms = forms
            self._is_valid = is_valid

        return self._embedded_forms, self._is_valid


    def get_embedded_form(self, seq, instance=None):
        """
        Return a new embedded form for the given instance in given seq.
        order.
        """
        # edit mode?
        edit = instance is not None

        # get form class from model
        formclass = self.model.get_form()

        # instance argument
        if edit and issubclass(formclass, ModelForm):
            kwargs = {'instance': instance}
        else:
            kwargs = {}

        # generate unique prefix
        prefix = self.get_prefix(seq)

        # create form
        if seq == 0:
            form = formclass(initial={}, prefix=prefix)
        elif self._request.method == 'POST':
            form = formclass(self._form.data, self._form.files, prefix=prefix, **kwargs)
        else:
            if instance:
                # create initials
                initial = copy.copy(self._form.initial)
                for field in get_fields(instance.__class__):
                    if field.name in initial:
                        del initial[field.name]
            else:
                initial = self._form.initial

            form = formclass(initial=initial, prefix=prefix, **kwargs)

        # indicate that the form is used as an embedded form
        form.is_embedded = True
        form.parent_form = self._form
        form.parent_instance = self._instance

        # configure form
        if hasattr(form, 'configure'):
            form.configure(self._request, instance, edit)

        # remove sections
        section_fieldnames = []
        for fieldname, field in form.fields.items():
            if isinstance(field, SectionField):
                section_fieldnames.append(fieldname)
        for fieldname in section_fieldnames:
            del form.fields[fieldname]

        # attach sequence number to form
        form.seq = seq

        return form


    def get_summary(self, forms):
        """
        Return summary information presented on the footer.
        """
        if self.calc:
            return self.calc(self._request, self._instance, [form.instance for form in forms])
        else:
            return {}


    def widget_attrs(self, widget):
        attrs = super(RelatedEditField, self).widget_attrs(widget)
        attrs['model'] = self.model
        attrs['sortable'] = self.sortable
        attrs['class'] = 'no-label' if self.no_label else ''
        return attrs


    def configure(self, request, form, instance=None, edit=False):
        """
        Configure this form field based on the configuration of the form.
        """
        self._request = request
        self._form = form
        self._instance = instance
        self._edit = edit
        self.widget.configure(request, form, self, instance, edit)


class InfoWidget(widgets.Widget):
    """
    Widget for rendering arbitrary html content.
    """
    def render(self, name, value, attrs=None, renderer=None):
        if self._field.render:
            return self._field.render(self._request, self._instance, self._edit)
        elif self._field.html:
            return self._field.html
        else:
            return ''


    def configure(self, request, form, field, instance=None, edit=False):
        """
        Configure this form field based on the configuration of the form.
        """
        self._request = request
        self._form = form
        self._field = field
        self._instance = instance
        self._edit = edit


class InfoField(fields.Field):
    """
    Form field for rendering arbitrary html content.
    """
    widget = InfoWidget


    def __init__(self, *args, **kwargs):
        kwargs['required'] = False
        self.no_label = kwargs.pop('no_label', False)
        self.render = kwargs.pop('render', None)
        self.html = kwargs.pop('html', None)
        super(InfoField, self).__init__(*args, **kwargs)


    def configure(self, request, form, instance=None, edit=False):
        """
        Configure this form field based on the configuration of the form.
        """
        self._request = request
        self._form = form
        self._instance = instance
        self._edit = edit
        self.widget.configure(request, form, self, instance, edit)
