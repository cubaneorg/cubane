# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.template.defaultfilters import slugify
from cubane.lib.libjson import decode_json
from datetime import datetime
from requests.exceptions import ConnectionError
import requests
import sys


class FontDescriptor(object):
    """
    Describes any given font containing all information that is required by
    the system in order to use custom web fonts.
    """
    def __init__(self, font_name, family, category, variants, version, mtime):
        self.backend = None
        self.font_name = font_name
        self.family = family
        self.category = category
        self.variants = variants
        self.version = version
        self.mtime = mtime


class FontBackendBase(object):
    """
    Base class for font backend.
    """
    def get_font(self, font_name):
        """
        Download a font with the given name or return None if the font is
        not available by this backend.
        """
        raise NotImplementedError('Override get_font() method to implement the font downloading mechanism.')


class GoogleFontsBackend(FontBackendBase):
    """
    Uses google web-fonts helper API to download google web fonts. Please see
    https://google-webfonts-helper.herokuapp.com/.
    """
    def get_font(self, font_name):
        """
        Download the given font via the google web font helper api.
        """
        json = self._get_font_by_name(font_name)
        return self._get_descriptor(font_name, json)


    def _get_font_by_name(self, font_name):
        """
        Return a font descriptor record for the given font name or None.
        """
        url = 'https://google-webfonts-helper.herokuapp.com/api/fonts/%s?subsets=latin' % \
            slugify(font_name)

        try:
            response = requests.get(url, timeout=3000)
            if response == None: return None
            if response.status_code != 200: return None
            return decode_json(response.content)
        except ConnectionError:
            # simply fail in debug mode
            if settings.DEBUG:
                raise

            # present error message otherwise and return None
            if not settings.TEST: # pragma: no cover
                sys.stderr.write(
                    ('ERROR: Connection error while trying to load font ' + \
                     'information for \'%s\'.\n') % font_name
                )
            return None


    def _get_descriptor(self, font_name, meta_data):
        """
        Return a font descriptor for the given google font meta data.
        """
        if meta_data is None:
            return None

        variants = meta_data.get('variants')
        for variant in variants:
            variant['fontFamily'] = variant.get('fontFamily').strip('\'')

        return FontDescriptor(
            font_name=font_name,
            family=meta_data.get('family'),
            category=meta_data.get('category'),
            variants=variants,
            version=meta_data.get('version'),
            mtime=datetime.strptime(meta_data.get('lastModified'), '%Y-%m-%d')
        )