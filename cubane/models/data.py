# coding=UTF-8
from __future__ import unicode_literals
from django.http import HttpResponse
from wsgiref.util import FileWrapper
from django.core.files.temp import NamedTemporaryFile
from django.contrib import messages
from django.db.models.fields import FieldDoesNotExist
from django.utils.safestring import mark_safe
from django.db.models.fields.related import ForeignKey, ManyToManyField, ReverseManyToOneDescriptor
from cubane.lib.model import get_model_related_field, get_listing_option
from cubane.lib.templatetags import get_object_reference_value
from cubane.models import DateTimeBase
import cubane.lib.ucsv as csv
import re


class ImportExportBase(object):
    def __init__(self, model, encoding='utf-8'):
        self.model = model
        self.encoding = encoding


    def get_related(self):
        """
        Return related fields for this model.
        """
        related = get_listing_option(self.model, 'data_related')
        ignore = get_listing_option(self.model, 'data_ignore', [])

        if related:
            manager_name = related.get('manager', '')
            manager = getattr(self.model, manager_name, None)
            if not manager:
                raise ValueError(
                    'Unable to access related manager \'%s\' on model class \'%s\'.' % (
                        manager_name,
                        self.model.__name__
                    )
                )
            if not isinstance(manager, ReverseManyToOneDescriptor):
                raise ValueError(
                    'Related manager \'%s\' on model class \'%s\' does not appear to be a reverse many-to-one descriptor.' % (
                        manager_name,
                        self.model.__name__
                    )
                )
            related_model = manager.rel.related_model
            columns = related.get('columns', [])
            repeat = related.get('repeat', True)

            # extract column names
            column_names = []
            _columns = []
            for column in columns:
                column_name = '%s_%s' % (manager_name, column)

                if column_name in ignore:
                    continue

                try:
                    # test for database field
                    related_model._meta.get_field(column)
                except FieldDoesNotExist:
                    continue

                column_names.append(column_name)
                _columns.append(column)

            # construct related structure with additional information
            related = {
                'manager_name': manager_name,
                'manager': manager,
                'model': related_model,
                'repeat': repeat,
                'columns': _columns,
                'column_names': column_names
            }

        return related


    def get_fieldnames(self):
        """
        Return a list of exportable field names. This generally are all fields
        in the model. However it may be overridden by the model. Also the model
        may define a list of fields that are ignored. In addition, it may
        contain related fields.
        """
        # get list of field names
        pk_name = self.get_data_id_field()
        _fieldnames = get_listing_option(self.model, 'data_columns')
        if _fieldnames is not None:
            fieldnames = _fieldnames
        else:
            fieldnames = [field.name for field in self.model._meta.fields]

            # if we have a custom primary key used to refer to entries,
            # remove the regular primary key
            if pk_name != self.model._meta.pk.name and self.model._meta.pk.name in fieldnames and pk_name in fieldnames:
                fieldnames.remove(self.model._meta.pk.name)

        # id field should always be the first column
        pk_selector = None
        for selector in fieldnames:
            if selector == pk_name or selector.startswith('%s:as' % pk_name):
                pk_selector = selector
                break
        if pk_selector:
            fieldnames.remove(pk_selector)
            fieldnames.insert(0, pk_selector)

        # get list of ignored fields
        ignore = get_listing_option(self.model, 'data_ignore', [])

        # process fields
        names = []
        for fieldname in fieldnames:
            # ignored?
            if fieldname in ignore:
                continue

            # fieldname mapping
            column_name = None
            m = re.match(r'(?P<fieldname>[_\w\d]+)(:as\((?P<columnname>[-\._\w\d\s]+)\))?$', fieldname)
            if m:
                fieldname = m.group('fieldname')
                column_name = m.group('columnname')

            if column_name == None:
                column_name = fieldname

            try:
                # test for database field
                field = self.model._meta.get_field(fieldname)
                names.append((fieldname, column_name))
            except FieldDoesNotExist:
                if self._is_property_or_function(fieldname):
                    # property or function
                    names.append((fieldname, column_name))
                else:
                    # related, e.g. foo__bar
                    field, related, rel_fieldname, rel_model, title = get_model_related_field(self.model, fieldname)
                    if rel_model:
                        names.append((fieldname, column_name))

        return names


    def get_mapped_fieldnames(self):
        mappedfieldnames = get_listing_option(self.model, 'data_map_fields', {})
        names = {}
        for fieldname in mappedfieldnames:
            try:
                # test for database field
                field = self.model._meta.get_field(mappedfieldnames[fieldname])
                names[fieldname] = mappedfieldnames[fieldname]
            except FieldDoesNotExist:
                # there might be property for it
                if self._is_property_or_function(mappedfieldnames[fieldname]):
                    names[fieldname] = mappedfieldnames[fieldname]

        return names


    def get_default_value(self, row, field):
        defaultvalues = get_listing_option(self.model, 'data_default_values', {})

        if field in defaultvalues:
            value = row[defaultvalues[field]]
        else:
            value = None

        return value


    def get_data_id_field(self):
        """
        Return the name of the field that is used to uniquely reference between
        the existing dataset and the exported dataset in order to determine
        update/insert/delete commands.
        """
        _data_id_field = get_listing_option(self.model, 'data_id_field')
        if _data_id_field is not None:
            return _data_id_field
        else:
            return self.model._meta.pk.name


    def _get_test_instance(self):
        """
        Return a new instance of the registered model for the purpose of
        testing for properties and functions (cached).
        """
        if not hasattr(self, '_test_instance'):
            self._test_instance = self.model()
        return self._test_instance


    def _is_property_or_function(self, fieldname):
        """
        Return True, if the model that is registered with this importer/exporter
        has a property or function with the given name.
        """
        instance = self._get_test_instance()
        if hasattr(instance, fieldname):
            # property?
            if isinstance(getattr(instance.__class__, fieldname), property):
                return True

            # callable?
            p = getattr(instance, fieldname)
            return hasattr(p, '__call__')
        return False


class Importer(ImportExportBase):
    def __init__(self, model, form, objects, user, encoding='utf-8'):
        super(Importer, self).__init__(model, encoding)
        self.form = form
        self.objects = objects
        self.user = user


    def import_from_stream(self, request, stream):
        """
        Import model data from given stream, read the data as CSV data, process
        the data through the attached form and import successfully validated
        data.
        """
        # create CSV reader
        reader = csv.reader(
            stream,
            delimiter=b',',
            quotechar=b'"',
            quoting=csv.QUOTE_ALL,
            encoding=self.encoding
        )

        # read data and validate through form
        header = None
        i_success = 0
        i_error = 0
        entity_map = {}
        entity_map_self = []
        deferred = []
        pk_name = self.get_data_id_field()
        ignored_fields = []
        fields = self.get_mapped_fieldnames()
        data_map_fields = get_listing_option(self.model, 'data_map_fields', {})
        fieldnames = [fieldname for fieldname, _ in self.get_fieldnames()]

        for row in reader:
            if not header:
                # read first line to extract header field names that are used to
                # map data to model fields.
                header = [fieldname.lower() for fieldname in row]
            else:
                # valid? If we have an 'id' field, try to get the existing
                # record for it
                d = dict(zip(header, row))
                instance = self.model()
                edit = False
                form_args = {}

                # strip whitespace and ignore empty field names
                for k, v in d.items():
                    if k and (v is None or v == ''):
                        v = self.get_default_value(d, k)
                        d[k] = v
                    if k != '':
                        try:
                            k = k.replace('\n', ' ').replace('.', ' ')
                            if k in fields:
                                d[fields[k]] = v.strip()
                                k = fields[k]
                            d[k] = v.strip()
                        except:
                            pass
                    else:
                        # ignore unnamed columns
                        d.pop(k, None)

                if d.get(pk_name) != '':
                    try:
                        instance = self.objects.get(**{ pk_name: d.get(pk_name) })
                        edit = True
                        form_args = {'instance': instance}
                    except self.model.DoesNotExist:
                        instance = self.model()
                        edit = False
                        setattr(instance, pk_name, d.get(pk_name))

                # accept formatted email addresses
                def sub_email(m):
                    return m.group(1)
                if 'email' in d and d['email'] != '':
                    d['email'] = re.sub('^\w+\s+\w+\s*<(.*?@.*?)>\s*$', sub_email, d['email'])

                # transform data for choice/foreign key fields
                for k, v in d.items():
                    # determine the field
                    field = None
                    try:
                        field = self.model._meta.get_field(k)
                    except FieldDoesNotExist:
                        # remove characters we don't want
                        k = k.replace('\n', ' ').replace('.', ' ')
                        if k in fields:
                            try:
                                field = self.model._meta.get_field(data_map_fields[k])
                                d[fields[k]] = v
                                k = fields[k]
                            except FieldDoesNotExist:
                                field = None

                    if not field:
                        if k not in ignored_fields:
                            # field might be a property or function, ignore if
                            # this is the case
                            if not self._is_property_or_function(k):
                                ignored_fields.append(k)
                                messages.add_message(request, messages.WARNING, "Header field '%s' in the CSV file does not exist in database. Ignoring field." % k)
                        d.pop(k, None)
                    else:
                        # foreign key
                        if isinstance(field, ForeignKey):
                            # build entity map
                            if k not in entity_map:
                                entity_map[k] = dict([(unicode(item), item.pk) for item in field.rel.to.objects.all()])

                            # resolve
                            if v in entity_map[k]:
                                d[k] = entity_map[k][v]

                            # if the related model is 'self', then we need to
                            # maintain it as we are importing new records...
                            if field.rel.to == self.model:
                                if k not in entity_map_self:
                                    entity_map_self.append(k)

                        # many to many
                        elif isinstance(field, ManyToManyField):
                            if not v:
                                continue

                            # mark field as deferred
                            if k not in deferred:
                                deferred.append(k)

                            # split field
                            ref_names = filter(lambda x: x, [x.strip() for x in v.split('|')])
                            ref_instances = []
                            if ref_names:
                                # determine target model
                                target_model = field.rel.to
                                through = not field.rel.through._meta.auto_created

                                # construct mapping
                                if k not in entity_map:
                                    target_objects = target_model.objects.all()
                                    entity_map[k] = dict([(unicode(item), item.pk) for item in target_objects])

                                # determine target list of values
                                for ref_name in ref_names:
                                    if ref_name in entity_map[k]:
                                        ref_instances.append(entity_map[k][ref_name])
                                    else:
                                        messages.add_message(request, messages.ERROR, "Reference value '%s' for field '%s' does not match any record." % (ref_name, k))
                                        i_error += 1

                            # assign new value
                            d[k] = ref_instances

                        # choices
                        elif len(field.choices) > 0:
                            # see if the model implements a converter function
                            converter = getattr(self.model, 'import_%s' % k, None)
                            if callable(converter):
                                d[k] = converter(v)

                # ignore blank lines
                is_blank = True
                for k, v in d.items():
                    if v != '' and v != None:
                        is_blank = False
                        break
                if is_blank:
                    continue

                # construct model form
                f = self.form(d, **form_args)
                if hasattr(f, 'configure'):
                    f.configure(request, instance, edit)

                    # configure() may add a checksum field, which is required
                    if '_cubane_instance_checksum' in f.fields:
                        del f.fields['_cubane_instance_checksum']

                # remove fields that we are not processing
                for fieldname in f.fields.keys():
                    if fieldname not in fieldnames:
                        del f.fields[fieldname]

                # process CSV row through forms
                if not f.is_valid():
                    for fieldname, errormsg in f.errors.items():
                        messages.add_message(request, messages.ERROR,
                            mark_safe("Field <em>%s</em> with the value <em>'%s'</em> did not validate: %s" % (fieldname, d.get(fieldname, ''), errormsg)))
                    i_error += 1
                    continue

                # copy data to model and save entry. Only copy non-deferred
                # fields...
                data = f.cleaned_data
                for k, v in data.items():
                    if k not in deferred:
                        setattr(instance, k, v)

                # set creator/updater
                if isinstance(instance, DateTimeBase):
                    if edit:
                        instance.updated_by = self.user
                    else:
                        instance.created_by = self.user

                # save record
                instance.save()

                # set deferred fields
                if deferred:
                    for k in deferred:
                        v = data.get(k)

                        field = self.model._meta.get_field(k)
                        if isinstance(field, ManyToManyField):
                            if not field.rel.through._meta.auto_created:
                                # through intermediate model
                                target_model = field.rel.through
                                object_field_name = field.m2m_field_name()
                                target_field_name = field.m2m_reverse_field_name()

                                target_model.objects.filter(**{object_field_name: instance}).delete()

                                for i, ref in enumerate(v, start=1):
                                    intermediate_ref = target_model()
                                    setattr(intermediate_ref, object_field_name, instance)
                                    setattr(intermediate_ref, target_field_name, ref)

                                    if hasattr(intermediate_ref, 'seq'):
                                        intermediate_ref.seq = i

                                    intermediate_ref.save()

                                continue

                        setattr(instance, k, v)
                    instance.save()

                # maintain entity map for 'self' references
                try:
                    instance_unicode = unicode(instance)
                    for k in entity_map_self:
                        entity_map[k][instance_unicode] = instance.pk
                except TypeError:
                    pass

                # keep track of count of successfully imported records
                i_success += 1

        return (i_success, i_error)


class Exporter(ImportExportBase):
    def instance_to_value_list(self, obj, fieldnames):
        """
        Return a list of values for the given object that correlates the given
        list of fieldnames.
        """
        has_value_func = hasattr(self.model, 'data_export_value')
        values = []
        for fieldname in fieldnames:
            try:
                field = self.model._meta.get_field(fieldname)
            except:
                field = None

            v = get_object_reference_value(obj, fieldname, '__', '')
            #v = getattr(obj, fieldname, '')

            if field is not None and isinstance(field, ManyToManyField):
                v = '|'.join([unicode(x) for x in v.all()])
            elif callable(v):
                v = v()

            if has_value_func:
                v = self.model.data_export_value(fieldname, v)

            if v is None:
                v = ''

            values.append(v)
        return values


    def export_to_stream(self, objects, f):
        """
        Export given set of objects to given stream
        """
        # create CSV writer
        writer = csv.writer(
            f,
            delimiter=b',',
            quotechar=b'"',
            quoting=csv.QUOTE_ALL,
            encoding=self.encoding
        )

        # generate header fields
        fields = self.get_fieldnames()
        fieldnames = [fieldname for fieldname, _ in fields]
        column_names = [column_name for _, column_name in fields]

        # related fields
        related = self.get_related()
        if related:
            column_names.extend(related.get('column_names'))

        # write header row
        writer.writerow(column_names)

        # export data
        for obj in objects:
            # write record, ignoring related fields
            values = self.instance_to_value_list(obj, fieldnames)

            # get list of related fields
            related_records = []
            if related:
                related_manager_name = related.get('manager_name')
                related_objects = getattr(obj, related_manager_name).all()
                related_fieldnames = related.get('columns')
                for related_object in related_objects:
                    related_values = self.instance_to_value_list(related_object, related_fieldnames)
                    related_records.append(related_values)

            # write inital data line (containing the first related object data)
            if len(related_records) > 0:
                first_row_values = values + related_records.pop(0)
            else:
                first_row_values = values
            writer.writerow(first_row_values)

            # write subsequent data rows, repeating all initial data by default
            if related_records:
                if related.get('repeat'):
                    repeat_values = values
                else:
                    repeat_values = [''] * len(values)
            for related_record in related_records:
                writer.writerow(repeat_values + related_record)


    def export_to_tmp(self, objects):
        """
        Export given set of objects to a temporary file and return a handle
        to that file.
        """
        f = NamedTemporaryFile()
        self.export_to_stream(objects, f)
        f.seek(0)
        return f


    def export_to_response(self, objects, filename, content_type='text/csv'):
        """
        Export given set of objects directly to the html response as a file
        download with given content type and filename.
        """
        f = self.export_to_tmp(objects)
        response = HttpResponse(FileWrapper(f), content_type=content_type)
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response
