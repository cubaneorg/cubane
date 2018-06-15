# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, models
from cubane.dbmigrate.schema import Schema
from cubane.dbmigrate.ask import ask_confirm


def get_schema(connection):
    """
    Return a representation of the current database schema, which also provides
    methods for manipulating the database schema.
    """
    return Schema(connection)


class Command(BaseCommand):
    """
    Re-index all tables with full text search indices.
    """
    args = ''
    help = 'Re-index full text search index.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        print 'Re-indexing...Please Wait...'

        schema = get_schema(connection)
        schema.begin()

        schema.fts_reindex()

        if ask_confirm("Apply changes?"):
            schema.commit()
        else:
            schema.rollback()
