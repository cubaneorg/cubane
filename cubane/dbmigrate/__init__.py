# -*- coding: utf-8 -*-
#
# Database migration will appear in django 1.7. However, the way cubane works
# presents some issues in the long run. Many tables are defined in cubane, yet
# they belong to the actual application, for example settings or child pages.
#
# What we need is a quick and automatic way for migrating database schema.
#
# This solution is not updating complex things, like ManyToMany etc. yet. It is
# only capable of removing deprecated fields and adding new ones as well as
# renaming database tables and creating new tables.
#
# We would estimate that in about 90% of the cases this is good enough to make
# a real difference. In most cases we would add a few fields and/or remove
# some fields. In rare cases we would actually rename tables.
#
# We further assume that we will not encounter silly things like renaming field
# 'a' to 'b' and field 'b' to 'c' in one step, which the automatic migration
# whould fail to detect.
#
from __future__ import unicode_literals
from django.db import connection, models
from cubane.dbmigrate.schema import Schema
from cubane.dbmigrate.ask import ask_confirm, ask_rename_table, ask_rename_field
from cubane.dbmigrate.indexing import get_class_name_with_modules, check_custom_indexing
from cubane.lib.app import get_models
from cubane.lib.fixtures import load_model_fixtures


def get_referenced_tables(schema, model):
    """
    Return a list of models that are references by the given model via
    ForeignKey or ManyToMany or OneToOne relationships
    """
    for field in schema.get_model_fields(model):
        if field.rel:
            yield field.rel.model


def create_or_rename_table(schema, model, interactive, models_visited):
    """
    Create a new table in the database. This could also mean that we've renamed
    the table, so we need to ask the user.
    """
    if not schema.table_exists(model) and model not in models_visited:
        models_visited.append(model)

        # before we create this table, scan the model for any tables that
        # are referenced to and create those first
        for ref_model in get_referenced_tables(schema, model):
            create_or_rename_table(schema, ref_model, interactive, models_visited)

        # ask to rename or create
        i, previous_name = ask_rename_table(model, schema.get_table_names(), interactive)
        if i == 1:
            schema.create_table(model)
        else:
            schema.rename_table(previous_name, model)


def create_or_rename_fields(schema, model, interactive):
    """
    Create new fields in the database. New fields are django fields in the given
    model for which there is no corresponding column in the database. This could
    also mean that we've renamed the field, so we need to ask the user what
    applies.
    """
    columnnames = schema.get_column_names(model)
    for field in schema.get_model_fields(model):
        # if the field does not exist in db schema, it might have been
        # created or renamed. Ask user for advise...
        if field.column not in columnnames:
            i, previous_name = ask_rename_field(model, field, columnnames, interactive)
            if i == 1:
                schema.create_field(model, field)
            else:
                schema.rename_field(model, previous_name, field)


def drop_deprecated_fields(schema, model):
    """
    Drop all deprecated fields for the given django model. A deprecated field
    is a database column that does not match any field in the corresponding
    django model. Fields that are used for full text search (FTS) are ignored.
    """
    for columnname in schema.get_column_names(model):
        # ignore FTS fields
        if columnname.startswith('fts_'):
            continue

        # see if we find a matching field in the django model
        found = False
        for field in schema.get_model_fields(model):
            if field.column == columnname:
                found = True
                break

        # if no django model fields exists for this column,
        # then assume the field is no longer in use and drop it...
        if not found:
            schema.drop_field(model, columnname)


def update_fields(schema, model):
    """
    Update field attributes for each column of the given model/tabel.
    """
    # update individual fields
    for field in schema.get_model_fields(model):
        schema.update_field(model, field)

    # remove deprecated indices
    schema.remove_deprecated_indices(model)


def fts_install_for_model(schema, model):
    """
    Installs FTS for the given django model. A django model is epxected to
    have the FTS class that controls which columns made up additional
    (indexed) columns that are used for full text searching.
    """
    columns = schema.get_fts_columns_for_model(model)

    # remove all fields that start with fts_ but are not in the list (removed)
    schema.fts_remove_fields(model, columns)

    # install fts for all columns
    changed = False
    for column, fields in columns.items():
        if schema.fts_install_for_column(model, column, fields):
            changed = True

    return changed


def get_schema(connection, _verbose):
    """
    Return a representation of the current database schema, which also provides
    methods for manipulating the database schema.
    """
    return Schema(connection, _verbose)


def commit_changes(schema):
    """
    Commit all database schema changes.
    """
    schema.commit()


def auto_migrate(interactive=True, load_fixtures=True, verbose=True):
    """
    Automatically migrate current schema.
    """
    # get database schema manager and start transaction, so that we can confirm
    # all changes at the end...
    schema = get_schema(connection, verbose)
    schema.begin()

    # lock all tables, so that we have exclusive access to the schema and data
    schema.lock(get_models())

    # create/rename tables
    models_visited = []
    for model in get_models():
        create_or_rename_table(schema, model, interactive, models_visited)

    # update tables
    for model in get_models():
        schema.update_table(model)

    # list containing custom indices that will be checked for existence and
    # created if not present.
    from django.contrib.contenttypes.models import ContentType
    custom_index = {
        get_class_name_with_modules(ContentType): [
            'app_label',
            'model',
            [
                'app_label',
                'model'
            ]
        ]
    }

    # apply custom indecies not defined in the model, for example adding
    # index to auth_user's email address...
    indicies = []
    for model in get_models():
        indicies.extend(check_custom_indexing(schema, model, custom_index))
    schema.keep_indicies(indicies)

    # migrate schema for each table
    fts_reindex_models = []
    for model in get_models():
        create_or_rename_fields(schema, model, interactive)
        drop_deprecated_fields(schema, model)
        update_fields(schema, model)
        if fts_install_for_model(schema, model):
            fts_reindex_models.append(model)

    # migrate content types
    schema.migrate_django_content_types()

    # ask user if he realy wants to go ahead with these changes...
    if ask_confirm("Apply changes?", interactive):
        commit_changes(schema)

        # ask for fts reindex if required
        if len(fts_reindex_models) > 0:
            if ask_confirm("One or more models changed regarding full text search. Do you want to re-index now?", interactive):
                for model in fts_reindex_models:
                    schema.fts_reindex_model(model)

        # re-install fixtures
        if load_fixtures:
            load_model_fixtures(connection, verbosity=1 if interactive else 0)
    else:
        schema.rollback()
