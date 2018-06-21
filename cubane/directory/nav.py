# coding=UTF-8
from __future__ import unicode_literals
from cubane.directory.models import DirectoryPageAggregator


class DirectoryNavigationExtensions(object):
    def __init__(self, *args, **kwargs):
        """
        Override: Initialise aggregation cache.
        """
        super(DirectoryNavigationExtensions, self).__init__(*args, **kwargs)
        self.agg_cache = {}


    def get_nav_item(self, page, nav_name=None, aggregate=True):
        """
        Override: Inject aggregated pages into navigation item.
        """
        item = super(DirectoryNavigationExtensions, self).get_nav_item(page, nav_name)
        item['aggregated_pages'] = self.get_aggregated_pages_getter(page) if aggregate else []
        return item


    def get_aggregated_pages_getter(self, page):
        """
        Return a getter method for receiving a list of aggregated pages.
        """
        def get_aggregated_pages():
            if isinstance(page, DirectoryPageAggregator):
                pk = page.id
                if pk in self.agg_cache:
                    return self.agg_cache[pk]

                self.agg_cache[pk] = [self.get_nav_item(child, aggregate=False) for child in self.cms.get_aggregated_pages(page.nav_include_tags, page.nav_exclude_tags, page.nav_order_mode, navigation=True)]
                return self.agg_cache[pk]
        return get_aggregated_pages