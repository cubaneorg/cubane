# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.libjson import decode_json, to_json


class ExtendedJSONSerializer(object):
    """
    Extended version of the default django JSON serializer supporting
    additional complex objects such as Decimal date DateTime types.
    """
    def dumps(self, obj):
        # would use utf-8, but this is what django is using
        # and we want to maintain compatibility with default sessions
        return to_json(obj).encode('latin-1')


    def loads(self, data):
        return decode_json(data.decode('latin-1'))