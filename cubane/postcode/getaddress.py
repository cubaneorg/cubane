# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.libjson import decode_json
from cubane.postcode.base import PostcodeLookup
import requests


class GetAddressPostcodeLookup(PostcodeLookup):
    def get_addresses(self, postcode):
        if settings.POSTCODE_DEBUG:
            json = '''{
                "latitude": 54.52716539999999,
                "longitude": -1.5611093,
                "addresses": [
                "1 Street, Address2, Address3, Address4, Locality, Town/City, County",
                "2 Street, Address2, Address3, Address4, Locality, Town/City, County",
                "3 Street, Address2, Address3, Address4, Locality, Town/City, County",
                "4 Street, Address2, Address3, Address4, Locality, Town/City, County",
                "5 Street, Address2, Address3, Address4, Locality, Town/City, County",
                "6 Street, Address2, Address3, Address4, Locality, Town/City, County",
                "7 Street, Address2, Address3, Address4, Locality, Town/City, County",
                "8 Street, Address2, Address3, Address4, Locality, Town/City, County",
                "9 Street, Address2, Address3, Address4, Locality, Town/City, County"
            ]}'''
            return self._normalize_addresses(postcode, json)

        if not postcode:
            return None

        request = requests.get('https://api.getAddress.io/find/%s?sort=True&api-key=%s' % (postcode, settings.POSTCODE_API_KEY), timeout=5)

        if request.status_code == 200:
            return self._normalize_addresses(postcode, request.text)
        else:
            return None


    def _get_address_lines(self, address_chunks):
        # we only support address line 1, 2 and 3 and no locality
        head = []
        tail = None
        for line in address_chunks[:5]:
            if line:
                if tail is None:
                    head.append(line)
                else:
                    tail.append(line)
            elif tail is None:
                tail = []

        while len(head) < 3:
            head.append('')

        if tail:
            i = 2
            for line in reversed(tail):
                if head[i] == '':
                    head[i] = line
                    i -= 1
                if i < 0:
                    break

        return head


    def _normalize_addresses(self, postcode, json):
        addresses = []
        try:
            decoded_json = decode_json(json)
        except:
            return addresses

        if not 'addresses' in decoded_json:
            return addresses

        for address in decoded_json['addresses']:
            address_chunks = [x.strip() for x in address.split(',')]
            lines = self._get_address_lines(address_chunks)

            address_dict = {}
            address_dict['address_line_1']   = lines[0] if len(lines) > 0 else ''
            address_dict['address_line_2']   = lines[1] if len(lines) > 1 else ''
            address_dict['address_line_3']   = lines[2] if len(lines) > 2 else ''
            address_dict['address_city']     = address_chunks[5]
            address_dict['address_county']   = address_chunks[6]
            address_dict['address_postcode'] = self.clean_postcode(postcode)
            address_dict['address_full']     = ', '.join(x.strip() for x in address_chunks if x.strip())
            addresses.append(address_dict)
        return addresses