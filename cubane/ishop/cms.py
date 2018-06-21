# coding=UTF-8
from __future__ import unicode_literals


class ShopPageContextExtensions(object):
    """
    Extension of the CMS Context object that adds shop-specific functionality.
    """
    def get_legacy_url_models(self):
        """
        Return a list of models to test against for legacy url support.
        """
        models = super(ShopPageContextExtensions, self).get_legacy_url_models()

        from cubane.ishop import get_category_model
        from cubane.ishop import get_product_model

        models.append(get_category_model())
        models.append(get_product_model())

        return models