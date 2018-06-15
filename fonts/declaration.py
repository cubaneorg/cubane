# coding=UTF-8
from __future__ import unicode_literals
import re


class FontVariant(object):
    """
    Encapsulates a specific font variation based on font weight and style.
    """
    def __init__(self, weight, style):
        self.weight = weight
        self.style = style


    def matches(self, weight, style):
        """
        Return True, if this font variant matches the given weight and style.
        """
        return (
            self.weight == weight and
            self.style == style
        )


    def equals_to(self, variant):
        """
        Returns True, if this font variant equals to the given variant.
        """
        return self.matches(variant.weight, variant.style)


    def __unicode__(self):
        """
        Return display representation of this font variant.
        """
        return '%s%s' % (self.weight, 'i' if self.style == 'italic' else '')


class FontDeclaration(object):
    """
    Captures a font declaration in terms of its name and weights and styles
    that should be loaded.
    """
    WEIGHTS = ['100', '200', '300', '400', '500', '600', '700', '800', '900']
    STYLES = ['normal', 'italic']


    def __init__(self, font_name, variants):
        self.font_name = font_name
        self.variants = []

        if self.font_name:
            self.font_name = self.font_name.strip()

        if variants:
            for v in variants:
                self.add_variant(v)


    @property
    def variants_display(self):
        """
        Return list of variants for display purposes.
        """
        return [unicode(v) for v in self.variants]


    @classmethod
    def parse(cls, declaration):
        """
        Parse given declaration string and return the font declaration
        information including the name of the font and supported weights and
        styles.
        Format:
          <font_name> [:<variant-selector>,...]
        Examples:
          Open Sans :300,300i
          Abel :400
        """
        m = re.match(r'^(?P<font_name>.*?)(:(?P<variants>.*?))?$', declaration)
        font_name = m.group('font_name')
        if font_name:
            variants_decl = m.group('variants')
            variants = []
            if variants_decl:
                for v in variants_decl.strip().split(','):
                    m = re.match(r'^(?P<weight>100|200|300|400|500|600|700|800|900)(?P<italic>i)?$', v.strip())
                    if m:
                        variants.append(FontVariant(
                            weight=m.group('weight'),
                            style='italic' if m.group('italic') else 'normal'
                        ))
            else:
                # if no varients have been declared, assume that all possible
                # varients are supported...
                for weight in cls.WEIGHTS:
                    for style in cls.STYLES:
                        variants.append(FontVariant(weight, style))
            return FontDeclaration(font_name, variants)
        else:
            return None


    def join_with(self, declaration):
        """
        Join this font declaration with the given declaration. Given that the
        font names match, the variants are updated, so that this font
        declaration supports all previously supported variants but also all
        variants declared by the given font declaration.
        """
        # cannot join if font name does not match
        if self.font_name != declaration.font_name:
            return

        # join variants
        for v in declaration.variants:
            self.add_variant(v)


    def supports_variant(self, variant):
        """
        Return True, if this font declaration supports the given font variant.
        """
        for v in self.variants:
            if v.equals_to(variant):
                return True


    def supports_variant_by_components(self, weight, style):
        """
        Return True, if this font declaration supports the given
        font weight and style.
        """
        for v in self.variants:
            if v.matches(weight, style):
                return True


    def add_variant(self, variant):
        """
        Add the given variant to the list of supported variants, if it is
        not supported already.
        """
        if not self.supports_variant(variant):
            self.variants.append(variant)