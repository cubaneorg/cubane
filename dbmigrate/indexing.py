# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def get_class_name_with_modules(cls):
    """
    Returns the class name with appended modules as a unique identifier.
    """
    return cls.__module__ + '.' + cls.__name__


def check_custom_indexing(schema, model, to_index):
    """
    Installs custom indicies, regardless of what the model dictates.
    """
    class_name = get_class_name_with_modules(model)
    indicies = []
    if class_name in to_index.keys():
        for field_name in to_index[class_name]:
            # get column_name for this index
            column_name = None
            if isinstance(field_name, list) and len(field_name) > 0:
                # unique together index. Check if all fields exists
                fields_set = set(field_name)
                set_diff = fields_set - set([field.name for field in model._meta.fields])
                if len(set_diff) > 0:
                    continue

                # check whether they are unique together (fields_set has at
                # least one element, set xor is 0 only if sets are equal)
                index_is_unique = True in [len(fields_set.symmetric_difference(s2)) == 0 for s2 in model._meta.unique_together]

                # joining the field names set to form the index column name
                # (sort first, so we can define it in arbitrary order)
                column_name = sorted(field_name)
                column_list = ','.join(sorted(field_name))
            elif field_name in [field.name for field in model._meta.fields]:
                # single index, test if field exists
                field = model._meta.get_field(field_name)
                index_is_unique = field.unique
                column_name = field_name
                column_list = None

                # create like index for varchar and text fields with index
                if isinstance(field, schema.TEXTFIELDS):
                    index_name = schema.sql.get_like_index_name(model._meta.db_table, column_name)
                    index_exists = schema.sql.index_exists(index_name)
                    indicies.append(index_name)
                    if not index_exists:
                        schema.sql.create_like_index(model._meta.db_table, column_name)

            if column_name:
                # create regular index
                index_name = schema.sql.get_index_name(model._meta.db_table, column_name, unique=index_is_unique)
                index_exists = schema.sql.index_exists(index_name)
                indicies.append(index_name)
                if not index_exists:
                    # create regular index
                    schema.sql.create_column_index(
                        table=model._meta.db_table,
                        column_name=column_name,
                        unique=index_is_unique,
                        column_list= column_list
                    )

    return indicies