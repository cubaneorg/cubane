# coding=UTF-8
from __future__ import unicode_literals
from cubane.ishop import get_category_model, get_product_model


class ShopNavigationExtensions(object):
    def get_pages(self):
        """
        Override: Add shop categories as navigate-able items.
        """
        pages = super(ShopNavigationExtensions, self).get_pages()

        # get navigatable shop categories (ishop)
        category_model = get_category_model()
        categories = list(category_model.objects.filter(enabled=True, _nav__isnull=False).select_related('image').order_by('seq'))

        # homepage goes to the beginning, followed by categories and finally
        # followed by all other pages...
        if len(pages) > 0 and self.page_context.page_is_homepage(pages[0]):
            pages = [pages[0]] + categories + pages[1:]
        else:
            pages.extend(categories)

        return pages


    def get_nav_children(self, parent, nav_name=None):
        """
        Override: Allow for show categories in navigation
        """
        category_model = get_category_model()

        if isinstance(parent, category_model):
            children = filter(lambda c: isinstance(c, category_model) and c.parent_id == parent.id, self.pages)
            return [self.get_nav_item(child) for child in children]
        else:
            return super(ShopNavigationExtensions, self).get_nav_children(parent, nav_name)