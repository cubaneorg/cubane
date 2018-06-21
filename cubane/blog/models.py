# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db import models
from cubane.cms.models import ChildPage


class BlogPost(ChildPage):
    """
    Blog Post.
    """
    class Meta:
        verbose_name        =  settings.BLOG_VERBOSE_NAME if hasattr(settings, 'BLOG_VERBOSE_NAME') else 'Blog Post'
        verbose_name_plural =  settings.BLOG_VERBOSE_NAME_PLURAL if hasattr(settings, 'BLOG_VERBOSE_NAME_PLURAL') else 'Blog Posts'
        ordering            = ['seq']

    class Listing:
        columns = ['title', '_meta_title', '_meta_description', 'disabled']
        filter_by = ['title', '_meta_title', '_meta_description', 'disabled']
        sortable  = True
        grid_view = True


    @classmethod
    def get_form(self):
        from cubane.blog.forms import BlogPostForm
        return BlogPostForm
