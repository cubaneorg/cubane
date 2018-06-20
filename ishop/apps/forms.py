# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.db.models import Q
from django.core import validators
from django.forms.utils import flatatt
from django.core.urlresolvers import reverse
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape, conditional_escape
from cubane.ishop.models import Variety
from cubane.media.templatetags.media_tags import render_image
from cubane.forms import BaseForm as CubaneBaseForm
from cubane.lib.widget import build_attrs
from itertools import chain


class VarietySelectWidget(forms.Widget):
    """
    Field widget for choosing a product variety.
    """
    allow_multiple_selected = False


    def __init__(self, request, variety, assignments, has_skus, attrs=None):
        self._request = request
        self._variety = variety
        self._assignments = assignments
        self._appended_content = False
        self._has_skus = has_skus
        super(VarietySelectWidget, self).__init__(attrs)


    def render(self, name, value, attrs=None, renderer=None):
        if value is None: value = ''

        # get shop
        from cubane.ishop.views import get_shop
        shop = get_shop()

        # class
        _class = attrs.get('class', '')
        _class += ' product-variety'
        if len(self._assignments) == 1:
            _class += ' single-option'
        if self._variety.sku:
            _class += ' sku'
        _class = _class.strip()
        attrs['class'] = _class

        # variety svg layer identifier
        if self._variety.layer:
            attrs['data-layer'] = self._variety.layer

        final_attrs = build_attrs(self.attrs, attrs, name=name)
        output = []

        if self._appended_content:
            output.append('<div class="input-append">')

        if self._variety.style == Variety.STYLE_SELECT:
            output.append('<select%s>' % flatatt(final_attrs))

            options = self.render_options(shop, self._assignments, [value])
            if options: output.append(options)
            output.append('</select>')
        else:
            with_image = self._variety.style == Variety.STYLE_LIST_WITH_IMAGE
            attrs['class'] += ' select-list' + (' select-list-image' if with_image else ' select-list-plain')
            final_attrs = build_attrs(self.attrs, attrs, name=name)

            output.append('<div%s">' % flatatt(final_attrs))
            options = self.render_list_options(shop, self._assignments, [value], with_image)
            if options: output.append(options)
            output.append('<input type="hidden" name="%s" value="%s">' % (
                final_attrs.get('name'),
                escape(value)
            ))
            output.append('</div>')

        if self._appended_content:
            output.append('<span class="add-on">' + self._appended_content + '</span>')
            output.append('</div>')

        return mark_safe(u'\n'.join(output))


    def render_options(self, shop, assignments, selected_options):
        selected_options = set(force_unicode(v) for v in selected_options)
        output = []
        for assignment in assignments:
            output.append(self.render_option(shop, selected_options, assignment))

        return u'\n'.join(output)


    def render_option(self, shop, selected_options, assignment):
        option = assignment.variety_option
        option_label = unicode(option)
        option_value = force_unicode(option.id)
        if option_value in selected_options:
            selected_html = ' selected="selected"'
            if not self.allow_multiple_selected:
                # only allow for a single selection.
                selected_options.remove(option_value)
        else:
            selected_html = ''

        escaped_option_value = escape(option_value)

        # default attributes
        attrs = {
            'class': 'variety-option',
            'data-value': escaped_option_value,
            'value': escaped_option_value
        }

        # svg layer color
        if option.color:
            attrs['data-layer-color'] = option.color

        # label options
        if option.text_label_placeholder:
            attrs['data-label-placeholder'] = option.text_label_placeholder
        if option.text_label_help:
            attrs['data-label-help-text'] = option.text_label_help

        # if we do not have SKUs, the display label may include the
        # price increase for the given option...
        if not self._has_skus:
            option_label = shop.get_variety_display_title(self._request, option_label, assignment)

        # render markup
        return u'<option %s%s>%s</option>' % (
            flatatt(attrs),
            selected_html,
            conditional_escape(force_unicode(option_label))
        )


    def render_list_options(self, shop, assignments, selected_options, with_image):
        selected_options = set(force_unicode(v) for v in selected_options)
        output = []
        for assignment in assignments:
            output.append(self.render_list_option(shop, selected_options, assignment, with_image))
        return u'\n'.join(output)


    def render_list_option(self, shop, selected_options, assignment, with_image):
        option = assignment.variety_option
        option_label = option.title
        option_value = force_unicode(option.id)
        classes = ['variety-option', 'select-list-option']

        if option_value in selected_options:
            classes.append('selected')
            if not self.allow_multiple_selected:
                selected_options.remove(option_value)

        inner_html = ""

        # render image if available
        if with_image and option.image != None:
            image = option.image

            inner_html = '<span class="variety-image" data-large-image-url="%s">%s</span>' % (
                image.url,
                render_image(image)
            )
            classes.append('with-image')
            if self._variety.style == Variety.STYLE_LIST:
                classes.append('with-image-preview')

        inner_html += '<span class="veriety-label">%s</span>' % conditional_escape(force_unicode(option_label))

        # default attr
        attrs = {
            'class': ' '.join(classes),
            'title': conditional_escape(force_unicode(option_label)),
            'data-value': escape(option_value),
        }

        # label options
        if option.text_label_placeholder:
            attrs['data-label-placeholder'] = option.text_label_placeholder
        if option.text_label_help:
            attrs['data-label-help-text'] = option.text_label_help

        # svg layer color
        if option.color:
            attrs['data-layer-color'] = option.color

            # inline css background color to express colour directly
            # if we are supporse to present an image but we do not have one...
            if not option.image:
                if with_image:
                    attrs['style'] = 'background-color: %s;' % option.color
                else:
                    inner_html = (
                        ('<span class="variety-color" style="background-color: %s;"></span>' % option.color) +
                        inner_html
                    )

        # render option button
        return '<button %s>%s</button>' % (
            flatatt(attrs),
            inner_html
        )


class VarietyField(forms.Field):
    """
    Form field for choosing a product variety.
    """
    def __init__(self, request, variety, assignments, has_skus, *args, **kwargs):
        self._variety = variety
        self._assignments = assignments
        self.widget = VarietySelectWidget(request, variety, assignments, has_skus)
        super(VarietyField, self).__init__(*args, **kwargs)


    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            return ''
        return smart_unicode(value)


    def validate(self, value):
        super(VarietyField, self).validate(value)
        if value and not self.valid_value(value):
            raise forms.ValidationError('Select a valid variety option. %s is not one of the available choices.' % value)


    def valid_value(self, value):
        for assignment in self._assignments:
            if value == smart_unicode(assignment.variety_option.id):
                return True
        return False
