# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.fonts.declaration import FontVariant
from cubane.fonts.declaration import FontDeclaration


class FontsFontVariantTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontVariant()
    """
    def test_should_create_font_variant_with_given_weight_and_style(self):
        d = FontVariant('300', 'italic')
        self.assertEqual('300', d.weight)
        self.assertEqual('italic', d.style)


class FontsFontVariantMatchesTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontVariant.matches()
    """
    def test_should_return_true_if_given_weight_and_style_matches(self):
        d = FontVariant('300', 'italic')
        self.assertTrue(d.matches('300', 'italic'))


    def test_should_return_false_if_weight_does_not_match(self):
        d = FontVariant('300', 'italic')
        self.assertFalse(d.matches('200', 'italic'))


    def test_should_return_false_if_style_does_not_match(self):
        d = FontVariant('300', 'italic')
        self.assertFalse(d.matches('300', 'normal'))


class FontsFontVariantEqualsToTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontVariant.equals_to()
    """
    def test_should_return_true_if_given_weight_and_style_matches(self):
        d = FontVariant('300', 'italic')
        self.assertTrue(d.equals_to(FontVariant('300', 'italic')))


    def test_should_return_false_if_weight_does_not_match(self):
        d = FontVariant('300', 'italic')
        self.assertFalse(d.equals_to(FontVariant('200', 'italic')))


    def test_should_return_false_if_style_does_not_match(self):
        d = FontVariant('300', 'italic')
        self.assertFalse(d.equals_to(FontVariant('300', 'normal')))


class FontsFontDeclarationTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontDeclaration()
    """
    def test_should_create_font_declaration_with_given_font_name_and_list_of_variants(self):
        d = FontDeclaration('Abel', [])
        self.assertEqual('Abel', d.font_name)
        self.assertEqual([], d.variants)


class FontsFontDeclarationParseTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontDeclaration.parse()
    """
    def test_should_parse_font_name_with_all_possible_variants_if_no_variant_defined(self):
        d = FontDeclaration.parse('Abel')
        self.assertEqual('Abel', d.font_name)
        self.assertEqual(
            [
                '100',
                '100i',
                '200',
                '200i',
                '300',
                '300i',
                '400',
                '400i',
                '500',
                '500i',
                '600',
                '600i',
                '700',
                '700i',
                '800',
                '800i',
                '900',
                '900i'
            ],
            d.variants_display
        )


    def test_should_parse_font_name_with_variants(self):
        d = FontDeclaration.parse('Open Sans:400,300,300i')
        self.assertEqual('Open Sans', d.font_name)
        self.assertEqual(['400', '300', '300i'], d.variants_display)


    def test_should_ignore_duplicates(self):
        d = FontDeclaration.parse('Open Sans:300,300,400i,400i')
        self.assertEqual('Open Sans', d.font_name)
        self.assertEqual(['300', '400i'], d.variants_display)


    def test_should_accept_white_space(self):
        d = FontDeclaration.parse('  Open Sans  : 300, 300i,   400, 400i')
        self.assertEqual('Open Sans', d.font_name)
        self.assertEqual(['300', '300i', '400', '400i'], d.variants_display)


    def test_should_return_none_if_empty_string(self):
        d = FontDeclaration.parse('')
        self.assertIsNone(d)


class FontsFontDeclarationJoinWithTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontDeclaration.join_with()
    """
    def test_should_join_variants_of_given_declaration(self):
        d = FontDeclaration.parse('Abel:300')
        d.join_with(FontDeclaration.parse('Abel:300i'))
        self.assertEqual('Abel', d.font_name)
        self.assertEqual(['300', '300i'], d.variants_display)


    def test_should_not_yield_duplicates(self):
        d = FontDeclaration.parse('Abel:300')
        d.join_with(FontDeclaration.parse('Abel:300'))
        self.assertEqual('Abel', d.font_name)
        self.assertEqual(['300'], d.variants_display)


    def test_should_only_join_same_font(self):
        d = FontDeclaration.parse('Abel:300')
        d.join_with(FontDeclaration.parse('Open Sans:300i'))
        self.assertEqual('Abel', d.font_name)
        self.assertEqual(['300'], d.variants_display)


class FontsFontDeclarationSupportsVariantTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontDeclaration.supports_variant()
    """
    def test_should_return_true_if_variant_is_supported(self):
        d = FontDeclaration.parse('Abel:300,400i')
        self.assertTrue(d.supports_variant(FontVariant('400', 'italic')))


    def test_should_return_false_if_variant_is_not_supported(self):
        d = FontDeclaration.parse('Abel:300,400i')
        self.assertFalse(d.supports_variant(FontVariant('300', 'italic')))
        self.assertFalse(d.supports_variant(FontVariant('400', 'normal')))


class FontsFontDeclarationSupportsVariantByComponentsTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontDeclaration.supports_variant_by_components()
    """
    def test_should_return_true_if_variant_is_supported(self):
        d = FontDeclaration.parse('Abel:300,400i')
        self.assertTrue(d.supports_variant_by_components('400', 'italic'))


    def test_should_return_false_if_variant_is_not_supported(self):
        d = FontDeclaration.parse('Abel:300,400i')
        self.assertFalse(d.supports_variant_by_components('300', 'italic'))
        self.assertFalse(d.supports_variant_by_components('400', 'normal'))


class FontsFontDeclarationAddVariantTestCase(CubaneTestCase):
    """
    cubane.fonts.declaration.FontDeclaration.add_variant()
    """
    def test_should_add_new_variant(self):
        d = FontDeclaration.parse('Abel:300')
        d.add_variant(FontVariant('300', 'italic'))
        self.assertEqual(['300', '300i'], d.variants_display)


    def test_should_not_add_existing_variant(self):
        d = FontDeclaration.parse('Abel:300')
        d.add_variant(FontVariant('300', 'normal'))
        self.assertEqual(['300'], d.variants_display)