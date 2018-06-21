# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.testapp.models import Location
from cubane.lib.latlng import install_postgresql
from cubane.lib.latlng import distance_to
from cubane.lib.latlng import parse_distance
from cubane.lib.latlng import parse_distance_components
from cubane.lib.latlng import km_to_miles
from cubane.lib.latlng import km_to_nautical_miles
from cubane.lib.latlng import degree_to_dms
from cubane.lib.latlng import degree_lat_direction
from cubane.lib.latlng import degree_lng_direction
from cubane.lib.latlng import format_latlng_to_dms_display
from cubane.lib.latlng import format_lat_to_dms_display
from cubane.lib.latlng import format_lng_to_dms_display
from cubane.lib.latlng import parse_latlng_component
from cubane.lib.latlng import parse_latlng


@CubaneTestCase.complex()
class AAAAAAAATestLatLng(CubaneTestCase):
    """
    Test distance calculation and conversions.
    The name AAAAAAAAAA is set to force this test to be loaded and executed
    first, since it installs distance calculation support for postgresql.
    """
    # Data Source: http://www.wolframalpha.com/
    # We allow a 3% error, since the distance calculation is not
    # as accurate as the one wolfram alpha is using.
    ROUTES = [
        # from/to                              (km)
        ('23.5S 46.4W to 56.8N 60.6E',         13191),
        ('52.63N 1.3E to 51.5N 0.1167W',       158.9),  # norwich -> london
        ('51.5N 0.1167W to 40.66N 73.94W',     5586),   # london -> new york
        ('51.5N 0.1167W to 48.86N, 2.34E',     342),    # london -> paris
        ('19.43°N, 99.14°W to 37.81°S, 145°E', 13563),  # mexico city -> melbourne
    ]
    DISTANCES = [
        # km      # miles   # nautical miles
        (13191,   8197,     7323),
        (158.9,   98.736,   85.799),
        (5586,    3471,     3016),
        (342,     212.5,    184.7),
        (13563,   8428,     7323),
    ]


    @classmethod
    def setUpClass(cls):
        """
        Install custom SQL required for distance calculation (only once).
        """
        super(AAAAAAAATestLatLng, cls).setUpClass()
        install_postgresql()


    def tearDown(self):
        for l in Location.objects.all():
            l.delete()


    def test_distance_python(self):
        """
        Test distance calculation (python).
        """
        for s, km in self.ROUTES:
            d = parse_distance(s)
            error = abs(km - d) / km
            self.assertTrue(error < 0.03, '%f (calc) != %f (expected), error: %f' % (d, km, error))


    def test_distance_python_none_should_return_distance_of_zero(self):
        """
        Test desitance calculation (python) with None values.
        """
        self.assertEqual(distance_to(None, 1.0, 1.0, 1.0), 0)
        self.assertEqual(distance_to(1.0, None, 1.0, 1.0), 0)
        self.assertEqual(distance_to(1.0, 1.0, None, 1.0), 0)
        self.assertEqual(distance_to(1.0, 1.0, 1.0, None), 0)


    def test_distance_sql(self):
        """
        Test distance calculation (sql).
        """
        i = 1
        for s, km in self.ROUTES:
            (lat1, lng1, lat2, lng2) = parse_distance_components(s)
            l = self.create_location(lat1, lng1)
            location = Location.objects.extra(select={'distance': 'distance_in_km(lat, lng, %s, %s)'}, select_params=[lat2, lng2]).get(pk=l.id)
            d = location.distance
            error = abs(km - d) / km
            self.assertTrue(error < 0.03, '%f (calc) != %f (expected), error: %f' % (d, km, error))
            i += 1


    def test_km_to_miles_and_nautical_miles_conversions(self):
        """
        Test distance conversion from km to miles and km to nautical mmiles.
        Allow an error of 3%.
        """
        for km, miles, nmi in self.DISTANCES:
            self.compare_distances(km, km_to_miles(km), miles, 'miles')
            self.compare_distances(km, km_to_nautical_miles(km), nmi, 'nmi')


    def test_degree_to_dms(self):
        """
        Sources:
        http://www.wolframalpha.com/input/?i=23.5S+46.4W
        http://www.wolframalpha.com/input/?i=56.8N+60.6E
        """
        self.assert_dms(23.5, 23, 30, 0)
        self.assert_dms(46.4, 46, 23, 59) # close enought
        self.assert_dms(56.8, 56, 47, 59) # close enought
        self.assert_dms(60.6, 60, 36, 0)


    def test_degree_lat_direction(self):
        self.assertEqual(degree_lat_direction(12.0), 'N')
        self.assertEqual(degree_lat_direction(-12.0), 'S')


    def test_degree_lng_direction(self):
        self.assertEqual(degree_lng_direction(12.0), 'E')
        self.assertEqual(degree_lng_direction(-12.0), 'W')


    def test_format_latlng_to_dms_display(self):
        self.assertEqual(format_latlng_to_dms_display(-23.5, -46.4), '23°30′0″ S 46°23′59″ W')
        self.assertEqual(format_latlng_to_dms_display(56.8, 60.6), '56°47′59″ N 60°36′0″ E')


    def test_format_lat_to_dms_display(self):
        self.assertEqual(format_lat_to_dms_display(-23.5), '23°30′0″ S')
        self.assertEqual(format_lat_to_dms_display(56.8), '56°47′59″ N')


    def test_format_lng_to_dms_display(self):
        self.assertEqual(format_lng_to_dms_display(-46.4), '46°23′59″ W')
        self.assertEqual(format_lng_to_dms_display(60.6), '60°36′0″ E')


    def test_parse_latlng_component_exceptions(self):
        self.assertIsNone(parse_latlng_component(None))
        self.assertIsNone(parse_latlng_component(' '))
        self.assertIsNone(parse_latlng_component(''))
        self.assertEqual(parse_latlng_component('N'), 0)
        self.assertEqual(parse_latlng_component('°N'), 0)


    def test_parse_latlng_exceptions(self):
        (lat, lng) = parse_latlng(None)
        self.assertIsNone(lat)
        self.assertIsNone(lng)


    def test_parse_distance_components_exceptions(self):
        (lat1, lng1, lat2, lng2) = parse_distance_components(None)
        self.assertIsNone(lat1)
        self.assertIsNone(lng1)
        self.assertIsNone(lat2)
        self.assertIsNone(lng2)


    def compare_distances(self, km, actual, expected, unit):
        error = abs(expected - actual) / expected
        self.assertTrue(error < 0.03, '%f km should be %f %s but was %f %s. Error: %f.' % (km, expected, unit, actual, unit, error))


    def create_location(self, lat, lng):
        location = Location()
        location.lat = lat
        location.lng = lng
        location.save()
        return location


    def assert_dms(self, degree, abs_degree, minutes, seconds):
        (d, m, s) = degree_to_dms(degree)
        self.assertEqual(d, abs_degree, 'Expacted %d degrees, but was %d.' % (abs_degree, d))
        self.assertEqual(m, minutes, 'Expacted %d minutes, but was %d.' % (minutes, m))
        self.assertEqual(s, seconds, 'Expacted %d seconds, but was %d.' % (seconds, s))