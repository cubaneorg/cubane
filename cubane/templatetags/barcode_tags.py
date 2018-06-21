from __future__ import unicode_literals
from django import template
from django.utils.safestring import mark_safe
from cubane.lib.barcodes import render_barcode_image
register = template.Library()


@register.simple_tag()
def barcode_image(barcode_system, barcode_digits):
    return mark_safe(render_barcode_image(barcode_system, barcode_digits))