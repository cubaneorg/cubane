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
                "1 Wycombe Street, , , , , Darlington, County Durham",
                "2 Wycombe Street, , , , , Darlington, County Durham",
                "3 Wycombe Street, , , , , Darlington, County Durham",
                "4 Wycombe Street, , , , , Darlington, County Durham",
                "5 Wycombe Street, , , , , Darlington, County Durham",
                "6 Wycombe Street, , , , , Darlington, County Durham",
                "7 Wycombe Street, , , , , Darlington, County Durham",
                "8 Wycombe Street, , , , , Darlington, County Durham",
                "9 Wycombe Street, , , , , Darlington, County Durham",
                "10 Wycombe Street, , , , , Darlington, County Durham",
                "11 Wycombe Street, , , , , Darlington, County Durham",
                "12 Wycombe Street, , , , , Darlington, County Durham",
                "14 Wycombe Street, , , , , Darlington, County Durham",
                "15 Wycombe Street, , , , , Darlington, County Durham",
                "16 Wycombe Street, , , , , Darlington, County Durham",
                "17 Wycombe Street, , , , , Darlington, County Durham",
                "18 Wycombe Street, , , , , Darlington, County Durham",
                "19 Wycombe Street, , , , , Darlington, County Durham",
                "20 Wycombe Street, , , , , Darlington, County Durham",
                "21 Wycombe Street, , , , , Darlington, County Durham",
                "22 Wycombe Street, , , , , Darlington, County Durham",
                "23 Wycombe Street, , , , , Darlington, County Durham",
                "24 Wycombe Street, , , , , Darlington, County Durham",
                "25 Wycombe Street, , , , , Darlington, County Durham",
                "26 Wycombe Street, , , , , Darlington, County Durham",
                "27 Wycombe Street, , , , , Darlington, County Durham",
                "28 Wycombe Street, , , , , Darlington, County Durham",
                "29 Wycombe Street, , , , , Darlington, County Durham",
                "30 Wycombe Street, , , , , Darlington, County Durham",
                "31 Wycombe Street, , , , , Darlington, County Durham",
                "32 Wycombe Street, , , , , Darlington, County Durham",
                "33 Wycombe Street, , , , , Darlington, County Durham",
                "34 Wycombe Street, , , , , Darlington, County Durham",
                "35 Wycombe Street, , , , , Darlington, County Durham",
                "37 Wycombe Street, , , , , Darlington, County Durham",
                "39 Wycombe Street, , , , , Darlington, County Durham"
            ]}'''
            return self._normalize_addresses(postcode, json)

        if not postcode:
            return None

        request = requests.get('https://api.getAddress.io/find/%s?sort=True&api-key=%s' % (postcode, settings.POSTCODE_API_KEY), timeout=5)

        if request.status_code == 200:
            return self._normalize_addresses(postcode, request.text)
        else:
            return None


    def _normalize_addresses(self, postcode, json):
        addresses = []
        try:
            decoded_json = decode_json(json)
        except:
            return addresses

        if not 'addresses' in decoded_json:
            return addresses

        for address in decoded_json['addresses']:
            address_chunks = address.split(',')

            address_dict = {}
            address_dict['address_line_1']   = address_chunks[0]
            address_dict['address_line_2']   = address_chunks[1]
            address_dict['address_line_3']   = address_chunks[2]
            address_dict['address_line_4']   = address_chunks[3]
            address_dict['address_locality'] = address_chunks[4]
            address_dict['address_city']     = address_chunks[5]
            address_dict['address_postcode'] = self.clean_postcode(postcode)
            address_dict['address_county']   = address_chunks[6]
            address_dict['address_full']     = ', '.join(x.strip() for x in address_chunks if x.strip())

            addresses.append(address_dict)
        return addresses
