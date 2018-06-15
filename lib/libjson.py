################################################################################
#
# nb.lib.json
#
# NB JSON Helpers
#
################################################################################
import decimal
import datetime
import json
import inspect
from django.db import models
from django.db.models.query import QuerySet, RawQuerySet
from django.db.models.fields import Field
from django.http import HttpResponse
from cubane.lib.model import get_model_field_names
from itertools import chain


def get_model_attr(obj, attr):
    """
    Get given attribute name from obj. If the name contains dots, the method
    will try to follow the object hierarchy down.
    """
    (name, _, rest) = attr.partition('.')

    if name.endswith('()'):
        name = name[:-2]
    	v = getattr(obj, name)()
    else:
        v = getattr(obj, name)

    if rest != '':
        v = get_model_attr(v, rest)

    return v


def model_to_dict(m, field_names=None):
    """
    Convert Django Model instance to dict based on given field names.
    Attribute names can be re-written if the given field_names is a dict.
    """
    if field_names == None:
        if hasattr(m, 'get_json_fieldnames'):
            field_names = m.get_json_fieldnames()
        else:
            field_names = get_model_field_names(m)

    obj = {}

    # encode fields
    for attr in field_names:
        try:
            v = get_model_attr(m, attr)

            if isinstance(field_names, list):
                obj[attr] = v
            elif isinstance(field_names, dict):
                obj[field_names[attr]] = v
        except:
            pass

    return obj


class number_str(float):
     def __init__(self, o):
         self.o = o

     def __repr__(self):
         return unicode(self.o)


class CustomEncoder(json.JSONEncoder):
    """
    JSON Encoding extension to encode decimal.Decimal data type as simple floats
    and to deal with other data types, such as model instances, datetime, date
    and timedelta.
    """
    def default(self, obj):
        if isinstance(obj, models.Model):
            return model_to_dict(obj)

        if isinstance(obj, decimal.Decimal):
            return number_str(obj)

        if isinstance(obj, datetime.datetime):
            return obj.isoformat(' ').split('.')[0]

        if isinstance(obj, datetime.date):
            return obj.isoformat().split('T')[0]

        if isinstance(obj, datetime.time):
            return obj.isoformat()

        if isinstance(obj, datetime.timedelta):
            return unicode(obj)

        return json.JSONEncoder.default(self, obj)


def to_json(obj, fields=None, compact=True):
    """
    Compact JSON encoding of the given object, which might be a dict, a queryset
    or a raw query set, a list, a model instance or anything else that can be
    encoded into JSON.

    If a model or queryset is provided, only the given list of
    fields are encoded into JSON. If no fields are given, all model fields are
    encoded.

    If compact is true (default), the resulting JSON is encoded using a compact
    format; otherwise a more human-readable formatting is used.
    """
    if isinstance(obj, QuerySet) or isinstance(obj, RawQuerySet):
        # query set
        result = []
        for model_obj in obj:
            result.append(model_to_dict(model_obj, fields))
    elif isinstance(obj, list):
        # list
        if len(obj) > 0 and isinstance(obj[0], models.Model):
            result = []
            for model_obj in obj:
                result.append(model_to_dict(model_obj, fields))
        else:
            result = obj
    elif isinstance(obj, models.Model):
        # single model instance
        result = model_to_dict(obj, fields)
    else:
        # fallback
        result = obj

    if compact:
        return json.dumps(result, separators=(',',':'), cls=CustomEncoder)
    else:
        return json.dumps(result, sort_keys=False, indent=4, cls=CustomEncoder)


def decode_json(s):
    """
    Decode given string (JSON) and return a dictionary that represents the JSON
    string.
    """
    return json.loads(s, parse_float=decimal.Decimal)


def modellist_to_json(obj, fields):
    """
    Encode list of model objects to json.
    """
    result = []
    for model_obj in obj:
        result.append( model_to_dict(model_obj, fields) )

    return json.dumps(result, separators=(',',':'), cls=CustomEncoder)


def modellist_to_json_response(obj, fields=None):
    """
    Encode modellist into JSON and return a JSON response.
    """
    return HttpResponse(
        modellist_to_json(obj, fields),
        content_type='text/javascript'
    )


def to_json_response(obj={}, fields=None, content_type='text/javascript', mimetype=None):
    """
    Encode result into JSON and return a JSON response.
    """
    # still support old argument 'mimetype'.
    if mimetype is not None:
        content_type = mimetype

    return HttpResponse(to_json(obj, fields), content_type=content_type)


def to_json_response_with_messages(request, obj={}, fields=None, content_type='text/javascript', mimetype=None):
    """
    Encode result as JSON and return a JSON response that also contains
    'messages', which encodes all system messages.
    """
    from django.contrib import messages

    obj['messages'] = [{
        'type': m.tags,
        'message': unicode(m),
        'change': m.extra_tags
    } for m in messages.get_messages(request)]

    return to_json_response(obj, fields, content_type, mimetype)


def jsonp_response(obj, callback='jsonp', fields=None):
    """
    Return given content within JSONP format.
    """
    # caller might pass None for callback in case of passing request.GET
    # directly...
    if callback == None: callback = 'jsonp'
    return HttpResponse(''.join([
        callback,
        '(',
        to_json(obj, fields),
        ');'
    ]), content_type='text/javascript')