# coding=UTF-8
from __future__ import unicode_literals
from bs4 import BeautifulSoup, element
import re


def parse_style(style):
    """
    Parse the given stylesheet and return style information by selector.
    """
    selectors = {}
    for selector, styleblock in re.findall(r'(?P<selector>.*?){(?P<style>.*?)}', style):
        selector = selector.strip()
        styleblock = styleblock.strip()
        styleblock = re.sub(r'\r\n\t', ' ', styleblock)
        if selector not in selectors:
            selectors[selector] = styleblock
        else:
            selectors[selector] += styleblock

    return selectors


def strip_style(style):
    """
    Strip given style down to the minimal set of style rules that we would
    retain in case we wanted to remove style. Such style rules are for example
    fill: none.
    """
    result = {}
    for k, v in style.items():
        rules = filter(lambda rule: rule, [rule.strip() for rule in v.split(';')])
        for rule in rules:
            attr, value = [term.strip() for term in rule.split(':')]
            if not (attr == 'fill' and value == 'none'):
                continue

            if k not in result:
                result[k] = ''

            result[k] += '%s:%s;' % (attr, value)

    return result


def inline_style(node, style, strip=False):
    """
    Apply given external stylesheet as inline style for the given
    node and all its children where applicable.
    """
    if isinstance(node, element.NavigableString):
        return

    # extract classes
    try:
        classes = node['class']
    except KeyError:
        classes = []

    # split classes
    if isinstance(classes, basestring):
        classes = [c.strip() for c in classes.split(' ')]

    # collect matching style blocks by class names
    blocks = []
    for cl in classes:
        try:
            blocks.append(style['.%s' % cl])
        except KeyError:
            pass

    # apply style (if found)
    if len(blocks) > 0:
        node['style'] = ' '.join(blocks)

    # process children
    for child in node.children:
        inline_style(child, style)


def parse_inline_style(inline_style):
    """
    Parse the given inline stylesheet and return a dictionary that maps
    css attributes to css expressions.
    """
    style = {}

    if inline_style:
        parts = inline_style.split(';')
        for part in parts:
            try:
                attr, value = part.split(':')
            except:
                continue

            style[attr.strip()] = value.strip()

    return style


def encode_inline_style(inline_style_dict):
    """
    Encode given inline style dictionary as inline style string.
    """
    if isinstance(inline_style_dict, dict):
        return ';'.join([
            '%s:%s' % (attr.strip(), value.strip())
            for attr, value
            in inline_style_dict.items()
        ])
    else:
        return ''


def remove_attr(node, attrnames):
    """
    Remove given attribute name from the given xml node and all its children.
    """
    if not isinstance(attrnames, list):
        attrnames = [attrnames]

    if isinstance(node, element.NavigableString):
        return

    # remove attributes from node
    for attrname in attrnames:
        del node[attrname]

    # process children
    for child in node.children:
        remove_attr(child, attrnames)