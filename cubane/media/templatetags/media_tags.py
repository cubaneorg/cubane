# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import template
from django import forms
from django.template import Context
from cubane.lib.templatetags import value_or_literal, value_or_none, template_error
from cubane.lib.image import get_ext
from cubane.lib.template import get_template
import re
register = template.Library()


def get_inline_style_align(style):
    """
    Return the alignment style for an image based on the given inline style.
    """
    # no style information, no alignment
    if not style:
        return None

    # remove spaces from inline style
    style = re.sub(r'\s', '', style)

    # identify left/right alignment by looking for float:left or float:right
    m = re.search(r'float:(?P<align>left|right)', style, flags=re.IGNORECASE)
    if m:
        return m.groups('align')[0]

    # identify left/right alignment by looking for text-align:left
    # or text-align:right
    m = re.search(r'text-align:(?P<align>left|right)', style, flags=re.IGNORECASE)
    if m:
        return m.groups('align')[0]

    # identify center alignment by looking for margin-left:auto and
    # margin-right:auto
    margin_left = re.search(r'margin-left:auto', style, flags=re.IGNORECASE)
    margin_right = re.search(r'margin-right:auto', style, flags=re.IGNORECASE)
    if margin_left and margin_right:
        return 'center'

    # we do have inline style but we cannot determine any specific
    # alignment based on the inline style provided
    return None


def render_image(
    image,
    shape=None,
    width=None,
    style=None,
    lightbox=False,
    noscript=False,
    attr=None,
    inline=False
):
    """
    Render given image as a responsive image. For performance reasons, we do
    not go through the template system here...Ugly, but faster than running
    through the template system.
    """
    # inline style carried through tinymce for example
    if width:
        if not style:
            style = ''
        style += 'width:' + unicode(width) + 'px;'

    if shape is None:
        shape = settings.DEFAULT_IMAGE_SHAPE

    # determine alignment based on inline style, which then lets us annotate the
    # container in addition to the inline style, so we can override things
    # with custom css.
    align = get_inline_style_align(style)

    # if we use a lightbox, the outer container becomes an anker tag
    # with a reference to the full sizes image
    tag = 'a' if lightbox else 'span'
    a_href = (' href="' + image.default_url + '"') if lightbox else ''
    a_title = (' title="' + image.caption + '"') if lightbox else ''

    if noscript:
        return '<img src="' + image.default_url + '" alt="' + image.caption + '"' + \
        ((' style="width:' + unicode(width) + 'px"') if width else '') + ' title="' + image.caption + '">';
    else:
        ar = unicode(image.get_aspect_ratio_percent(shape))
        return \
            '<' + tag + ' class="lazy-load' + \
            (' custom-width' if width else '') + \
            (' lightbox' if lightbox else '') + \
            (' img-align-%s' % align if align else '') + '"' + \
            a_href + a_title + \
            ((' style="' + style + '"') if style else '') + \
            '><span class="lazy-load-shape-' + shape + '"' + \
            (' style="padding-bottom:' + ar + '%;"' if shape == 'original' else '') + '>' + \
            '<noscript' + \
            ' data-shape="' + shape + '"' + \
            ' data-path="' + image.get_image_url_component() + '"' + \
            ' data-blank="' + ('1' if image.is_blank else '0') + '"' + \
            ' data-sizes="' + ('|'.join(image.get_available_image_sizes())) + '"' + \
            ' data-alt="' + image.caption + '"' + \
            ' data-title="' + image.caption + '"' + \
            ' data-svg="' + ('1' if image.is_svg else '0') + '"' + \
            ' data-inline="' + ('1' if inline else '0') + '"' + \
            ((' data-attr="' + attr + '"') if attr else '') + \
            '><img src="' + \
            image.default_url + '" alt="' + image.caption + '"' + \
            ' title="' + image.caption + '"' + \
            ((' style="width:' + unicode(width) + 'px"') if width else '') + \
            '></noscript></span></' + tag + '>'


def render_background_image_attr(
    image,
    shape=settings.DEFAULT_IMAGE_SHAPE,
    height=None,
    attr=None
):
    """
    Render background image attributes for rendering the given image as a
    background image.
    """
    if image:
        return \
            ' data-background-image' + \
            ' data-shape="' + shape + '"' + \
            ' data-path="' + image.get_image_url_component() + '"' + \
            ' data-blank="' + ('1' if image.is_blank else '0') + '"' + \
            ' data-sizes="' + ('|'.join(image.get_available_image_sizes())) + '"' + \
            ' data-svg="' + ('1' if image.is_svg else '0') + '"' + \
            ((' data-attr="' + attr + '"') if attr else '') + \
            (' data-background-image-height-ar="%s"' % (image.get_aspect_ratio(shape)) if height else '')
    else:
        return ''


def render_svg_image(image, shape, clippath):
    ar = unicode(image.get_aspect_ratio_percent(shape))
    return \
        '<span class="lazy-load lazy-load-svg">' + \
        '<span class="lazy-load-shape-' + shape + '"' + \
        (' style="padding-bottom:' + ar + '%;"' if shape == 'original' else '') + '>' + \
        '<noscript ' + \
        ' data-shape="' + shape + '"' + \
        ' data-path="' + image.get_image_url_component() + '"' + \
        ' data-blank="' + ('1' if image.is_blank else '0') + '"' + \
        ' data-sizes="' + ('|'.join(image.get_available_image_sizes())) + '"' + \
        ' data-alt="' + image.caption + '"' + \
        ' data-title="' + image.caption + '"' + \
        ' data-ar="' + ar + '"' + \
        ((' data-clippath="' + clippath + '"') if clippath else '') + \
        '><img src="' + \
        image.default_url + '" alt="' + image.caption + '"' + \
        ' title="' + image.caption + '"></noscript></span></span>'


class ImageNode(template.Node):
    def __init__(self, image, shape, noscript, attr, inline):
        self.image = image
        self.shape = shape
        self.noscript = noscript
        self.attr = attr
        self.inline = inline


    def render(self, context):
        image = value_or_none(self.image, context)
        shape = value_or_literal(self.shape, context)

        # additional attributes
        if self.attr:
            attr = value_or_literal(self.attr, context)
        else:
            attr = None

        return self.render_image(image, shape, self.noscript, attr, self.inline)


    def render_image(self, image, shape, noscript=False, attr=None, inline=False):
        if shape:
            if shape not in settings.IMAGE_SHAPES and \
               shape not in settings.IMAGE_ART_DIRECTION and \
               shape != 'original':
                # show error within template that we do not know the shape
                return template_error('Shape \'%s\' not defined.' % shape)
        else:
            shape = 'original'

        if image:
            return render_image(
                image,
                shape,
                noscript=noscript,
                attr=attr,
                inline=inline
            )
        else:
            return ''


class BackgroundImageNode(template.Node):
    def __init__(self, image, shape, height, attr):
        self.image = image
        self.shape = shape
        self.height = height
        self.attr = attr


    def render(self, context):
        image = value_or_none(self.image, context)
        shape = value_or_literal(self.shape, context)

        # additional attributes
        if self.attr:
            attr = value_or_literal(self.attr, context)
        else:
            attr = None

        if shape:
            if shape not in settings.IMAGE_SHAPES and shape != 'original':
                return template_error("Shape '%s' not defined." % shape)
        else:
            shape = 'original'

        return render_background_image_attr(image, shape, self.height, attr)


class SvgImageNode(template.Node):
    def __init__(self, image, shape, clippath):
        self.image = image
        self.shape = shape
        self.clippath = clippath


    def render(self, context):
        image = value_or_none(self.image, context)
        shape = value_or_literal(self.shape, context)
        clippath = value_or_literal(self.clippath, context)

        if shape:
            if shape not in settings.IMAGE_SHAPES and shape != 'original':
                return template_error("Shape '%s' not defined." % shape)
        else:
            shape = 'original'

        return render_svg_image(image, shape, clippath)


def parse_image_tag(parser, token, inline):
    """
    Parse image or inline_image tag and return an ImageNode with the
    corresponding options set.
    """
    bits = token.split_contents()

    if len(bits) not in [2, 3, 4, 5]:
        raise template.TemplateSyntaxError("'%s' takes max. three arguments: <image> [<shape>] [<noscript>, <attr>]" % bits[0])

    image = bits[1]

    if len(bits) > 2:
        shape = bits[2]
    else:
        shape = settings.DEFAULT_IMAGE_SHAPE

    attr = ''
    noscript = False
    if len(bits) > 3:
        if bits[3] in ['True', 'False']:
            noscript = bits[3] == 'True'
            if len(bits) > 4:
                attr = bits[4]
        else:
            attr = bits[3]

    return ImageNode(image, shape, noscript, attr, inline)


@register.tag('image')
def image(parser, token):
    """
    Renders a responsive image.

    Syntax: {% image <image> [<shape>] [<noscript>, <attr>] %}
    """
    return parse_image_tag(parser, token, inline=False)


@register.tag('inline_image')
def inline_image(parser, token):
    """
    Renders a responsive image by inlining the image data (svg only).

    Syntax: {% image <image> [<shape>] [<noscript>, <attr>] %}
    """
    return parse_image_tag(parser, token, inline=True)


@register.simple_tag
def media_api_url(media, size=None, attr_url=None):
    """
    Return the full url to the given media asset for the given shape and size
    by using the media api. Optionally, any given image customisations are
    applied.
    """
    if size is None:
        size = settings.DEFAULT_IMAGE_SIZE

    return media.get_image_url(size, 'original', attr_url)


@register.tag('background_image')
def background_image_attr(parser, token):
    """
    Renders a list of data attributes for supporting a responsive background image.
    """
    bits = token.split_contents()

    if len(bits) not in [2, 3, 4, 5]:
        raise template.TemplateSyntaxError("'%s' takes max. two arguments: <background_image> [<shape>] [<height>, <attr>]" % bits[0])

    image = bits[1]

    if len(bits) > 2:
        shape = bits[2]
    else:
        shape = settings.DEFAULT_IMAGE_SHAPE

    attr = ''
    height_ar = False
    if len(bits) > 3:
        if bits[3] in ['True', 'False']:
            height_ar = bits[3] == 'True'
            if len(bits) > 4:
                attr = bits[4]
        else:
            attr = bits[3]

    return BackgroundImageNode(image, shape, height_ar, attr)


@register.tag('svg_image')
def svg_image(parser, token):
    """
    Renders a responsive svg image with an optional clip path.
    """
    bits = token.split_contents()

    if len(bits) not in [2, 3, 4]:
        raise template.TemplateSyntaxError("'%s' takes max. two arguments: <svg_image> [<shape>] [<clippath>]" % bits[0])

    image = bits[1]

    if len(bits) > 2:
        shape = bits[2]
    else:
        shape = settings.DEFAULT_IMAGE_SHAPE

    if len(bits) > 3:
        clippath = bits[3]
    else:
        clippath = None

    return SvgImageNode(image, shape, clippath)