from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^index/', views.index, name='dummy.index'),
    url(r'^edit/$', views.edit, name='dummy.edit'),
    url(r'^create/', views.create, name='dummy.create'),
    url(r'^preview/$', views.preview, name='dummy.preview'),
]