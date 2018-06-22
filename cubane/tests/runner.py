# coding=UTF-8
from __future__ import unicode_literals
from django.test.runner import DiscoverRunner
from cubane.lib.fixtures import load_model_fixtures


class CubaneTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        # create database
        old_config = super(CubaneTestRunner, self).setup_databases(**kwargs)

        # install initial data
        for connection, _, _ in old_config:
            load_model_fixtures(connection, verbosity=self.verbosity)

        return old_config