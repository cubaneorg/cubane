# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from cubane.cms.forms import ChildPageForm
from cubane.blog.models import *


class BlogPostForm(ChildPageForm):
    """
    Form for editing Events.
    """
    class Meta:
        model = BlogPost
        fields = '__all__'
