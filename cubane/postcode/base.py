# coding=UTF-8
from __future__ import unicode_literals
import re


class PostcodeLookup(object):
    def get_addresses(self, postcode):
        """
        Return json with an array of the all addresses for the given postcode.
        """
        raise NotImplementedException()


    def clean_postcode(self, postcode):
        """
        Return a cleaned postcode which has been normalised to UK format.
        """
        if postcode:
            postcode = postcode.strip().upper()
            postcode = re.sub(r' ', '', postcode)
            m = re.match(r'^([A-Z]{1,2}[0-9R][0-9A-Z])?([0-9][ABD-HJLNP-UW-Z]{2})$', postcode)
            if m:
                postcode = '%s %s' % (m.group(1), m.group(2))
        return postcode