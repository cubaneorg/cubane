# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import template
from django.core.urlresolvers import get_resolver
from django.utils.safestring import mark_safe
from django.utils.html import format_html, escape
from django.template import Context
from cubane.lib.resources import get_resources, get_resource
from cubane.lib.resources import get_minified_filename
from cubane.lib.resources import load_resource_version_identifier
from cubane.lib.resources import get_resource_target_definition
from cubane.lib.resources import is_external_resource
from cubane.lib.url import url_join, get_url_patterns
from cubane.lib.libjson import to_json
from cubane.lib.templatetags import literal, value_or_literal
from cubane.lib.template import get_template


register = template.Library()


def get_resources_markup(target, ext, css_media=None, is_async=None, inline=False, additional_data=None):
    """
    Return the markup to include resources.
    """
    return ResourcesNode('target', ext, 'css_media', 'is_async', inline, 'additional_data').render({
        'target': target,
        'css_media': css_media,
        'is_async': is_async,
        'additional_data': additional_data
    })


class ResourcesNode(template.Node):
    def __init__(self, target, ext, css_media=None, is_async=None, inline=False, additional_data=None):
        self.target = target
        self.ext = ext
        self.css_media = css_media
        self.inline = inline
        self.is_async = is_async
        self.additional_data = additional_data
        self._identifier = None
        self._identifier_loaded = False


    def get_identifier(self):
        """
        Return the current resource identifier for the current version for
        all assets.
        """
        return load_resource_version_identifier()


    def include(self, url, css_media=None, is_async=False, additional_data=None):
        """
        Generate include statement for including the given resource url.
        """
        # local resource (not media or external)?
        if not url.startswith('/media/') and not is_external_resource(url):
            url = url_join(settings.STATIC_URL, url)

        if self.ext == 'css':
            if not css_media:
                css_media = 'screen'

            if not is_async or not settings.MINIFY_RESOURCES:
                return format_html(
                    '<link href="{}" rel="stylesheet" media="{}"/>\n',
                    url,
                    css_media
                )
            else:
                return mark_safe(
                    '<script>' + \
                    '(function(){' + \
                        'var appendStylesheet = function(){'+ \
                            'var stylesheet = document.createElement("link");' + \
                            'stylesheet.href = "%s";' % escape(url) + \
                            'stylesheet.rel = "stylesheet";' + \
                            'stylesheet.type = "text/css";' + \
                            'document.getElementsByTagName("head")[0].appendChild(stylesheet);' + \
                        '};' + \
                        'if (document.addEventListener) {' + \
                            'document.addEventListener("readystatechange", function() {' + \
                                'if (document.readyState === \'complete\') {' + \
                                    'appendStylesheet();'+ \
                                '}'+ \
                            '});'+ \
                        '} else { appendStylesheet(); }' + \
                    '})();' + \
                    '</script>' + \
                    '<noscript><link rel="stylesheet" href="%s" media="screen"></noscript>' % escape(url)
                )
        else:
            _async = ' async' if settings.MINIFY_RESOURCES and is_async else ''
            return '<script%s src="%s"%s></script>\n' % (_async, escape(url), self.render_additional_data(additional_data))


    def render_additional_data(self, additional_data):
        if additional_data is None:
            additional_data = ''
        else:
            additional_data = ' ' + additional_data
        return additional_data


    def inline_include(self, content, additional_data=None, css_media=None):
        """
        Generate inline resource statement for embedding the given content
        within the page.
        """
        from cubane.lib.serve import serve_static_with_context
        content = serve_static_with_context(content)
        if self.ext == 'css':
            if not css_media:
                css_media = 'screen'

            return '<style%s%s>%s</style>\n' % (
                self.render_additional_data(additional_data),
                ' media="%s"' % css_media if css_media else '',
                mark_safe(content)
            )
        else:
            return '<script%s>%s</script>\n' % (self.render_additional_data(additional_data), mark_safe(content))


    def render(self, context):
        """
        Render resource tag.
        """
        target = value_or_literal(self.target, context)
        css_media = value_or_literal(self.css_media, context)

        # async
        if self.is_async is not None:
            is_async = value_or_literal(self.is_async, context)
        elif self.ext == 'js':
            is_async = True
        else:
            is_async = False

        # additonal_data
        if self.additional_data is not None:
            additional_data = value_or_literal(self.additional_data, context)
        else:
            additional_data = None

        if css_media and css_media not in settings.CSS_MEDIA:
            raise template.TemplateSyntaxError(
                ("'resources' only accepts the following values for css_media argument: " +
                 "%s."
                ) % settings.CSS_MEDIA
            )

        # if target is not defined, just ignore it.
        if target not in get_resource_target_definition():
            return ''

        if self.inline:
            if not settings.MINIFY_RESOURCES:
                resources = get_resources(target, self.ext)
                content = '\n'.join([get_resource(url) for url in resources])
            else:
                content = get_resource(
                    get_minified_filename(
                        target,
                        self.ext,
                        'screen' if self.ext == 'css' else None,
                        self.get_identifier()
                    )
                )

            return self.inline_include(content, additional_data, css_media)
        else:
            if not settings.MINIFY_RESOURCES:
                resources = get_resources(target, self.ext, css_media)
                return ''.join([
                    self.include(url, css_media, is_async, additional_data) for url in resources
                ])
            else:
                return self.include(
                    get_minified_filename(
                        target,
                        self.ext,
                        css_media,
                        self.get_identifier()
                    ), css_media, is_async, additional_data
                )


class JavascriptUrlsNode(template.Node):
    def render(self, context):
        json = to_json(get_url_patterns(get_resolver(None).url_patterns))
        script = \
            "<script>" + \
            "(function(g){" + \
            "if(!('cubane' in g))g.cubane = {};" + \
            "if(!('urls' in g.cubane))g.cubane.urls = {};" + \
            "g.cubane.urls.patterns = " + json + ";" + \
            "}(this));" + \
            "</script>"

        return mark_safe(script);


@register.tag('resources')
def resources(parser, token):
    """
    Renders a list of include statements for css or javascript resources in
    DEBUG mode. In PRODUCTION, all resources are compiled and minified into
    one resource file.

    Syntax: {% resources <target> <'css' | 'js'> [<css_media> | <async>] [<additional_data>]  %}
    """
    bits = token.split_contents()

    if len(bits) > 5:
        raise template.TemplateSyntaxError(
            ("'%s' takes at most four argument " +
             "<target> <'css' | 'js'> [<css_media> | <async>] [<additional_data>]"
            ) % bits[0]
        )

    target = bits[1]
    ext = literal(bits[0], 'extension', bits[2]).lower()
    if ext not in ('css', 'js'):
        raise template.TemplateSyntaxError(
            "'%s' takes two argument <target> <css' | 'js'>" % bits[0]
        )

    if len(bits) > 3:
        css_media = bits[3]
    else:
        css_media = None

    is_async = None
    additional_data = None
    if ext == 'js' and css_media:
        is_async = css_media
        css_media = None

        if len(bits) > 4:
            additional_data = bits[4]
    elif ext == 'css':
        if len(bits) > 4:
            is_async = bits[4]

        if len(bits) > 5:
            additional_data = bits[4]

    return ResourcesNode(target, ext, css_media, is_async, additional_data=additional_data)


@register.tag('inline_resources')
def inline_resources(parser, token):
    """
    Renders the actual content of a list of css or javascript resources in
    DEBUG mode. In PRODUCTION, all resources are compiled and minified into
    one resource file which content is then inlined into the document.

    Syntax: {% inline_resources <target> <'css' | 'js'> [<additional_data>] %}
    """
    bits = token.split_contents()

    if len(bits) not in [3, 4]:
        raise template.TemplateSyntaxError("'%s' takes three or four arugments <target> <'css' | 'js'> [<additional_data>]" % bits[0])

    target = bits[1]
    ext = literal(bits[0], 'extension', bits[2]).lower()
    if ext not in ('css', 'js'):
        raise template.TemplateSyntaxError("'%s' takes three or four arugments <target> <'css' | 'js'>" % bits[0])

    additional_data = None
    if len(bits) == 4:
        additional_data = bits[3]

    # inline in PRODUCTION, DO NOT inline in DEBUG mode...
    return ResourcesNode(target, ext, inline=not settings.DEBUG, additional_data=additional_data)


@register.tag('javascript_urls')
def javascript_urls(parser, token):
    """
    Renders a script tag that injects all django url patterns in order to make
    them available to javascript, so that we can resolve url patterns at runtime
    through javascript if required.

    Syntax: {% javascript_urls %}
    """
    bits = token.split_contents()
    if len(bits) != 1:
        raise template.TemplateSyntaxError("'%s' takes no arguments." % bits[0])

    return JavascriptUrlsNode()


@register.simple_tag()
def favicons():
    """
    Renders the favicon.
    Usage {% favicons %}
    """
    return get_template('cubane/favicons.html').render({
        'STATIC_URL': settings.STATIC_URL
    })
