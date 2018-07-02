# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponseRedirect
from django import template
from django.template import Context
from django.contrib import messages
from django.template.loader import TemplateDoesNotExist
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe
from django.utils.html import format_html, escape
from django.core.paginator import Page as PaginatorPage
from cubane.lib.templatetags import *
from cubane.lib.html import transpose_html_headlines
from cubane.lib.html import cleanup_html
from cubane.lib.app import model_to_hash
from cubane.lib.acl import Acl
from cubane.lib.template import get_template
from cubane.cms.forms import MailChimpSubscriptionForm
from cubane.media.views import load_images_for_content
from cubane.cms.views import get_page_links_from_content
from cubane.cms.views import get_page_links_from_page
from cubane.cms.views import get_cms
from cubane.cms.views import get_cms_settings
from mailsnake import MailSnake
import re
import copy


register = template.Library()


# old (deprecated) google analytics (ga.js)
GOOGLE_ANALYTICS_SNIPPET = """<script>var _gaq=_gaq||[];_gaq.push(['_setAccount','%s']);_gaq.push(['_trackPageview']);(function(){var ga=document.createElement('script');ga.type='text/javascript';ga.async=true;ga.src=('https:'==document.location.protocol?'https://ssl':'http://www')+'.google-analytics.com/ga.js';var s=document.getElementsByTagName('script')[0];s.parentNode.insertBefore(ga, s);})();</script>"""

# universal google analytics (analytics.js)
GOOGLE_ANALYTICS_UNIVERSAL_SNIPPET = """<script>(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m) })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');ga('create','%s','auto');ga('send','pageview');</script>"""
GOOGLE_ANALYTICS_UNIVERSAL_SNIPPET_ASYNC = """<script>window.ga=window.ga||function(){(ga.q=ga.q||[]).push(arguments)};ga.l=+new Date;ga('create', '%s', 'auto');ga('send', 'pageview');</script><script async src='https://www.google-analytics.com/analytics.js'></script>"""

# universal google analytics for ecommerce
GOOGLE_ANALYTICS_ECOMMERCE_SNIPPET = """<script>(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)})(window,document,'script','https://www.google-analytics.com/analytics.js','ga');ga('create', '%s');ga('require', 'ec');</script>"""
GOOGLE_ANALYTICS_ECOMMERCE_SNIPPET_ASYNC = """<script>window.ga=window.ga||function(){(ga.q=ga.q||[]).push(arguments)};ga.l=+new Date;ga('create', '%s', 'auto');ga('require', 'ec');</script><script async src='https://www.google-analytics.com/analytics.js'></script>"""

# other
GOOGLE_ANALYTICS_UNIVERSAL_WITH_HASH_LOCATION_SNIPPET = """<script>(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)})(window,document,'script','https://www.google-analytics.com/analytics.js','ga');ga('create','%s','auto');ga('send','pageview',{'page':location.pathname+location.search+location.hash});window.onhashchange=function(){ga('send','pageview',{'page':location.pathname+location.search+location.hash});};</script>"""
TWITTER_WIDGET_ID = """<a class="twitter-timeline" href="https://twitter.com/twitterapi" data-widget-id="%s">Tweets by %s</a><script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>"""


def get_attr(s, attrname):
    """
    Return XML attribute value within given string s of given attribute name.
    """
    m = re.search(r'%s="(.*?)"' % attrname, s)
    if m:
        return m.group(1)
    elif 'cubane' in attrname:
        # for legacy reasons, also support data-ikit-... attributes
        attrname = attrname.replace('data-cubane-', 'data-ikit-')
        m = re.search(r'%s="(.*?)"' % attrname, s)
        if m:
            return m.group(1)

    # not found
    return ''


def set_attr(s, attrname, value):
    """
    Set XML attribute value of given attribute in given string s.
    """
    return re.sub(r'%s="(.*?)"' % attrname, '%s="%s"' % (attrname, value), s)


def rewrite_images(content, images, render_image, noscript=False, image_shape=settings.DEFAULT_IMAGE_SHAPE):
    """
    Rewrite img tags to the responsive format for fast responsive websites.
    """
    if image_shape not in settings.IMAGE_SHAPES:
        image_shape = 'original'

    def rewrite_image(match):
        s = match.group(1)

        _id = get_attr(s, 'data-cubane-media-id')
        width = get_attr(s, 'data-width')
        size = get_attr(s, 'data-cubane-media-size')
        style = get_attr(s, 'style')
        lightbox = get_attr(s, 'data-cubane-lightbox') == 'true'

        # only generate code for lightbox if we have cubane.lightbox
        # installed...
        if 'cubane.lightbox' not in settings.INSTALLED_APPS:
            lightbox = False

        # remove width if we are in auto size mode...
        if size == 'auto':
            width = None

        try:
            _id = int(_id)
            image = images.get(_id, None)
            if image:
                return render_image(image, shape=image_shape, width=width, style=style, lightbox=lightbox, noscript=noscript)
        except ValueError:
            pass

        return match.group(0)

    return re.sub(r'<img(.*?\/?)>',
        rewrite_image,
        content
    )


def rewrite_image_references(content):
    """
    Rewrites image content that might refer to an outdated image version, since
    the original image has been re-uploaded which might have been changed the
    version number.
    """
    if content is None:
        return content

    # collect all media identifiers
    images = load_images_for_content(content)

    def rewrite_image(match):
        s = match.group(0)

        _id = get_attr(s, 'data-cubane-media-id')

        try:
            _id = int(_id)
            image = images.get(_id, None)
            if image:
                s = set_attr(s, 'src', image.url)
        except ValueError:
            pass

        return s

    return re.sub(r'<img(.*?\/?)>',
        rewrite_image,
        content
    )


def rewrite_page_links(content, page_links):
    """
    Rewrite given cms slot content by replacing any page link references in
    the form #link[type:id] into the corresponding actual URL of the references
    entity bby using the page link data structure provided.
    """
    def rewrite_page_link(match):
        s = match.group(1)
        m = re.match(r'(\w+):(\d+)', s)
        if m:
            _type = m.group(1)
            _id = m.group(2)
            items = page_links.get(_type, {})
            obj = items.get(_id)
            if obj and hasattr(obj, 'url'):
                s = obj.url
            elif obj and hasattr(obj, 'get_absolute_url'):
                s = obj.get_absolute_url()
            else:
                if settings.DEBUG:
                    raise ValueError('Unable to resolve page link #link[%s:%s].' % (
                        _type,
                        _id
                    ))
                else:
                    s = ''
        return s
    return re.sub(r'#link\[(.*?)\]', rewrite_page_link, content)


def render_meta_tag(name, value):
    """
    Render a meta tag with the given name and value if a value is defined.
    """
    if value:
        return format_html('<meta name="{}" content="{}" />', name, value)
    else:
        return ''


def get_edit_reference(request, instance, property_names, help_text=None, shortcut=False):
    """
    Return reference information about editing the given list of properties for the
    given object instance.
    """
    if settings.CUBANE_FRONTEND_EDITING:
        if request is not None and request.user is not None and (request.user.is_staff or request.user.is_superuser):
            if instance is not None and property_names:
                # make sure that the user has access to the instance
                if Acl.of(instance.__class__).can_edit_instance(request, instance):
                    # try to extract help text from form
                    if help_text is None and len(property_names) == 1:
                        if hasattr(instance.__class__, 'get_form'):
                            form = instance.__class__.get_form()
                            if form:
                                field = form.declared_fields.get(property_names[0])
                                if field:
                                    help_text = field.help_text

                    # construct reference
                    return '%s%s|%s|%s%s' % (
                        '!' if shortcut else '',
                        model_to_hash(instance.__class__),
                        instance.pk,
                        ':'.join(property_names),
                        '|%s' % help_text if help_text else ''
                    )

    return None


class SlotNode(template.Node):
    def __init__(self, slotname, headline_transpose=0, image_shape=None):
        self.slotname = slotname
        self.headline_transpose = headline_transpose
        self.image_shape = image_shape


    def render(self, context):
        """
        Render slot content.
        """
        slotname = value_or_literal(self.slotname, context)
        headline_transpose = value_or_literal(self.headline_transpose, context)
        image_shape = value_or_literal(self.image_shape, context)
        page = value_or_none('page', context)
        child_page = value_or_none('child_page', context)
        preview = value_or_default('cms_preview', context, False)
        noscript = value_or_default('noscript', context, False)
        images = context.get('images', {})
        is_enquiry_template = value_or_default('is_enquiry_template', context, False)

        # make sure that this slot actually exists
        if slotname not in settings.CMS_SLOTNAMES:
            return template_error("Slot '%s' does not exist (referenced via %s)" % (slotname, self.slotname))

        # switch page to child_page if present
        if child_page:
            page = child_page

        # extract correct content from page based on the slotname provided
        if page:
            content = page.get_slot_content(slotname)
        else:
            content = ''

        # make sure that headline transpose is an integer we can work with
        try:
            headline_transpose = int(headline_transpose)
        except ValueError:
            headline_transpose = 0

        # run through content pipeline
        cms = get_cms()
        request = context.get('request')
        content = cms.on_render_content_pipeline(request, content, context)

        # rewrite image url to use responsive lazy-load mechanism for images,
        # (we are not doing this in preview mode).
        if not preview and not is_enquiry_template and 'cubane.media' in settings.INSTALLED_APPS:
            from cubane.media.templatetags.media_tags import render_image
            content = rewrite_images(content, images, render_image, noscript, image_shape)

        # page links
        if not preview:
            page_links = context.get('page_links', {})
            content = rewrite_page_links(content, page_links)

        # transpose headlines
        content = transpose_html_headlines(content, headline_transpose)

        # cleanup markup
        content = cleanup_html(content)

        # mark content as safe
        content = mark_safe(content)

        # wrap content into a seperate slot container if we are configured
        # to do so...
        if settings.CMS_RENDER_SLOT_CONTAINER:
            content = '<div class="cms-slot-container">' + content + '</div>'

        # frontend editing?
        if settings.CUBANE_FRONTEND_EDITING:
            ref = get_edit_reference(request, page, ['slot_%s' % slotname])
            if ref:
                content = '<div edit="%s">%s</div>' % (ref, content)

        # in preview mode, we wrap the content into a container, so that we
        # can identify the content in the backend and provide live-editing
        # preview capabilities...
        if preview:
            return '<div class="cms-slot" data-slotname="%s" data-headline-transpose="%d">%s</div>' % (
                slotname,
                headline_transpose,
                content
            )
        else:
            return content


class ChildPagesNode(template.Node):
    def __init__(self, child_pages, child_page_slug):
        self.child_pages = child_pages
        self.child_page_slug = child_page_slug


    def render(self, context):
        """
        Render list of child pages for the current page.
        """
        def _get_post_template(prefix, slug):
            t = None
            template_filename = 'cubane/cms/%s/%s.html' % (prefix, slug)

            try:
                if slug:
                    t = get_template(template_filename)
            except TemplateDoesNotExist:
                pass

            return t, template_filename

        page = value_or_none('page', context)
        child_page_slug = value_or_literal(self.child_page_slug, context)
        child_pages = None

        # get child pages or paged child pages
        if self.child_pages == 'child_pages':
            # default argument
            child_pages = value_or_none('paged_child_pages', context)
        if child_pages == None:
            child_pages = value_or_none(self.child_pages, context)

        if child_pages:
            # resolve template for rendering entities
            t, template_filename = _get_post_template('posts', child_page_slug)
            if t is None:
                t, template_filename = _get_post_template('child_pages', child_page_slug)

            # if we cannot find the template, tell the user about it
            if t == None:
                raise ValueError(
                    ("Error rendering child page listing item for '%s'. " +
                     "Unable to load template '%s'. Please make sure that " +
                     "the template exists.") % (
                        child_page_slug,
                        template_filename
                    )
                )

            # inject child pages into copy of context for rendering the template
            # if child pages is a paginator page, inject paginator itself
            # into the template context
            d = {
                'child_pages': child_pages,
                'paginator': child_pages.paginator if isinstance(child_pages, PaginatorPage) else None
            }
            with context.push(**d):
                return t.render(context)
        else:
            return ''


class MapNode(template.Node):
    def __init__(self, lat, lng, zoom, name, api_key):
        self.lat = lat
        self.lng = lng
        self.zoom = zoom
        self.name = name
        self.api_key = api_key


    def render(self, context):
        lat = value_or_none(self.lat, context)
        lng = value_or_none(self.lng, context)
        zoom = value_or_none(self.zoom, context)
        name = value_or_none(self.name, context)
        if lat and lng and zoom and name:
            return htmltag('div', {
                'class': 'enquiry-map-canvas',
                'data-lat': lat,
                'data-lng': lng,
                'data-zoom': zoom,
                'data-title': name,
                'data-key': self.api_key
            })
        else:
            return ''


class ContactMapNode(template.Node):
    def __init__(self, settings, api_key):
        self.api_key = api_key
        self.settings = settings


    def render(self, context):
        settings = value_or_none(self.settings, context)
        if settings:
            return htmltag('div', {
                'class': 'enquiry-map-canvas',
                'data-lat': settings.lat,
                'data-lng': settings.lng,
                'data-zoom': settings.zoom,
                'data-title': settings.name,
                'data-key': self.api_key
            })
        else:
            return ''


class EditNode(template.Node):
    """
    Renders additional information that enables frontend editing.
    """
    def __init__(self, reference, property_names, help_text, css_class=None, shortcut=False, nodelist=None):
        self.reference = reference
        self.property_names = property_names
        self.help_text = help_text
        self.css_class = css_class
        self.shortcut = shortcut
        self.nodelist = nodelist


    def render(self, context):
        if settings.CUBANE_FRONTEND_EDITING:
            request = value_or_none('request', context)
            property_names = value_or_literal(self.property_names, context)
            css_class = value_or_none(self.css_class, context)
            help_text = value_or_none(self.help_text, context)

            # resolve property names
            if property_names is None:
                instance, property_name, _value = resolve_object_property_reference(context, self.reference)
                property_names = [property_name]
            else:
                instance = value_or_none(self.reference, context)
                property_names = property_names.split(',')
                property_names = [p.strip() for p in property_names]
                property_names = filter(lambda x: x, property_names)

            # get edit reference
            ref = get_edit_reference(request, instance, property_names, help_text, self.shortcut)
            if ref:
                if self.nodelist is not None:
                    inner_content = self.nodelist.render(context)
                    return '<div edit="%s"%s>%s</div>' % (
                        ref,
                        (' class="%s"' % css_class) if css_class else '',
                        inner_content
                    )
                else:
                    return ' edit="%s"' % ref

        return '' if self.nodelist is None else self.nodelist.render(context)


@register.tag('slot')
def slot(parser, token):
    """
    Renders a cms slot with content from the current page, which is assumed to
    be in a template variable with the name 'page'.

    Syntax: {% slot <slotname> [<headline-transpose>] %}
    """
    bits = token.split_contents()

    # slotname
    if len(bits) < 2:
        raise template.TemplateSyntaxError(
            "'%s' takes at least one argument: <slotname> [<headline-transpose>] [<image-shape>]" % bits[0]
        )
    slotname = bits[1]

    # headline transpose
    headline_transpose = bits[2] if len(bits) >= 3 else '0'

    # image shape
    image_shape = bits[3] if len(bits) >= 4 else None

    return SlotNode(slotname, headline_transpose, image_shape)


@register.tag('child_pages')
def child_pages(parser, token):
    """
    Renders a list of child pages, such as projects that belong to the
    current page.

    Syntax: {% child_pages [<child_pages>] [child_page_slug] %}
    """
    bits = token.split_contents()
    entities = 'child_pages'
    entity_slug = 'child_page_slug'

    if len(bits) >= 2:
        entities = bits[1]

    if len(bits) == 3:
        entity_slug = bits[2]

    return ChildPagesNode(entities, entity_slug)


@register.tag('posts')
def posts(parser, token):
    """
    Renders a list of posts, such as projects that belong to the
    current page. This is a replacement of the child_pages template tag, in
    order to replace the term child-page.

    Syntax: {% posts [<posts>] [post_slug] %}
    """
    return child_pages(parser, token)


@register.tag('contact_map')
def contact_map(parser, token):
    """
    Presents an interactive google map showing the location of the business
    according to settings.

    Syntax: {% contact_map [<settings>] %}
    """
    bits = token.split_contents()
    return ContactMapNode(bits[1] if len(bits) == 2 else 'settings', settings.CUBANE_GOOGLE_MAP_API_KEY)


@register.tag('map')
def map(parser, token):
    """
    Presents an interactive google map showing the location according
    to the values given.

    Syntax: {% contact_map <lat>, <lng>, <zoom>, <name> %}
    """
    bits = token.split_contents()
    lat = bits[1]
    lng = bits[2]
    zoom = bits[3]
    name = bits[4]
    return MapNode(lat, lng, zoom, name, settings.CUBANE_GOOGLE_MAP_API_KEY)


@register.simple_tag
def image_tag(src, *args, **kwargs):
    """
    This tag provides method for generating HTML image

    Syntax: {% image_tag <src> <args> %}
    """
    image = '<img src="%s"' % escape(src)

    for key, value in kwargs.iteritems():
        image += ' %s="%s"' % (escape(key), escape(value))

    image += '>'

    return mark_safe(image)



@register.simple_tag
def link_tag(href, content, *args, **kwargs):
    """
    This tag provides method for generating HTML link

    Syntax: {% link_tag <href> <name> <args> %}
    """
    link = '<a href="%s"' % escape(href)

    for key, value in kwargs.iteritems():
        link += ' %s="%s"' % (escape(key), escape(value))

    link += '>%s</a>' % content

    return mark_safe(link)


@register.simple_tag
def social_tag(href, src):
    """
    Render mixed link_tag and image_tag because django doesn't support nesting
    template tags

    Syntax: {% social_tag <href> <src> <link_args> <image_args>
    """

    image = image_tag(src)
    social_link = link_tag(href, image)

    return mark_safe(social_link)


@register.simple_tag(takes_context=True)
def site_identification(context):
    """
    Embeds various site identification keys, such as webmaster tools etc.
    """
    settings = value_or_none('settings', context)
    s = ''
    if settings:
        s += render_meta_tag(
            'google-site-verification',
            settings.webmaster_key
        )

        s += render_meta_tag(
            'globalsign-domain-verification',
            settings.globalsign_key
        )

    return mark_safe(s)


def get_google_analytics_key(context):
    """
    Return the default google analytics integration key which is configured in
    cms settings for PRODUCTION mode. However, in DEBUG mode we rely on
    setting.DEBUG_GOOGLE_ANALYTICS.
    """
    if settings.DEBUG:
        if settings.DEBUG_GOOGLE_ANALYTICS:
            return settings.DEBUG_GOOGLE_ANALYTICS
        else:
            return ''
    else:
        cms_settings = value_or_none('settings', context)
        if cms_settings and cms_settings.analytics_key:
            return cms_settings.analytics_key
        else:
            return ''


def get_google_analytics_universal(context):
    """
    Return code snippet for google analytics universal (async or sync).
    """
    key = get_google_analytics_key(context)
    if settings.CUBANE_GOOGLE_ANALYTICS_ASYNC:
        return mark_safe(GOOGLE_ANALYTICS_UNIVERSAL_SNIPPET_ASYNC % key)
    else:
        return mark_safe(GOOGLE_ANALYTICS_UNIVERSAL_SNIPPET % key)


def get_google_analytics_ecommerce(context):
    """
    Return code snippet for google analytics universal for e-commerce
    (async or sync).
    """
    key = get_google_analytics_key(context)
    if settings.CUBANE_GOOGLE_ANALYTICS_ASYNC:
        return mark_safe(GOOGLE_ANALYTICS_ECOMMERCE_SNIPPET_ASYNC % key)
    else:
        return mark_safe(GOOGLE_ANALYTICS_ECOMMERCE_SNIPPET % key)


@register.simple_tag(takes_context=True)
def google_analytics(context):
    """
    Embeds google analytics tracking facility.
    """
    return mark_safe(GOOGLE_ANALYTICS_SNIPPET % get_google_analytics_key(context))


@register.simple_tag(takes_context=True)
def google_analytics_universal(context):
    """
    Embeds google analytics tracking facility.
    """
    key = get_google_analytics_key(context)
    cms_settings = value_or_none('settings', context)
    if cms_settings and cms_settings.analytics_hash_location:
        return mark_safe(GOOGLE_ANALYTICS_UNIVERSAL_WITH_HASH_LOCATION_SNIPPET % key)
    else:
        return get_google_analytics_universal(context)


@register.simple_tag(takes_context=True)
def google_analytics_ecommerce(context):
    """
    Embeds google analytics tracking facility for ecommerce application.
    """
    return get_google_analytics_ecommerce(context)


@register.simple_tag(takes_context=True)
def google_analytics_ecommerce_send(context):
    """
    Send page impression for google analytics ecommernce.
    """
    return mark_safe("<script>ga('send', 'pageview');</script>")


@register.simple_tag(takes_context=True)
def twitter_widget(context):
    """
    Embeds twitter widget.
    """
    settings = value_or_none('settings', context)
    if settings and settings.twitter_widget_id and settings.twitter_name:
        return mark_safe(TWITTER_WIDGET_ID % (settings.twitter_widget_id, settings.twitter_name))
    else:
        return ''

@register.simple_tag(takes_context=True)
def social_media_links(context, social_id=None):
    """
    Renders social media links.
    Usage {% social_media_links %}
    """
    d = {
        'social_id': social_id
    }
    with context.push(**d):
        return get_template('cubane/cms/social.html').render(context)


@register.simple_tag(takes_context=True)
def opening_times(context):
    """
    Renders the opening times if enabled.
    Usage {% opening_times %}
    """
    return get_template('cubane/cms/opening_times.html').render(context)


@register.simple_tag(takes_context=True)
def meta_title(context, page=None):
    """
    Renders the meta title of the current page based on the current page's
    meta title or title (depending on what is available). The name of the website
    is appended at the end (unless it is already included within the page title or
    meta title).
    """
    if page == None:
        page = context.get('current_page')

    cms_settings = context.get('settings')
    if page:
        if isinstance(page, basestring):
            title = page
        else:
            title = page.meta_title

        if title:
            title = title.strip()
            if cms_settings:
                if cms_settings.meta_name:
                    meta_name = cms_settings.meta_name
                else:
                    meta_name = cms_settings.name

                if meta_name:
                    meta_name = meta_name.strip()
                    if not title.endswith(meta_name):
                        title += settings.CMS_META_TITLE_SEPARATOR + meta_name.strip()

            return title
    elif cms_settings and cms_settings.name:
        return cms_settings.name.strip()

    return ''


@register.simple_tag(takes_context=True)
def newsletter_signup_form(context):
    """
    Renders a default nessletter signup form based on MailChimp.
    """
    settings = value_or_none('settings', context)
    if not settings:
        raise ValueError("Expected 'settings' in template context.")

    if not settings.mailchimp_api or not settings.mailchimp_list_id:
        return ''

    request = value_or_none('request', context)
    if not request:
        raise ValueError("Expected 'request' in template context.")

    if request.method == 'POST':
        form = MailChimpSubscriptionForm(request.POST)
    else:
        form = MailChimpSubscriptionForm()

    msg = None
    msg_type = None

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data

        merge_vars = { 'FNAME': d.get('mailchimp_subscription__name', '') }
        ms = MailSnake(settings.mailchimp_api)

        try:
            ms.listSubscribe(id=settings.mailchimp_list_id, email_address=d['mailchimp_subscription__email'], merge_vars=merge_vars)
            msg = 'Almost finished...We need to confirm your email address. To complete the subscription process, please click the link in the email we just sent you.'
            msg_type = 'success'
        except:
            msg = 'Unfortunately we were unable to process your request. Please try again later...'
            msg_type = 'error'

    # render form
    t = get_template('cubane/cms/newsletter_form.html')
    c = copy.copy(context)
    c['form'] = form
    c['msg'] = msg
    c['msg_type'] = msg_type
    return t.render(c)


@register.simple_tag(takes_context=True)
def newsletter_signup_form_ajax(context):
    """
    Renders a default nessletter signup form based on MailChimp.
    """
    settings = value_or_none('settings', context)
    if not settings:
        raise ValueError("Expected 'settings' in template context.")

    if not settings.mailchimp_api or not settings.mailchimp_list_id:
        return ''

    request = value_or_none('request', context)
    if not request:
        raise ValueError("Expected 'request' in template context.")

    if request.method == 'POST':
        form = MailChimpSubscriptionForm(request.POST)
    else:
        form = MailChimpSubscriptionForm()

    form.fields['mailchimp_subscription__name'].required = False
    del form.fields['mailchimp_subscription__name']

    # render form
    t = get_template('cubane/cms/newsletter_form.html')
    c = copy.copy(context)
    c['form'] = form
    return t.render(c)


@register.simple_tag(takes_context=True)
def cms_content(context, content, headline_transpose=0, image_shape=None):
    """
    Renders cms content.
    """
    if content is None:
        return ''

    # run through content pipeline
    cms = get_cms()
    request = context.get('request')
    content = cms.on_render_content_pipeline(request, content, context)

    # make sure that headline transpose is an integer we can work with
    try:
        headline_transpose = int(headline_transpose)
    except ValueError:
        headline_transpose = 0

    preview = value_or_default('cms_preview', context, False)

    # lazy-loaded images (not in preview mode)
    if not preview and 'cubane.media' in settings.INSTALLED_APPS:
        from cubane.media.templatetags.media_tags import render_image
        images = context.get('images', {})
        images = load_images_for_content(content, images)
        noscript = value_or_default('noscript', context, False)
        content = rewrite_images(content, images, render_image, noscript, image_shape)

    # page links
    if not preview:
        page_links = context.get('page_links', {})
        page_links = get_page_links_from_content(content, preview)
        content = rewrite_page_links(content, page_links)

    # transpose headlines
    if headline_transpose > 0:
        content = transpose_html_headlines(content, headline_transpose)

    # cleanup markup
    content = cleanup_html(content)

    # frontend editing
    return mark_safe(content)


def edit_or_compose(parser, token, shortcut=False):
    """
    Edit or compose template tags:
    following format:
    {% edit object.property %} or
    {% edit object 'property' %} or
    {% edit object 'property1, property2...' %}"
    """
    bits = token.split_contents()

    # usage
    tag_name = bits[0]
    if len(bits) < 2:
        raise template.TemplateSyntaxError(
            'Usage: %s <reference_or_instance> [<property_names>] [<help_text>] [class=<class-name>]' % tag_name
        )

    # extract keyword arguments
    args, kwargs = get_template_args(bits)

    # object/property reference
    reference = args[0]

    # optional argument: property names
    property_names = args[1] if len(args) >= 2 else None

    # optional argument: help text
    help_text = args[2] if len(args) >= 3 else None

    # optional class (kwarg)
    css_class = kwargs.get('class')

    # compose block tag?
    if tag_name == 'compose':
        nodelist = parser.parse(('endcompose',))
        parser.delete_first_token()
    elif tag_name == 'compose!':
        nodelist = parser.parse(('endcompose!',))
        parser.delete_first_token()
    else:
        nodelist = None

    # edit node
    return EditNode(reference, property_names, help_text, css_class, shortcut, nodelist)


@register.tag('edit')
def edit(parser, token):
    """
    Inject additional hidden information that is used for frontend editing:

    {% edit object.property %} or
    {% edit object 'property' %} or
    {% edit object 'property1, property2...' %}"
    """
    return edit_or_compose(parser, token)


@register.tag('edit!')
def edit_shortcut(parser, token):
    """
    Inject additional hidden information that is used for frontend editing:

    {% edit! object.property %} or
    {% edit! object 'property' %} or
    {% edit! object 'property1, property2...' %}"
    """
    return edit_or_compose(parser, token, shortcut=True)


@register.tag('compose')
def compose(parser, token):
    """
    Inject additional hidden information that is used for frontend editing by
    wrapping the containing content into a separate 'div' tag:

    {% compose object.property %}
        ...
    {% endcompose %}
    """
    return edit_or_compose(parser, token)


@register.tag('compose!')
def compose_shortcut(parser, token):
    """
    Inject additional hidden information that is used for frontend editing by
    wrapping the containing content into a separate 'div' tag:

    {% compose! object.property %}
        ...
    {% endcompose %}
    """
    return edit_or_compose(parser, token, shortcut=True)


@register.simple_tag()
def site_notification():
    """
    Render notification message if configured in settings.
    """
    if settings.CUBANE_SITE_NOTIFICATION:
        cms_settings = get_cms_settings()
        if cms_settings.notification_enabled and cms_settings.notification_text:
            return mark_safe('<div class="cubane-notification-container" style="background-color: #b94a48; color: white; font-family: Arial, Helvetica, sans-serif; padding: 15px 0; margin: 0; line-height: 1.25em; font-size: 16px;"><div class="cubane-notification" style="max-width: 1200px; margin: 0 auto; padding: 0;">%s</div></div>' % cms_settings.notification_text)

    return ''