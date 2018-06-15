# coding=UTF-8
from __future__ import unicode_literals
from cubane.cms.models import Entity
from cubane.directory.models import DirectoryTag
from cubane.directory.models import DirectoryContentBase
from cubane.directory.models import DirectoryContentEntity
from cubane.directory.models import DirectoryEntity
from cubane.directory.models import DirectoryCategory
from cubane.lib.app import get_models


class DirectoryScriptingMixin(object):
    def get_supported_models(self):
        return super(DirectoryScriptingMixin, self).get_supported_models() + [
            DirectoryTag,
            DirectoryContentBase,
            DirectoryContentEntity,
            DirectoryEntity,
            DirectoryCategory
        ]


    def delete_content(self):
        """
        Delete directory content as well when deleting all content
        """
        super(DirectoryScriptingMixin, self).delete_content()
        self.delete_directory_content()



    def delete_entities(self):
        """
        Override: Deleting all CMS entities but NOT directory entities.
        """
        for model in get_models():
            if (issubclass(model, Entity) and not issubclass(model, DirectoryContentEntity)) or issubclass(model, DirectoryEntity):
                for page in model.objects.all():
                    page.delete()


    def delete_directory_content(self):
        """
        Delete all directory content.
        """
        self.delete_directory_tags()
        self.delete_directory_content_pages()
        self.delete_directory_categories()


    def delete_directory_tags(self):
        """
        Delete all directory tags.
        """
        for tag in DirectoryTag.objects.all():
            tag.delete()


    def delete_directory_content_pages(self):
        """
        Delete all directory content pages.
        """
        for model in get_models():
            if issubclass(model, DirectoryContentBase) or issubclass(model, DirectoryContentEntity) or issubclass(model, DirectoryEntity):
                for page in model.objects.all():
                    page.delete()


    def delete_directory_categories(self):
        """
        Delete all directory categories.
        """
        for model in get_models():
            if issubclass(model, DirectoryCategory):
                for c in model.objects.all():
                    c.delete()