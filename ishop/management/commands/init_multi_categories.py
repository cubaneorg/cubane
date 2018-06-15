#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from cubane.ishop import get_category_model, get_product_model
from cubane.ishop.models import ProductCategory


class Command(BaseCommand):
    USAGE = 'Usage: init_multi_categories'

    args = ''
    help = 'Creates correct multi-category assignments based on existing single-category assigments.'


    def handle(self, *args, **kwargs):
        print 'Installing multi-category support...Please Wait...'

        i = 0
        for product in get_product_model().objects.select_related('category').all():
            # empty category?
            if not product.category:
                continue

            print product.title

            # create multi-category assignment based on existing category
            ProductCategory.objects.filter(product=product).delete()
            assignment = ProductCategory()
            assignment.product = product
            assignment.category = product.category
            assignment.seq = product.seq
            assignment.save()

            # remove existing relationship
            product.category = None
            product.seq = 0
            product.save()

            i += 1

        print '%d products updated.' % i
        print