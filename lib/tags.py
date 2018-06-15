# coding=UTF-8
from __future__ import unicode_literals


def get_string_tags(tags):
    """
    Return a list of all tags that are assigned to this directory content.
    """
    if tags == None:
        return []
    else:
        return filter(lambda tag: len(tag) > 0, [tag.strip().lower() for tag in tags.split('#')])
    

def set_string_tags(tags):
    """
    Set a list of tag names for this directory content.
    """
    if tags == None or len(tags) == 0:
        return None
    else:
        return ' '.join(['#%s' % tag.strip().lower() for tag in tags])
