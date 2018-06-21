# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from cubane.forms import BaseModelForm
from cubane.media.forms import BrowseImagesField
from cubane.ishop.apps.merchant.forms import BrowseProductField
from cubane.ishop.apps.merchant.categories.forms import BrowseCategoryField
from cubane.cms.forms import BrowsePagesField
from cubane.ishop.models import FeaturedItemBase
from cubane.ishop.featured.views import get_featured_item_model


class FeaturedItemBaseForm(BaseModelForm):
    class Meta:
        model = get_featured_item_model()
        fields = '__all__'
        sections = {
            'title': 'Title and Description',
            'product': 'Featured Content'
        }


    image = BrowseImagesField(required=False)
    product = BrowseProductField(required=False)
    category = BrowseCategoryField(required=False)
    page = BrowsePagesField(required=False)


    def clean(self):
        d = self.cleaned_data
        product = d.get('product')
        category = d.get('category')
        page = d.get('page')

        if len(filter(lambda x: x, [product != None, category != None, page != None])) > 1:
            raise forms.ValidationError(
                'Only a product OR category OR page can be featured; not a combination of those.'
            )

        if not product and not category and not page:
            raise forms.ValidationError(
                'A product OR a category OR a page must be chosen.'
            )

        return d