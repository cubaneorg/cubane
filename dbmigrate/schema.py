# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from django.apps import apps
from django.db.models.fields import NOT_PROVIDED
from django.core.management.color import no_style
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import RelatedField, ForeignKey
from django.db.utils import IntegrityError
from django.utils import timezone
from cubane.lib.app import get_models
from cubane.lib.model import get_model_field_names
from datetime import datetime
import sys


class Schema(object):
    """
    Provides database-independent access to the database schema.
    """
    TEXTFIELDS = (models.CharField, models.SlugField, models.TextField)


    def __init__(self, connection, _verbose=True):
        self.connection = connection
        self.pending_references = {}
        self._keep_indicies = []
        self._content_types = []

        vendor = connection.vendor

        if vendor == 'postgresql':
            from cubane.dbmigrate.sql import PostgresSql
            self.sql = PostgresSql(connection, _verbose)
        else:
            raise NotImplementedError(
                "Database vendor '%s' is currently not supported." % vendor
            )


    def keep_indicies(self, indicies):
        """
        Keep the given list of indicies, even if they are not defined by a
        model and they would usually be removed.
        """
        self._keep_indicies.extend(indicies)


    def get_column_names(self, model):
        """
        Return a list of the names of all columns in the corresponding database
        table for the given model.
        """
        return self.sql.get_column_names(model._meta.db_table)


    def begin(self):
        """
        Start transaction.
        """
        self.sql.begin()


    def lock(self, models):
        """
        Lock all tables to have exclusive access to the schema and all data.
        """
        for model in models:
            if self.table_exists(model):
                self.sql.lock_table(model._meta.db_table)


    def commit(self):
        """
        Comit previous transaction.
        """
        self.sql.commit()


    def rollback(self):
        """
        Rollback previous transaction.
        """
        self.sql.rollback()


    def get_table_names(self):
        """
        Return a list of all table names that are available.
        """
        return self.sql.get_table_names()


    def table_exists(self, model):
        """
        Return True, if the table with the given name exists.
        """
        return self.sql.table_exists(model._meta.db_table)


    def get_model_fields(self, model):
        """
        Return a list of all fields for the given model. Certain fields are
        excluded for now, for example ManyToMany fields, because we do not
        support them yet.
        """
        for fieldname in get_model_field_names(model):
            try:
                field = model._meta.get_field(fieldname)
            except FieldDoesNotExist:
                continue

            # we do not attempt to sync arbitary relations yet, the only
            # field that we do support is ForeignKey
            if isinstance(field, RelatedField) and not \
               isinstance(field, models.ForeignKey):
                continue

            yield field


    def get_effective_field_default(self, field):
        """
        Returns the effective default value of the given model field.
        """
        with self.connection.schema_editor(atomic=False) as schema_editor:
            return schema_editor.effective_default(field)


    def is_auto_now_field(self, field):
        """
        Return True, if the given field has a default value that should express
        the current timestamp at the time a new record is created, e.g. NOW().
        """
        return (
            (isinstance(field, models.DateTimeField) and getattr(field, 'auto_now_add', False)) or \
            field.default == timezone.now or \
            field.default == datetime.now
        )


    def create_table(self, model):
        """
        Creates the schema for the given model.
        """
        # let django do this bit
        deferred_sql = []
        sql = []
        with self.connection.schema_editor(collect_sql=True, atomic=False) as editor:
            editor.create_model(model)
            sql.extend(editor.collected_sql)
            deferred_sql.extend(editor.deferred_sql)
            editor.deferred_sql = []
            editor.collected_sql = []

        # create table
        for statement in sql:
            self.sql.sql(statement)

        # deferred sql
        for statement in deferred_sql:
            self.sql.sql(statement)

        # create content type
        self._create_content_type(model)


    def rename_table(self, previous_name, model):
        """
        Renames the table with the given previous name to the new table name.
        """
        # rename table itself
        self.sql.rename_table(previous_name, model._meta.db_table)

        # rename indices and constraints for all fields, usually the name of
        # the table is contained in the name of indices and constraints...
        old_table = previous_name
        new_table = model._meta.db_table
        for field in self.get_model_fields(model):
            # foreign key constraint
            if isinstance(field, models.ForeignKey):
                self.sql.rename_foreign_key_constraint(
                    new_table,
                    field.column,
                    field.column,
                    field.rel.to._meta.db_table,
                    field.rel.get_related_field().column,
                    old_table=old_table
                )

            # index
            if field.db_index or field.unique:
                # regular index
                self.sql.rename_index(
                    new_table,
                    '%s_%s' % (old_table, field.column),
                    '%s_%s' % (new_table, field.column)
                )

                # like index for varchar and text fields with index
                if isinstance(field, self.TEXTFIELDS):
                    self.sql.rename_index(
                        new_table,
                        '%s_%s_like' % (old_table, field.column),
                        '%s_%s_like' % (new_table, field.column)
                    )

        # update or create content type
        content_types = self._get_content_type().objects.all()
        is_content_type_updated = False

        for ct in content_types:
            if ct.app_label + ct.model == previous_name:
                self._update_content_type(ct, model)
                is_content_type_updated = True
                break

        if not is_content_type_updated:
            self._create_content_type(model)


    def update_table(self, model):
        """
        Update table properties and check M2M tables
        """
        # create M2M tables that may be missing
        for field in model._meta.local_many_to_many:
            if field.remote_field.through._meta.auto_created:
                # test if intermediate table exists...
                if not self.sql.table_exists(field.remote_field.through._meta.db_table):
                    self.create_table(field.remote_field.through)


    def create_field(self, model, field):
        """
        Creates the given field for the given model in the database schema.
        """
        datatype = self.sql.get_data_type_from_field(field)

        # if the field is not null, we need a default value, unless we do
        # not have any records...
        if (not field.null and \
            field.default == NOT_PROVIDED and \
            not isinstance(field, models.BooleanField) and \
            not self.is_auto_now_field(field) and \
            not self.sql.is_empty_table(model._meta.db_table) \
        ):
            raise ValueError(
                ("Field '%s' of model '%s' must be null or must have a " + \
                "default value, since the table is not empty.") % (
                    field.name,
                    model.__name__
                )
            )

        # create column
        self.sql.create_column(
            model._meta.db_table,
            field.column,
            datatype,
            field.null,
            self.get_effective_field_default(field),
            auto_now=self.is_auto_now_field(field)
        )

        # foreign key
        if isinstance(field, models.ForeignKey):
            self.sql.create_foreign_key_constraint(
                model._meta.db_table,
                field.column,
                field.rel.to._meta.db_table,
                field.rel.get_related_field().column
            )

        # index
        if field.db_index or field.unique:
            # regular index
            self.sql.create_column_index(
                model._meta.db_table,
                field.column,
                field.unique
            )

            # like index for varchar and text fields with index
            if isinstance(field, self.TEXTFIELDS):
                index_type, pattern_ops = self.get_index_info(model, field.column)
                self.sql.create_like_index(model._meta.db_table, field.column, index_type, pattern_ops)


    def get_index_info(self, model, fieldname):
        """
        Return additional information about the index type and operator type
        for like indices.
        """
        if hasattr(model, 'DbIndex'):
            if hasattr(model.DbIndex, fieldname):
                info = getattr(model.DbIndex, fieldname)
                if not isinstance(info, (list, tuple)):
                    info = [info, 'varchar_pattern_ops']
                return info
        return ('btree', 'varchar_pattern_ops')


    def rename_field(self, model, previous_name, field):
        """
        Rename column from given previous name to the new name. This also
        renames indices and constraints.
        """
        self.sql.rename_column(
            model._meta.db_table,
            previous_name,
            field.column
        )

        # foreign key
        if isinstance(field, models.ForeignKey):
            self.sql.rename_foreign_key_constraint(
                model._meta.db_table,
                previous_name,
                field.column,
                field.rel.to._meta.db_table,
                field.rel.get_related_field().column
            )

        # index
        if field.db_index or field.unique:
            # regular index
            self.sql.rename_column_index(
                model._meta.db_table,
                previous_name,
                field.column
            )

            # like index for varchar and text fields with index
            if isinstance(field, self.TEXTFIELDS):
                self.sql.rename_like_index(
                    model._meta.db_table,
                    previous_name,
                    field.column
                )


    def default_added(self, field, default):
        """
        Return True, if the given field contains a default value but
        the given default value from the database is not defined.
        Therefore a default value has been added to the model, which does not
        exists in the database yet.
        """
        return \
            (
                field.default != NOT_PROVIDED and \
                not hasattr(field.default, '__call__') and \
                default == None
            ) or (
                self.is_auto_now_field(field) and \
                default != 'now()'
            )


    def default_removed(self, field, default):
        """
        Return True, if the given field does NOT contain a default value but
        the given default value from the database IS indeed defined.
        Therefore a default value has been removed from the model, which still
        exists in the database.
        """
        return \
            (
                field.default == NOT_PROVIDED and \
                not isinstance(field, models.ForeignKey) and \
                not field.primary_key and \
                default != None
            ) or (
                not self.is_auto_now_field(field) and \
                default == 'now()'
            )


    def update_field(self, model, field):
        """
        Update properties of the given field.
        """
        # default
        default = self.sql.get_column_default(model._meta.db_table, field.column)
        if self.default_added(field, default):
            # default added -> add default to schema
            self.sql.set_column_default(model._meta.db_table, field.column, field.default, self.is_auto_now_field(field))
        elif self.default_removed(field, default):
            # default removed -> drop default from schema
            self.sql.drop_column_default(model._meta.db_table, field.column)

        # nullable?
        nullable = self.sql.column_is_nullable(model._meta.db_table, field.column)
        if field.null and not nullable:
            # null=True added -> drop not null constraint
            self.sql.make_nullable(model._meta.db_table, field.column)
        elif not field.null and nullable:
            # null=False added -> set not null constraint
            if field.default == NOT_PROVIDED:
                # no default, make sure that there is no NULL in the data,
                # otherwise we cannot make the field NOT NULL-able.
                if self.sql.has_null_value(model._meta.db_table, field.column):
                    raise ValueError(
                        ("Field '%s' of model '%s' is suppose to be NOT NULL " +
                         "but contains NULL values. Remove NULL values."
                        ) % (field.name, model.__name__)
                    )
            else:
                # we have a default value. We simply update all data that is
                # currently NULL to the default value
                self.sql.update_null_to_default(model._meta.db_table, field.column, field.default)

            # set not null
            self.sql.make_not_nullable(model._meta.db_table, field.column)

        # index/unique (ignore primary keys for now)
        if not field.primary_key:
            index_name = self.sql.get_index_name(model._meta.db_table, field.column)
            like_index_name = self.sql.get_like_index_name(model._meta.db_table, field.column)
            index_name_key = self.sql.get_index_name(model._meta.db_table, field.column, unique=True)
            index_exists_db = self.sql.index_exists(index_name) or self.sql.index_exists(index_name_key)
            index_exists_model = field.db_index or field.unique
            if index_exists_model and not index_exists_db:
                # index exists in model but not in db -> create index
                self.sql.create_column_index(
                    model._meta.db_table,
                    field.column,
                    field.unique
                )

                # like index for varchar and text fields with index
                if isinstance(field, self.TEXTFIELDS):
                    if not self.sql.index_exists(like_index_name):
                        index_type, pattern_ops = self.get_index_info(model, field.column)
                        self.sql.create_like_index(model._meta.db_table, field.column, index_type, pattern_ops)
            elif not index_exists_model and index_exists_db:
                # index does not exist in model but in db -> drop index
                if self.sql.index_exists(index_name):
                    self.drop_index(model._meta.db_table, index_name)
                if self.sql.index_exists(index_name_key):
                    self.drop_index(model._meta.db_table, index_name_key)

                if isinstance(field, self.TEXTFIELDS):
                    if self.sql.index_exists(like_index_name):
                        self.drop_index(model._meta.db_table, like_index_name)
            elif index_exists_model and index_exists_db:
                # index did not change (exists in model and db), but perhabs
                # we changed unique contraint?
                unique_db = self.sql.is_index_unique(index_name_key)
                if field.unique != unique_db:
                    # unique constraint added or dropped. Re-create index
                    if self.sql.index_exists(index_name):
                        self.drop_index(model._meta.db_table, index_name)
                    if self.sql.index_exists(index_name_key):
                        self.drop_index(model._meta.db_table, index_name_key)

                    self.sql.create_column_index(
                        model._meta.db_table,
                        field.column,
                        field.unique
                    )

            # like index removed from db but required by model?
            if index_exists_model and isinstance(field, self.TEXTFIELDS) and not self.sql.index_exists(like_index_name):
                index_type, pattern_ops = self.get_index_info(model, field.column)
                self.sql.create_like_index(model._meta.db_table, field.column, index_type, pattern_ops)


        # changing varchar length
        if isinstance(field, models.CharField):
            data_type, max_length = self.sql.get_column_datatype(model._meta.db_table, field.column)
            if data_type == 'varchar':
                if field.max_length != max_length:
                    self.sql.update_varchar_length(model._meta.db_table, field.column, field.max_length)
                    self.sql.change_column_data_type(model._meta.db_table, field.column, 'varchar(%d)' % field.max_length)


    def remove_deprecated_indices(self, model):
        """
        Remove any indices that no longer exist.
        """
        # collect all indices that should be present
        table = model._meta.db_table
        indices = set()
        for field in self.get_model_fields(model):
            indices.add(self.sql.get_index_name(table, field.column))

            if isinstance(field, self.TEXTFIELDS):
                indices.add(self.sql.get_like_index_name(table, field.column))

            if field.unique and not field.primary_key:
                indices.add(self.sql.get_index_name(table, field.column, unique=True))

            if field.primary_key:
                indices.add(self.sql.get_index_name(table, 'pkey'))

        # collect FTS indices
        fts_columns = self.get_fts_columns_for_model(model)
        for column, fields in fts_columns.items():
            index_name = 'cubane_fts_%s_%s' % (table, column)
            indices.add(index_name)

        # determine all indices that are actually present and remove those
        # that should not be there...
        actual_indices = self.sql.get_table_indices(table)
        for index in actual_indices:
            if index not in indices and index not in self._keep_indicies:
                self.sql.drop_index(table, index, cascade=True)


    def drop_index(self, table, index_name):
        """
        Drop the given index from the given table, unless the index should
        be kept regardless of the model definition.
        """
        if not index_name in self._keep_indicies:
            self.sql.drop_index(table, index_name)


    def drop_field(self, model, columnname):
        """
        Drop the given column for the given model in the database schema.
        """
        self.sql.drop_column(model._meta.db_table, columnname)


    def get_fts_columns_for_model(self, model):
        """
        Return the column definition for the given model or empty list.
        """
        try:
            return model.FTS.columns
        except:
            return {}


    def fts_install_for_column(self, model, column, fields):
        """
        Installs FTS capabilities for the given model and column combination
        where the full text search index field combines the content of all
        given fields and insert/update triggers maintain the search index.
        """
        # column name needs to start with fts_
        if not column.startswith('fts_'):
            raise ValueError(
                ('By convention, column name \'%s\' that is used for ' + \
                 'full text search must start with \'fts_\'.\n'
                ) % column
            )

        # determine object names
        table = model._meta.db_table
        changed = False

        # create column if it does not exist yet
        if not self.sql.column_exists(table, column):
            changed = True
            self.sql.create_column(
                table,
                column,
                'tsvector'
            )

        # create index if it does not exist yet
        index_name = 'cubane_fts_%s_%s' % (table, column)
        if not self.sql.index_exists(index_name):
            changed = True
            self.sql.create_fts_index(table, index_name, column)

        # create update and insert triggers if they do not exist yet
        fieldnames = '_'.join(fields)
        trigger_name = 'cubane_fts_%s_%s_%s' % (table, column, fieldnames)
        if not self.sql.trigger_exists(table, trigger_name):
            changed = True
            self.sql.create_trigger(
                table,
                trigger_name,
                'before insert or update',
                'each row',
                'tsvector_update_trigger',
                [
                    column,
                    '\'pg_catalog.english\'',
                ] + fields
            )

        return changed


    def fts_remove_fields(self, model, columns):
        """
        Remove all fields that start with fts_ but are no longer defined for the
        given model (removed).
        """
        # determine table name for the given model
        table = model._meta.db_table

        # generate name of columns, indices and triggers for all fts-related
        # fields that the model should have
        index_names = []
        trigger_names = []
        for column, fields in columns.items():
            index_names.append('cubane_fts_%s_%s' % (table, column))
            trigger_names.append('cubane_fts_%s_%s_%s' % (table, column, '_'.join(fields)))

        # remove deprecated triggers
        triggers = self.sql.get_triggers(table)
        for trigger in triggers:
            if trigger.startswith('cubane_fts_') and trigger not in trigger_names:
                self.sql.drop_trigger(table, trigger)

        # remove deprecated indices
        indices = self.sql.get_indices(table)
        for index in indices:
            if index.startswith('cubane_fts_') and index not in index_names:
                self.sql.drop_index(table, index)

        # remove deprecated columns
        db_columns = self.get_column_names(model)
        for db_column in db_columns:
            if db_column.startswith('fts_') and db_column not in columns:
                self.sql.drop_column(table, db_column)


    def fts_reindex_model(self, model):
        """
        Reindex full text search index for the given model.
        """
        table = model._meta.db_table
        columns = self.get_fts_columns_for_model(model)
        if len(columns.items()) > 0:
            # collect columns that we need to update
            db_columns = []
            for column, fields in columns.items():
                for field in fields:
                    if field not in db_columns:
                        db_columns.append(field)
                        break

            # reindex table if we found at least one column to update
            if len(db_columns) > 0:
                self.sql.fts_index(table, db_columns)


    def fts_reindex(self):
        """
        Reindex full text search index for all models with full text search index.
        """
        for model in get_models():
            self.fts_reindex_model(model)


    def migrate_django_content_types(self):
        for content_type in self._content_types:
            content_type.save()


    def _get_content_type(self):
        return apps.get_model('contenttypes', 'ContentType')


    def _is_content_type_collision(self, model):
        content_types = self._get_content_type().objects.all()

        for ct in content_types:
            if ct.app_label == model._meta.app_label and ct.model == model._meta.model_name:
                return True
        return False


    def _create_content_type(self, model):
        if self._is_content_type_collision(model):
            return

        content_type = self._get_content_type()()
        content_type.app_label = model._meta.app_label
        content_type.model = model._meta.model_name
        self._content_types.append(content_type)


    def _update_content_type(self, content_type, model):
        if self._is_content_type_collision(model):
            return

        content_type.app_label = model._meta.app_label
        content_type.model = model._meta.model_name
        self._content_types.append(content_type)
