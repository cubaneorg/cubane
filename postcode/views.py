# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.libjson import to_json_response


def _postcode_provider_by_identifier(identifier):
    if identifier == settings.POSTCODE_GETADDRESS:
        from cubane.postcode.getaddress import GetAddressPostcodeLookup
        return GetAddressPostcodeLookup()

    raise ValueError(
        'Unknown or unsupported postcode provider %s.' % (
            identifier
        )
    )


def postcode_lookup(request):
    postcode = request.GET.get('postcode', None)

    postcode_provider = _postcode_provider_by_identifier(settings.POSTCODE_PROVIDER)

    return to_json_response(
        postcode_provider.get_addresses(postcode)
    )
