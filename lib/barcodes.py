# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
import barcode
import re


MINIMUM_DIGITS = 6


class BarcodeError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


    def __unicode__(self):
        return self.msg


def get_barcode_systems():
    """
    Return a list of barcode systems that are supported.
    """
    return barcode.PROVIDED_BARCODES


def get_barcode_choices():
    """
    Return a list of choices for all supported barcode systems.
    """
    return [(c, c.upper()) for c in get_barcode_systems()]


def verify_barcode(barcode_system, barcode_digits):
    """
    Raises BarcodeError if the given barcode of the given system is invalid.
    Returns the full barcode as a sequence of digits (string) without any
    formatting characters.
    """
    # pick default barcode system from settings, if no barcode system
    # has been defined...
    if barcode_system is None:
        if 'cubane.cms' in settings.INSTALLED_APPS:
            from cubane.cms.views import get_cms_settings
            cms_settings = get_cms_settings()
            barcode_system = cms_settings.barcode_system

    # remove invalid digits from barcode to begin with
    if barcode_digits is not None:
        barcode_digits = re.sub(r'[^\d]', '', barcode_digits)

    # get decoder based on system
    try:
        system = barcode.get_barcode_class(barcode_system)
    except barcode.errors.BarcodeNotFoundError, e:
        raise BarcodeError(
            'The barcode system \'%s\' is not known or invalid.' % barcode_system
        )

    # reject barcodes with less than 6 digits from the outset.
    # the current implementation of barcodes may crash with too few
    # digists...
    if barcode_digits is None or len(barcode_digits) < MINIMUM_DIGITS:
        raise BarcodeError(
            'The barcode must have at least %d digits.' % MINIMUM_DIGITS
        )

    # decode given barcode
    try:
        bc = system(barcode_digits)
        full_barcode = bc.get_fullcode()

        # if we did not provide a check digit, then raise an error
        plain_barcode = re.sub(r'[^\d]', '', barcode_digits).strip()
        if full_barcode != plain_barcode:
            diff = ''
            for i, digit in enumerate(full_barcode):
                if i >= len(plain_barcode) or digit != plain_barcode[i]:
                    diff += digit
                else:
                    diff += '_'
            diff = re.sub(r'_{2,}', '_', diff)
            diff = diff.strip('_')

            raise BarcodeError(
                'The barcode checksum is invalid. Missing digits: %s?' % diff
            )

        return full_barcode
    except barcode.errors.BarcodeError, e:
        raise BarcodeError(e.msg)


def render_barcode_image(barcode_system, barcode_digits):
    """
    Return an SVG image representation of the given barcode in the given
    barcode system.
    """
    try:
        system = barcode.get_barcode_class(barcode_system)
        bc = system(barcode_digits)
        return bc.render()
    except:
        return ''