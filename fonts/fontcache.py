# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.template.defaultfilters import slugify
from cubane.lib.module import get_class_from_string
from cubane.lib.excerpt import excerpt_from_text
from cubane.lib.file import file_put_contents
from cubane.lib.file import folder_delete_content
from cubane.lib.file import file_set_mtime
from cubane.lib.verbose import out
from cubane.lib.filelock import FileLock
from cubane.lib.resources import (
    get_resource_targets,
    get_resources
)
from cubane.fonts.declaration import FontDeclaration
from requests.exceptions import ConnectionError
import re
import os
import requests
import sys


class FontCache(object):
    """
    Manages the download and caching of font resources for debug and
    production.
    """
    FONT_TYPES = ['woff2', 'woff']


    @classmethod
    def get_unique_font_name(cls, font_name):
        """
        Return a unique font name based on the given presentation name
        of the font.
        """
        return slugify(font_name)


    @classmethod
    def get_font_css_url(cls, font_name):
        """
        Return the url path to the corresponding css file that declares the
        font with the given name.
        """
        name = FontCache.get_unique_font_name(font_name)
        return '/media/fonts/%(name)s/%(name)s.css' % {
            'name': name
        }


    @classmethod
    def get_font_declaration(cls, declaration):
        """
        Return the font name and variant information from the given font
        declaration as it would be defined for RESOURCES.
        Format:
          <font_name> [:<variant-selector>,...]
        Examples:
          Open Sans :300,300i
          Abel :400
        """
        return FontDeclaration.parse(declaration)


    def clear(self, verbose=False):
        """
        Remove all downloaded and cached font resources from the font cache.
        """
        self._access_lock(self._clear, verbose)


    def update(self, verbose=False):
        """
        Update font cache and download missing font resources.
        """
        self._access_lock(self._update, verbose)


    def get_used_font_declarations(self):
        """
        Return a unique list of font declarations that are currently used by the
        system and need to be cached.
        """
        font_declarations = {}
        targets = get_resource_targets()
        for target in targets:
            font_resources = get_resources(
                target,
                css_media='font',
                data_only=True
            )

            for font_resource in font_resources:
                font_declaration = FontCache.get_font_declaration(font_resource)
                font_name = font_declaration.font_name
                if font_name in font_declarations:
                    # font already listed. Join varients
                    font_declarations[font_name].join_with(font_declaration)
                else:
                    # new font
                    font_declarations[font_name] = font_declaration

        return sorted(
            font_declarations.values(),
            key=lambda decl: decl.font_name
        )


    def is_font_cached(self, font_name):
        """
        Return True, if the given font has already been cached; otherwise False.
        """
        name = FontCache.get_unique_font_name(font_name)
        path = os.path.join(settings.CUBANE_FONT_ROOT, name)
        return os.path.isdir(path)


    def get_backends(self):
        """
        Return a list of all registered font backends that are used to acquire
        fonts.
        """
        if not hasattr(self, '_backends'):
            self._backends = []

            if isinstance(settings.CUBANE_FONT_BACKENDS, list):
                for class_name in settings.CUBANE_FONT_BACKENDS:
                    _class = get_class_from_string(class_name)
                    backend = _class()
                    self._backends.append(backend)

        return self._backends


    def _get_lock(self):
        """
        Return a file lock that is unique based on the domain name for this
        website for the purpose of accessing the font cache.
        """
        return FileLock.temp(settings.DOMAIN_NAME, 'fonts')


    def _access_lock(self, func, verbose=False):
        """
        Execute the given func if we can acquire the access lock, if not we do
        nothing.
        """
        lock = self._get_lock()
        if not lock.acquire(wait=False): # pragma: no cover
            return

        try:
            func(verbose)
        finally:
            lock.release()


    def _clear(self, verbose=False):
        """
        Remove all downloaded and cached font resources from the font cache.
        """
        out('Clearing font cache...Please Wait...', verbose=verbose)

        if os.path.isdir(settings.CUBANE_FONT_ROOT):
            folder_delete_content(settings.CUBANE_FONT_ROOT)

        out('Font cache cleared.', verbose=verbose)


    def _update(self, verbose=False):
        """
        Update font cache and download missing font resources.
        """
        out('Updating font cache...Please Wait...', verbose=verbose)

        # get list of used fonts.
        font_declarations = self.get_used_font_declarations()
        if not font_declarations:
            return

        # get available backends and raise error, if we do not have at least
        # one font backend available to us...
        backends = self.get_backends()
        if not backends:
            raise ValueError(
                'Unable to update fonts because no font backend is ' + \
                'available. Please make sure that a list of font backends ' + \
                'is defined as \'CUBANE_FONT_BACKENDS\' in settings and ' + \
                'that each module path is correct and the module ' + \
                'can be imported.'
            )

        for font_declaration in font_declarations:
            if not self.is_font_cached(font_declaration.font_name):
                if self._cache_font(backends, font_declaration):
                    status = 'UPDATED'
                else:
                    status = 'NOT FOUND'

                    # raise error on debug, so the developer will instantly
                    # notice that a font could not be found, perhabs because
                    # of a spelling error...
                    if settings.DEBUG:
                        raise ValueError(
                            ('The font \'%s\' could not be found by any ' + \
                             'of the installed font backends.') %
                                 font_declaration.font_name
                        )
            else:
                status = 'CACHED'

            if not settings.TEST and verbose: # pragma: no cover
                print '%-35s  [%s]' % (
                    excerpt_from_text(
                        font_declaration.font_name,
                        length=32,
                        prefix=True
                    ),
                    status
                )


    def _cache_font(self, backends, font_declaration):
        """
        Download the given font to the font cache.
        """
        for backend in backends:
            descriptor = backend.get_font(font_declaration.font_name)
            if descriptor is not None:
                descriptor.backend = backend
                if self._store_font_data(font_declaration, descriptor):
                    return True
        return False


    def _download_font_file(self, url, path, mtime):
        """
        Download the given font file to the given local path.
        """
        # download file
        try:
            response = requests.get(url, timeout=3000)
            if response == None: return False
            if response.status_code != 200: return False
        except ConnectionError: # pragma: no cover
            # hard fail in debug
            if settings.DEBUG:
                raise

            return False

        # write file to disk
        with open(path, 'wb') as f:
            f.write(response.content)

        # update file's modification time
        file_set_mtime(path, mtime)

        return True


    def _store_font_data(self, font_declaration, descriptor):
        """
        Store the given font data within the store cache.
        """
        # get base path for font
        font_name = descriptor.font_name
        name = FontCache.get_unique_font_name(font_name)
        path = os.path.join(settings.CUBANE_FONT_ROOT, name)
        version = descriptor.version
        mtime = descriptor.mtime

        # create base path if it does not exist yet
        if not os.path.isdir(settings.CUBANE_FONT_ROOT):
            os.makedirs(settings.CUBANE_FONT_ROOT)

        # create folder if not exists yet
        if not os.path.isdir(path):
            os.mkdir(path)

        # download font files for each varient that has been declared and is
        # supported by the font and generate css font declaration code...
        css = []
        for variant in descriptor.variants:
            # extract key information from variant
            family = variant.get('fontFamily')
            font_weight = variant.get('fontWeight')
            font_style = variant.get('fontStyle')
            local = variant.get('local')

            # skip if not declared
            if not font_declaration.supports_variant_by_components(font_weight, font_style):
                continue

            # determine list of available font files, some may not be available
            # due to download errors...
            imports = []
            for ext in self.FONT_TYPES:
                filename = '%(name)s-%(version)s-%(weight)s-%(style)s.%(ext)s' % {
                    'name': name,
                    'version': version,
                    'weight': font_weight,
                    'style': font_style,
                    'ext': ext
                }
                font_path = os.path.join(path, filename)
                url = variant.get(ext)
                if self._download_font_file(url, font_path, mtime):
                    imports.append(
                        (
                            ext,
                            '/media/fonts/%s/%s' % (name, filename)
                        )
                    )
                else:
                    # unable to download file
                    if not settings.TEST: # pragma: no cover
                        sys.stderr.write(
                            ('ERROR: Unable to download font ' + \
                             'file from \'%s\'.\n') % url
                        )

            # generate font-declaration (css) for this variant...
            if len(imports) > 0:
                css.extend([
                    '/* %s %s %s latin */' % (font_name, font_weight, font_style),
                    '@font-face {',
                    '    font-family: \'%s\';' % family,
                    '    font-style: %s;' % font_style,
                    '    font-weight: %s;' % font_weight,
                    '    src: ' + ', '.join([
                        'local(\'%s\')' % local_name
                        for local_name
                        in local
                    ]) + ',',
                    ',\n'.join([
                        '         url(\'%s\') format(\'%s\')' % (url, ext)
                        for ext, url
                        in imports
                    ]) + ';',
                    '}\n'
                ])

        # write css file for the entire font, covering all variants...
        if len(css) > 0:
            css_filename = os.path.join(path, '%s.css' % name)
            file_put_contents(css_filename, '\n'.join(css))
            return True
        else:
            # if we failed, remove font folder and skip this font
            if os.path.isdir(path):
                folder_delete_content(path)
                os.rmdir(path)

            return False