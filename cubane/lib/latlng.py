# coding=UTF-8
from __future__ import unicode_literals
import math
import re


"""
Constants
"""
EARTH_RADIUS_KM      = 6371        # radius of the earth in km (approx.)
KM_IN_MILES          = 0.621371192 # the equivilent of 1 km in miles
KM_IN_NAUTICAL_MILES = 0.539956803 # the equivilent of 1 km in nautical miles


def distance_to(lat1, lng1, lat2, lng2):
    """
    Calculate the distance from the given location (lat1, lng2) to the second
    given location (lat2, lng2). 
    The distance is given as the length of the great circle between the
    the two given locations in kilimeters based on the Haversine Formula.
    """
    if lat1 == None or lng1 == None or lat2 == None or lng2 == None:
        return 0
    else:
        f1 = math.radians(lat1)
        f2 = math.radians(lat2)
        df = math.radians(lat2 - lat1)
        dd = math.radians(lng2 - lng1)
        
        a = math.sin(df/2) * math.sin(df/2) + \
            math.cos(f1)   * math.cos(f2) *   \
            math.sin(dd/2) * math.sin(dd/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return EARTH_RADIUS_KM * c;


def km_to_miles(km):
    """
    Convert given distance from km into miles.
    """
    return km * KM_IN_MILES


def km_to_nautical_miles(km):
    """°
    Convert given distance from km into miles.
    """
    return km * KM_IN_NAUTICAL_MILES


def degree_to_dms(degrees):
    """
    Convert given degrees to degree/minute/second (dms) format.
    """
    d = int(degrees)
    m = int( (degrees - d) * 60.0 )
    s = int( (degrees - d - (m / 60.0)) * 3600.0 )
    return (abs(d), abs(m), abs(s))


def degree_lat_direction(lat):
    """
    Return N/S depending on the given latidude, where 
    lat > 0 is north (N) and lat < 0 is south (S).
    """
    return 'N' if lat > 0 else 'S'


def degree_lng_direction(lng):
    """
    Return E/W depending on the given longitude, wehere 
    lng > 0 is east (E) and lng < 0 is west (W).
    """
    return 'E' if lng > 0 else 'W'


def format_latlng_to_dms_display(lat, lng):
    """
    Return latitude and longitude as a string formated in dms format.
    """
    return '%s %s %s %s' % (
        '%d°%d′%d″' % degree_to_dms(lat),
        degree_lat_direction(lat),
        '%d°%d′%d″' % degree_to_dms(lng),
        degree_lng_direction(lng),
    )


def format_lat_to_dms_display(lat):
    """
    Return latitude as a string formated in dms format.
    """
    return ('%d°%d′%d″' % degree_to_dms(lat)) + ' ' + degree_lat_direction(lat)


def format_lng_to_dms_display(lng):
    """
    Return longitude as a string formated in dms format.
    """
    return ('%d°%d′%d″' % degree_to_dms(lng)) + ' ' + degree_lng_direction(lng)
        

def parse_latlng_component(s):
    """
    Parse latitude or longitude in the format 23.5N, 23.5S, 23.5E or 23.5W.
    """
    if s == None:
        return None
        
    s = s.strip().lower()
    if s == '':
        return None
    
    d = s[-1]
    s = s[:-1]
    if s == '':
        return 0
    
    # ignore degree symbol
    if s[-1] == '°':
        s = s[:-1]
        
    if s == '':
        return 0
        
    v = float(s)
    if d in ['s', 'w']:
        v = -v
        
    return v
    

def parse_latlng(s):
    """
    Parse latitude/longitude given in the format:
    23.5S 46.4W.
    """
    if s != None:
        p = [x for x in re.split(r'[\s,]', s.strip().lower()) if x != '']        
        if len(p) == 2:
            lat = parse_latlng_component(p[0])
            lng = parse_latlng_component(p[1])
            return (lat, lng)
    return (None, None)
        

def parse_distance_components(s):
    """
    Parse distance expressed as two points in latitude/longitude in the format
    23.5S 46.4W to 56.8N 60.6E and return each component as a float.
    """
    if s != None:
        p = s.strip().lower().split('to')
        if len(p) == 2:
            (lat1, lng1) = parse_latlng(p[0])
            (lat2, lng2) = parse_latlng(p[1])
            return (lat1, lng1, lat2, lng2)
    return (None, None, None, None)


def parse_distance(s):
    """
    Parse distance expressed as two points in latitude/longitude in the format
    23.5S 46.4W to 56.8N 60.6E and return the actual (computed) distance 
    in km.
    """
    (lat1, lng1, lat2, lng2) = parse_distance_components(s)
    return distance_to(lat1, lng1, lat2, lng2)
    
    
def install_postgresql():
    """
    Install support for distance calculation for postgresql.
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute(
        """
        --
        -- Add function for performing distance calculation (Haversine Formula)
        --
        CREATE OR REPLACE LANGUAGE plpgsql;
        CREATE OR REPLACE FUNCTION distance_in_km(lat1 float, lng1 float, lat2 float, lng2 float) RETURNS float AS $$
        DECLARE
            R FLOAT  := 6371;
            f1 FLOAT := radians(lat1);
            f2 FLOAT := radians(lat2);
            df FLOAT := radians(lat2 - lat1);
            dd FLOAT := radians(lng2 - lng1);
            a FLOAT  := sin(df/2) * sin(df/2) + cos(f1) * cos(f2) * sin(dd/2) * sin(dd/2);
            c FLOAT  := 2 * atan2(sqrt(a), sqrt(1 - a));
        BEGIN
            RETURN R * c;
        END;
        $$ LANGUAGE plpgsql;"""
    )
    connection._commit()
