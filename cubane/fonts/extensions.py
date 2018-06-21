# coding=UTF-8
from __future__ import unicode_literals
from cubane.fonts.fontcache import FontCache


class ResourceManagerExtension(object):
    def process_resource_entry(self, target, ext, css_media, prefix, resource):
        """
        Process the given (raw) resource.
        """
        prefix, resource = super(ResourceManagerExtension, self).process_resource_entry(target, ext, css_media, prefix, resource)

        # if we are rendering css and the resource is a font,
        # then substitude it with its corresponding font css
        # file
        if ext == '.css' and prefix == 'font':
            font_declaration = FontCache.get_font_declaration(resource)
            if font_declaration is not None:
                resource = FontCache.get_font_css_url(
                    font_declaration.font_name
                )
                prefix = 'screen'

        return prefix, resource