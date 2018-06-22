# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.resources import get_resource
from cubane.lib.style import parse_style, inline_style, remove_attr, strip_style
from cubane.lib.image import prefix_ids
from bs4 import BeautifulSoup, element
import os
import re


RESOURCES = [
    'css/svgicons.css'
]


def get_svg_name_from_file(filename):
    """
    Return the name of the svg based on the file name of the svg asset,
    where _ and spaces are replaced with -, only accepting lowercase
    characters. The word 'icon' is removed. For example the filename
    'Background_Icon 2' becomes 'background-2', so ultimatly the svg id and
    css class becomes 'svgicon-background-2'.
    """
    name = os.path.splitext(os.path.basename(filename))[0].lower()
    name = re.sub(r'icon', ' ', name, flags=re.I)
    name = re.sub(r'[^\w\d]', '-', name)
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')
    return name


def get_svg_content(filename, svg_markup, with_style=False):
    """
    Return the actual svg content of the given svg markup and the viewbox
    declaration. Any external stylesheet is inlined.
    """
    xml = BeautifulSoup(svg_markup, 'xml')
    svg = xml.svg
    viewbox = svg.get('viewBox')

    # extract style
    style = ''
    for tag in svg.find_all('style'):
        style += '\n'.join(tag.contents) + '\n'
        tag.decompose()

    # inline style (if we retain it)
    node_style = parse_style(style)
    if with_style:
        inline_style(svg, node_style)
    elif node_style:
        node_style = strip_style(node_style)
        if node_style:
            inline_style(svg, node_style)
        else:
            remove_attr(svg, 'style')

    # remove class and other style attributes from all nodes
    remove_attr(svg, ['class'])

    # add unique prefix to ids
    prefix_ids(svg, '%s-' % filename)

    # if we have external style, remove inline style attributes
    if not with_style or style != '':
        remove_attr(svg, ['fill', 'stroke'])

    # build inner content for symbol
    content = ''
    for child in svg.children:
        if not isinstance(child, element.NavigableString):
            content += re.sub(r'\s+', ' ', re.sub(r'\s', ' ', unicode(child)))

    return viewbox, content


def get_combined_svg_for_resources(resources, with_style=False):
    """
    Combine the given list of resources.
    """
    markup = ''
    for filename in resources:
        try:
            file_content = get_resource(filename)
        except:
            raise ValueError('Unable to read svg icon file \'%s\'.' % filename)


        name = get_svg_name_from_file(filename)
        viewbox, svg_content = get_svg_content(name, file_content, with_style)
        markup += '<symbol id="svgicon-%(name)s" viewBox="%(viewbox)s">' % {
            'name': name,
            'viewbox': viewbox
        }
        markup += svg_content
        markup += '</symbol>'

    return markup


def get_combined_svg(resources, resources_with_style=[]):
    """
    Return the markup for one svg file based on all svg icon assets provided.
    Regular resources are cleaned from any style information, while style
    information for resources provided as the second argument are retained but
    inlined automatically.
    """
    markup = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" style="display: none;">'
    markup += get_combined_svg_for_resources(resources, with_style=False)
    markup += get_combined_svg_for_resources(resources_with_style, with_style=True)
    markup += '</svg>'
    return markup


def get_svgicons_filename(target, identifier=None):
    """
    Return the filename of the minified svg icon sheet file for the given revision
    of this application and the given target (bucket name).
    """
    if identifier and settings.TRACK_REVISION:
        return 'cubane.svgicons.%s.%s.svg' % (target, identifier)
    else:
        return 'cubane.svgicons.%s.svg' % target
