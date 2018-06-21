# coding=UTF-8
from __future__ import unicode_literals
from cubane.directory.models import DirectoryContentBase
from cubane.directory.models import DirectoryContentEntity
from cubane.directory.models import DirectoryContentAggregator
from cubane.directory.models import DirectoryContentAndAggregator
from cubane.lib.app import get_models


class DirectoryPageContextExtensions(object):
    """
    Extension of the CMS Context object that adds directory-specific functionality.
    """
    def get_template_context(self, preview=False):
        """
        Override: Inject additional template context information for
        directory content.
        """
        context = super(DirectoryPageContextExtensions, self).get_template_context(preview)

        # aggregated content
        current_page = context.get('current_page')
        if current_page and isinstance(current_page, DirectoryContentAggregator):
            context.update({
                'aggregated_pages': self._view.get_aggregated_pages_for_page(current_page)
            })

        return context