# coding=UTF-8
from __future__ import unicode_literals
from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template.defaulttags import token_kwargs
from django.utils.safestring import mark_safe
from cubane.lib.templatetags import value_or_literal, value_or_none
from cubane.lib.url import make_absolute_url
from cubane.lib.currency import format_currency
from cubane.lib.currency import currency_symbol as lib_currency_symbol
from cubane.lib.template import get_template
from cubane.media.templatetags.media_tags import ImageNode
from cubane.media.templatetags.media_tags import render_background_image_attr
from cubane.cms.models import ChildPage, PageBase
from cubane.ishop import get_category_model, get_product_model
from cubane.ishop.apps.shop.basket.forms import AddToBasketForm
from cubane.cms.views import get_cms_settings
register = template.Library()


def get_shop_price(amount, decimal=True, grouping=True):
    """
    Return the given price correctly formatted in the target culture setting
    including delimiters and currency.
    """
    return format_currency(amount, decimal, grouping, lc=settings.SHOP_LOCALE)


################################################################################
# Breadcrumbs
################################################################################
@register.tag()
def shop_breadcrumb(parser, token):
    args = token.split_contents()

    if len(args) not in [1, 2, 3]:
        raise template.TemplateSyntaxError("Invalid syntax. Usage: shop_breadcrumbs [<category>|<product>|<name>] [<sep>]")

    if len(args) >= 2:
        target = args[1]
    else:
        target = None

    if len(args) == 3:
        sep = args[2]
    else:
        sep = "'>'"

    return BreadcrumbNode(target, sep)


class BreadcrumbNode(template.Node):
    def __init__(self, target, sep):
        self._target = target
        self._sep = sep


    def render(self, context):
        # resolve target (none, category or product)
        if self._target == None:
            target = None
        else:
            target = value_or_literal(self._target, context)
            if target == 'None': target = None

        # resolve sep
        request = value_or_none('request', context)
        sep = value_or_literal(self._sep, context)

        # build list of pages based on given target
        items = [('Home', '/')]
        if target == None:
            pass
        elif isinstance(target, str) or isinstance(target, unicode):
            # static page
            items.append((target, make_absolute_url(request.path)))
        elif isinstance(target, get_category_model()):
            # category page
            items.extend([(c.title, c.get_absolute_url()) for c in target.get_path()])
        elif isinstance(target, get_product_model()):
            # product category first...
            if target.primary_category:
                items.extend([(c.title, c.get_absolute_url()) for c in target.primary_category.get_path()])

            # ...then the product itself
            items.append((target.title, target.get_absolute_url()))
        elif isinstance(target, ChildPage):
            # page/child page
            page = target.page
            items.append((page.title, page.get_absolute_url()))
            items.append((target.title, target.get_absolute_url()))
        elif isinstance(target, PageBase):
            # single cms page
            items.append((target.title, target.get_absolute_url()))
        else:
            raise ValueError('Invalid target argument: Must be instance of Category, Product or None.')

        t = get_template('cubane/ishop/elements/breadcrumbs.html')
        d = {
            'items': items,
            'sep': sep,
        }
        with context.push(**d):
            return t.render(context)


################################################################################
# Add to Basket
################################################################################
@register.tag()
def shop_add_to_basket(parser, token):
    args = token.split_contents()

    # product
    product = args[1]

    # optional: basket prefix
    if len(args) > 2:
        basket_prefix_name = args[2]
    else:
        basket_prefix_name = None

    # optional: template
    if len(args) > 3:
        template_name = args[3]
    else:
        template_name = None

    # usage
    if len(args) > 4:
        raise template.TemplateSyntaxError("Invalid syntax. Usage: shop_add_to_basket <product> [<basket_prefix_name>] [<template_name>]")

    return AddToBasketNode(product, basket_prefix_name, template_name, with_varieties=True)


################################################################################
# Quick Add to Basket (without varieties)
################################################################################
@register.tag()
def shop_quick_add_to_basket(parser, token):
    args = token.split_contents()

    # product
    product = args[1]

    # optional: basket prefix
    if len(args) > 2:
        basket_prefix_name = args[2]
    else:
        basket_prefix_name = None

    # optional: template
    if len(args) > 3:
        template_name = args[3]
    else:
        template_name = None

    # usage
    if len(args) > 4:
        raise template.TemplateSyntaxError("Invalid syntax. Usage: shop_quick_add_to_basket <product> [<basket_prefix_name>] [<template_name>]")

    return AddToBasketNode(product, basket_prefix_name, template_name, with_varieties=False)


class AddToBasketNode(template.Node):
    def __init__(self, product, basket_prefix_name, template_name, with_varieties=True):
        self._product = product
        self._basket_prefix_name = basket_prefix_name
        self._template_name = template_name
        self._with_varieties = with_varieties


    def render(self, context):
        request = value_or_none('request', context)
        product = value_or_literal(self._product, context)
        basket_prefix = value_or_literal(self._basket_prefix_name, context)

        template_name = value_or_literal(self._template_name, context)
        if not template_name:
            template_name = 'cubane/ishop/elements/add_to_basket.html'

        # construct return url
        category = product.primary_category
        if category:
            return_url = reverse('shop.category', args=[category.slug, category.pk])
        else:
            return_url = ''

        # render add to basket form
        form = AddToBasketForm(request=request, product=product, prefix=basket_prefix, with_varieties=self._with_varieties)
        t = get_template(template_name)
        d = {
            'product': product,
            'form': form,
            'basket_prefix': basket_prefix,
            'post_url': reverse('shop.basket.add') + '?r=%s' % return_url
        }
        with context.push(**d):
            return t.render(context)


################################################################################
# Render product price
################################################################################
@register.tag()
def shop_product_price(parser, token):
    args = token.split_contents()

    if len(args) != 2:
        raise template.TemplateSyntaxError("Invalid syntax. Usage: shop_product_price <product>|<price>")

    return ProductPriceNode(args[1])


class ProductPriceNode(template.Node):
    def __init__(self, product):
        self._product = product

    def render(self, context):
        request = context.get('request')

        product = value_or_literal(self._product, context)
        if product:
            if isinstance(product, get_product_model()):
                amount = product.price
            else:
                amount = product

            return get_shop_price(amount)
        else:
            return ''


################################################################################
# Render price from value
################################################################################
@register.tag()
def shop_previous_price(parser, token):
    args = token.split_contents()

    if len(args) != 2:
        raise template.TemplateSyntaxError("Invalid syntax. Usage: shop_previous_price <value>")

    return ProductPriceValue(args[1])


class ProductPriceValue(template.Node):
    def __init__(self, product):
        self._product = product

    def render(self, context):
        request = context.get('request')
        currency = context.get('CURRENCY')

        product = value_or_literal(self._product, context)
        if product and isinstance(product, get_product_model()):
            return u'%s%.2f' % (currency, product.previous_price)
        else:
            return u''


################################################################################
# Render arbitary price
################################################################################
@register.tag()
def shop_price(parser, token):
    args = token.split_contents()

    if len(args) != 2:
        raise template.TemplateSyntaxError("Invalid syntax. Usage: shop_price <price>")

    return PriceNode(args[1])


class PriceNode(template.Node):
    def __init__(self, price):
        self._price = price


    def render(self, context):
        request = context.get('request')

        price = value_or_literal(self._price, context)
        if price is not None:
            return get_shop_price(price)
        else:
            return ''


################################################################################
# Render excerpt - using the get_excerpt provided by the ExcerptMixin
################################################################################
@register.tag()
def render_excerpt(parser, token):
    args = token.split_contents()
    if len(args) != 3:
        raise template.TemplateSyntaxError("Invalid syntax. Usage render_excerpt object length")

    length = int(args[2])
    return RenderExcerptNode(args[1], length)

class RenderExcerptNode(template.Node):
    def __init__(self, obj, length):
        self.obj = obj
        self.length = length

    def render(self, context):
        return value_or_literal(self.obj, context).get_excerpt(length=self.length)


################################################################################
# Render content block
################################################################################
@register.tag()
def render_content_block(parser, token):
    args = token.split_contents()

    if len(args) != 2:
        raise template.TemplateSyntaxError("Invalid syntax. Usage render_content_block block_name")

    return RenderContentBlockNode(args[1])

class RenderContentBlockNode(template.Node):
    def __init__(self, block_name):
        self._block_name = block_name

    def render(self, context):
        block = value_or_literal(self._block_name, context)
        return mark_safe(context.get('request').client.content.get(block))


################################################################################
# Default Image Node
################################################################################
@register.tag('image_placeholder')
def image_placeholder(parser, token):
    """
    Renders the missing image placeholder image if configured in settings.
    """
    bits = token.split_contents()

    if len(bits) > 1:
        shape = bits[1]
    else:
        shape = settings.DEFAULT_IMAGE_SHAPE

    return DefaultImageNode(shape)


class DefaultImageNode(ImageNode):
    def __init__(self, shape):
        self.shape = shape


    def render(self, context):
        settings = get_cms_settings()
        if settings and settings.image_placeholder_id:
            shape = value_or_literal(self.shape, context)
            return self.render_image(settings.image_placeholder, shape, noscript=False)
        else:
            return ''


################################################################################
# Default Image Node (background image)
################################################################################
@register.simple_tag(takes_context=True)
def background_image_placeholder(context, shape):
    """
    Renders the missing image placeholder image if configured in settings as
    a background image.
    """
    settings = get_cms_settings()
    if settings and settings.image_placeholder_id:
        return render_background_image_attr(settings.image_placeholder, shape)
    else:
        return ''


@register.simple_tag()
def currency_symbol():
    return lib_currency_symbol(settings.SHOP_LOCALE)
