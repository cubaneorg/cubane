# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.geocode import geocode
from cubane.lib.geocode import reverse_geocode
from cubane.lib.libjson import decode_json
from mock.mock import patch
from decimal import Decimal


class HttpResponseMock(object):
    def __init__(self, code, data):
        self.code = code
        self.data = data


@CubaneTestCase.complex()
class LibGeoCodeTestCase(CubaneTestCase):
    """
    cubane.lib.geocode.geocode()
    """
    RESPONSE_MOCK = """
        {
           "results" : [
              {
                 "address_components" : [
                    {
                       "long_name" : "4",
                       "short_name" : "4",
                       "types" : [ "street_number" ]
                    },
                    {
                       "long_name" : "Basey Road",
                       "short_name" : "Basey Rd",
                       "types" : [ "route" ]
                    },
                    {
                       "long_name" : "Rackheath",
                       "short_name" : "Rackheath",
                       "types" : [ "locality", "political" ]
                    },
                    {
                       "long_name" : "Norwich",
                       "short_name" : "Norwich",
                       "types" : [ "postal_town" ]
                    },
                    {
                       "long_name" : "Norfolk",
                       "short_name" : "Norfolk",
                       "types" : [ "administrative_area_level_2", "political" ]
                    },
                    {
                       "long_name" : "England",
                       "short_name" : "England",
                       "types" : [ "administrative_area_level_1", "political" ]
                    },
                    {
                       "long_name" : "United Kingdom",
                       "short_name" : "GB",
                       "types" : [ "country", "political" ]
                    },
                    {
                       "long_name" : "NR13 6PZ",
                       "short_name" : "NR13 6PZ",
                       "types" : [ "postal_code" ]
                    }
                 ],
                 "formatted_address" : "4 Basey Rd, Rackheath, Norwich NR13 6PZ, UK",
                 "geometry" : {
                    "location" : {
                       "lat" : 52.6753647,
                       "lng" : 1.3738345
                    },
                    "location_type" : "ROOFTOP",
                    "viewport" : {
                       "northeast" : {
                          "lat" : 52.6767136802915,
                          "lng" : 1.375183480291502
                       },
                       "southwest" : {
                          "lat" : 52.6740157197085,
                          "lng" : 1.372485519708498
                       }
                    }
                 },
                 "place_id" : "ChIJ3xQuRbji2UcR-EWd5UK0gE0",
                 "types" : [ "establishment", "point_of_interest" ]
              }
           ],
           "status" : "OK"
        }
    """


    @patch('cubane.lib.geocode.wget')
    def test_geocode(self, mock_function):
        mock_function.return_value = HttpResponseMock(200, self.RESPONSE_MOCK)
        json = geocode('Oak Tree Business Park, Basey Rd, Rackheath, Norfolk, NR13 6PZ, United Kingdom')

        results = json.get('results')
        self.assertEqual(json.get('status'), 'OK')
        self.assertEqual(len(results), 1)

        geometry = results[0].get('geometry')
        self.assertIsNotNone(geometry)

        location = geometry.get('location')
        self.assertIsNotNone(location)

        lat = location.get('lat')
        lng = location.get('lng')
        self.assertTrue(abs(lat - Decimal('52.6753647')) < Decimal('0.001'), lat)
        self.assertTrue(abs(lng - Decimal('1.3738345')) < Decimal('0.001'), lng)


    def test_geocode_with_invalid_url_should_return_none(self):
        json = geocode(
            'Merchants Hall, Chapelfield, intu Chapelfield, Norwich, Norfolk NR2 1SH',
            url='http://www.innershed.com/does-not-exist/'
        )
        self.assertIsNone(json)


@CubaneTestCase.complex()
class LibGeocodeReverseTestCase(CubaneTestCase):
    """
    cubane.lib.geocode.reverse_geocode()
    """
    RESPONSE_MOCK = """
        {
           "results" : [
              {
                 "address_components" : [
                    {
                       "long_name" : "40-46",
                       "short_name" : "40-46",
                       "types" : [ "street_number" ]
                    },
                    {
                       "long_name" : "Saint Stephens Street",
                       "short_name" : "St Stephens St",
                       "types" : [ "route" ]
                    },
                    {
                       "long_name" : "Norwich",
                       "short_name" : "Norwich",
                       "types" : [ "locality", "political" ]
                    },
                    {
                       "long_name" : "Norwich",
                       "short_name" : "Norwich",
                       "types" : [ "postal_town" ]
                    },
                    {
                       "long_name" : "Norfolk",
                       "short_name" : "Norfolk",
                       "types" : [ "administrative_area_level_2", "political" ]
                    },
                    {
                       "long_name" : "England",
                       "short_name" : "England",
                       "types" : [ "administrative_area_level_1", "political" ]
                    },
                    {
                       "long_name" : "United Kingdom",
                       "short_name" : "GB",
                       "types" : [ "country", "political" ]
                    },
                    {
                       "long_name" : "NR1 3SH",
                       "short_name" : "NR1 3SH",
                       "types" : [ "postal_code" ]
                    }
                 ],
                 "formatted_address" : "40-46 St Stephens St, Norwich NR1 3SH, UK",
                 "geometry" : {
                    "bounds" : {
                       "northeast" : {
                          "lat" : 52.626919,
                          "lng" : 1.2916411
                       },
                       "southwest" : {
                          "lat" : 52.6247509,
                          "lng" : 1.288168
                       }
                    },
                    "location" : {
                       "lat" : 52.6259699,
                       "lng" : 1.2894532
                    },
                    "location_type" : "ROOFTOP",
                    "viewport" : {
                       "northeast" : {
                          "lat" : 52.62718393029149,
                          "lng" : 1.2916411
                       },
                       "southwest" : {
                          "lat" : 52.6244859697085,
                          "lng" : 1.288168
                       }
                    }
                 },
                 "place_id" : "ChIJXStm2uPj2UcRmDuXOx3TzsQ",
                 "types" : [ "premise" ]
              }
           ],
           "status" : "OK"
        }
    """


    @patch('cubane.lib.geocode.wget')
    def test_geocode_reverse(self, mock_function):
        mock_function.return_value = HttpResponseMock(200, self.RESPONSE_MOCK)
        json = reverse_geocode(Decimal('52.6258732'), Decimal('1.2897716'))
        results = json.get('results')
        self.assertEqual(json.get('status'), 'OK')
        self.assertTrue(len(results) > 0, 'no results')

        components = results[0].get('address_components')
        self.assertIsNotNone(components)
        self._assertComponent(components, 'street_number', '40-46')
        self._assertComponent(components, 'route', 'St Stephens St')
        self._assertComponent(components, 'locality', 'Norwich')
        self._assertComponent(components, 'administrative_area_level_2', 'Norfolk')
        self._assertComponent(components, 'country', 'United Kingdom')
        self._assertComponent(components, 'postal_code', 'NR1 3SH')


    def test_geocode_reverse_with_invalid_url_should_return_none(self):
        json = reverse_geocode(
            Decimal('52.6258732'),
            Decimal('1.2897716'),
            url='http://www.innershed.com/does-not-exist/'
        )
        self.assertIsNone(json)


    def _assertComponent(self, components, typ, expected):
        self.assertTrue(
            self._containsComponent(components, typ, expected),
            'Address component \'%s\' with expected value \'%s\' not found is reverse geocoded result or did not match expected value.' % (
                typ,
                expected
            )
        )


    def _containsComponent(self, components, typ, expected):
        for c in components:
            if typ in c.get('types'):
                if expected == c.get('long_name') or expected == c.get('short_name'):
                    return True
        return False
