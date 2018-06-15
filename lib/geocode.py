# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.http import wget
from cubane.lib.libjson import decode_json


def geocode(address, apikey=settings.CUBANE_GOOGLE_MAP_API_KEY, url='https://maps.googleapis.com/maps/api/geocode/json'):
    """
    Make an API call to google's geocoding API and return the raw response
    as JSON based on the given human-readable address.
    """
    response = wget(url, {
        'address': address,
        'key': apikey
    })

    if response.code == 200:
        return decode_json(response.data)
    else:
        return None


def geocode_location(address, apikey=settings.CUBANE_GOOGLE_MAP_API_KEY, url='https://maps.googleapis.com/maps/api/geocode/json'):
    """
    Make an API call to google's geocoding API and return the latitude, longitude coordinates.
    """
    if address:
        r = geocode(address, apikey, url)
        if r and r.get('status') == 'OK' and len(r.get('results')) > 0:
            location = r.get('results')[0].get('geometry').get('location')
            lat = location.get('lat')
            lng = location.get('lng')
            return lat, lng
    return None, None


def reverse_geocode(lat, lng, apikey=settings.CUBANE_GOOGLE_MAP_API_KEY, url='https://maps.googleapis.com/maps/api/geocode/json'):
    """
    Make an API call to google's geocoding API and return the raw response
    as JSON based on the given latitude/longitude coordinates.
    """
    response = wget(url, {
        'latlng': '%f,%f' % (lat, lng),
        'key': apikey
    })

    if response.code == 200:
        return decode_json(response.data)
    else:
        return None


def reverse_geocode_address(lat, lng, apikey=settings.CUBANE_GOOGLE_MAP_API_KEY, url='https://maps.googleapis.com/maps/api/geocode/json'):
    """
    Make an API call to google's geocoding API and return a pre-formatted response
    containing common address components.
    """
    def find_component(components, typ):
        for c in components:
            if typ in c.get('types'):
                return c.get('long_name')

    if lat and lng:
        r = reverse_geocode(lat, lng, apikey, url)
        if r and r.get('status') == 'OK' and len(r.get('results')) > 0:
            c = r.get('results')[0].get('address_components')

            street_number = find_component(c, 'street_number')
            address1 = find_component(c, 'route')
            address2 = find_component(c, 'locality')
            postcode = find_component(c, 'postal_code')
            city = find_component(c, 'postal_town')
            county = find_component(c, 'administrative_area_level_2')
            country = find_component(c, 'country')

            if address2 == city:
                address2 = None

            return {
                'street_number': street_number,
                'address1': address1,
                'address2': address2,
                'city': city,
                'county': county,
                'country': country,
                'postcode': postcode,
                'formatted_address': r.get('results')[0].get('formatted_address'),
            }

    return None