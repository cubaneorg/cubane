# coding=UTF-8
from __future__ import unicode_literals
from urlparse import urlparse
from django.conf import settings
from django import forms
from django.forms import widgets, fields
from django.core.urlresolvers import reverse_lazy
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.contrib import messages
from cubane.forms import BaseForm, BaseModelForm
from cubane.forms import NumberInput, EmailInput, PhoneInput, UrlInput, BootstrapTextInput, TimeInput
from cubane.forms import LocationMapField, LocationMapWidget
from cubane.forms import FormInputLimit
from cubane.backend.forms import BrowseField, ModelCollectionField
from cubane.media.forms import BrowseImagesField
from cubane.media.models import Media
from cubane.cms.models import MediaGallery, PageBase, ChildPage, Entity, OpeningTimesSettingsMixin
from cubane.cms.views import get_cms, get_cms_settings
from cubane.cms import get_page_model
from cubane.lib.app import get_models
from cubane.lib.url import to_legacy_url
from datetime import datetime
import re


def collides_with_child_page_of_homepage(slug):
    """
    Return True, if the given slug matches any child page of the homepage.
    """
    homepage = get_cms().get_homepage()
    if homepage:
        child_page_model = homepage.get_entity_model()
        if child_page_model:
            return child_page_model.objects.filter(slug=slug, page=homepage).count() > 0
    return False


def collides_with_reserved_name(slug):
    """
    Return True, if the given slug collides with any reserved system name.
    """
    reserved_urls = [
        settings.STATIC_URL,
        settings.MEDIA_URL,
        settings.MEDIA_DOWNLOAD_URL,
        settings.MEDIA_API_URL,
        'admin',
        'cache'
    ]
    return slug in [re.sub(r'\/', '', s) for s in reserved_urls]


class EditableHtmlWidget(forms.Textarea):
    """
    Editable HTML widget (TinyMCE).
    """
    def __init__(self, attrs=None, no_label=False, full_height=False, preview=False):
        if attrs is None:
            attrs = {}

        # extract classes
        classes = attrs.get('class', '').split(' ')
        classes = [cl.strip() for cl in classes]
        classes = filter(lambda cl: cl, classes)

        # add widget-specific classes
        def _add_class(cl):
            if cl not in classes:
                classes.append(cl)
        _add_class('editable-html')
        if no_label: _add_class('no-label')
        if full_height: _add_class('full-height')
        if preview: _add_class('preview')

        # write classes back
        attrs['class'] = ' '.join(classes)
        super(EditableHtmlWidget, self).__init__(attrs)


class EditableHtmlField(forms.CharField):
    """
    HTML text (presented as TinyMCE widget).
    """
    widget = EditableHtmlWidget


    def before_initial(self, initial):
        from cubane.cms.templatetags.cms_tags import rewrite_image_references
        return rewrite_image_references(initial)


class BrowseCmsModelField(BrowseField):
    """
    Simplified version of browse select widget specialised in
    browsing cms models.
    """
    def __init__(self, *args, **kwargs):
        model = kwargs.pop('model')
        kwargs['queryset'] = model.objects.all()
        kwargs['name'] = model._meta.verbose_name_plural
        kwargs['browse'] = reverse_lazy('cubane.cms.%s.index' % slugify(model._meta.verbose_name_plural))
        kwargs['create'] = reverse_lazy('cubane.cms.%s.create' % slugify(model._meta.verbose_name_plural))
        super(BrowseCmsModelField, self).__init__(*args, **kwargs)


class BrowseEntityField(BrowseCmsModelField):
    """
    Simplified version of browse select widget specialised in
    browsing cms entities.
    """
    pass


class BrowsePagesField(BrowseField):
    """
    Simplified version of browse select widget specialisied in
    browsing pages.
    """
    def __init__(self, *args, **kwargs):
        kwargs['queryset'] = get_page_model().objects.all()
        kwargs['name'] = 'Pages'
        kwargs['browse'] = reverse_lazy('cubane.cms.pages.index')
        kwargs['create'] = reverse_lazy('cubane.cms.pages.create')
        super(BrowsePagesField, self).__init__(*args, **kwargs)


class BrowseChildPagesField(BrowseCmsModelField):
    """
    Simplified version of browse select widget specialisied in
    browsing pages.
    """
    pass


class MetaPreviewWidget(widgets.Widget):
    """
    Widget to preview the meta data displaying an
    entry on a search page
    """
    re_create = r'/create[/]{0,1}$'
    re_edit = r'/edit[/]{0,1}$'
    re_duplicate = r'/duplicate[/]{0,1}$'
    re_pages = r'/pages[/]{0,1}$'

    def render(self, name, value, attrs=None, renderer=None):
        """
        Returns this Widget rendered as HTML, as a Unicode string.

        The 'value' given is not guaranteed to be valid input, so subclass
        implementations should program defensively.
        """
        path = self.attrs.get('path', '')

        # remove unwanted actions or directions from the path info
        if len(path) >= 6 and path[0:6] == '/admin':
            path = path[6:]
            path = re.sub(self.re_create, '/', path)
            path = re.sub(self.re_edit, '/', path)
            path = re.sub(self.re_duplicate, '/', path)
            path = re.sub(self.re_pages, '/', path)

        # get form and instance
        form = self.attrs.get('form')
        if form is None:
            return ''

        if hasattr(form, '_edit') and form._edit:
            instance = form._instance
        else:
            instance = form._meta.model()
            instance.pk = 1
            instance.title = form.data.get('title')
            instance.slug = form.data.get('slug')
            instance._meta_title = form.data.get('_meta_title')
            instance._meta_description = form.data.get('_meta_description')

        # try to replace childpage_verbose_name with the parent slug
        if instance and isinstance(instance, ChildPage):
            try:
                belongs_to = instance.page
                path = belongs_to.get_fullslug()
            except:
                pass

        # generate the green url
        url = ''.join((
            'www.',
            settings.DOMAIN_NAME,
            path,
            '<span data-watch-field="slug">',
            instance.get_slug() + '/' if instance and instance.slug else '&lt;slug&gt;/',
            '</span>'
            ))

        # render HTML
        output = '<div id="id_' + name + '">' +\
                render_to_string('cubane/cms/meta_widget.html', {
                    'title': instance.title,
                    'meta_title': instance._meta_title,
                    'meta_description': instance._meta_description,
                    'url': url,
                }) +\
                '</div>'
        return mark_safe(output)


class PageFormBase(BaseModelForm):
    """
    Form for editing CMS pages. This is the base form class for cms pages and
    cms entities. However, when deriving new forms, use PageForm or EntityForm.
    """
    class Meta:
        exclude = ['_nav', '_data']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'slugify', 'autocomplete': 'off'}),
            'slug': forms.TextInput(attrs={'class': 'slug', 'autocomplete': 'off'}),
            'seq': NumberInput(attrs={'class': 'input-mini', 'min': '0'}),
            '_excerpt': widgets.Textarea(attrs={'rows': '8'}),
            '_meta_description': widgets.Textarea()
        }
        tabs = [
            {
                'title': 'Content',
                'fields': []
            }, {
                'title': 'Title',
                'fields': [
                    'title',
                    'slug',
                    'legacy_url',
                    '_excerpt',
                    '_meta_title',
                    '_meta_description',
                    '_meta_keywords',
                    '_meta_preview',
                ]
            }, {
                'title': 'Presentation',
                'fields': [
                    'template',
                ]
            }, {
                'title': 'Gallery',
                'fields': [
                    'image',
                    '_gallery_images'
                ]
            }, {
                'title': 'Visibility',
                'fields': ['disabled', 'sitemap', 'seq']
            }
        ]
        sections = {
            'title': 'Page Data',
            '_excerpt': 'Excerpt',
            '_meta_title': 'Meta Data',
            '_meta_preview': 'Search Result Preview',
            'template': 'Template',
            'image': 'Primary Image and Gallery'
        }
        limits = {
            '_meta_title':       FormInputLimit(65),
            '_meta_description': FormInputLimit(240)
        }


    image = BrowseImagesField(required=False)

    _gallery_images = ModelCollectionField(
        label='Image Gallery',
        required=False,
        queryset=Media.objects.filter(is_image=True),
        url='/admin/images/',
        title='Gallery',
        model_title='Images',
        help_text='Add an arbitrarily number of images to this page.'
    )

    _meta_preview = fields.Field(
        label=None,
        required=False,
        help_text='This preview is for demonstration purposes only ' + \
                  'and the actual search result may differ from the preview.'
    )

    parent = BrowsePagesField(
        required=False,
        help_text='Select the parent page for this page for the purpose of ' + \
                  'presenting multi-level navigation.'
    )


    def clean_legacy_url(self):
        """
        Allow a full domain name to be copy into the legacy_url field and
        have the absolute path extracted automatically.
        """
        legacy_url = self.cleaned_data.get('legacy_url')

        if legacy_url:
            legacy_url = to_legacy_url(legacy_url)

        return legacy_url


    def clean(self):
        """
        Detect navigation changes
        """
        cleaned_data = super(PageFormBase, self).clean()

        if self._instance and self._instance.pk:
            nav_changed = (
                self.cleaned_data.get('title') != getattr(self._instance, 'title', None) or
                self.cleaned_data.get('navigation_title') != getattr(self._instance, 'navigation_title', None) or
                self.cleaned_data.get('slug') != getattr(self._instance, 'slug', None)
            )
            if nav_changed:
                self._instance.nav_updated_on = datetime.now()

        return cleaned_data


    def configure(self, request, instance, edit):
        """
        Configure form
        """
        super(PageFormBase, self).configure(request, instance, edit)
        from cubane.cms.templatetags.cms_tags import rewrite_image_references

        # create textarea field for each slot.
        if self.is_tabbed:
            for slotname in settings.CMS_SLOTNAMES:
                fieldname = 'slot_%s' % slotname
                self.fields[fieldname] = forms.CharField(
                    required=False,
                    widget=forms.Textarea(attrs={'class': 'editable-html preview no-label full-height', 'data-slotname': slotname})
                )
                self._tabs[0]['fields'].append(fieldname)

        # load initial content for each slot.
        if edit or self.is_duplicate:
            for slotname in settings.CMS_SLOTNAMES:
                fieldname = 'slot_%s' % slotname
                self.fields[fieldname].initial = \
                    rewrite_image_references(instance.get_slot_content(slotname))

        self.fields['_meta_preview'].widget = MetaPreviewWidget(attrs={
            'class': 'no-label',
            'path': request.path_info,
            'form': self
        })


class PageForm(PageFormBase):
    """
    Base class for CMS pages. Derive from this form in order to customize
    the behavior when editing CMS pages.
    """
    class Meta:
        model = get_page_model()
        fields = '__all__'
        widgets = {
            'identifier': BootstrapTextInput(prepend='#', attrs={'class': 'make-identifier', 'autocomplete': 'off'}),
        }
        tabs = [
            {
                'title': 'Navigation',
                'fields': [
                    'nav',
                    'navigation_title',
                    'identifier',
                    'parent',
                ]
            }, {
                'title': 'Presentation',
                'fields': [
                    'entity_type',
                ]
            }
        ]
        sections = {
            'nav': 'Navigation',
            'parent': 'Hierarchy'
        }


    ERROR_SLUG_COLLISION = (
        'There is already a slug with this name. Please ' +
        'choose another name.'
    )
    ERROR_SLUG_SYSTEM_NAME = (
        'This slug is reserved for system purposes. ' +
        'Please choose a differnt slug.'
    )
    ERROR_IDENTIFIER_INVALID_FORMAT = (
        'Invalid identifier format: Only lowercase letters, ' +
        'numbers and underscore but cannot start with letters ' +
        'and/or underscore.'
    )
    ERROR_IDENTIFIER_COLLISION = (
        'There is already an identifier with this name. Please ' +
        'choose another name.'
    )


    entity_type = forms.ChoiceField(
        label='Child Pages (type)',
        required=False,
        help_text="Select the type of entities that this page may present " +
                  "(for example 'News' if you want to presents news articles " +
                  "on this page)."
    )

    nav = forms.MultipleChoiceField(
        label='Navigation',
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=settings.CMS_NAVIGATION,
        help_text='Tick the navigation sections in which this page ' +
                  'should appear in.'
    )


    def configure(self, request, instance = None, edit = True):
        super(PageForm, self).configure(request, instance, edit)

        # generate list of entity type choices based on all django models
        # that subclass from PageBase (but not Page itself).
        choices = [('', '-------')]
        for model in get_models():
            if issubclass(model, ChildPage):
                choices.append( (model.__name__, model._meta.verbose_name) )
        self.fields['entity_type'].choices = choices

        # navigation
        if edit or self.is_duplicate:
            self.fields['nav'].initial = instance.nav

        # parent page only available if hierarchical pages is enabled
        if not settings.PAGE_HIERARCHY:
            self.remove_field('parent')
            self.update_sections()

        # 404 page cannot be disabled!
        cms_settings = get_cms_settings()
        if instance and cms_settings.default_404 and instance.pk == cms_settings.default_404.pk:
            self.fields['disabled'].widget.attrs['disabled'] = True
            self.fields['disabled'].help_text = 'This page is configured as the default 404 (Page Not Found) page and can therefore not be disabled.'
            self.fields['sitemap'].widget.attrs['disabled'] = True
            self.fields['sitemap'].help_text = 'This page is configured as the default 404 (Page Not Found) page and can therefore not be excluded from the sitemap.'


    def is_colliding_page(self, *args, **kwargs):
        pages = get_page_model().objects.filter(**kwargs)
        if self._edit:
            pages = pages.exclude(pk=self._instance.id)
        return pages.count() > 0


    def clean_slug(self):
        slug = self.cleaned_data.get('slug')

        if slug:
            # is there another page with the same slug?
            if self.is_colliding_page(slug=slug):
                raise forms.ValidationError(self.ERROR_SLUG_COLLISION)

            # child page?
            if collides_with_child_page_of_homepage(slug):
                raise forms.ValidationError(self.ERROR_SLUG_COLLISION)

            # is the slug reserved for system purposes?
            if collides_with_reserved_name(slug):
                raise forms.ValidationError(self.ERROR_SLUG_SYSTEM_NAME)

        return slug


    def clean_identifier(self):
        identifier = self.cleaned_data.get('identifier')
        if identifier:
            identifier = identifier.lower()

            # validate identifier format
            if not re.match(r'^[a-z][_a-z0-9]+$', identifier):
                raise forms.ValidationError(self.ERROR_IDENTIFIER_INVALID_FORMAT)

            # is there another page with the same identifier?
            if self.is_colliding_page(identifier=identifier):
                raise forms.ValidationError(self.ERROR_IDENTIFIER_COLLISION)

        return identifier


class EntityForm(BaseModelForm):
    """
    Base class for editing cms entities. Derive from this form in order to
    create new cms entity forms for your specific business objects.
    """
    pass


class ChildPageForm(PageFormBase):
    """
    Base class for editing CMS page entities. Derive from this form in order to
    create new forms for your specific business objects.
    """
    class Meta:
        tabs = [
            {
                'title': 'Presentation',
                'fields': [
                    'page',
                ]
            }
        ]


    def configure(self, request, instance=None, edit=True):
        super(ChildPageForm, self).configure(request, instance, edit)

        # configure parent page dropdown with list of pages that are available
        # for the given child page model.
        pages = get_page_model().objects.filter(
            entity_type=self._meta.model.__name__
        )
        self.fields['page'].queryset = pages

        # do not show empty label
        self.fields['page'].empty_label = None


    def clean(self):
        d = self.cleaned_data
        slug = d.get('slug')
        page = d.get('page')

        if slug and page:
            # no collision with any other child page (with the same parent page)
            pages = self._meta.model.objects.filter(page=page, slug=slug)
            if self._edit and not self.is_duplicate:
                pages = pages.exclude(pk=self._instance.id)
            if pages.count() > 0:
                self.field_error('slug', PageForm.ERROR_SLUG_COLLISION)

            # parent is the homepage!
            if page.is_homepage:
                # collision with any other page, if the parent page is the homepage
                if get_page_model().objects.filter(is_homepage=False, slug=slug).count() > 0:
                    self.field_error('slug', PageForm.ERROR_SLUG_COLLISION)

                # is the slug reserved for system purposes?
                if collides_with_reserved_name(slug):
                    self.field_error('slug', PageForm.ERROR_SLUG_SYSTEM_NAME)

        return d


class PostForm(ChildPageForm):
    """
    Introducing another term instead of ChildPage.
    """
    pass


class SettingsForm(BaseModelForm):
    """
    Form for editing website-wide settings.
    """
    ERROR_CLOSING_TIME_REQUIRED = (
        'You have to specify a closing time if you specify an opening time.'
    )
    ERROR_OPENING_TIME_REQUIRED = (
        'You have to specify an opening time if you specify a closing time.'
    )
    ERROR_OPENING_TIME_MUST_COME_BEFORE_CLOSING_TIME = (
        'The opening time has to be before the closing time.'
    )
    ERROR_FROM_EMAIL_CANNOT_BE_THE_SAME_AS_ENQUIRY_EMAIL = (
        'From email cannot be the same as Enquiry email.'
    )


    class Meta:
        widgets = {
            'lat': forms.HiddenInput(),
            'lng': forms.HiddenInput(),
            'zoom': forms.HiddenInput(),
            'email': EmailInput(),
            'phone': PhoneInput(),
            'twitter': UrlInput(),
            'facebook': UrlInput(),
            'linkedin': UrlInput(),
            'google_plus': UrlInput(),
            'youtube': UrlInput(),
            'instagram': UrlInput(),
            'blogger': UrlInput(),
            'pinterest': UrlInput(),
            'twitter_widget_id': BootstrapTextInput(prepend='#'),
            'enquiry_email': EmailInput(),
            'enquiry_from': EmailInput(),
            'enquiry_reply': EmailInput(),
            'page_size': NumberInput(attrs={'min': 2}),
            'max_page_size': NumberInput(attrs={'min': 2}),
            'monday_start': TimeInput(),
            'monday_close': TimeInput(),
            'tuesday_start': TimeInput(),
            'tuesday_close': TimeInput(),
            'wednesday_start': TimeInput(),
            'wednesday_close': TimeInput(),
            'thursday_start': TimeInput(),
            'thursday_close': TimeInput(),
            'friday_start': TimeInput(),
            'friday_close': TimeInput(),
            'saturday_start': TimeInput(),
            'saturday_close': TimeInput(),
            'sunday_start': TimeInput(),
            'sunday_close': TimeInput()
        }
        tabs = [
            {
                'title': 'Pages and Address',
                'fields': [
                    'homepage',
                    'default_404',
                    'contact_page',
                    'enquiry_template',
                    'name',
                    'meta_name',
                    'address1',
                    'address2',
                    'postcode',
                    'city',
                    'county',
                    'country',
                    'default_encoding',
                    'notification_text',
                    'notification_enabled'
                ]
            }, {
                'title': 'Location',
                'fields': [
                    '_location',
                    'lat',
                    'lng',
                    'zoom',
                ]
            }, {
                'title': 'Contact',
                'fields': [
                    'email',
                    'phone',
                    'mailchimp_api',
                    'mailchimp_list_id',
                    'enquiry_email',
                    'enquiry_from',
                    'enquiry_reply'
                ]
            },{
                'title': 'Social Media',
                'fields': [
                    'skype',
                    'linkedin',
                    'facebook',
                    'twitter',
                    'google_plus',
                    'youtube',
                    'instagram',
                    'blogger',
                    'pinterest',
                    'twitter_name',
                    'twitter_widget_id',
                ]
            }, {
                'title': 'Identification',
                'fields': [
                    'analytics_key',
                    'analytics_hash_location',
                    'webmaster_key',
                    'globalsign_key'
                ]
            }, {
                'title': 'Pagination',
                'fields': [
                    'paging_enabled',
                    'paging_child_pages',
                    'page_size',
                    'max_page_size'
                ]
            }, {
                'title': 'Opening Times',
                'fields': [
                    'monday_start',
                    'tuesday_start',
                    'wednesday_start',
                    'thursday_start',
                    'friday_start',
                    'saturday_start',
                    'sunday_start',
                    'monday_close',
                    'tuesday_close',
                    'wednesday_close',
                    'thursday_close',
                    'friday_close',
                    'saturday_close',
                    'sunday_close',
                    'opening_times_enabled',
                ]
            }, {
                'title': 'Directory',
                'fields': [
                    'order_mode'
                ]
            }

        ]
        sections = {
            'homepage': 'Default Pages',
            'name': 'Name and Address',
            'default_encoding': 'Default Encoding',
            'notification_text': 'Important Notification',
            '_location': 'Location',
            'email': 'Contact',
            'skype': 'Social Media Links',
            'twitter_name': 'Social Media Widgets',
            'mailchimp_api': 'Newsletter Signup (MailChimp)',
            'enquiry_email': 'Sending Emails',
            'monday_start': 'Start Times',
            'monday_close': 'Finish Times',
            'opening_times_enabled': 'Enable Opening Times',
            'order_mode': 'Directory Default Order'
        }


    homepage = BrowsePagesField(
        help_text='Select the page that should be presented as the ' +
                  'homepage for your website.'
    )

    default_404 = BrowsePagesField(
        help_text='Select the page that should be present in the case that ' +
                  'no other page could be found. Usually the 404 page gives ' +
                  'some useful links for the visitor to progress to.'
    )

    contact_page = BrowsePagesField(
        required=False,
        help_text='Select the page that should present the contact us form ' +
                  'that allows visitors to send an enquiry message to you.'
    )

    enquiry_template = BrowsePagesField(
        required=False,
        help_text='Select the page that is used to send the enquiry email ' + \
                  'to customers who are using the enquiry form on the website.'
    )

    _location = LocationMapField(
        label='Location',
        widget=LocationMapWidget(attrs={'class': 'no-label fill-space searchable'}),
        help_text='Click and drag the marker to the exact location of ' +
                  'your business.'
    )


    def configure(self, request, instance = None, edit = True):
        super(SettingsForm, self).configure(request, instance, edit)

        # configure pagination
        from cubane.cms.models import get_child_page_model_choices
        child_page_choices = get_child_page_model_choices()

        # child page pagination
        if child_page_choices:
            self.fields['paging_child_pages'].choices = child_page_choices
        else:
            # no child pages available -> remove entire pagination tab
            self.remove_tab('Pagination')
            del self.fields['page_size']
            del self.fields['max_page_size']

        # hide directory settings if no directory is used...
        if 'cubane.directory' not in settings.INSTALLED_APPS:
            self.remove_tab('Directory')
            del self.fields['order_mode']

        # site notification
        if not settings.CUBANE_SITE_NOTIFICATION:
            self.remove_fields(['notification_text', 'notification_enabled'])
            self.update_sections()



    def clean_max_page_size(self):
        d = self.cleaned_data
        page_size = d.get('page_size')
        max_page_size = d.get('max_page_size')

        try:
            page_size = int(page_size)
            max_page_size = int(max_page_size)
        except (ValueError, TypeError) as e:
            pass

        if page_size and max_page_size:
            if max_page_size < page_size:
                raise forms.ValidationError(
                    ('Max. page size needs to be at least ' +
                     'the page size of %d.') % page_size
                )

        return max_page_size


    def test_spf(self, field, message):
        if field:
            if settings.CMS_TEST_SPF:
                from cubane.lib.spfcheck import SPFCheck
                check = SPFCheck()
                check.check_local_ips(field)

                if not check.test_pass:
                    msg = mark_safe(
                        message +
                        '<a href="https://en.wikipedia.org/wiki/Sender_Policy_Framework" target="_blank">Sender Policy Framework</a> (SPF).' +
                        check.html_results
                    )

                    if settings.DEBUG or settings.CMS_SOFTFAIL_SPF or 'cubane.enquiry' not in settings.INSTALLED_APPS:
                        # soft fail in development or otherwise...
                        messages.error(self._request, msg)
                    else:
                        # hard fail in production.
                        raise forms.ValidationError(msg)

        return field


    def clean_enquiry_from(self):
        enquiry_from = self.cleaned_data.get('enquiry_from')
        return self.test_spf(enquiry_from, 'SPF check did not pass. Please make sure that the <em>sender email address</em> passes the ')


    def clean_enquiry_reply(self):
        reply_to = self.cleaned_data.get('enquiry_reply')
        return self.test_spf(reply_to, 'SPF check did not pass. Please make sure that the <em>reply to address</em> passes the ')


    def clean(self):
        d = self.cleaned_data
        days = [
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'friday',
            'saturday',
            'sunday'
        ]

        for day in days:
            if d.get(day+'_start') != None and d.get(day+'_close') == None:
                self.field_error(day+'_close', self.ERROR_CLOSING_TIME_REQUIRED)

            if d.get(day+'_start') == None and d.get(day+'_close') != None:
                self.field_error(day+'_start', self.ERROR_OPENING_TIME_REQUIRED)

            if d.get(day+'_start') and d.get(day+'_close'):
                if d.get(day+'_start') > d.get(day+'_close'):
                    self.field_error(day+'_start', self.ERROR_OPENING_TIME_MUST_COME_BEFORE_CLOSING_TIME)

        if d.get('enquiry_email') and d.get('enquiry_from') and d.get('enquiry_email') == d.get('enquiry_from'):
            self.field_error('enquiry_from', self.ERROR_FROM_EMAIL_CANNOT_BE_THE_SAME_AS_ENQUIRY_EMAIL)

        return d


class MailChimpSubscriptionForm(BaseForm):
    """
    Form for subscribing to MailChimp newsletter.
    """
    mailchimp_subscription__name = forms.CharField(
        label='Name',
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Name'})
    )

    mailchimp_subscription__email = forms.EmailField(
        label='Email',
        max_length=255,
        required=True,
        widget=EmailInput(attrs={'placeholder': 'Email'})
    )