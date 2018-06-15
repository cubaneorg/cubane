# coding=UTF-8
from __future__ import unicode_literals
from django.conf.urls import url
from cubane.directory.models import DirectoryContentBase
from cubane.lib.app import get_models
from cubane.directory import views

# dispatch directory content
urls = []
for model in get_models():
    if issubclass(model, DirectoryContentBase):
        ctypes = model.get_directory_content_type_slugs()
        for attr_name, backend_section, ct in ctypes:
            p = r'^' + ct + r'/(?P<slug>[-\w\d]+)-(?P<pk>\d+)/$';
            urls.append(url(p, views.content, kwargs={'model': model, 'attr_name': attr_name, 'backend_section': backend_section}, name='cubane.directory.content.%s' % ct))


# url patterns
urlpatterns = urls