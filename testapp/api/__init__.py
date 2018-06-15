# coding=UTF-8
from __future__ import unicode_literals
from cubane.views import ApiView


class TestApiView(ApiView):
    pass


def install_backend(backend):
    backend.register_api(TestApiView())