# coding=UTF-8
from __future__ import unicode_literals


def request_int(d, name, default=None):
    """
    Return the given request variable from POST or GET as an integer or return
    the given default value.
    """
    try:
        return int(d.get(name))
    except:
        return default


def request_bool(d, name, default=False):
    """
    Return the given request variable from POST or GET as a boolean or return
    the given default value.
    """
    try:
        return d.get(name).lower() == 'true'
    except:
        return default


def request_int_list(d, name):
    """
    Return a list of integers.
    """
    if hasattr(d, 'getlist'):
        values = d.getlist(name)
    else:
        values = None
        
    if not values: 
        values = []
    
    result = []
    for value in values:
        try:
            result.append(int(value))
        except:
            pass
            
    return result
